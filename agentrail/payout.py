"""Participant payment in two parts, integrity review, and the only penalties allowed.

Each round: 80% is paid when the contribution is confirmed (the key-reveal escrow of each week);
20% is held per round in a separate XRPL escrow until a short review ends. The default is to pay:
the held part is released when the review passes or when its time runs out without a decision.
It stays unpaid only when fraud is confirmed by a named person after the participant was told why
and had time to respond. Code finds the signals; the LLM never judges.

Penalties apply only to fraud (fabricated or copied data, duplicate accounts, someone else's
device or data) and to repeatedly missing a round the participant accepted. Declining, pausing
and withdrawing are never inputs: `decision_inputs` is the only thing a payout or sanction
decision reads, and it does not look at them (tests/test_payout.py). Money already paid is never
taken back on the ledger; confirmed fraud only records a repayment claim. Trust levels stay in
the off-ledger `standing` table and never go into a Credential or memo.

A completion bonus is a separate escrow: paid when every requested week is contributed,
returned to the institution if the participant withdraws.
"""
from __future__ import annotations

import hashlib
import json
import os
import time

from .agents import talk
from .engine import canonical
from .ledger.conditions import condition_hex, fulfillment_hex, new_key

XRP = 1_000_000
IMMEDIATE_PCT = 80
MISSED_LIMIT = 2            # accepted rounds missed in a row -> automatic requests paused (not a penalty)
BLOCK_DAYS = 180
DAY = 86400
REASONS = {"copied_series": "the same data series was already contributed by another participant",
           "impossible_value": "values outside what a body or device can produce",
           "quality": "below the data standard announced in the request"}
BOUNDS = {"sleep.daily": ("minutes", 0, 1000), "heart_rate.daily": ("resting_bpm", 25, 220),
          "activity.daily": ("steps", 0, 100_000), "fatigue.survey": ("score_0_10", 0, 10)}


def immediate(price_drops: int) -> int:
    return price_drops * IMMEDIATE_PCT // 100


def held(price_drops: int) -> int:
    return price_drops - immediate(price_drops)


def windows(ledger) -> dict:
    """Seconds of ledger time. Mock: the real policy (7 days, +14 days if fraud is suspected).
    Testnet: the same steps shortened so the release and the refusal show up in one run. The review
    extension is long (10 min) so a named reviewer decides before the default payment of a suspected
    part; the window from FinishAfter to CancelAfter (extension + grace, 11 min) is what a held part
    that was due but not yet released has before the ledger refuses EscrowFinish."""
    if ledger.name == "mock":
        return {"review": 7 * DAY, "extend": 14 * DAY, "grace": 7 * DAY, "respond": 3 * DAY, "bonus": 60 * DAY}
    g = lambda k, d: int(os.environ.get(k, d))
    return {"review": g("HOLDBACK_REVIEW_S", 20), "extend": g("HOLDBACK_EXTEND_S", 600),
            "grace": g("HOLDBACK_GRACE_S", 60), "respond": g("HOLDBACK_RESPOND_S", 5),
            "bonus": g("BONUS_WINDOW_S", 90)}


def _url(w, h):
    return w.ledger.explorer_url(h) if h else None


def _review_keys(w):
    """The review service's own key store (not the study's DB): it holds each held share's fulfillment."""
    ks = w.__dict__.get("review_keystore")
    if ks is None:
        from .security.keystore import LocalKeyStore
        root = os.environ.get("AGENTRAIL_KEYSTORE") or (".keystore" if w.ledger.name == "testnet" else None)
        ks = w.review_keystore = LocalKeyStore("review_service", root)
    return ks


def _send(w, prep):
    """Submit and wait. A refusal or a lost response comes back as a failed status (logged by the
    caller), so one bad escrow never stops the rest of a release run."""
    try:
        w.ledger.submit(prep)
        return w.ledger.wait_validated(prep.tx_hash)
    except Exception as e:
        from types import SimpleNamespace
        return SimpleNamespace(validated=False, success=False, result=f"{type(e).__name__}: {e}")


