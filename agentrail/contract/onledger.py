"""A data-contract round on the study's ledger: the providers are cohort participants' agents, the
sources are registered on the ledger, and every payment is a transaction.

  setup     the registry issues DATA_SOURCE Credentials to each source issuer (on the ledger)
  contract  each participant's agent profiles its columns locally and negotiates with the study's
            agent; consent decides which columns it may offer (a column outside consent goes to the
            owner and is not offered)
  pay       80% by key-reveal escrow through the engine; the EscrowCreate memo carries the contract
            hash next to the bundle hash, and the sealed bundle carries the contract, the native
            values and the manifest
  hold      the other 20% of each contribution in its own escrow; released after a pass, or held
            for a named reviewer after a failure (payout.decide)
"""
from __future__ import annotations

from .. import units

import json

from .. import payout
from ..engine import BudgetExceeded, NeedsHumanApproval, OrderRequest, sha256_hex
from . import market, provenance
from .round import Round, requirements

LAB = "org_sleeplab"
REGISTRY = "org_registry"
COLUMN_ITEM = market.ITEM_OF
CONTRIB_BASE = 100_000          # holdback request ids for contributions: 100000 + order id


def setup(w) -> dict:
    """Source issuers and their DATA_SOURCE Credentials. Idempotent per world."""
    if getattr(w, "contract_registry", None):
        return {"registry": w.contract_registry, "issuers": w.contract_issuers}
    from ..study import ensure
    ensure(w)
    e, L = w.engine, w.ledger
    reg = provenance.Registry(L, e.party(REGISTRY)["address"])
    issuers = {n: provenance.SourceIssuer(n) for n in market.ISSUERS + ["unknown_app"]}
    for n in market.ISSUERS:
        pid = f"src_{n}"
        if pid not in {r["id"] for r in w.store.q("SELECT id FROM parties")}:
            e.add_party(pid, f"Data source {n} (synthetic issuer)", "organization", L.new_account(pid))
        txs = reg.register(issuers[n], e.party(pid)["address"])
        w.store.log(REGISTRY, "credential", f"issued XRPL Credential {provenance.DATA_SOURCE} to source issuer {n}; "
                    "its signing key is registered with the registry", {"tx": txs, "url": L.explorer_url(txs[-1]) if txs else None})
    w.contract_registry, w.contract_issuers = reg, issuers
    return {"registry": reg, "issuers": issuers}


