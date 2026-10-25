"""Both sides of one research study on the same engine and ledger (all synthetic).

Research side: goal -> LLM gap reading checked by code -> co-signed budget -> participation
requests -> sealed contributions -> power. Participant side: request card -> preview of what leaves
the device -> approve / decline -> payment by key-reveal escrow -> data licence (MPT) -> pause or
revoke. The web pages call only these functions.
"""
from __future__ import annotations

import hashlib
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import payout
from .agents import talk
from .cohort import (HERO, PRIMARY, WEEKS, apply_deliveries, heatmap, infer_needs, person_gaps, power)
from .connectors import HospitalExportSource
from . import uniqdata_live
from .engine import BudgetExceeded, NeedsHumanApproval, OrderRequest, canonical, sha256_hex
from .ledger.licence import licence_metadata
from .ledger.amm_terms import SLIPPAGE, STABLE_CODE, STABLE_ISSUER, STABLE_LABEL
from .policy import DUO, PURPOSE_DUO, SENSITIVITY, BuyerMandate

XRP = 1_000_000
LAB = "org_sleeplab"
CLINIC = "src_clinic"
CELL_PRICE = XRP // 5
LABELS = {"sleep.daily": "Sleep (wearable)", "activity.daily": "Activity (wearable)",
          "heart_rate.daily": "Resting heart rate (wearable)", "fatigue.survey": "Fatigue survey",
          "blood_pressure.daily": "Blood pressure (clinic visit)", "birth_date": "Exact birth date",
          "zip5": "5-digit postal code", "diagnosis.rare": "Rare diagnosis"}
IRB_NUMBER = "IRB-SYN-2026-014"   # synthetic ethics approval number shown in the console
HOLD_WINDOW_S = 120     # escrow deadline for a round the participant's agent has not released yet
BONUS_DROPS = CELL_PRICE   # completion bonus offered on the followed participant's request


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
    # Required at registration: no budget is approved and no request goes out without it.
    irb_approval: str = ""
    payout_currency: dict = field(default_factory=dict)   # pid -> "XRP" | "stable" (participant's choice)
    swaps: list = field(default_factory=list)              # stablecoin conversions done by participants' agents


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
    s.irb_approval = os.environ.get("STUDY_IRB_APPROVAL", "DEMO-IRB-0000 (synthetic demo value)")
    for pid in os.environ.get("PAYOUT_STABLE_FOR", HERO).split(","):     # demo: P-017 holds a stablecoin
        if pid.strip():
            s.payout_currency[pid.strip()] = "stable"
    hm = heatmap(w, w.coverage, LAB)
    s.power_before, s.pairs_before = hm["power"], hm["complete_pairs"]
    sec = getattr(w, "security", None)
    if sec:   # approvers' keys live on their own devices; the ledger adapter never sees them
        s.treasury = w.ledger.new_account("org_sleeplab_treasury_cosign")
        s.signers = sec.register_treasury(s.treasury)
    else:
        s.treasury = w.ledger.new_account("org_sleeplab_treasury")
        s.signers = {"owner": w.ledger.new_keypair("sleeplab_pi"),
                     "compliance": w.ledger.new_keypair("sleeplab_compliance")}
    hashes = w.ledger.setup_multisig(s.treasury, list(s.signers.values()), quorum=2)
    w.store.log(LAB, "multisig", "study treasury: SignerList (principal investigator + compliance officer, "
                "quorum 2), master key disabled", {"tx": hashes, "url": _url(w, hashes[-1])})
    if CLINIC not in {r["id"] for r in w.store.q("SELECT id FROM parties")}:
        w.engine.add_party(CLINIC, "Clinic records export (synthetic source institution)", "organization",
                           w.ledger.new_account(CLINIC))
    w.engine.set_mandate(BuyerMandate(LAB, 0, 3 * XRP, ["sleep_research"]))
    from .mandate import MandateChain
    chain = MandateChain(LAB)          # the PI signs the agent's delegation when the budget is approved
    chain.payees, chain.ceiling_drops = sorted(w.cohort_people), 100 * XRP
    w.engine.mandate_chains[LAB] = chain
    w.study = s
    _kyb(w)
    return s


REGISTRY = "org_registry"
VERIFIED_ORG = "VERIFIED_ORG"