# ---------------- standing (off ledger) ----------------

def _standing(store, study, pid):
    r = store.one("SELECT * FROM standing WHERE study=? AND person=?", study, pid)
    if r is None:
        with store.tx() as c:
            c.execute("INSERT OR IGNORE INTO standing (study, person) VALUES (?,?)", (study, pid))
        r = store.one("SELECT * FROM standing WHERE study=? AND person=?", study, pid)
    return r


def decision_inputs(store, study: str, pid: str) -> dict:
    """Everything a payout or sanction decision may read. Decline, pause and withdrawal history is
    deliberately absent: stopping must never cost a participant anything."""
    st = _standing(store, study, pid)
    cases = [r["status"] for r in store.q("SELECT status FROM integrity_cases WHERE study=? AND person=?", study, pid)]
    return {"fraud_confirmed": "confirmed" in cases, "fraud_suspected": "suspected" in cases,
            "missed_in_row": st["missed_in_row"], "auto_requests": st["auto_requests"],
            "excluded": bool(st["excluded"]), "block_until": st["block_until"]}


def may_request(w, study: str, pid: str) -> tuple[bool, str]:
    inp = decision_inputs(w.store, study, pid)
    if inp["excluded"] or (inp["block_until"] and w.ledger.now() < inp["block_until"]):
        return False, "excluded after confirmed fraud"
    return True, ""


def auto_paused(w, study: str, pid: str) -> bool:
    return decision_inputs(w.store, study, pid)["auto_requests"] == "paused"


def _audit(w, study, pid, action, code, signals=None, reviewer=None, notified=None):
    with w.store.tx() as c:
        c.execute("INSERT INTO sanctions_audit (study, person, action, reason_code, signals, reviewer_id, "
                  "notified_at, ts) VALUES (?,?,?,?,?,?,?,?)",
                  (study, pid, action, code, json.dumps(signals or []), reviewer, notified, time.time()))


# ---------------- escrows ----------------

def _create(w, kind, study, pid, rid, cells, amount, finish_after, review_until, cancel_after, status,
            order_ids=()):
    e, L = w.engine, w.ledger
    if kind == "bonus" and w.store.one("SELECT id FROM holdbacks WHERE kind='bonus' AND study=? AND person=? "
                                       "AND request_id=?", study, pid, rid):
        return None
    if amount <= 0:
        return None
    if e.available_drops(study) < amount:
        w.store.log(study, "stop", f"{pid}: {kind} escrow not created, the signed budget is used up")
        return None
    owner, dest = e.party(study)["address"], e.party(pid)["address"]
    key = new_key()
    memo = f"{kind}:r{rid}|share:{100 - IMMEDIATE_PCT if kind == 'round' else 0}"
    prep = L.prepare_escrow_create(owner, dest, amount, condition_hex(key), cancel_after, memo,
                                   finish_after=finish_after)
    st = _send(w, prep)
    if not (st.validated and st.success):
        w.store.log(study, "error", f"{pid}: {kind} EscrowCreate failed ({st.result})")
        return None
    with w.store.tx() as c:
        cur = c.execute("INSERT INTO holdbacks (kind, study, person, request_id, cells, amount_drops, owner, "
                        "destination, offer_sequence, condition, finish_after, review_until, cancel_after, status, "
                        "order_ids, create_tx, ts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (kind, study, pid, rid, cells, amount, owner, dest, prep.sequence, condition_hex(key),
                         finish_after, review_until, cancel_after, status, json.dumps(sorted(order_ids)),
                         prep.tx_hash, time.time()))
        hid = cur.lastrowid
        c.execute("UPDATE mandates SET spent_drops=spent_drops+? WHERE buyer_id=?", (amount, study))
    _review_keys(w).get_or_create(f"holdback.{w.ledger.name}.{owner}.{prep.sequence}", lambda: key)
    return hid


