"""The hardest boundary first: one person's health record carries consent, re-identification and
withdrawal all at once. Each issue is shown the same way: problem, our answer, where code or the
ledger enforces it, the demo moment, and the evidence (tests and transactions) produced by `run`.
Other domains (organization-to-organization robot data, scene A) use the same engine with only
the consent layer made lighter.
"""
from __future__ import annotations

import json

from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, SealedBox

from . import study
from .cohort import HERO
from .policy import PURPOSE_DUO, QUASI_IDENTIFIERS
from .study import LAB, _tx

ISSUES = [
    {"id": "consent", "title": "Consent",
     "problem": "A person's record may be used only for the use, period and recipient they agreed to, and that "
                "has to be checked on every round, not once at sign-up.",
     "solution": "Per-study consent document with GA4GH DUO codes, versioned and hashed. The person's agent "
                 "checks every request: inside consent runs automatically, outside consent waits for the "
                 "person, prohibited purposes are refused. The LLM only summarizes the request for the person.",
     "enforced": ["code: PersonalConsentPolicy.evaluate (agentrail/policy.py) on order and again before the key "
                  "is published", "code: compliance layer refuses prohibited purposes before consent is read",
                  "ledger: consent version hash in every escrow memo",
                  "ledger: ethics-review Credential checked before sensitive items",
                  "ledger: verified-organization Credential checked before any answer; direct payments from "
                  "unverified organizations refused by DepositAuth + DepositPreauth (tecNO_PERMISSION)"],
     "moment": "The same lab sends a second request for a commercial product. Its DUO codes drop NCU, so the "
               "person's agent stops it at 'needs your approval'. Nothing is sent and no escrow is created.",
     "tests": ["test_items_outside_consent_wait_for_person_even_at_higher_price",
               "test_prohibited_purpose_refused_even_with_consent", "test_payment_memo_carries_consent_version_hash",
               "test_sensitive_items_follow_the_ledger_credential", "test_new_purpose_waits_for_the_person"]},
    {"id": "reidentification", "title": "Re-identification",
     "problem": "The more of one person's life is joined into one record, the easier it is to tell who they are.",
     "solution": "Only the protocol's items and weeks leave the device; a per-study pseudonym (studies cannot "
                 "link records); dates shifted by a per-study offset only the person's agent knows; bundle sealed "
                 "to the study's key; quasi-identifier combinations never released; the ledger sees hashes only.",
     "enforced": ["code: PersonalVaultConnector.extract (minimization, pseudonym, date shift)",
                  "code: ComplianceRules.check refuses 2+ quasi-identifiers (birth date, postal code, rare diagnosis)",
                  "code: SealedBox to the study key; the operator cannot open bundles",
                  "ledger: memo holds order id, bundle hash and consent hash only"],
     "moment": "A request for birth date + postal code + rare diagnosis is refused by code. The operator tries "
               "to open a bundle with its own key and fails. The same person appears under different IDs in two studies.",
     "tests": ["test_quasi_identifier_combination_is_never_released", "test_pseudonym_differs_per_study",
               "test_locked_bundle_cannot_be_opened_before_finish"]},
    {"id": "withdrawal", "title": "Withdrawal",
     "problem": "People must be able to stop at any time, and it has to be clear what stops, what comes back "
                "and what cannot be recalled.",
     "solution": "Three kinds. Decline this round: nothing leaves. Pause: no new rounds, past payments and licence "
                 "stay. Revoke: the study's data licence (MPT) is clawed back, rounds not yet released are "
                 "withheld and their escrow returns to the study after the deadline, the consent history stays. "
                 "Delivered rounds cannot be recalled, and the person is told so.",
     "enforced": ["ledger: Clawback of the per-(study, participant) licence MPT (RequireAuth, no transfer)",
                  "code: key is published only after re-checking consent and that the study still holds the licence",
                  "ledger: EscrowCancel after CancelAfter refunds withheld rounds",
                  "code: consent_history keeps every version and hash"],
     "moment": "P-017 taps revoke: a Clawback transaction, the held week-5 escrow withheld, then an "
               "EscrowCancel refund, all with explorer links; P-017's row turns grey on the researcher heatmap.",
     "tests": ["test_revoke_before_finish_withholds_key_and_refunds_after_deadline",
               "test_pause_blocks_new_orders_but_keeps_history", "test_three_withdrawals_on_one_study"]},
    {"id": "payment", "title": "Fair pay and penalties",
     "problem": "Pay must not punish people for stopping, yet a study needs protection against fabricated or "
                "copied data, and money once paid cannot be pulled back from a person's wallet.",
     "solution": "Each round pays 80% when the contribution is confirmed and holds 20% in its own escrow for a "
                 "short review. The default is to pay. Code looks for fraud signals (values no body or device "
                 "produces, a series already contributed by someone else); a named reviewer decides only after "
                 "the person was told why and could respond. Only then the held part returns to the study, the "
                 "person is excluded for a period, and a repayment claim is recorded off the ledger. Declines, "
                 "pauses and withdrawals are never inputs. A completion bonus sits in a separate escrow and "
                 "returns to the study on withdrawal.",
     "enforced": ["ledger: held share in an EscrowCreate with FinishAfter and a condition kept by the review "
                  "service; EscrowFinish pays, EscrowCancel after CancelAfter returns it",
                  "code: payout.decision_inputs is the only input to pay or sanction decisions; it has no "
                  "decline, pause or withdrawal fields (tested)",
                  "code: confirmation refused without a reviewer id or before the response period ends",
                  "code: no on-chain recovery of paid money; trust level stays in an off-ledger table"],
     "moment": "A synthetic participant's survey reports 12 on a 0-10 scale. The held part is frozen, the person "
               "is told why, a reviewer confirms after the response period, and the held part goes back to the "
               "study. P-017 withdrew, yet P-017's held part is still paid; only the completion bonus returns.",
     "tests": ["test_round_pays_80_now_and_releases_the_held_20_by_default",
               "test_fraud_needs_a_named_reviewer_and_the_response_period",
               "test_withdrawal_history_is_never_an_input",
               "test_withdrawal_still_pays_reviewed_share_and_returns_the_bonus",
               "test_two_missed_accepted_rounds_pause_automatic_requests_only"]},
    {"id": "other_domains", "title": "Other domains are easier",
     "problem": "Does the same engine work where data is not about a person?",
     "solution": "Robot sensor data between companies (scene A) runs on the same engine with only the consent "
                 "layer made lighter: the seller's licence terms and policy replace personal consent. Schema "
                 "matching, licence reading, budget, multi-signed top-up and settlement are unchanged.",
     "enforced": ["code: SellerPolicy instead of PersonalConsentPolicy", "ledger: multi-signed treasury top-up",
                  "ledger: payments with terms hash in memo"],
     "moment": "The robot company's agent closes its evaluation gaps from two sellers on Testnet.",
     "tests": ["test_scene_a_selects_b_and_c_within_budget", "test_hostile_llm_can_only_narrow",
               "test_agent_cannot_raise_its_own_budget_but_cosigned_top_up_can"]},
]