class LedgerSettle:
    name = "ledger"

    def __init__(self, w):
        self.w = w

    def key_for(self, rnd, p, k, wnum) -> bytes | None:
        """The escrow K the participant's keyring will lock this order with; it wraps the intake keys."""
        holder = self.w.engine.key_holders.get(p.id)
        if holder is None or not hasattr(holder, "key"):
            return None
        ok = sha256_hex(f"{LAB}|{p.id}|contract:{k.hash}|{p.id}|w{wnum}:contract|{k.purpose}")
        return holder.key(ok)

    def pay_immediate(self, rnd, p, k, wnum, payload, amount):
        w = self.w
        pa = w.cohort_people[p.id]
        items = sorted({COLUMN_ITEM[t["column"]] for t in k.terms if wnum in t["windows"]})
        d = pa.handle_request(LAB, k.purpose, items, wnum, max(1, amount // max(1, len(items))))
        if not d.ok or d.pending:
            raise RuntimeError(f"{p.id}: consent does not cover {items} for window {wnum} ({d.reason or d.status})")
        r = OrderRequest(LAB, p.id, p.id, f"contract:{k.hash}", f"{p.id}|w{wnum}:contract", k.purpose, items,
                         amount, payload["rows"], d, settle="escrow",
                         extra={"native": payload["native"], "manifest": payload["manifest"], "contract": k.body(),
                                **{x: payload[x] for x in ("sealed", "wrapped") if x in payload}})
        oid = w.engine.place_order(r)
        w.engine.process(oid)
        pm = w.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        o = w.store.one("SELECT status FROM orders WHERE id=?", oid)
        if o["status"] != "delivered":
            raise RuntimeError(f"order {oid} {o['status']}")
        opened = w.engine.open_payload(LAB, oid)
        return {"paid": amount, "payload": opened, "order_id": oid,
                "txs": {"escrow_create": pm["tx_hash"], "escrow_finish": pm["finish_tx"]}}

    def hold(self, rnd, p, k, wnum, amount, passed, signals, paid):
        w, oid = self.w, paid["order_id"]
        win, now = payout.windows(w.ledger), w.ledger.now()
        fa = now + win["review"]
        hid = payout._create(w, "contribution", LAB, p.id, CONTRIB_BASE + oid, len(k.terms), amount, fa,
                             fa + win["extend"], fa + win["extend"] + win["grace"],
                             "held" if passed else "suspected", [oid])
        h = w.store.one("SELECT * FROM holdbacks WHERE id=?", hid) if hid else None
        if h is None:
            return {"released": 0, "held": amount, "txs": {}}
        if passed:
            payout._review_note(w, hid, "pass: contract check")
        else:
            payout.open_case(w, LAB, p.id, CONTRIB_BASE + oid, signals)
        return {"released": amount if passed else 0, "held": 0 if passed else amount,
                "txs": {"holdback_create": h["create_tx"]}, "holdback_id": hid}


def pool(w, n: int = 14, seed: int = 31) -> list:
    """Providers: cohort participants whose consent covers sleep and heart rate automatically; one of
    them is the scripted decliner (negotiation example)."""
    ids = []
    for pid, pa in sorted(w.cohort_people.items()):
        c = w.store.one("SELECT items, automation, status FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
        if (c and c["status"] == "active" and c["automation"] in ("auto_standard", "auto_all") and pid != "P-017"
                and payout.may_request(w, LAB, pid)[0] and not payout.auto_paused(w, LAB, pid)):
            its = set(json.loads(c["items"]))
            if {"sleep.daily", "heart_rate.daily"} <= its:
                ids.append(pid)
    ids = ids[: n]
    out = market.make_market(len(ids) - 1, seed=seed, ids=ids[1:], fault_rate=0.25)
    return [market.scripted_decliner(ids[0])] + out


def review_cases(w, reviewer: str) -> list[dict]:
    """A named reviewer decides the open contribution cases once the response time has passed."""
    import time
    cases = w.store.q("SELECT * FROM integrity_cases WHERE study=? AND status='suspected' AND request_id>=?",
                      LAB, CONTRIB_BASE)
    if not cases:
        return []
    wait = max(c["respond_by"] for c in cases) - w.ledger.now()
    if wait > 0:
        if w.ledger.name == "mock":
            w.ledger.clock += wait + 1
        else:
            time.sleep(wait + 2)
    out = []
    for c in cases:
        r = payout.decide(w, LAB, c["id"], reviewer, confirm=True)
        out.append({"case": c["id"], "person": c["person"], **r})
        w.store.log(LAB, "contract", f"{reviewer} decided case {c['id']} ({c['person']}): {r.get('status')}")
    return out


def run(w, n: int = 14, target: int = 8, model=None, reviewer: str | None = "reviewer-1@org_sleeplab") -> dict:
    s = setup(w)
    providers = pool(w, n)
    consent = lambda pid: (w.store.one("SELECT doc_hash FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
                           or {"doc_hash": ""})["doc_hash"]

    def allows(pid):
        c = w.store.one("SELECT items FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
        its = set(json.loads(c["items"])) if c else set()
        return {col for col, item in COLUMN_ITEM.items() if item in its}

    log = lambda kind, msg: w.store.log(LAB, "contract", msg)
    r = Round(requirements(LAB), providers, s["registry"], s["issuers"], model, strategy="forecast",
              target=target, settle=LedgerSettle(w), consent_hash_of=consent, owner_allows_of=allows, log=log)
    w.contract_round = r
    w.store.scene = "K"
    orig = r.contribute

    def contribute(pid, wnum):
        try:
            o = orig(pid, wnum)
        except (RuntimeError, BudgetExceeded, NeedsHumanApproval) as e:
            w.store.log(LAB, "contract", f"{pid} window {wnum}: not settled ({e})")
            return r._record(pid, r.contracts[pid], wnum, "not_settled", [{"code": "not_settled", "detail": str(e)}],
                             0, 0, 0)
        codes = sorted({x["code"] for x in o["signals"]})
        w.store.log(pid, "contract", f"{pid} window {wnum}: {o['verdict']} at {o['stage'].replace('_', ' ')}"
                    + (f" ({', '.join(codes)})" if codes else "") + f"; paid {o['paid_drops'] / 1e6:g} {units.UNIT}"
                    + (f", held part {'released after review time' if o['verdict'] == 'pass' else 'to a reviewer'}"
                       if o["stage"] == "after_reveal" else ""),
                    {"tx_hash": (o["txs"] or {}).get("escrow_finish"), "contract": o["contract"][:16]})
        return o

    r.contribute = contribute
    summary = r.run()
    if reviewer:
        summary["reviews"] = review_cases(w, reviewer)
    rel = payout.release_due(w)
    summary["holdbacks_released"] = len([x for x in rel["released"] if x["kind"] == "contribution"])
    summary["negotiation_example"] = {"provider": providers[0].id, "transcript": r.transcripts.get(providers[0].id)}
    return summary


def view(w) -> dict:
    r = getattr(w, "contract_round", None)
    if r is None:
        return {"status": "no contract round yet", "projections": [], "contracts": []}
    L = w.ledger
    return {"status": "running" if len(r.projections) < 2 or r.projections[-1]["after_window"] < r.req.windows[-1]
            else "done",
            "requirements": {"hash": r.req.hash(), "columns": [c.__dict__ for c in r.req.columns],
                             "windows": r.req.windows, "tier": r.req.tier, "lowest_tier": r.req.lowest_tier},
            "latest": r.projections[-1] if r.projections else None, "projections": r.projections,
            "warnings": r.warnings,
            "contracts": [{"provider": pid, "hash": k.hash, "tier": k.tier, "windows": k.windows, "terms": k.terms,
                           "price_xrp_per_window": k.price_drops_per_window / 1e6,
                           "transcript": r.transcripts.get(pid)} for pid, k in r.contracts.items()],
            "contributions": [{**{k: v for k, v in o.items() if k != "x"},
                               "urls": {n: L.explorer_url(h) for n, h in (o["txs"] or {}).items() if h}}
                              for o in r.outcomes]}