def _finish(w, hb) -> bool:
    key = _review_keys(w).get(f"holdback.{w.ledger.name}.{hb['owner']}.{hb['offer_sequence']}")
    L = w.ledger
    prep = L.prepare_escrow_finish(hb["owner"], hb["owner"], hb["offer_sequence"], hb["condition"],
                                   fulfillment_hex(key), f"{hb['kind']}:r{hb['request_id']}|release",
                                   destination=hb["destination"])
    st = _send(w, prep)
    if not (st.validated and st.success):
        w.store.log(hb["study"], "error", f"{hb['person']}: {hb['kind']} EscrowFinish {st.result}")
        return False
    with w.store.tx() as c:
        c.execute("UPDATE holdbacks SET status='released', finish_tx=? WHERE id=?", (prep.tx_hash, hb["id"]))
    return prep.tx_hash


def _cancel(w, hb) -> bool:
    prep = w.ledger.prepare_escrow_cancel(hb["owner"], hb["owner"], hb["offer_sequence"])
    st = _send(w, prep)
    if not (st.validated and st.success):
        w.store.log(hb["study"], "error", f"{hb['person']}: {hb['kind']} EscrowCancel {st.result}")
        return False
    with w.store.tx() as c:
        c.execute("UPDATE holdbacks SET status='returned', cancel_tx=? WHERE id=?", (prep.tx_hash, hb["id"]))
        c.execute("UPDATE mandates SET spent_drops=spent_drops-? WHERE buyer_id=?", (hb["amount_drops"], hb["study"]))
    return prep.tx_hash


# ---------------- per round ----------------

TERMINAL = {"delivered", "withheld", "refunded", "blocked", "failed"}


def settle_round(w, study: str, req: dict, withdrawn: bool = False):
    """When every order of a round has settled: lock the held share of the delivered weeks and review it."""
    pid, rid = req["person"], req["id"]
    if not req["orders"]:
        return None
    st = {o["order_id"]: w.store.one("SELECT status, price_drops FROM orders WHERE id=?", o["order_id"])
          for o in req["orders"]}
    if any(r["status"] not in TERMINAL for r in st.values()):
        return None
    covered = {oid for r in w.store.q("SELECT order_ids FROM holdbacks WHERE kind='round' AND study=? AND person=?",
                                      study, pid) for oid in json.loads(r["order_ids"])}
    delivered = [o for o in req["orders"] if st[o["order_id"]]["status"] == "delivered"
                 and o["order_id"] not in covered]
    if not delivered:
        return None
    cells = sum(len(o["items"]) for o in delivered)
    full = sum(st[o["order_id"]]["price_drops"] for o in delivered) * 100 // IMMEDIATE_PCT
    amount = full - sum(st[o["order_id"]]["price_drops"] for o in delivered)
    win, now = windows(w.ledger), w.ledger.now()
    fa = now + win["review"]
    hid = _create(w, "round", study, pid, rid, cells, amount, fa, fa + win["extend"],
                  fa + win["extend"] + win["grace"], "held", [o["order_id"] for o in delivered])
    if hid is None:
        return None
    with w.store.tx() as c:
        c.execute("UPDATE standing SET missed_in_row=0 WHERE study=? AND person=?", (study, pid))
    h = w.store.one("SELECT * FROM holdbacks WHERE id=?", hid)
    w.store.log(study, "holdback", f"{pid}: {IMMEDIATE_PCT}% paid with each week; {amount / XRP:g} XRP "
                f"({100 - IMMEDIATE_PCT}%) held in escrow until review ends", {"tx_hash": h["create_tx"],
                                                                                "url": _url(w, h["create_tx"])})
    review(w, h, delivered, withdrawn)
    return hid


def _series_hash(rows, item):
    vals = [r.get(item) for r in sorted(rows, key=lambda r: r["day"])]
    return hashlib.sha256(canonical(vals).encode()).hexdigest()