def _kyb(w):
    """A registry issues VERIFIED_ORG to the lab. Every participant's agent requires it before it
    answers a request (escrow route); the followed participant's account also accepts direct
    payments only from verified organizations (DepositAuth + DepositPreauth by credential)."""
    e, L = w.engine, w.ledger
    if REGISTRY not in {r["id"] for r in w.store.q("SELECT id FROM parties")}:
        e.add_party(REGISTRY, "Organization registry (synthetic)", "organization", L.new_account(REGISTRY))
    reg, lab = e.party(REGISTRY)["address"], e.party(LAB)["address"]
    txs = L.issue_credential(reg, lab, VERIFIED_ORG)
    w.kyb_tx = txs[-1] if txs else None
    w.store.log(REGISTRY, "credential", f"issued XRPL Credential {VERIFIED_ORG} to {LAB} (accepted on ledger)",
                {"tx": txs, "url": _url(w, w.kyb_tx)})
    check = lambda buyer: L.has_credential(e.party(buyer)["address"], reg, VERIFIED_ORG)
    for pa in w.cohort_people.values():
        pa.policy.compliance.verified_check = check
    hero = e.party(HERO)["address"]
    if L.can_sign(hero) and hasattr(L, "require_credential_deposits"):
        txs = L.require_credential_deposits(hero, reg, VERIFIED_ORG)
        w.store.log(HERO, "deposit_auth", f"{HERO}'s account accepts direct payments only from organizations "
                    f"holding {VERIFIED_ORG} (DepositAuth + DepositPreauth)", {"tx": txs, "url": _url(w, txs[-1]) if txs else None})


def direct_payment_attempt(w, payer: str, pid: str, amount_drops: int = XRP) -> dict:
    """An organization tries to pay a participant directly, outside any request. The ledger decides."""
    src, dst = w.engine.party(payer)["address"], w.engine.party(pid)["address"]
    inv = hashlib.sha256(f"direct|{payer}|{pid}|{time.time()}".encode()).hexdigest().upper()
    prep = w.ledger.prepare_payment(src, dst, amount_drops, inv, "unsolicited payment")
    w.ledger.submit(prep)
    st = w.ledger.wait_validated(prep.tx_hash)
    w.store.log(payer, "refused" if not st.success else "paid",
                f"{payer} pays {pid} directly: ledger result {st.result}", {"tx_hash": prep.tx_hash,
                                                                           "url": _url(w, prep.tx_hash)})
    return {"result": st.result, **_tx(w, prep.tx_hash)}


# ---------------- research side ----------------

def set_goal(w, goal: str, propose=None) -> dict:
    s = ensure(w)
    from .scenario import ETHICS_CREDENTIAL
    w.store.scene = "H"
    s.goal = goal or "Bring the primary analysis back to 80% power before the interim report."
    ethics = w.ledger.has_credential(w.engine.party(LAB)["address"], w.engine.party("org_ethics")["address"],
                                     ETHICS_CREDENTIAL)
    s.needs = infer_needs(w.store, LAB, w.coverage, ["sleep_research"], 40 * XRP, ethics, propose, s.goal)
    tl = w.cohort_people[HERO].vault.timeline(WEEKS)
    available = {wk: [i for i, v in items.items() if v["days"]] for wk, items in tl.items()}
    s.person_claims = {HERO: person_gaps(w.store, LAB, w.coverage, HERO, propose, available, ethics)}
    # The followed participant's request follows the per-person reading (verified above).
    for c in s.person_claims[HERO]:
        if c["verdict"] == "kept":
            wk = s.needs.cells.setdefault(HERO, {}).setdefault(c["week"], [])
            if c["item"] not in wk:
                wk.append(c["item"])
    _plant_integrity_case(w, s)
    s.status = "draft"
    n = s.needs
    w.store.log(LAB, "spec", f"gap reading ({'LLM' if n.source == 'llm' else 'rule baseline'}, checked by code): "
                + ("; ".join(f"{i} weeks {ws}" for i, ws in n.gaps.items()) or "no gaps")
                + f"; {len(n.cells)} participants asked", {"hash": n.proposal_hash, "notes": n.notes})
    return study_view(w)


