"""Both sides of one research study on the same engine and ledger (all synthetic).

Research side: goal -> LLM gap reading checked by code -> co-signed budget -> participation
requests -> sealed contributions -> power. Participant side: request card -> preview of what leaves
the device -> approve / decline -> reward by key-reveal escrow -> data licence (MPT) -> pause or
revoke. The web pages call only these functions.
"""
from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .agents import talk
from .cohort import (HERO, PRIMARY, WEEKS, apply_deliveries, heatmap, infer_needs, person_gaps, power)
from .connectors import HospitalExportSource
from .engine import BudgetExceeded, NeedsHumanApproval, OrderRequest, canonical, sha256_hex
from .ledger.licence import licence_metadata
from .policy import DUO, PURPOSE_DUO, QUASI_IDENTIFIERS, SENSITIVITY, BuyerMandate

XRP = 1_000_000
LAB = "org_sleeplab"
CLINIC = "src_clinic"
CELL_PRICE = XRP // 5
LABELS = {"sleep.daily": "Sleep (wearable)", "activity.daily": "Activity (wearable)",
          "heart_rate.daily": "Resting heart rate (wearable)", "fatigue.survey": "Fatigue survey",
          "blood_pressure.daily": "Blood pressure (clinic visit)", "birth_date": "Exact birth date",
          "zip5": "5-digit postal code", "diagnosis.rare": "Rare diagnosis"}
HOLD_WINDOW_S = 120     # escrow deadline for a round the participant's agent has not released yet


@dataclass
class StudyState:
    goal: str = ""
    needs: object = None
    status: str = "none"                 # none | draft | approved | sent
    approval: dict = field(default_factory=dict)
    requests: dict = field(default_factory=dict)       # id -> participation request
    next_id: int = 1
    power_before: float | None = None
    pairs_before: int | None = None
    licences: dict = field(default_factory=dict)       # pid -> {mpt_id, txs, clawback}
    export_fees: list = field(default_factory=list)
    person_claims: dict = field(default_factory=dict)
    withdrawals: list = field(default_factory=list)
    treasury: str | None = None
    signers: dict = field(default_factory=dict)        # name -> address


def _url(w, h):
    return w.ledger.explorer_url(h) if h else None


def _tx(w, h):
    return {"tx": h, "url": _url(w, h)}


def ensure(w) -> StudyState:
    """Set up the study once: 50 participants, coverage table, lab treasury under multi-signing."""
    if getattr(w, "study", None):
        return w.study
    from .scenario import build_cohort
    if not getattr(w, "cohort_people", None):
        build_cohort(w)
    s = StudyState()
    hm = heatmap(w, w.coverage, LAB)
    s.power_before, s.pairs_before = hm["power"], hm["complete_pairs"]
    s.treasury = w.ledger.new_account("org_sleeplab_treasury")
    s.signers = {"owner": w.ledger.new_keypair("sleeplab_pi"), "compliance": w.ledger.new_keypair("sleeplab_compliance")}
    hashes = w.ledger.setup_multisig(s.treasury, list(s.signers.values()), quorum=2)
    w.store.log(LAB, "multisig", "study treasury: SignerList (principal investigator + compliance officer, "
                "quorum 2), master key disabled", {"tx": hashes, "url": _url(w, hashes[-1])})
    if CLINIC not in {r["id"] for r in w.store.q("SELECT id FROM parties")}:
        w.engine.add_party(CLINIC, "Clinic records export (synthetic source institution)", "organization",
                           w.ledger.new_account(CLINIC))
    w.engine.set_mandate(BuyerMandate(LAB, 0, 3 * XRP, ["sleep_research"]))
    w.study = s
    return s


# ---------------- research side ----------------