def review(w, hb, delivered, withdrawn=False):
    """Code review of one round: the announced data standard and fraud signals. No LLM."""
    study, pid = hb["study"], hb["person"]
    if withdrawn or not all(o["order_id"] in w.engine.inbox.received for o in delivered):
        verdict = "pass: data destroyed on withdrawal before review, counts as passed"
        with w.store.tx() as c:
            c.execute("UPDATE holdbacks SET review=? WHERE id=?", (verdict, hb["id"]))
        return verdict
    seen = w.__dict__.setdefault("series_seen", {})
    signals = []
    for o in delivered:
        rows = w.engine.open_bundle(study, o["order_id"])
        for item in o["items"]:
            if item in BOUNDS:
                k, lo, hi = BOUNDS[item]
                bad = [r[item][k] for r in rows if r.get(item) and not lo <= r[item][k] <= hi]
                if bad:
                    signals.append({"code": "impossible_value", "item": item, "week": o["week"], "values": bad[:3]})
            if item.endswith(".daily") and item != "blood_pressure.daily":
                h = _series_hash(rows, item)
                other = seen.setdefault((o["week"], item, h), pid)
                if other != pid:
                    signals.append({"code": "copied_series", "item": item, "week": o["week"],
                                    "matches": "another participant's contribution"})
    if not signals:
        with w.store.tx() as c:
            c.execute("UPDATE holdbacks SET review='pass' WHERE id=?", (hb["id"],))
        return "pass"
    now, win = w.ledger.now(), windows(w.ledger)
    with w.store.tx() as c:
        c.execute("UPDATE holdbacks SET status='suspected', review='signals found' WHERE id=?", (hb["id"],))
        cur = c.execute("INSERT INTO integrity_cases (study, person, request_id, signals, status, notified_at, "
                        "respond_by, ts) VALUES (?,?,?,?,?,?,?,?)",
                        (study, pid, hb["request_id"], json.dumps(signals), "suspected", now, now + win["respond"],
                         time.time()))
        case = cur.lastrowid
    codes = sorted({s["code"] for s in signals})
    talk(w.store, study, pid, "integrity_notice", {"case": case, "signals": codes},
         f"We are holding the {100 - IMMEDIATE_PCT}% review part of this round for up to "
         f"{(win['review'] + win['extend']) // DAY or win['review'] + win['extend']}"
         f"{' days' if w.ledger.name == 'mock' else ' s (Testnet)'}: "
         + "; ".join(REASONS[c] for c in codes) + ". You can respond; a staff member reviews the case.")
    _audit(w, study, pid, "hold", ",".join(codes), signals, notified=now)
    return "signals found"


def respond(w, study: str, pid: str, case_id: int, text: str) -> dict:
    c = w.store.one("SELECT * FROM integrity_cases WHERE id=? AND person=?", case_id, pid)
    if c is None:
        return {"ok": False, "message": "no such case"}
    with w.store.tx() as x:
        x.execute("UPDATE integrity_cases SET response=? WHERE id=?", (text[:1000], case_id))
    talk(w.store, pid, study, "integrity_response", {"case": case_id}, f"{pid} responded to case {case_id}.")
    return {"ok": True}