def _plant_integrity_case(w, s):
    """Synthetic test case for the integrity review: one automatic contributor's survey app returns
    scores outside the 0-10 scale (fabricated data). Logged as a fixture, not hidden."""
    if getattr(w, "integrity_fixture", None):
        return
    for pid in sorted(s.needs.cells, reverse=True):
        c = w.store.one("SELECT automation FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
        if pid != HERO and c is not None and c["automation"] == "auto_all":
            w.cohort_people[pid].vault.fabricate = True
            w.integrity_fixture = {"person": pid, "kind": "fabricated survey scores"}
            w.store.log("engine", "fixture", f"synthetic integrity test case: {pid}'s survey app returns scores "
                        "outside the 0-10 scale (the review should catch it)")
            return


def approve(w, signers: list[str]) -> dict:
    """Budget for the spec, released from the study treasury only with both co-signatures."""
    from .scenario import top_up
    s = ensure(w)
    if s.status != "draft":
        return {"ok": False, "message": "no draft spec to approve"}
    if not s.irb_approval.strip():
        return {"ok": False, "message": "register the ethics committee (IRB) approval number first"}
    if getattr(w, "security", None):
        # Each approver signs on their own device (security/cosign.py); this entry point is the
        # scripts' and demo harness's way to drive those devices.
        from .security.cosign import approve_with_devices
        return approve_with_devices(w, signers)
    unknown = [x for x in signers if x not in s.signers]
    if unknown:
        return {"ok": False, "engine_result": "unknown_signer", "signers": signers,
                "message": f"not on the treasury's signer list: {', '.join(unknown)}"}
    addrs = [s.signers[x] for x in signers]
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
    if not s.irb_approval.strip():
        return {"ok": False, "message": "register the ethics committee (IRB) approval number first"}
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
        got = _answer(w, req)
        if len(got) > 1 and not any(o.get("hold") for o in req["orders"]):
            w.engine.escrow_create_batch(got)      # all of this person's weeks, or none
        oids += got
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(w.engine.process, oids))
    for req in s.requests.values():
        _after_contribution(w, req)
        if req["person"] == HERO:
            payout.offer_bonus(w, LAB, req, BONUS_DROPS)
        _settle(w, req)
    s.status = "sent"
    return study_view(w)


def _answer(w, req, hold_last=False) -> list[int]:
    """The participant's agent answers a request week by week; contributes what consent allows."""
    pa = w.cohort_people[req["person"]]
    ok, why = payout.may_request(w, LAB, pa.id)
    if not ok:
        req["status"], req["classes"] = "excluded", {i: ("blocked", why) for its in req["weeks"].values() for i in its}
        return []
    decisions = {wk: pa.handle_request(LAB, req["purpose"], its, wk, CELL_PRICE)
                 for wk, its in sorted(req["weeks"].items())}
    if "classes" not in req:
        merged = {}
        for wk, d in decisions.items():
            for i, c in _classify(d, req["weeks"][wk]).items():
                rank = {"blocked": 2, "approval": 1, "auto": 0}
                if i not in merged or rank[c[0]] > rank[merged[i][0]]:
                    merged[i] = c
        req["classes"] = merged
    granted = {wk: [i for i in req["weeks"][wk] if i in d.granted] for wk, d in decisions.items() if d.ok}
    granted = {wk: its for wk, its in granted.items() if its and not _done(w, req, wk, its)}
    pending = any(d.pending for d in decisions.values())
    if payout.auto_paused(w, LAB, pa.id) and not req.get("weeks_approved"):
        granted, pending = {}, True      # automatic requests paused: the person answers by hand
    if not granted and not any(_done(w, req, wk, its) for wk, its in req["weeks"].items()):
        req["status"] = "open" if pending else "blocked"
        return []
    oids = []
    for i, (wk, its) in enumerate(sorted(granted.items())):
        if any(x in HospitalExportSource.items for x in its):
            _export_fee(w, pa, its)
        rows = pa.vault.extract(its, wk, study=LAB)
        prov = uniqdata_live.provenance(pa, its, [wk])
        if prov:
            w.store.log(pa.id, "uniqdata_read", f"{pa.id}'s agent read {prov['records']} records for week {wk} "
                        f"from the person's UniQdata account", {"records": prov["records"],
                        "record_hashes_sha256": sha256_hex(canonical(prov["record_hashes"]))})
        last = hold_last and i == len(granted) - 1
        r = OrderRequest(LAB, pa.id, pa.id, "cohort.fill", f"{pa.id}|w{wk}:{'+'.join(its)}", req["purpose"],
                         sorted(its), payout.immediate(len(its) * CELL_PRICE), rows, decisions[wk], settle="escrow",
                         escrow_window_s=HOLD_WINDOW_S if last else 600)
        try:
            oid = w.engine.place_order(r)
        except (BudgetExceeded, NeedsHumanApproval) as e:
            w.store.log(LAB, "stop", f"{pa.id}: {e}")
            continue
        req["orders"].append({"order_id": oid, "week": wk, "items": its, "hold": last})
        oids.append(oid)
    req["status"] = "partly_open" if pending else "contributed"
    return oids


def _done(w, req, wk, its):
    return any(o["week"] == wk and set(its) <= set(o["items"]) for o in req["orders"])


