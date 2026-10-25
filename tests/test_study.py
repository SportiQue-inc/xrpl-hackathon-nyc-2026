"""Both sides of the health study on one engine, and the boundary checks (all synthetic)."""
import pytest
from fastapi.testclient import TestClient

from agentrail import boundaries, scenario, study, web
from agentrail.cohort import HERO
from agentrail.policy import DENY, NEEDS_APPROVAL
from tests.llm_doubles import capable_needs, hostile

LAB = study.LAB


@pytest.fixture
def w():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    return w


def sent(w):
    assert study.approve(w, ["owner", "compliance"])["ok"]
    return study.send(w)


def test_one_signer_cannot_release_the_study_budget(w):
    r = study.approve(w, ["owner"])
    assert r == {**r, "ok": False, "engine_result": "tefBAD_QUORUM"}
    assert r["ledger_response"]["engine_result"] == "tefBAD_QUORUM" and r["ledger_response"]["applied"] is False
    assert study.study_view(w)["study"]["budget_xrp"] == 0


def test_gap_claims_show_llm_reading_next_to_code_verdict(w):
    v = study.study_view(w)
    claims = {c["item"]: c for c in v["proposal"]["claims"]}
    assert claims["fatigue.survey"]["kept_weeks"] == [3, 4, 5]
    hero = v["proposal"]["person_claims"][HERO]
    assert {(c["week"], c["item"]) for c in hero if c["verdict"] == "kept"} == {
        (3, "fatigue.survey"), (4, "fatigue.survey"), (5, "fatigue.survey"), (4, "heart_rate.daily"),
        (2, "blood_pressure.daily"), (4, "blood_pressure.daily")}      # clinic visits, ethics credential held


def test_person_gap_claim_for_a_held_cell_is_removed(w):
    from agentrail.cohort import person_gaps
    bad = lambda system, payload: {"missing": [{"week": 1, "item": "sleep.daily", "reason": "looks thin"}]}
    out = person_gaps(w.store, LAB, w.coverage, HERO, bad)
    assert out[0]["verdict"] == "removed" and "already held" in out[0]["code_reason"]


def test_send_contributes_auto_items_and_raises_power(w):
    v = sent(w)
    assert v["heatmap"]["power"] > v["heatmap"]["power_before"]
    assert v["responses"]["auto"] > 0 and v["responses"]["approval"] > 0
    assert all(c["status"] == "delivered" for c in v["contributions"])


def test_repeating_send_keeps_the_same_requests_and_payments(w):
    first = sent(w)
    requests = len(w.study.requests)
    payments = len(w.store.q("SELECT * FROM payments"))
    again = study.send(w)
    assert again["spec_status"] == first["spec_status"] == "sent"
    assert len(w.study.requests) == requests
    assert len(w.store.q("SELECT * FROM payments")) == payments


def test_repeating_an_approved_goal_does_not_reset_its_budget_approval(w):
    assert study.approve(w, ["owner", "compliance"])["ok"]
    approvals = len(w.store.q("SELECT * FROM approvals"))
    budget = study.study_view(w)["study"]["budget_xrp"]
    assert study.set_goal(w, "", capable_needs)["spec_status"] == "approved"
    assert len(w.store.q("SELECT * FROM approvals")) == approvals
    assert study.study_view(w)["study"]["budget_xrp"] == budget


def test_study_and_participant_expose_the_actual_settlement_asset(w):
    from agentrail import units
    assert study.study_view(w)["study"]["asset"] == units.UNIT
    assert study.participant_view(w, HERO)["asset"] == units.UNIT


def test_participant_card_classifies_items_and_shows_ledger_badge(w):
    sent(w)
    card = study.participant_view(w, HERO)["requests"][0]
    cls = {i["item"]: i["class"] for i in card["items"]}
    assert cls == {"fatigue.survey": "approval", "heart_rate.daily": "auto", "blood_pressure.daily": "approval"}
    assert card["institution"]["badges"][0]["kind"] == "ethics_review"
    assert [d["code"] for d in card["duo"]][:2] == ["DUO:0000006", "DUO:0000046"]