def set_goal(w, goal: str, propose=None) -> dict:
    s = ensure(w)
    from .scenario import ETHICS_CREDENTIAL
    w.store.scene = "H"
    s.goal = goal or "Bring the primary analysis back to 80% power before the interim report."
    ethics = w.ledger.has_credential(w.engine.party(LAB)["address"], w.engine.party("org_ethics")["address"],
                                     ETHICS_CREDENTIAL)
    s.needs = infer_needs(w.store, LAB, w.coverage, ["sleep_research"], 40 * XRP, ethics, propose, s.goal)
    s.person_claims = {HERO: person_gaps(w.store, LAB, w.coverage, HERO, propose)}
    s.status = "draft"
    n = s.needs
    w.store.log(LAB, "spec", f"gap reading ({'LLM' if n.source == 'llm' else 'rule baseline'}, checked by code): "
                + ("; ".join(f"{i} weeks {ws}" for i, ws in n.gaps.items()) or "no gaps")
                + f"; {len(n.cells)} participants asked", {"hash": n.proposal_hash, "notes": n.notes})
    return study_view(w)


def approve(w, signers: list[str]) -> dict:
    """Budget for the spec, released from the study treasury only with both co-signatures."""
    from .scenario import top_up
    s = ensure(w)
    if s.status != "draft":
        return {"ok": False, "message": "no draft spec to approve"}
    addrs = [s.signers.get(x) or w.engine.party(LAB)["address"] for x in signers]
    amount = s.needs.budget_drops / XRP
    h = top_up(w, LAB, amount, addrs, treasury=s.treasury)
    if not h:
        last = w.store.one("SELECT message FROM events WHERE actor=? AND kind='refused' ORDER BY id DESC LIMIT 1", LAB)
        import re
        m = re.search(r"\b(te[cfmlr][A-Z_]+)\b", last["message"] if last else "")
        return {"ok": False, "engine_result": m.group(1) if m else "refused", "signers": signers,
                "message": last["message"] if last else "refused by the ledger"}
    s.status = "approved"
    s.approval = {"signers": signers, **_tx(w, h), "amount_xrp": amount}
    return {"ok": True, **study_view(w)}


def _classify(d, items):
    out = {}
    for i in items:
        if i in d.granted:
            out[i] = ("auto", "within your consent")
        elif i in d.round_confirm:
            out[i] = ("approval", "your setting asks you each round")
        elif i in d.pending:
            out[i] = ("approval", d.reason if "purpose" in (d.reason or "") else "outside your consent")
        else:
            out[i] = ("blocked", d.reason or "not allowed")
    return out


def send(w, workers: int = 8) -> dict:
    s = ensure(w)
    if s.status not in ("approved", "sent"):
        return {"ok": False, "message": "spec not approved"}
    w.store.scene = "H"
    talk(w.store, LAB, "participants' agents", "round",
         {"people": len(s.needs.cells), "purpose": s.needs.purpose, "gaps": s.needs.gaps},
         f"Sending participation requests to {len(s.needs.cells)} participants for {s.needs.purpose}.")
    oids = []
    for pid, weeks in sorted(s.needs.cells.items()):
        rid = s.next_id
        s.next_id += 1
        req = {"id": rid, "person": pid, "study": LAB, "purpose": s.needs.purpose, "weeks": weeks,
               "status": "open", "created": time.time(), "orders": []}
        s.requests[rid] = req
        oids += _answer(w, req)
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(w.engine.process, oids))
    for req in s.requests.values():
        _after_contribution(w, req)
    s.status = "sent"
    return study_view(w)


def _answer(w, req, hold_last=False) -> list[int]:
    """The participant's agent answers a request; contributes what consent allows."""
    pa = w.cohort_people[req["person"]]
    items = sorted({i for its in req["weeks"].values() for i in its})
    d = pa.handle_request(LAB, req["purpose"], items, max(req["weeks"]), CELL_PRICE)
    req["classes"] = _classify(d, items)
    if not d.ok:
        req["status"] = "blocked" if not d.pending else "open"
        return []
    granted = {wk: [i for i in its if i in d.granted] for wk, its in req["weeks"].items()}
    granted = {wk: its for wk, its in granted.items() if its and not _done(w, req, wk, its)}
    oids = []
    for i, (wk, its) in enumerate(sorted(granted.items())):
        if any(SENSITIVITY.get(x) == "sensitive" for x in its) or any(
                x in HospitalExportSource.items for x in its):
            _export_fee(w, pa, its)
        rows = pa.vault.extract(its, wk, study=LAB)
        last = hold_last and i == len(granted) - 1
        r = OrderRequest(LAB, pa.id, pa.id, "cohort.fill", f"{pa.id}|w{wk}:{'+'.join(its)}", req["purpose"],
                         sorted(its), len(its) * CELL_PRICE, rows, d, settle="escrow",
                         escrow_window_s=HOLD_WINDOW_S if last else 600)
        try:
            oid = w.engine.place_order(r)
        except (BudgetExceeded, NeedsHumanApproval) as e:
            w.store.log(LAB, "stop", f"{pa.id}: {e}")
            continue
        req["orders"].append({"order_id": oid, "week": wk, "items": its, "hold": last})
        oids.append(oid)
    req["status"] = "contributed" if not d.pending else "partly_open"
    return oids