def _export_fee(w, pa, items):
    """Clinic records come through the clinic's export service, which charges a small fee per export.
    The participant's agent asks over HTTP, gets 402 Payment Required (x402), signs exactly the payment
    asked for from the participant's own account (no custody by the service) and retries."""
    from . import clinic
    addr = w.engine.party(pa.id)["address"]
    if not w.ledger.can_sign(addr):
        return
    if not clinic._cfg or clinic._cfg.get("ledger") is not w.ledger:
        clinic.configure(w.ledger, w.engine.party(CLINIC)["address"], HospitalExportSource.export_fee_drops)
    fee = HospitalExportSource.export_fee_drops
    nonce = hashlib.sha256(f"{pa.id}|{items}|{time.time()}".encode()).hexdigest()[:16]
    try:
        trail, body = clinic.pay_and_fetch(w.ledger, addr, pa.id, list(items), nonce,
                                           os.environ.get("CLINIC_EXPORT_URL") or None)
    except Exception as e:
        trail, body = ["error"], {"error": f"{type(e).__name__}: {e}"}
    rec = body.get("receipt") or {}
    ok = trail[-1] == 200 and rec.get("success")
    rail = f"x402 ({rec.get('settledBy')})" if ok else "failed"
    w.study.export_fees.append({"person": pa.id, "amount_xrp": fee / XRP, **_tx(w, rec.get("transaction")),
                                "ok": bool(ok), "rail": rail, "http": trail})
    if ok:
        w.store.log(pa.id, "export", f"{pa.id}'s agent asked the clinic for its records: HTTP "
                    f"{' -> '.join(map(str, trail))}; paid {fee / XRP:g} XRP by x402, settled by "
                    f"{rec.get('settledBy')}", {"tx_hash": rec.get("transaction"), "url": _url(w, rec.get("transaction"))})
    else:
        w.store.log(pa.id, "error", f"clinic export not paid: HTTP {trail} {body.get('error') or body}")


def set_payout_currency(w, pid: str, currency: str) -> dict:
    """The participant picks how they want to hold what they earn: XRP, or a stablecoin their own agent
    swaps into through an AMM pool right after each payment."""
    if currency not in ("XRP", "stable"):
        raise ValueError("currency must be XRP or stable")
    if pid not in w.cohort_people:
        raise KeyError(pid)
    ensure(w).payout_currency[pid] = currency
    return {"person": pid, "payout_currency": currency, "stablecoin": STABLE_LABEL}


def _swap_paid(w, pid: str, delivered: list):
    """After escrows pay out in XRP, the participant's agent converts exactly that amount."""
    s = w.study
    if s.payout_currency.get(pid) != "stable" or not hasattr(w.ledger, "swap_to_stable"):
        return
    addr = w.engine.party(pid)["address"]
    done = {o for x in s.swaps for o in x["orders"]}
    todo = [o["order_id"] for o in delivered if o["order_id"] not in done]
    if not todo or not w.ledger.can_sign(addr):
        return
    drops = sum(w.store.one("SELECT price_drops FROM orders WHERE id=?", o)["price_drops"] for o in todo)
    try:
        tl = w.ledger.ensure_trustline(addr, STABLE_CODE, STABLE_ISSUER)
        r = w.ledger.swap_to_stable(addr, drops, STABLE_CODE, STABLE_ISSUER)
    except Exception as e:
        w.store.log(pid, "error", f"stablecoin swap failed ({e}); payment stays in XRP")
        return
    s.swaps.append({"person": pid, "orders": todo, "xrp": drops / XRP, "trustline_tx": tl, **r,
                    "url": _url(w, r.get("tx"))})
    if r["ok"]:
        w.store.log(pid, "swap", f"{pid}'s agent swapped the {drops / XRP:g} XRP it was paid into {r['delivered']} "
                    f"{STABLE_LABEL} through the AMM pool (minimum set {int(SLIPPAGE * 100)}% under spot)",
                    {"tx_hash": r["tx"], "url": _url(w, r["tx"])})
    else:
        w.store.log(pid, "swap", f"{pid}: swap refused ({r['result']}); payment stays in XRP")


def _after_contribution(w, req):
    """First delivered contribution -> the participant's agent issues the study a data licence (MPT)."""
    s = w.study
    pid = req["person"]
    delivered = [o for o in req["orders"] if w.store.one("SELECT status FROM orders WHERE id=?",
                                                          o["order_id"])["status"] == "delivered"]
    apply_deliveries(w, w.coverage, [{"order_id": o["order_id"], "person": pid, "cells": {o["week"]: o["items"]}}
                                     for o in delivered])
    _swap_paid(w, pid, delivered)
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


def _settle(w, req, withdrawn=False):
    payout.bonus_progress(w, LAB, req)
    out = payout.settle_round(w, LAB, req, withdrawn=withdrawn)
    if w.ledger.name != "mock":       # live ledger: pay what is already due on the way, before CancelAfter
        payout.release_due(w)
    return out


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
        _settle(w, req)
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