def decide(w, study: str, case_id: int, reviewer_id: str, confirm: bool) -> dict:
    """A named person decides. Confirmation needs the response period to have passed."""
    c = w.store.one("SELECT * FROM integrity_cases WHERE id=?", case_id)
    if c is None or c["status"] != "suspected":
        return {"ok": False, "message": "no open case"}
    if not (reviewer_id or "").strip():
        return {"ok": False, "message": "a named reviewer must decide; code and the LLM cannot"}
    now = w.ledger.now()
    if confirm and now < c["respond_by"]:
        left = c["respond_by"] - now
        return {"ok": False, "message": "the participant can still respond for "
                + (f"{left / DAY:.1f} days" if left >= DAY else f"{left} s")}
    pid = c["person"]
    signals = json.loads(c["signals"])
    if not confirm:
        with w.store.tx() as x:
            x.execute("UPDATE integrity_cases SET status='cleared', reviewer_id=?, decided_at=? WHERE id=?",
                      (reviewer_id, now, case_id))
            x.execute("UPDATE holdbacks SET status='held', review='pass after review' WHERE study=? AND person=? "
                      "AND request_id=? AND kind='round' AND status='suspected'", (study, pid, c["request_id"]))
        _audit(w, study, pid, "clear", "reviewed", signals, reviewer_id, c["notified_at"])
        talk(w.store, study, pid, "integrity_notice", {"case": case_id, "status": "cleared"},
             "Review finished: nothing wrong found. The held part will be paid.")
        return {"ok": True, "status": "cleared"}
    paid = sum(r["price_drops"] for r in w.store.q(
        "SELECT price_drops FROM orders WHERE buyer_id=? AND seller_id=? AND status='delivered'", study, pid))
    # Only a part still frozen can be withheld. One already paid by default (no decision within the
    # extension) stays paid on the ledger; it joins the repayment claim instead of a doomed EscrowCancel.
    late = [h for h in w.store.q("SELECT * FROM holdbacks WHERE study=? AND person=? AND request_id=? "
                                 "AND kind='round' AND status='released'", study, pid, c["request_id"])]
    paid += sum(h["amount_drops"] for h in late)
    with w.store.tx() as x:
        x.execute("UPDATE integrity_cases SET status='confirmed', reviewer_id=?, decided_at=? WHERE id=?",
                  (reviewer_id, now, case_id))
        x.execute("UPDATE holdbacks SET status='withheld', review='fraud confirmed' WHERE study=? AND person=? "
                  "AND request_id=? AND kind='round' AND status='suspected'", (study, pid, c["request_id"]))
        x.execute("UPDATE holdbacks SET status='returning' WHERE study=? AND person=? AND kind='bonus' "
                  "AND status IN ('held','earned')", (study, pid))
        x.execute("INSERT OR IGNORE INTO standing (study, person) VALUES (?,?)", (study, pid))
        x.execute("UPDATE standing SET trust='restricted', excluded=1, block_until=? WHERE study=? AND person=?",
                  (now + BLOCK_DAYS * DAY, study, pid))
        x.execute("INSERT INTO repayment_claims (study, person, case_id, amount_drops, status, ts) "
                  "VALUES (?,?,?,?,?,?)", (study, pid, case_id, paid, "recorded", time.time()))
    _audit(w, study, pid, "exclude", ",".join(sorted({s["code"] for s in signals})), signals, reviewer_id,
           c["notified_at"])
    talk(w.store, study, pid, "integrity_notice", {"case": case_id, "status": "confirmed"},
         f"Reviewer {reviewer_id} confirmed the case. The held part of this round will not be paid, you are "
         f"removed from this study for {BLOCK_DAYS} days, and a claim for {paid / XRP:g} XRP already paid is "
         "recorded. Nothing is taken back on the ledger.")
    w.store.log(study, "repayment_claim", f"{pid}: repayment claim of {paid / XRP:g} XRP recorded off the ledger; "
                "no on-chain clawback of payments")
    return {"ok": True, "status": "confirmed", "repayment_claim_xrp": paid / XRP}


# ---------------- completion bonus ----------------

def offer_bonus(w, study: str, req: dict, amount: int):
    win, now = windows(w.ledger), w.ledger.now()
    hid = _create(w, "bonus", study, req["person"], req["id"], 0, amount, now + win["review"],
                  now + win["bonus"], now + win["bonus"], "held")
    if hid:
        h = w.store.one("SELECT * FROM holdbacks WHERE id=?", hid)
        w.store.log(study, "bonus", f"{req['person']}: completion bonus {amount / XRP:g} XRP locked in its own "
                    "escrow; paid when every requested week is in, returned to the study on withdrawal",
                    {"tx_hash": h["create_tx"], "url": _url(w, h["create_tx"])})
    return hid