def _done(w, req, wk, its):
    return any(o["week"] == wk and set(its) <= set(o["items"]) for o in req["orders"])


def _export_fee(w, pa, items):
    """Clinic records come through the clinic's export service, which charges a small fee.
    The participant's agent pays it from the participant's account (no custody by the service)."""
    addr = w.engine.party(pa.id)["address"]
    if not w.ledger.can_sign(addr):
        return
    fee = HospitalExportSource.export_fee_drops
    inv = hashlib.sha256(f"export|{pa.id}|{items}|{time.time()}".encode()).hexdigest().upper()
    prep = w.ledger.prepare_payment(addr, w.engine.party(CLINIC)["address"], fee, inv, "clinic records export")
    w.ledger.submit(prep)
    st = w.ledger.wait_validated(prep.tx_hash)
    w.study.export_fees.append({"person": pa.id, "amount_xrp": fee / XRP, **_tx(w, prep.tx_hash),
                                "ok": bool(st.success)})
    w.store.log(pa.id, "export", f"{pa.id}'s agent paid the clinic {fee / XRP:g} XRP to export visit records",
                {"tx_hash": prep.tx_hash, "url": _url(w, prep.tx_hash)})


def _after_contribution(w, req):
    """First delivered contribution -> the participant's agent issues the study a data licence (MPT)."""
    s = w.study
    pid = req["person"]
    delivered = [o for o in req["orders"] if w.store.one("SELECT status FROM orders WHERE id=?",
                                                          o["order_id"])["status"] == "delivered"]
    apply_deliveries(w, w.coverage, [{"order_id": o["order_id"], "person": pid, "cells": {o["week"]: o["items"]}}
                                     for o in delivered])
    if not delivered or pid in s.licences:
        return
    addr, lab = w.engine.party(pid)["address"], w.engine.party(LAB)["address"]
    if not (w.ledger.can_sign(addr) and hasattr(w.ledger, "issue_licence")):
        return
    c = w.store.one("SELECT doc_hash FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
    try:
        mpt, txs = w.ledger.issue_licence(addr, lab, licence_metadata(LAB, PURPOSE_DUO["sleep_research"], c["doc_hash"]))
    except Exception as e:     # licence is an extra guard; contribution already settled
        w.store.log(pid, "error", f"licence issue failed: {e}")
        return
    s.licences[pid] = {"mpt_id": mpt, "txs": [{"kind": k, **_tx(w, h)} for k, h in zip(
        ["MPTokenIssuanceCreate", "MPTokenAuthorize (study)", "MPTokenAuthorize (participant)", "Payment (1 licence)"],
        txs)], "clawback": None}
    w.cohort_people[pid].policy.licence_check = (
        lambda buyer, mpt=mpt, lab=lab: w.ledger.licence_held(lab, mpt) if buyer == LAB else None)
    w.store.log(pid, "licence", f"{pid}'s agent issued {LAB} a non-transferable data licence (MPT, supply 1, "
                f"clawback on revoke)", {"tx": txs, "url": _url(w, txs[0])})


def close_round(w) -> dict:
    """Participants' agents publish the keys of rounds they held back (end of week)."""
    s = ensure(w)
    done = []
    for req in s.requests.values():
        for o in req["orders"]:
            if o.get("hold"):
                st = w.engine.process(o["order_id"])
                o["hold"] = False
                done.append({"order_id": o["order_id"], "status": st})
        _after_contribution(w, req)
    return {"released": done, **study_view(w)}


def sweep(w) -> dict:
    """Refund escrows whose deadline passed. On the mock ledger the clock is moved forward."""
    if w.ledger.name == "mock":
        due = [r["cancel_after"] for r in w.store.q(
            "SELECT p.cancel_after FROM outbox x JOIN payments p ON p.order_id=x.order_id "
            "WHERE x.kind='cancel' AND x.status='pending'")]
        if due:
            w.ledger.clock = max(w.ledger.clock, max(due))
            w.store.log("engine", "clock", "mock ledger clock moved past the escrow deadline")
    return {"refunded": w.engine.sweep()}


def open_bundle(w, oid: int) -> dict:
    o = w.store.one("SELECT * FROM orders WHERE id=?", oid)
    p = w.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)
    if o is None or o["status"] != "delivered":
        return {"ok": False, "message": "not delivered: the key is not on the ledger"}
    rows = w.engine.open_bundle(LAB, oid)
    return {"ok": True, "rows": rows, "bundle_hash": o["bundle_hash"],
            "hash_matches": sha256_hex(canonical(rows)) == o["bundle_hash"],
            "key_from": _tx(w, p["finish_tx"])}