class Gone(Exception):
    """The participant withdrew and the study destroyed its copy."""


def licence_gate(w, pid: str, use: str) -> dict | None:
    """Every later access re-reads the licence on the ledger: the study must still hold it, and the
    use must keep every restriction the participant wrote into its metadata (DUO codes)."""
    lic = ensure(w).licences.get(pid)
    if not lic or not hasattr(w.ledger, "licence_held"):
        return None
    if not w.ledger.licence_held(w.engine.party(LAB)["address"], lic["mpt_id"]):
        raise PermissionError(f"licence_revoked: {pid} clawed back the study's licence {lic['mpt_id'][:12]}…")
    meta = json.loads(w.ledger.licence_metadata_of(lic["mpt_id"]) or "{}")
    duo = meta.get("duo", [])
    allowed = set(PURPOSE_DUO.get(use, []))
    missing = [c for c in duo if c not in allowed]
    if use not in PURPOSE_DUO or missing:
        raise PermissionError(f"outside_licence: use '{use}' does not keep {', '.join(missing) or 'the licence terms'} "
                              f"written in {pid}'s licence on the ledger")
    return {"mpt_id": lic["mpt_id"], "held": True, "duo": duo, "use": use}


def dispute(w, tx_hash: str) -> dict:
    """Dispute view: from one ledger tx (escrow, payment, finish or cancel) back to who authorized it.
    memo mandate hash -> L3 (the agent's signed order) -> L2 (the owner's signed limits, with the
    co-signed treasury tx that funded them) -> L1 (the issuer's ceiling)."""
    from .mandate import explain, presentation_hash
    h = tx_hash.upper()
    p = w.store.one("SELECT * FROM payments WHERE upper(tx_hash)=? OR upper(finish_tx)=? OR upper(cancel_tx)=?", h, h, h)
    if p is None:
        raise KeyError(f"no payment with tx {tx_hash}")
    o = w.store.one("SELECT * FROM orders WHERE id=?", p["order_id"])
    a = w.store.one("SELECT * FROM mandate_actions WHERE order_id=?", p["order_id"])
    if a is None:
        raise KeyError(f"order {p['order_id']} has no signed order")
    chain = w.engine.mandate_chains[o["buyer_id"]]
    st = w.ledger.lookup(p["tx_hash"])
    view = explain(a["l1"], a["l2"], a["l3"], chain.issuer_pub)
    t = view.get("l3", {}).get("transaction", {})
    view["ledger"] = {"tx": p["tx_hash"], "url": _url(w, p["tx_hash"]), "type": st.tx_type, "result": st.result,
                      "amount_drops": st.amount_drops, "finish_tx": p["finish_tx"], "cancel_tx": p["cancel_tx"],
                      "memo_mandate_hash": a["hash"], "memo_matches_l3": a["hash"] == presentation_hash(a["l3"])}
    view["checks"] = {"amount": t.get("amount") == p["amount_drops"], "invoice": t.get("invoiceId") == o["order_key"].upper(),
                      "purpose": t.get("purpose") == o["purpose"], "verdict_at_payment": a["verdict"], "reason": a["reason"]}
    funded = view.get("l2", {}).get("constraints", {}).get("treasury_tx")
    if funded:
        view["l2"]["treasury_tx_url"] = _url(w, funded)
    view["order"] = {"id": o["id"], "buyer": o["buyer_id"], "payee": o["payee_id"], "purpose": o["purpose"],
                     "status": o["status"]}
    return view