def _payment_evidence(w, s):
    import time as _t
    from . import payout
    fx = getattr(w, "integrity_fixture", None)
    case = w.store.one("SELECT * FROM integrity_cases WHERE study=? AND status='suspected' ORDER BY id", LAB)
    if case:
        sig = json.loads(case["signals"])
        _ev(w, "payment", f"{case['person']}: review found {sig[0]['code']} ({sig[0]['item']} week {sig[0]['week']}: "
            f"{sig[0].get('values')}); held part frozen, participant told why", person=case["person"],
            fixture=bool(fx))
        r = payout.decide(w, LAB, case["id"], "", True)
        _ev(w, "payment", "Confirm without a named reviewer: " + r["message"], result="refused")
        r = payout.decide(w, LAB, case["id"], "reviewer-1", True)
        if not r["ok"]:
            _ev(w, "payment", "Confirm during the response period: " + r["message"], result="refused")
        payout.respond(w, LAB, case["person"], case["id"], "My survey app crashed; I typed the scores myself.")
        if w.ledger.name == "mock":
            w.ledger.clock = max(w.ledger.clock, case["respond_by"])
        else:
            while w.ledger.now() < case["respond_by"]:
                _t.sleep(2)
        r = payout.decide(w, LAB, case["id"], "reviewer-1", True)
        _ev(w, "payment", f"Reviewer-1 confirms after reading the response: held part withheld, excluded for "
            f"{payout.BLOCK_DAYS} days, repayment claim {r.get('repayment_claim_xrp')} XRP recorded off the ledger "
            "(nothing taken back on chain)", result=r.get("status"))
    # Missed accepted rounds: a pause of automatic requests, not a penalty.
    active = lambda pid: (w.store.one("SELECT status FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
                          or {"status": ""})["status"] == "active"
    other = next((q for q in s.requests.values() if q["person"] not in (HERO, (fx or {}).get("person"))
                  and q["status"] == "contributed" and active(q["person"])), None)
    if other:
        for _ in range(payout.MISSED_LIMIT):
            n = payout.round_missed(w, LAB, other["person"], other["id"])
        _ev(w, "payment", f"{other['person']}: {n} accepted rounds missed in a row -> automatic requests paused "
            "(one tap resumes); priority and pay rules unchanged", person=other["person"])
    inp = payout.decision_inputs(w.store, LAB, HERO)
    _ev(w, "payment", f"{HERO} withdrew; what pay and sanction decisions read for {HERO}: fraud confirmed "
        f"{inp['fraud_confirmed']}, missed rounds {inp['missed_in_row']}, excluded {inp['excluded']} "
        "(withdrawal is not an input)", result=inp)
    # Release what is due, return what must go back (Testnet: wait for the short windows).
    deadline = _t.time() + 240
    while True:
        r = payout.release_due(w)
        mine = [x for x in r["released"] if x["person"] == HERO]
        for x in mine:
            _ev(w, "payment", f"{HERO} withdrew, and the reviewed held part {x['amount_xrp']:g} XRP is still paid "
                "(EscrowFinish)", tx=x["tx"], url=x["url"])
        rest = [x for x in r["released"] if x["person"] != HERO]
        if rest:
            _ev(w, "payment", f"{len(rest)} other participants: held parts released after review "
                f"({sum(x['amount_xrp'] for x in rest):.2f} XRP)", tx=rest[0]["tx"], url=rest[0]["url"])
        for x in r["returned"]:
            _ev(w, "payment", f"{x['person']}: {x['kind']} {x['amount_xrp']:g} XRP returned to the study "
                "(EscrowCancel)", tx=x["tx"], url=x["url"])
        open_ = [h for h in r["waiting"] if h["kind"] == "bonus" or h["person"] in (HERO, (fx or {}).get("person"))]
        if not open_ or w.ledger.name == "mock" or _t.time() > deadline:
            break
        _t.sleep(5)


def view(w) -> dict:
    ev = getattr(w, "boundary_evidence", {})
    return {"issues": [{**i, "evidence": ev.get(i["id"], [])} for i in ISSUES], "ledger": w.ledger.name}


def _ev(w, issue, label, **k):
    w.boundary_evidence.setdefault(issue, []).append({"label": label, **k})


def run(w) -> dict:
    s = study.ensure(w)
    w.boundary_evidence = {}
    if s.status == "none":
        study.set_goal(w, "")
    if s.status == "draft":
        study.approve(w, ["owner", "compliance"])
    if s.status == "approved":
        study.send(w)
    w.store.scene = "K"
    pa = w.cohort_people[HERO]

    # ---- consent ----
    d = pa.handle_request(LAB, "commercial_product_dev", ["sleep.daily"], 6, study.CELL_PRICE)
    _ev(w, "consent", "Same lab, new purpose (DUO " + ", ".join(PURPOSE_DUO["commercial_product_dev"])
        + " without NCU): " + d.status, result=d.status, reason=d.reason, sent=False)
    d = pa.handle_request("org_adtech", "marketing_profiling", ["sleep.daily"], 6, study.CELL_PRICE)
    _ev(w, "consent", f"Ad network, prohibited purpose: {d.status}", result=d.status, reason=d.reason, sent=False)
    if "org_unverified" not in {r["id"] for r in w.store.q("SELECT id FROM parties")}:
        w.engine.add_party("org_unverified", "Unverified lab (synthetic)", "organization",
                           w.ledger.new_account("org_unverified"))
    d = pa.handle_request("org_unverified", "sleep_research", ["sleep.daily"], 6, study.CELL_PRICE)
    _ev(w, "consent", f"Lab without a verified-organization Credential asks: {d.status}", result=d.status,
        reason=d.reason, sent=False)
    if w.ledger.can_sign(w.engine.party(HERO)["address"]):
        r = study.direct_payment_attempt(w, "org_unverified", HERO)
        _ev(w, "consent", f"Same lab pays {HERO} directly, outside any request: ledger says {r['result']}",
            result=r["result"], tx=r["tx"], url=r["url"])
    d = pa.handle_request(LAB, "sleep_research", ["sleep.daily"], 11, study.CELL_PRICE)
    _ev(w, "consent", f"Week 11, outside the consented period: {d.status}", result=d.status, reason=d.reason)
    o = w.store.one("SELECT o.id, o.policy_snapshot, p.tx_hash FROM orders o JOIN payments p ON p.order_id=o.id "
                    "WHERE o.buyer_id=? AND o.seller_id=? AND p.tx_hash IS NOT NULL ORDER BY o.id LIMIT 1", LAB, HERO)
    if o:
        c = w.store.one("SELECT doc_hash FROM consents WHERE person_id=? AND buyer_id=?", HERO, LAB)
        _ev(w, "consent", f"Escrow for {HERO}'s contribution carries consent hash {c['doc_hash'][:16]} in its memo",
            **_tx(w, o["tx_hash"]))

    # ---- re-identification ----
    d = pa.handle_request(LAB, "sleep_research", list(QUASI_IDENTIFIERS), 6, study.CELL_PRICE)
    _ev(w, "reidentification", f"Birth date + postal code + rare diagnosis: {d.status}", result=d.status,
        reason=d.reason)
    _ev(w, "reidentification", "Same person, two studies, unlinkable IDs",
        study_a=pa.vault.pseudonym(LAB), study_b=pa.vault.pseudonym("org_other_study"))
    rows = pa.vault.extract(["sleep.daily"], 1, study=LAB)
    _ev(w, "reidentification", "Rows that leave the device: pseudonym, shifted day, requested item only",
        sample=rows[0], items=sorted(k for k in rows[0] if k not in ("person", "day")))
    sealed = w.store.one("SELECT b.sealed FROM bundles b JOIN orders o ON o.id=b.order_id WHERE o.buyer_id=? "
                         "ORDER BY b.order_id LIMIT 1", LAB)
    if sealed:
        try:
            SealedBox(PrivateKey.generate()).decrypt(sealed["sealed"])
            opened = True
        except CryptoError:
            opened = False
        _ev(w, "reidentification", "Operator tries to open a stored bundle with its own key: "
            + ("opened (bug)" if opened else "fails"), result="opened" if opened else "refused")

    # ---- withdrawal: decline, pause, revoke ----
    asking = [r for r in s.requests.values() if r["status"] in ("open", "partly_open") and r["person"] != HERO]
    if asking:
        p = asking[0]["person"]
        before = w.ledger.payment_count() if hasattr(w.ledger, "payment_count") else None
        study.participant_decline(w, p, asking[0]["id"])
        _ev(w, "withdrawal", f"1. {p} declines this round: nothing sent, no escrow", person=p,
            ledger_tx_added=(w.ledger.payment_count() - before) if before is not None else 0)
    auto = next((r["person"] for r in s.requests.values() if r["status"] == "contributed" and r["person"] != HERO), None)
    if auto:
        study.participant_pause(w, auto)
        d = w.cohort_people[auto].handle_request(LAB, "sleep_research", ["sleep.daily"], 7, study.CELL_PRICE)
        kept = w.store.one("SELECT COUNT(*) n FROM orders WHERE seller_id=? AND status='delivered'", auto)["n"]
        _ev(w, "withdrawal", f"2. {auto} pauses: next request {d.status}; {kept} delivered rounds and payments stay",
            person=auto, result=d.status)
    hero_req = next((r for r in s.requests.values() if r["person"] == HERO), None)
    if hero_req and not any(o.get("hold") for o in hero_req["orders"]):
        study.participant_approve(w, HERO, hero_req["id"], ["fatigue.survey", "heart_rate.daily"])
    r = study.participant_revoke(w, HERO)
    if r["clawback"]:
        _ev(w, "withdrawal", f"3. {HERO} revokes: data licence (MPT) clawed back", **r["clawback"])
    for oid in r["withheld"]:
        _ev(w, "withdrawal", f"3. {HERO} revokes: order {oid} key withheld", order_id=oid)
    for f in r["refunds"]:
        _ev(w, "withdrawal", f"3. Escrow for order {f['order_id']} refunded to the study after its deadline",
            tx=f["tx"], url=f["url"])
    if hero_req and r["licence"]:
        held = r["licence"]["held_by_study"]
        _ev(w, "withdrawal", f"Study still holds the licence after clawback: {held}", result=held)
    _ev(w, "withdrawal", "Kept: " + r["kept"])
    _payment_evidence(w, s)

    # ---- other domains ----
    robo = w.store.q("SELECT o.product_id, p.tx_hash FROM orders o JOIN payments p ON p.order_id=o.id "
                     "WHERE o.buyer_id='org_robodev' AND o.status='delivered'")
    for x in robo:
        _ev(w, "other_domains", f"Robot data {x['product_id']} settled (seller licence only, no personal consent)",
            **_tx(w, x["tx_hash"]))
    if not robo:
        _ev(w, "other_domains", "Run scene A (POST /api/run/a-guarded) to add its transactions here")
    return view(w)