# ---------------- participant side ----------------

def _requests_for(w, pid):
    return [r for r in ensure(w).requests.values() if r["person"] == pid]


def _badges(w):
    from .scenario import ETHICS_CREDENTIAL
    lab, eth = w.engine.party(LAB)["address"], w.engine.party("org_ethics")["address"]
    out = []
    ev = w.store.one("SELECT data FROM events WHERE kind='credential' AND actor='org_ethics' ORDER BY id LIMIT 1")
    if w.ledger.has_credential(lab, eth, ETHICS_CREDENTIAL):
        txs = json.loads(ev["data"]).get("tx", []) if ev else []
        out.append({"kind": "ethics_review", "label": "Ethics review approved", "issuer": "org_ethics",
                    "on_ledger": True, **_tx(w, txs[-1] if txs else None)})
    kyb = getattr(w, "kyb_tx", None)
    if kyb:
        out.append({"kind": "verified_org", "label": "Verified organization", "on_ledger": True, **_tx(w, kyb)})
    return out


def request_card(w, req) -> dict:
    s = w.study
    items = sorted({i for its in req["weeks"].values() for i in its} | set(req.get("extra_items", [])))
    classes = req.get("classes", {})
    pa = w.cohort_people[req["person"]]
    srcs = pa.vault.by_item
    per_item = []
    for i in items:
        cls, why = classes.get(i, ("approval", ""))
        per_item.append({"item": i, "label": LABELS.get(i, i),
                         "weeks": sorted(wk for wk, its in req["weeks"].items() if i in its),
                         "source": srcs[i].name if i in srcs else None, "class": cls, "reason": why})
    n_cells = sum(len(v) for v in req["weeks"].values())
    return {"id": req["id"], "status": req["status"], "purpose": req["purpose"],
            "institution": {"id": LAB, "name": w.engine.party(LAB)["name"], "badges": _badges(w)},
            "summary": (s.needs.summary if s.needs else "") or "The study is missing some weeks of your record "
                       "and asks you to fill them.",
            "summary_source": s.needs.source if s.needs else "rules",
            "duo": [{"code": c, "label": DUO[c]} for c in PURPOSE_DUO.get(req["purpose"], [])],
            "items": per_item, "reward_xrp": n_cells * CELL_PRICE / XRP,
            "settlement": "escrow: the reward is locked on XRPL and released when your agent publishes the key"}