def open_bundle(w, oid: int, use: str = "sleep_research") -> dict:
    o = w.store.one("SELECT * FROM orders WHERE id=?", oid)
    if o is not None and o["seller_id"] in getattr(ensure(w), "withdrawn", set()):
        raise Gone(f"order {oid}: the participant withdrew and the study's copy was destroyed")
    p = w.store.one("SELECT kind, finish_tx FROM payments WHERE order_id=?", oid)
    if o is None or o["status"] != "delivered":
        return {"ok": False, "message": "not delivered: the key is not on the ledger"}
    lic = licence_gate(w, o["seller_id"], use)
    rows = w.engine.open_bundle(LAB, oid)
    f = w.ledger.lookup(p["finish_tx"]).fulfillment if p and p["kind"] == "escrow" else None
    return {"ok": True, "rows": rows, "bundle_hash": o["bundle_hash"],
            "hash_matches": True,      # engine.open_bundle checks the salted payload against the ledger hash
            "key_from": _tx(w, p["finish_tx"]),
            # The Fulfillment field of that EscrowFinish, as read from the ledger: the bundle key is inside it.
            "fulfillment_on_ledger": f, "licence": lic}


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
                         "source": srcs[i].name if i in srcs else None, "class": cls, "reason": why,
                         "sensitive": SENSITIVITY.get(i) == "sensitive"})
    n_cells = sum(len(v) for v in req["weeks"].values())
    return {"id": req["id"], "status": req["status"], "purpose": req["purpose"],
            "institution": {"id": LAB, "name": w.engine.party(LAB)["name"], "badges": _badges(w)},
            "summary": (s.needs.summary if s.needs else "") or "The study is missing some weeks of your record "
                       "and asks you to fill them.",
            "summary_source": s.needs.source if s.needs else "rules",
            "duo": [{"code": c, "label": DUO[c]} for c in PURPOSE_DUO.get(req["purpose"], [])],
            "items": per_item, "payment_xrp": n_cells * CELL_PRICE / XRP,
            "reward_xrp": n_cells * CELL_PRICE / XRP,      # old name, kept for the UI until it reads payment_xrp
            "payment": payout.card_terms(w.ledger),
            "completion_bonus_xrp": BONUS_DROPS / XRP if req["person"] == HERO else None,
            "partial_data_plan": "If you withdraw, person-level copies are destroyed and only aggregate "
                                 "statistics already produced remain; the ethics board decides any other use.",
            "if_you_stop": [
                {"kind": "decline_round", "label": "Skip this round", "effect": "Nothing is sent this time; "
                 "your consent stays as it is. It never affects future requests, priority or pay."},
                {"kind": "pause", "label": "Stop future rounds", "effect": "No new requests run; payments already made "
                 "stay yours."},
                {"kind": "revoke", "label": "Withdraw data access", "effect": "The study's licence is taken back on "
                 "the ledger, rounds not yet released are never released and their escrow returns to the study, "
                 "held review parts of rounds you already gave are still paid, the completion bonus returns, "
                 "and the study must destroy every person-level copy it holds about you and confirm it. Aggregate "
                 "statistics already produced remain. Payments already made stay yours."}],
            "settlement": "escrow: the payment is locked on XRPL and released when your agent publishes the key",
            "international_transfer": {"planned": False, "countries": [], "recipients": [], "purpose": None,
                                       "items": [], "retention": None,
                                       "notice": "No access from outside the participant's country is planned. "
                                                 "Any change needs your separate consent."},
            "identity": "The study gets your participant number and the items you agree to. The link between "
                        "you and that number stays with your agent, where the study cannot reach it.",
            "records": "Access records are kept 2 years, permission changes 3 years.",
            "ethics_approval": ensure(w).irb_approval,
            "other_studies": "Your data, even with identifiers removed, will not be used for other studies.",
            "separate_consents": [
                {"kind": "sensitive_data", "label": "Health data (sensitive)", "required": True},
                {"kind": "third_party_provision", "label": f"Provision to {LAB}", "required": True},
                {"kind": "international_transfer", "label": "Access from abroad", "required": False,
                 "planned": False}]}


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
        "payout": payout.view(w, LAB, pid),
    }


def _own_request(w, pid: str, rid: int) -> dict:
    """A participant can see and answer only their own requests (unknown or someone else's -> 404)."""
    req = ensure(w).requests[rid]
    if req["person"] != pid:
        raise KeyError(f"request {rid}")
    return req


def preview(w, pid: str, rid: int) -> dict:
    req = _own_request(w, pid, rid)
    pa = w.cohort_people[pid]
    card = request_card(w, req)
    ok = [i["item"] for i in card["items"] if i["class"] != "blocked"]
    rows = [r for wk, its in sorted(req["weeks"].items())
            for r in pa.vault.extract([i for i in its if i in ok], wk, study=LAB)]
    return {"pseudonym": pa.vault.pseudonym(LAB), "dates": "shifted by a per-study offset only your agent knows",
            "rows": rows[:14], "row_count": len(rows),
            "withheld_items": [i["item"] for i in card["items"] if i["class"] == "blocked"],
            "not_included": [i for i in pa.vault.ITEMS if i not in ok],
            "sealed_for": LAB,
            "from": uniqdata_live.provenance(pa, ok, sorted(req["weeks"]))}


def _uniqdata_person(w, pid: str):
    ensure(w)
    pa = w.cohort_people[pid]
    if getattr(pa.vault, "uniqdata", None) is None:
        raise KeyError(f"{pid} has no UniQdata account connected")
    return pa


def my_data(w, pid: str) -> dict:
    """'My data': what the person's UniQdata account holds, per source and item (no values)."""
    return {"person": pid, **uniqdata_live.my_data(_uniqdata_person(w, pid), LABELS, WEEKS)}