def bonus_progress(w, study: str, req: dict):
    hb = w.store.one("SELECT * FROM holdbacks WHERE kind='bonus' AND study=? AND person=? AND request_id=?",
                     study, req["person"], req["id"])
    if hb is None or hb["status"] != "held":
        return
    asked = {(wk, i) for wk, its in req["weeks"].items() for i in its}
    got = {(o["week"], i) for o in req["orders"] for i in o["items"]
           if w.store.one("SELECT status FROM orders WHERE id=?", o["order_id"])["status"] == "delivered"}
    if asked <= got:
        with w.store.tx() as c:
            c.execute("UPDATE holdbacks SET status='earned' WHERE id=?", (hb["id"],))


def on_withdrawal(w, study: str, pid: str):
    """Withdrawal returns the completion bonus to the study. Held shares of reviewed rounds stay the
    participant's and are paid as usual."""
    with w.store.tx() as c:
        c.execute("UPDATE holdbacks SET status='returning' WHERE kind='bonus' AND study=? AND person=? "
                  "AND status IN ('held','earned')", (study, pid))


# ---------------- missed accepted rounds ----------------

def round_missed(w, study: str, pid: str, rid: int, how: str = "accepted, nothing contributed by the deadline"):
    """Only a round the participant accepted counts. Declines, pauses and withdrawals never reach here."""
    _standing(w.store, study, pid)
    with w.store.tx() as c:
        c.execute("UPDATE standing SET missed_in_row=missed_in_row+1 WHERE study=? AND person=?", (study, pid))
    n = decision_inputs(w.store, study, pid)["missed_in_row"]
    w.store.log(study, "missed", f"{pid}: round {rid} {how}; that round is not paid ({n} in a row)")
    if n >= MISSED_LIMIT:
        with w.store.tx() as c:
            c.execute("UPDATE standing SET auto_requests='paused' WHERE study=? AND person=?", (study, pid))
        talk(w.store, study, pid, "notice", {"auto_requests": "paused"},
             f"{n} accepted rounds in a row had no upload, so automatic requests are paused to stop reminders. "
             "One tap resumes them; your priority and future pay do not change.")
    return n


def resume_requests(w, study: str, pid: str):
    _standing(w.store, study, pid)
    with w.store.tx() as c:
        c.execute("UPDATE standing SET auto_requests='on', missed_in_row=0 WHERE study=? AND person=?", (study, pid))


# ---------------- release / return ----------------

def release_due(w) -> dict:
    """Pay what is due, return what must go back. Default is to pay. On the mock ledger the clock
    is moved forward: first to the latest release time, then past the deadlines of what returns."""
    L = w.ledger
    rows = lambda: w.store.q("SELECT * FROM holdbacks WHERE status IN ('held','suspected','earned','withheld','returning')")
    out = {"released": [], "returned": [], "waiting": []}

    def to_release(h, now):
        if h["kind"] == "bonus":
            return h["status"] == "earned" and now >= h["finish_after"]
        if h["status"] == "held":
            return now >= h["finish_after"]
        if h["status"] == "suspected":            # no decision within the extension -> paid by default
            return now >= h["review_until"]
        return False

    if L.name == "mock":
        due = [h["finish_after"] for h in rows() if h["status"] in ("held", "earned")]
        if due:
            L.clock = max(L.clock, max(due))
    now = L.now()
    for h in rows():
        if to_release(h, now):
            if h["status"] == "suspected":
                w.store.log(h["study"], "holdback", f"{h['person']}: no decision within the review extension; "
                            "held part paid by default")
            tx = _finish(w, h)
            if tx:
                out["released"].append({"id": h["id"], "person": h["person"], "kind": h["kind"],
                                        "amount_xrp": h["amount_drops"] / XRP, "tx": tx, "url": _url(w, tx)})
                w.store.log(h["study"], "holdback", f"{h['person']}: {h['kind']} part {h['amount_drops'] / XRP:g} XRP "
                            "released (EscrowFinish)", {"tx_hash": tx, "url": _url(w, tx)})
    back = [h for h in rows() if h["status"] in ("withheld", "returning")]
    open_cases = [h for h in rows() if h["status"] == "suspected"]
    if L.name == "mock" and back and not open_cases:     # never jump past an undecided case's payment
        L.clock = max(L.clock, max(h["cancel_after"] for h in back))
        now = L.now()
    for h in back:
        if now >= h["cancel_after"]:
            tx = _cancel(w, h)
            if tx:
                out["returned"].append({"id": h["id"], "person": h["person"], "kind": h["kind"],
                                        "amount_xrp": h["amount_drops"] / XRP, "tx": tx, "url": _url(w, tx)})
                w.store.log(h["study"], "holdback", f"{h['person']}: {h['kind']} {h['amount_drops'] / XRP:g} XRP "
                            "returned to the study (EscrowCancel)", {"tx_hash": tx, "url": _url(w, tx)})
    out["waiting"] = [{"id": h["id"], "person": h["person"], "kind": h["kind"], "status": h["status"]}
                      for h in rows()]
    return out