def participant_view(w, pid: str) -> dict:
    s = ensure(w)
    pa = w.cohort_people[pid]
    reqs = _requests_for(w, pid)
    orders = w.store.q("SELECT o.id, o.scope, o.status, o.price_drops, o.policy_snapshot, p.tx_hash, p.finish_tx, "
                       "p.cancel_tx FROM orders o JOIN payments p ON p.order_id=o.id WHERE o.seller_id=? "
                       "AND o.buyer_id=? ORDER BY o.id", pid, LAB)
    contributions, cell_state = [], {}
    for o in orders:
        slot = json.loads(o["scope"])["slot"].split("|", 1)[1]
        wk, its = int(slot.split(":")[0][1:]), slot.split(":")[1].split("+")
        status = {"paid": "escrowed", "delivering": "escrowed"}.get(o["status"], o["status"])
        if o["cancel_tx"]:
            status = "refunded"
        contributions.append({"order_id": o["id"], "weeks": [wk], "items": its, "amount_xrp": o["price_drops"] / XRP,
                              "status": status, "escrow": _tx(w, o["tx_hash"]), "finish": _tx(w, o["finish_tx"]),
                              "cancel": _tx(w, o["cancel_tx"])})
        for i in its:
            cell_state[(wk, i)] = ("contributed" if status == "delivered" else
                                   "escrowed" if status == "escrowed" else status, o["finish_tx"] or o["tx_hash"])
    requested = {(wk, i) for r in reqs if r["status"] != "declined" for wk, its in r["weeks"].items() for i in its}
    rows = []
    for item in pa.vault.ITEMS:
        cells = []
        for wk in WEEKS:
            st, h = cell_state.get((wk, item), (None, None))
            if st is None:
                held = w.coverage.has(pid, wk, item)
                st = "held" if held else ("requested" if (wk, item) in requested else "missing")
                if item == "blood_pressure.daily" and not held:
                    st = "requested" if (wk, item) in requested else "not_in_protocol"
            cells.append({"week": wk, "state": st, **_tx(w, h)})
        rows.append({"item": item, "label": LABELS[item], "source": pa.vault.by_item[item].name, "cells": cells})
    c = w.store.one("SELECT * FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
    hist = w.store.q("SELECT version, status, doc_hash, ts FROM consent_history WHERE person_id=? AND buyer_id=? "
                     "ORDER BY id", pid, LAB)
    lic = s.licences.get(pid)
    if lic:
        lic = {**lic, "held_by_study": w.ledger.licence_held(w.engine.party(LAB)["address"], lic["mpt_id"])}
    return {
        "person": {"id": pid, "address": w.engine.party(pid)["address"], "study_pseudonym": pa.vault.pseudonym(LAB)},
        "requests": [request_card(w, r) for r in reqs],
        "timeline": {"weeks": WEEKS, "rows": rows},
        "gaps": s.person_claims.get(pid, []),
        "contributions": contributions,
        "licence": lic,
        "consent": {"version": c["version"], "status": c["status"], "automation": c["automation"],
                    "items": json.loads(c["items"]), "duo": json.loads(c["doc"]).get("data_use", []),
                    "doc_hash": c["doc_hash"], "history": [dict(h) for h in hist]} if c else None,
        "withdrawals": [x for x in s.withdrawals if x["person"] == pid],
        "export_fees": [x for x in s.export_fees if x["person"] == pid],
    }


def preview(w, pid: str, rid: int) -> dict:
    req = ensure(w).requests[rid]
    pa = w.cohort_people[pid]
    card = request_card(w, req)
    ok = [i["item"] for i in card["items"] if i["class"] != "blocked"]
    rows = [r for wk, its in sorted(req["weeks"].items())
            for r in pa.vault.extract([i for i in its if i in ok], wk, study=LAB)]
    return {"pseudonym": pa.vault.pseudonym(LAB), "dates": "shifted by a per-study offset only your agent knows",
            "rows": rows[:14], "row_count": len(rows),
            "withheld_items": [i["item"] for i in card["items"] if i["class"] == "blocked"],
            "not_included": [i for i in pa.vault.ITEMS if i not in ok],
            "sealed_for": LAB, "operator_can_open": False}


def participant_approve(w, pid: str, rid: int, items: list[str], hold_last: bool = True) -> dict:
    req = ensure(w).requests[rid]
    pa = w.cohort_people[pid]
    for r in pa.open_requests():
        if r["buyer_id"] == LAB:
            pa.approve(r["id"], [i for i in items if i in json.loads(r["items"])])
    asked = {wk: [i for i in its if i in items] for wk, its in req["weeks"].items()}
    req["weeks_approved"] = {wk: its for wk, its in asked.items() if its}
    sub = {**req, "weeks": req["weeks_approved"]}
    oids = _answer(w, sub, hold_last=hold_last)
    req["orders"], req["classes"] = sub["orders"], {**req.get("classes", {}), **sub.get("classes", {})}
    for oid in oids:
        o = next(x for x in req["orders"] if x["order_id"] == oid)
        w.engine.process(oid, until="finish" if o["hold"] else None)
    _after_contribution(w, req)
    req["status"] = "contributed"
    return participant_view(w, pid)


def participant_decline(w, pid: str, rid: int) -> dict:
    """Withdrawal 1: decline this round. Nothing leaves the device, nothing reaches the ledger."""
    req = ensure(w).requests[rid]
    pa = w.cohort_people[pid]
    with w.store.tx() as c:
        c.execute("UPDATE approval_requests SET status='decided', decided_items='[]' WHERE person_id=? AND "
                  "buyer_id=? AND status='open'", (pid, LAB))
    req["status"] = "declined"
    w.study.withdrawals.append({"person": pid, "kind": "decline_round", "request": rid, "ts": time.time(),
                                "ledger": "nothing sent, nothing paid"})
    talk(w.store, f"person {pid}", pid, "decline", {"request": rid},
         f"Decline this request. Nothing is sent.")
    return participant_view(w, pid)


def participant_pause(w, pid: str, resume: bool = False) -> dict:
    """Withdrawal 2: stop future supply. Past contributions and rewards stay."""
    pa = w.cohort_people[pid]
    (pa.resume if resume else pa.pause)(LAB)
    if not resume:
        w.study.withdrawals.append({"person": pid, "kind": "pause", "ts": time.time(),
                                    "ledger": "no new escrows; completed rewards and licence stay"})
    return participant_view(w, pid)


def participant_revoke(w, pid: str) -> dict:
    """Withdrawal 3: revoke data access consent. Licence clawed back, held rounds withheld and
    refunded to the study after the deadline, consent history kept. Delivered rounds cannot be recalled."""
    s = ensure(w)
    pa = w.cohort_people[pid]
    out = {"clawback": None, "withheld": [], "refunds": []}
    lic = s.licences.get(pid)
    if lic and not lic["clawback"]:
        h = w.ledger.clawback_licence(w.engine.party(pid)["address"], w.engine.party(LAB)["address"], lic["mpt_id"])
        lic["clawback"] = _tx(w, h)
        out["clawback"] = lic["clawback"]
        w.store.log(pid, "clawback", f"{pid}'s agent clawed back the study's data licence (MPT)",
                    {"tx_hash": h, "url": _url(w, h)})
    pa.revoke(LAB)
    for req in _requests_for(w, pid):
        for o in req["orders"]:
            if o.get("hold"):
                w.engine.process(o["order_id"])     # finish re-checks consent and licence -> withheld
                o["hold"] = False
                out["withheld"].append(o["order_id"])
    out["refunds"] = [{"order_id": oid, **_tx(w, w.store.one("SELECT cancel_tx FROM payments WHERE order_id=?",
                                                                oid)["cancel_tx"])} for oid in sweep(w)["refunded"]]
    out["kept"] = "consent history (every version hashed), rewards already paid, rounds already delivered"
    s.withdrawals.append({"person": pid, "kind": "revoke", "ts": time.time(), **out})
    return {**out, **participant_view(w, pid)}


# ---------------- research console view ----------------

def study_view(w) -> dict:
    s = ensure(w)
    m = w.store.one("SELECT * FROM mandates WHERE buyer_id=?", LAB)
    hm = heatmap(w, w.coverage, LAB)
    hm["power_before"], hm["pairs_before"] = s.power_before, s.pairs_before
    n = s.needs
    proposal = None
    if n:
        p = w.store.one("SELECT * FROM proposals WHERE hash=?", n.proposal_hash)
        proposal = {"source": n.source, "hash": n.proposal_hash, "raw": n.raw, "verdict": p["verdict"] if p else "",
                    "gaps": n.gaps, "evidence": n.evidence, "notes": n.notes, "claims": n.claims,
                    "person_claims": s.person_claims, "people": len(n.cells),
                    "cells": sum(len(v) for wk in n.cells.values() for v in wk.values()),
                    "budget_xrp": n.budget_drops / XRP, "summary_for_participants": n.summary}
    resp = {"auto": 0, "approval": 0, "blocked": 0, "people": []}
    for r in s.requests.values():
        cls = r.get("classes", {})
        kinds = {c for c, _ in cls.values()}
        k = "blocked" if r["status"] == "blocked" else ("approval" if "approval" in kinds and r["status"] != "contributed"
                                                         else "auto")
        if r["status"] == "declined":
            k = "declined"
        resp[k] = resp.get(k, 0) + 1
        resp["people"].append({"person": r["person"], "class": k, "status": r["status"],
                               "items": sorted(cls), "reason": "; ".join(sorted({why for c, why in cls.values()
                                                                                  if c != "auto"}))})
    contribs, paid, refunded = [], 0, 0
    for o in w.store.q("SELECT o.*, p.tx_hash, p.finish_tx, p.cancel_tx FROM orders o JOIN payments p ON "
                       "p.order_id=o.id WHERE o.buyer_id=? AND o.product_id='cohort.fill' ORDER BY o.id", LAB):
        slot = json.loads(o["scope"])["slot"]
        pid, rest = slot.split("|", 1)
        if o["status"] == "delivered":
            paid += o["price_drops"]
        if o["cancel_tx"]:
            refunded += o["price_drops"]
        contribs.append({"order_id": o["id"], "person": pid,
                         "pseudonym": w.cohort_people[pid].vault.pseudonym(LAB),
                         "weeks": [int(x.split(":")[0][1:]) for x in rest.split(",")],
                         "amount_xrp": o["price_drops"] / XRP, "status": o["status"],
                         "escrow": _tx(w, o["tx_hash"]), "finish": _tx(w, o["finish_tx"]),
                         "cancel": _tx(w, o["cancel_tx"]), "bundle_hash": o["bundle_hash"]})
    from .scenario import ETHICS_CREDENTIAL  # noqa: F401
    return {
        "study": {"id": LAB, "name": w.engine.party(LAB)["name"], "ledger": w.ledger.name,
                  "protocol": __import__("agentrail.cohort", fromlist=["PROTOCOL"]).PROTOCOL,
                  "purpose": "sleep_research",
                  "duo": [{"code": c, "label": DUO[c]} for c in PURPOSE_DUO["sleep_research"]],
                  "credentials": _badges(w),
                  "treasury": {"address": s.treasury, "multisig": True, "quorum": 2, "signers": list(s.signers)},
                  "budget_xrp": m["total_drops"] / XRP, "spent_xrp": m["spent_drops"] / XRP,
                  "reserved_xrp": m["reserved_drops"] / XRP},
        "goal": s.goal, "heatmap": hm, "power_target": 0.8, "proposal": proposal, "spec_status": s.status,
        "approval": s.approval, "responses": resp, "contributions": contribs,
        "licences": {k: {"mpt_id": v["mpt_id"], "clawed_back": bool(v["clawback"])} for k, v in s.licences.items()},
        "settlement": {"paid_xrp": paid / XRP, "refunded_xrp": refunded / XRP,
                       "people_paid": len({c["person"] for c in contribs if c["status"] == "delivered"}),
                       "export_fees_xrp": sum(x["amount_xrp"] for x in s.export_fees)},
    }


def events(w, after: int = 0) -> dict:
    rows = w.store.q("SELECT id, scene, actor, kind, message, data FROM events WHERE id>? ORDER BY id LIMIT 500", after)
    out = []
    for r in rows:
        d = json.loads(r["data"] or "{}")
        h = d.get("tx_hash") or (d.get("tx")[-1] if isinstance(d.get("tx"), list) and d.get("tx") else None)
        out.append({**dict(r), "data": d, "tx": h, "url": d.get("url") or _url(w, h)})
    return {"events": out, "last": out[-1]["id"] if out else after}