def upload_data(w, pid: str, weeks: list[int], items: list[str]) -> dict:
    """The person uploads synthetic records to their UniQdata account."""
    pa = _uniqdata_person(w, pid)
    bad = [i for i in items if i not in pa.vault.ITEMS] + [str(x) for x in weeks if x not in WEEKS]
    if bad:
        raise ValueError(f"unknown items or weeks: {bad}")
    out = uniqdata_live.upload_synthetic(pa, weeks, items)
    w.store.log(pid, "uniqdata_upload", f"{pid} stored {out['written']} records in their UniQdata account",
                {"written": out["written"]})
    return {**out, **my_data(w, pid)}


def participant_approve(w, pid: str, rid: int, items: list[str], hold_last: bool = True) -> dict:
    req = _own_request(w, pid, rid)
    pa = w.cohort_people[pid]
    asked = {wk: [i for i in its if i in items] for wk, its in req["weeks"].items()}
    req["weeks_approved"] = {wk: its for wk, its in asked.items() if its}
    # Ticking an item by name approves the scope and, for sensitive items, this round as well.
    for _ in range(4):
        for r in pa.open_requests():
            if r["buyer_id"] == LAB:
                pa.approve(r["id"], [i for i in items if i in json.loads(r["items"])])
        for wk, its in sorted(req["weeks_approved"].items()):
            pa.handle_request(LAB, req["purpose"], its, wk, CELL_PRICE)
    sub = {**req, "weeks": req["weeks_approved"]}
    oids = _answer(w, sub, hold_last=hold_last)
    req["orders"] = sub["orders"]          # the card keeps the classes the person was shown
    for oid in oids:
        o = next(x for x in req["orders"] if x["order_id"] == oid)
        w.engine.process(oid, until="finish" if o["hold"] else None)
    _after_contribution(w, req)
    _settle(w, req)
    req["status"] = "contributed"
    return participant_view(w, pid)


def participant_decline(w, pid: str, rid: int) -> dict:
    """Withdrawal 1: decline this round. Nothing leaves the device, nothing reaches the ledger."""
    req = _own_request(w, pid, rid)
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
    """Withdrawal 2: stop future supply. Past contributions and payments stay."""
    pa = w.cohort_people[pid]
    (pa.resume if resume else pa.pause)(LAB)
    if not resume:
        w.study.withdrawals.append({"person": pid, "kind": "pause", "ts": time.time(),
                                    "ledger": "no new escrows; completed payments and licence stay"})
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
    payout.on_withdrawal(w, LAB, pid)          # completion bonus goes back; reviewed held shares stay theirs
    out["deletion"] = _destroy_person_level(w, pid)
    for req in _requests_for(w, pid):
        _settle(w, req, withdrawn=True)
    out["kept"] = ("consent history (every version hashed); payments already made stay with the participant; "
                   "aggregate statistics already produced")
    s.withdrawals.append({"person": pid, "kind": "revoke", "ts": time.time(), **out})
    return {**out, **participant_view(w, pid)}


def _destroy_person_level(w, pid: str) -> dict:
    """Revoke: the participant's agent asks the study to destroy every person-level copy it holds
    (contributed bundles and its own records for this participant) and to confirm. Only aggregate
    statistics already produced remain."""
    s = w.study
    s.withdrawn = getattr(s, "withdrawn", set()) | {pid}
    talk(w.store, pid, LAB, "deletion_request", {"participant": pid},
         f"{pid} withdrew data access: destroy every person-level copy you hold for this participant and confirm.")
    orders = w.store.q("SELECT id, order_key, status FROM orders WHERE buyer_id=? AND seller_id=?", LAB, pid)
    oids = [r["id"] for r in orders]
    destroyed = []
    for oid in oids:
        got = w.engine.inbox.received.pop(oid, None)
        if got:
            destroyed.append(got[0])
    # The gate's copies go too: sealed bundles and any escrow key the engine held. The participant's
    # keyring forgets the keys of rounds never released, so they can never be published.
    with w.store.tx() as c:
        c.executemany("DELETE FROM bundles WHERE order_id=?", [(o,) for o in oids])
        c.executemany("DELETE FROM escrow_keys WHERE order_id=?", [(o,) for o in oids])
    kr = getattr(w.cohort_people.get(pid), "keyring", None)
    for o in orders:
        if kr is not None and o["status"] != "delivered":
            kr.forget(o["order_key"])
    cells = sum(len(v) for v in w.coverage.cells[pid].values())
    w.coverage.cells[pid] = {wk: set() for wk in WEEKS}
    receipt = {"participant_number": pid, "bundles_destroyed": sorted(destroyed), "own_cells_destroyed": cells,
               "aggregates_kept": True, "ts": int(time.time())}
    h = sha256_hex(canonical(receipt))
    w.store.log(LAB, "deletion_confirmed", f"{LAB} destroyed {len(destroyed)} contributed bundles and {cells} "
                f"person-level cells for {pid}; confirmation {h[:16]} sent to {pid}'s agent",
                {"receipt": receipt, "hash": h})
    return {"bundles_destroyed": len(destroyed), "cells_destroyed": cells, "confirmation_hash": h}