def test_preview_shows_only_requested_items_under_study_pseudonym(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    p = study.preview(w, HERO, rid)
    assert p["rows"] and all(r["person"].startswith("S-") for r in p["rows"])
    assert all(set(r) <= {"person", "day", "fatigue.survey", "heart_rate.daily", "blood_pressure.daily"}
               for r in p["rows"])
    assert "sleep.daily" in p["not_included"]


def test_approve_contributes_and_issues_a_licence_then_revoke_claws_back_and_refunds(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    v = study.participant_approve(w, HERO, rid, ["fatigue.survey"])
    st = {c["weeks"][0]: c["status"] for c in v["contributions"] if "fatigue.survey" in c["items"]}
    assert st == {3: "delivered", 4: "delivered", 5: "escrowed"}       # week 5 held until the round closes
    assert v["licence"]["held_by_study"]
    r = study.participant_revoke(w, HERO)
    assert r["clawback"]["tx"] and r["withheld"] and r["refunds"][0]["tx"]
    assert r["licence"]["held_by_study"] is False and r["consent"]["status"] == "revoked"
    assert {c["weeks"][0]: c["status"] for c in r["contributions"] if "fatigue.survey" in c["items"]}[5] == "refunded"
    d = r["deletion"]
    assert d["bundles_destroyed"] >= 3 and len(d["confirmation_hash"]) == 64
    kinds = [e["kind"] for e in w.store.q("SELECT kind FROM events")]
    assert "deletion_confirmed" in kinds
    row = [x for x in study.study_view(w)["heatmap"]["rows"] if x["person"] == HERO][0]
    assert {c["s"] for c in row["cells"]} == {"withdrawn"}


def test_clawed_back_licence_alone_stops_the_key(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    study.participant_approve(w, HERO, rid, ["fatigue.survey"])
    lic = w.study.licences[HERO]
    w.ledger.clawback_licence(w.engine.party(HERO)["address"], w.engine.party(LAB)["address"], lic["mpt_id"])
    study.close_round(w)
    held = [c for c in study.participant_view(w, HERO)["contributions"] if c["weeks"] == [5]]
    assert held[0]["status"] == "withheld"


def test_licence_cannot_be_passed_on(w):
    sent(w)
    lic = w.study.licences[next(iter(w.study.licences))]
    assert w.ledger.transfer_licence(w.engine.party(LAB)["address"], w.engine.party("org_adtech")["address"],
                                     lic["mpt_id"]) == "tecNO_AUTH"


def test_new_purpose_waits_for_the_person(w):
    d = w.cohort_people[HERO].handle_request(LAB, "commercial_product_dev", ["sleep.daily"], 6, study.CELL_PRICE)
    assert d.status == NEEDS_APPROVAL and not d.granted


def test_quasi_identifier_combination_is_never_released(w):
    d = w.cohort_people[HERO].handle_request(LAB, "sleep_research", ["birth_date", "zip5"], 6, study.CELL_PRICE)
    assert d.status == DENY and "re-identification" in d.reason


def test_pseudonym_differs_per_study(w):
    v = w.cohort_people[HERO].vault
    assert v.pseudonym(LAB) != v.pseudonym("org_other") and v.day_shift(LAB) != 0


def test_three_withdrawals_on_one_study(w):
    v = boundaries.run(w)
    ev = {i["id"]: i["evidence"] for i in v["issues"]}
    labels = " ".join(e["label"] for e in ev["withdrawal"])
    assert "declines this round" in labels and "pauses" in labels and "clawed back" in labels
    assert any("refunded" in e["label"] for e in ev["withdrawal"])
    assert any(e.get("result") == "refused" for e in ev["reidentification"])


def test_hostile_llm_cannot_widen_the_study(w):
    from agentrail.cohort import infer_needs
    n = infer_needs(w.store, LAB, w.coverage, ["sleep_research"], 40_000_000, True, hostile)
    assert n.budget_drops <= 40_000_000 and n.purpose == "sleep_research"


def test_api_drives_both_pages_on_one_engine():
    c = TestClient(web.app)
    tok = lambda sub: {"Authorization": "Bearer " + c.post(f"/api/dev/login/{sub}").json()["access_token"]}
    c.post("/api/reset?ledger=mock", headers=tok("operator"))
    web._state["w"].robot_buyer.propose = capable_needs
    R, P, O = tok("researcher@org_sleeplab"), tok(HERO), tok("operator")
    assert c.post("/api/study/goal", json={"goal": "back to 80% power"}, headers=R).json()["spec_status"] == "draft"
    assert c.post("/api/study/approve", json={"signers": ["owner"]}, headers=O).json()["engine_result"] == "tefBAD_QUORUM"
    assert c.post("/api/study/approve", json={"signers": ["owner", "compliance"]}, headers=O).json()["ok"]
    c.post("/api/study/send", headers=R)
    p = c.get(f"/api/p/{HERO}", headers=P).json()
    rid = p["requests"][0]["id"]
    assert c.get(f"/api/p/{HERO}/preview", params={"request": rid}, headers=P).json()["rows"]
    c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey"]}, headers=P)
    seen = c.get("/api/study", headers=R).json()["contributions"]
    assert any(x["pseudonym"] == p["person"]["study_pseudonym"] and x["weeks"] == [3] for x in seen)
    assert all("person" not in x for x in seen)                           # the console sees the pseudonym only
    assert c.get("/api/events", params={"after": 0}, headers=R).json()["last"] > 0
    oid = next(x["order_id"] for x in seen if x["status"] == "delivered")
    assert c.get(f"/api/study/bundle/{oid}", headers=R).json()["hash_matches"]
    r = c.post(f"/api/p/{HERO}/revoke", headers=P).json()
    assert r["clawback"] and r["refunds"]


def test_unverified_institution_gets_no_answer_and_its_direct_payment_is_refused(w):
    w.engine.add_party("org_x", "Unverified", "organization", w.ledger.new_account("org_x"))
    d = w.cohort_people[HERO].handle_request("org_x", "sleep_research", ["sleep.daily"], 6, study.CELL_PRICE)
    assert d.status == DENY and "verified-organization" in d.reason
    assert study.direct_payment_attempt(w, "org_x", HERO)["result"] == "tecNO_PERMISSION"
    assert study.direct_payment_attempt(w, LAB, HERO)["result"] == "tesSUCCESS"


def test_clinic_record_needs_the_person_by_name_and_the_agent_pays_the_export_fee(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    v = study.participant_approve(w, HERO, rid, ["fatigue.survey"])           # blood pressure not ticked
    assert not any("blood_pressure.daily" in c["items"] for c in v["contributions"]) and not v["export_fees"]
    v = study.participant_approve(w, HERO, rid, ["fatigue.survey", "blood_pressure.daily"])
    bp = [c for c in v["contributions"] if "blood_pressure.daily" in c["items"]]
    assert {c["weeks"][0]: c["status"] for c in bp} == {2: "delivered", 4: "escrowed"}   # last week held for the round
    assert len(v["export_fees"]) == 2 and all(f["ok"] for f in v["export_fees"])


def test_per_person_reading_drops_items_no_source_holds(w):
    from agentrail.cohort import person_gaps
    claim = lambda system, payload: {"missing": [{"week": 6, "item": "blood_pressure.daily", "reason": "x"}]}
    out = person_gaps(w.store, LAB, w.coverage, HERO, claim, {6: ["sleep.daily"]}, True)
    assert out[0]["verdict"] == "removed" and "sources" in out[0]["code_reason"]


def test_a_participant_cannot_answer_someone_elses_request(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    other = next(p for p in w.cohort_people if p != HERO)
    for call in (lambda: study.preview(w, other, rid), lambda: study.participant_decline(w, other, rid),
                 lambda: study.participant_approve(w, other, rid, ["fatigue.survey"])):
        with pytest.raises(KeyError):
            call()


def test_revoked_consent_cannot_be_flipped_back(w):
    sent(w)
    study.participant_revoke(w, HERO)
    with pytest.raises(ValueError):
        study.participant_pause(w, HERO, resume=True)
    assert w.store.one("SELECT status FROM consents WHERE person_id=? AND buyer_id=?", HERO, LAB)["status"] == "revoked"


def test_unknown_signer_name_is_refused(w):
    r = study.approve(w, ["owner", "intern"])
    assert r["ok"] is False and r["engine_result"] == "unknown_signer"


def test_withdrawn_participants_bundle_is_gone(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    v = study.participant_approve(w, HERO, rid, ["fatigue.survey"])
    oid = next(c["order_id"] for c in v["contributions"] if c["status"] == "delivered")
    study.participant_revoke(w, HERO)
    with pytest.raises(study.Gone):
        study.open_bundle(w, oid)


def test_pseudonym_needs_the_vault_secret(w):
    import hashlib
    v = w.cohort_people[HERO].vault
    assert v.pseudonym(LAB) != "S-" + hashlib.sha256(f"{LAB}|{HERO}".encode()).hexdigest()[:8]
    assert v.pseudonym(LAB) == v.pseudonym(LAB)


def test_compliance_runs_again_before_delivery(w):
    pa = w.cohort_people[HERO]
    pa.policy.compliance.verified_check = lambda buyer: False      # credential lost after the order
    d = pa.policy.evaluate(LAB, "sleep_research", ["sleep.daily"], study.CELL_PRICE, 4, for_delivery=True)
    assert d.status == "deny"


def test_no_budget_or_request_without_an_ethics_approval_number():
    w = scenario.build_world("mock", ":memory:")
    s = study.ensure(w)
    study.set_goal(w, "", capable_needs)
    s.irb_approval = ""
    assert "IRB" in study.approve(w, ["owner", "compliance"])["message"]
    s.irb_approval = "IRB-2026-001"
    assert study.approve(w, ["owner", "compliance"])["ok"]
    rid = study.send(w) and next(iter(s.requests))
    assert study.participant_view(w, s.requests[rid]["person"])["requests"][0]["ethics_approval"] == "IRB-2026-001"


def test_every_later_access_rereads_the_licence_on_the_ledger(w):
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    study.participant_approve(w, HERO, rid, ["fatigue.survey", "heart_rate.daily"])
    oid = next(o["order_id"] for o in w.study.requests[rid]["orders"]
               if w.store.one("SELECT status FROM orders WHERE id=?", o["order_id"])["status"] == "delivered")
    r = study.open_bundle(w, oid)
    assert r["fulfillment_on_ledger"] and r["licence"]["held"] and "DUO:0000046" in r["licence"]["duo"]
    with pytest.raises(PermissionError, match="outside_licence"):
        study.open_bundle(w, oid, use="commercial_product_dev")      # NCU on the ledger refuses it
    lic = w.study.licences[HERO]
    w.ledger.clawback_licence(w.engine.party(HERO)["address"], w.engine.party(study.LAB)["address"], lic["mpt_id"])
    with pytest.raises(PermissionError, match="licence_revoked"):
        study.open_bundle(w, oid)


def test_ethics_credential_expires_or_is_withdrawn_on_the_ledger(w):
    from agentrail.scenario import ETHICS_CREDENTIAL
    pa = w.cohort_people[HERO]
    L, lab, board = w.ledger, w.engine.party(study.LAB)["address"], w.engine.party("org_ethics")["address"]
    items = ["sleep.daily", "blood_pressure.daily"]
    assert pa.policy.compliance.check(study.LAB, "sleep_research", items)[0] == items
    L.delete_credential(board, lab, ETHICS_CREDENTIAL)
    assert pa.policy.compliance.check(study.LAB, "sleep_research", items)[0] == ["sleep.daily"]
    L.issue_credential(board, lab, ETHICS_CREDENTIAL, expiration=L.now() + 60)
    assert pa.policy.compliance.check(study.LAB, "sleep_research", items)[0] == items
    L.clock += 61
    assert pa.policy.compliance.check(study.LAB, "sleep_research", items)[0] == ["sleep.daily"]


def test_a_persons_weekly_escrows_are_created_together_or_not_at_all(w):
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    batches = [t for t in w.ledger.txs.values() if t.get("TransactionType") == "Batch"]
    assert batches and all(t["result"] == "tesSUCCESS" for t in batches)
    multi = [r for r in w.study.requests.values() if len(r["orders"]) > 1 and not any(o["hold"] for o in r["orders"])]
    oids = [o["order_id"] for o in multi[0]["orders"]]
    hashes = {w.store.one("SELECT tx_hash FROM payments WHERE order_id=?", o)["tx_hash"] for o in oids}
    inner = {h for b in batches for h in [__import__("hashlib").sha256(__import__("json").dumps(x, sort_keys=True)
                                                                         .encode()).hexdigest().upper() for x in b["RawTransactions"]]}
    assert hashes <= inner
    assert all(w.store.one("SELECT status FROM orders WHERE id=?", o)["status"] == "delivered" for o in oids)


def test_failed_batch_applies_nothing_and_orders_go_one_by_one():
    from agentrail.ledger import MockLedger
    L = MockLedger()
    a, b = L.new_account("a"), L.new_account("b")
    L.balances[a] = 3
    legs = [{"destination": b, "amount_drops": 2, "condition": "C", "cancel_after": 10, "memo": "m"}] * 2
    outer, hashes, _ = L.prepare_escrow_batch(a, legs)
    L.submit(outer)
    assert L.lookup(outer.tx_hash).success and not any(L.lookup(h).found for h in hashes) and L.balances[a] == 3


def test_participant_who_picked_a_stablecoin_has_their_agent_swap_what_it_was_paid(w):
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    study.participant_approve(w, HERO, rid, ["fatigue.survey", "heart_rate.daily"])
    sw = [x for x in w.study.swaps if x["person"] == HERO]
    assert sw and sw[0]["ok"] and float(sw[0]["delivered"]) > 0
    addr = w.engine.party(HERO)["address"]
    from agentrail.ledger.amm_terms import STABLE_CODE, STABLE_ISSUER
    assert w.ledger.ious[(addr, STABLE_CODE, STABLE_ISSUER)] == pytest.approx(sum(float(x["delivered"]) for x in sw))
    assert all(x["person"] == HERO for x in w.study.swaps)          # others kept XRP
    assert study.set_payout_currency(w, "P-002", "XRP")["payout_currency"] == "XRP"


def test_clinic_export_is_paid_over_real_http_402(w):
    from fastapi.testclient import TestClient
    from agentrail import clinic
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    clinic_addr = w.engine.party(study.CLINIC)["address"]
    before = w.ledger.balance_drops(clinic_addr)
    study._export_fee(w, w.cohort_people[HERO], ["blood_pressure.daily"])
    fees = [f for f in w.study.export_fees if f["ok"]]
    assert fees and all(f["http"] == [402, 200] and f["rail"].startswith("x402") for f in fees)
    assert w.ledger.balance_drops(clinic_addr) == before + clinic._cfg["fee"]
    c = TestClient(clinic.app)
    q = {"person": HERO, "items": "blood_pressure.daily", "nonce": "n1"}
    r = c.get("/export", params=q)
    assert r.status_code == 402 and r.json()["accepts"][0]["amount"] == str(clinic._cfg["fee"])
    payer = w.engine.party(HERO)["address"]
    tampered = {**r.json()["accepts"][0], "amount": "1"}
    bad = clinic.b64({"x402Version": 2, "accepted": tampered, "payload": {"signedTxBlob": "x", "invoiceId": "y"}})
    assert c.get("/export", params=q, headers={"PAYMENT-SIGNATURE": bad}).json()["error"] == \
        "payment_requirements_mismatch"
    hdr = clinic._payment_header(w.ledger, payer, r.json()["accepts"][0])
    ok = c.get("/export", params=q, headers={"PAYMENT-SIGNATURE": hdr})
    assert ok.status_code == 200 and ok.json()["receipt"]["success"] and "PAYMENT-RESPONSE" in ok.headers
    again = c.get("/export", params=q, headers={"PAYMENT-SIGNATURE": hdr})
    assert again.status_code == 402 and again.json()["error"] == "payment_already_used"


@pytest.mark.parametrize("network", ["mock", "testnet"])
def test_participant_reports_the_configured_ledger(w, monkeypatch, network):
    monkeypatch.setattr(w.ledger, "name", network)
    assert study.participant_view(w, HERO)["ledger"] == network


def test_clinic_export_fee_settles_in_xrp_when_orders_settle_in_a_token(w, monkeypatch):
    """Token mode: the ledger's amount parser only counts the settlement token, so an XRP fee read as
    'no amount' used to fail with not_settled:tesSUCCESS. The clinic now checks the delivered XRP."""
    import dataclasses
    from agentrail import clinic
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    real = w.ledger.lookup
    monkeypatch.setattr(w.ledger, "lookup", lambda h: dataclasses.replace(
        real(h), amount_drops=None, xrp_drops=real(h).amount_drops))
    n = len(w.study.export_fees)
    study._export_fee(w, w.cohort_people[HERO], ["blood_pressure.daily"])
    f = w.study.export_fees[n]
    assert f["ok"] and f["http"] == [402, 200], f
    assert clinic._cfg["fee"] > 0