def view(w, study: str, pid: str | None = None) -> dict:
    q = "SELECT * FROM holdbacks WHERE study=?" + (" AND person=?" if pid else "") + " ORDER BY id"
    hbs = [{"id": h["id"], "person": h["person"], "kind": h["kind"], "request_id": h["request_id"],
            "amount_xrp": h["amount_drops"] / XRP, "status": h["status"], "review": h["review"],
            "create": {"tx": h["create_tx"], "url": _url(w, h["create_tx"])},
            "release": {"tx": h["finish_tx"], "url": _url(w, h["finish_tx"])} if h["finish_tx"] else None,
            "return": {"tx": h["cancel_tx"], "url": _url(w, h["cancel_tx"])} if h["cancel_tx"] else None}
           for h in w.store.q(q, *([study, pid] if pid else [study]))]
    cq = "SELECT * FROM integrity_cases WHERE study=?" + (" AND person=?" if pid else "") + " ORDER BY id"
    cases = [{"id": c["id"], "person": c["person"], "request_id": c["request_id"],
              "signals": json.loads(c["signals"]), "status": c["status"], "respond_by": c["respond_by"],
              "response": c["response"], "reviewer_id": c["reviewer_id"]}
             for c in w.store.q(cq, *([study, pid] if pid else [study]))]
    out = {"split": {"immediate_pct": IMMEDIATE_PCT, "held_pct": 100 - IMMEDIATE_PCT}, "holdbacks": hbs,
           "cases": cases}
    if pid:
        inp = decision_inputs(w.store, study, pid)
        out["automatic_requests"] = inp["auto_requests"]          # the internal trust level is never shown
    else:
        out["repayment_claims"] = [dict(r) for r in w.store.q("SELECT person, case_id, amount_drops, status "
                                                              "FROM repayment_claims WHERE study=?", study)]
    return out


def card_terms(ledger) -> dict:
    win = windows(ledger)
    unit = "days" if ledger.name == "mock" else "s (Testnet)"
    k = DAY if ledger.name == "mock" else 1
    return {"immediate_pct": IMMEDIATE_PCT, "held_pct": 100 - IMMEDIATE_PCT,
            "review": f"{win['review'] // k} {unit}", "extension_if_fraud_suspected": f"{win['extend'] // k} {unit}",
            "text": (f"{IMMEDIATE_PCT}% of each round is paid when your contribution is confirmed. "
                     f"{100 - IMMEDIATE_PCT}% is held for a short review and then paid, also if you withdraw. "
                     "It is not paid only if fraud (fabricated data, someone else's device or data, several "
                     "accounts) is confirmed by a staff member after you were told why and could respond."),
            "you_can_always_stop": "Declining or withdrawing never affects future study requests, priority or "
                                   "compensation.",
            "trust_on_ledger": "Trust information is never written to the public ledger."}