# ---------------- research console view ----------------

def study_view(w) -> dict:
    s = ensure(w)
    m = w.store.one("SELECT * FROM mandates WHERE buyer_id=?", LAB)
    hm = heatmap(w, w.coverage, LAB)
    hm["power_before"], hm["pairs_before"] = s.power_before, s.pairs_before
    for row in hm["rows"]:
        row["pseudonym"] = w.cohort_people[row["person"]].vault.pseudonym(LAB)
        if row["person"] in getattr(s, "withdrawn", set()):
            row["cells"] = [{"s": "withdrawn"} for _ in row["cells"]]
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
        resp["people"].append({"person": r["person"], "pseudonym": w.cohort_people[r["person"]].vault.pseudonym(LAB),
                               "class": k, "status": r["status"],
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
        contribs.append({"order_id": o["id"],
                         "pseudonym": w.cohort_people[pid].vault.pseudonym(LAB),
                         "weeks": [int(x.split(":")[0][1:]) for x in rest.split(",")],
                         "items": sorted({i for x in rest.split(",") for i in x.split(":")[1].split("+")}),
                         "amount_xrp": o["price_drops"] / XRP, "status": o["status"],
                         "escrow": _tx(w, o["tx_hash"]), "finish": _tx(w, o["finish_tx"]),
                         "cancel": _tx(w, o["cancel_tx"]), "bundle_hash": o["bundle_hash"]})
    from .scenario import ETHICS_CREDENTIAL  # noqa: F401
    return {
        "study": {"id": LAB, "name": w.engine.party(LAB)["name"], "ledger": w.ledger.name,
                  "protocol": __import__("agentrail.cohort", fromlist=["PROTOCOL"]).PROTOCOL,
                  "irb": IRB_NUMBER,
                  "purpose": "sleep_research",
                  "duo": [{"code": c, "label": DUO[c]} for c in PURPOSE_DUO["sleep_research"]],
                  "credentials": _badges(w),
                  "treasury": {"address": s.treasury, "multisig": True, "quorum": 2, "signers": list(s.signers)},
                  "budget_xrp": m["total_drops"] / XRP, "spent_xrp": m["spent_drops"] / XRP,
                  "reserved_xrp": m["reserved_drops"] / XRP},
        "goal": s.goal, "heatmap": hm, "power_target": 0.8, "proposal": proposal, "spec_status": s.status,
        "approval": s.approval, "responses": resp, "contributions": contribs,
        "licences": {k: {"mpt_id": v["mpt_id"], "clawed_back": bool(v["clawback"])} for k, v in s.licences.items()},
        "withdrawals": [{"pseudonym": w.cohort_people[x["person"]].vault.pseudonym(LAB), "kind": x["kind"],
                         "ts": x["ts"]} for x in s.withdrawals],
        "settlement": {"paid_xrp": paid / XRP, "refunded_xrp": refunded / XRP,
                       "people_paid": len({c["pseudonym"] for c in contribs if c["status"] == "delivered"}),
                       "export_fees_xrp": sum(x["amount_xrp"] for x in s.export_fees),
                       "export_fee_rails": {r: sum(1 for x in s.export_fees if x["rail"] == r)
                                            for r in sorted({x["rail"] for x in s.export_fees})},
                       "batches": len(w.store.q("SELECT id FROM events WHERE kind='batch'")),
                       "stablecoin_swaps": [{k: x.get(k) for k in ("ok", "xrp", "delivered", "tx", "url", "result")}
                                            for x in s.swaps]},
        "payout": payout.view(w, LAB),
    }


def events(w, after: int = 0) -> dict:
    rows = w.store.q("SELECT id, ts, scene, actor, kind, message, data FROM events WHERE id>? ORDER BY id LIMIT 500",
                     after)
    out = []
    for r in rows:
        d = json.loads(r["data"] or "{}")
        h = d.get("tx_hash") or (d.get("tx")[-1] if isinstance(d.get("tx"), list) and d.get("tx") else None)
        out.append({**dict(r), "data": d, "tx": h, "url": d.get("url") or _url(w, h)})
    return {"events": out, "last": out[-1]["id"] if out else after}
