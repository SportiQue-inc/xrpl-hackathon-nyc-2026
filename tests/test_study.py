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
    assert study.study_view(w)["study"]["budget_xrp"] == 0


def test_gap_claims_show_llm_reading_next_to_code_verdict(w):
    v = study.study_view(w)
    claims = {c["item"]: c for c in v["proposal"]["claims"]}
    assert claims["fatigue.survey"]["kept_weeks"] == [3, 4, 5]
    hero = v["proposal"]["person_claims"][HERO]
    assert {(c["week"], c["item"]) for c in hero if c["verdict"] == "kept"} == {
        (3, "fatigue.survey"), (4, "fatigue.survey"), (5, "fatigue.survey"), (4, "heart_rate.daily")}


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


def test_participant_card_classifies_items_and_shows_ledger_badge(w):
    sent(w)
    card = study.participant_view(w, HERO)["requests"][0]
    cls = {i["item"]: i["class"] for i in card["items"]}
    assert cls == {"fatigue.survey": "approval", "heart_rate.daily": "auto"}
    assert card["institution"]["badges"][0]["kind"] == "ethics_review"
    assert [d["code"] for d in card["duo"]][:2] == ["DUO:0000006", "DUO:0000046"]


def test_preview_shows_only_requested_items_under_study_pseudonym(w):
    sent(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    p = study.preview(w, HERO, rid)
    assert p["rows"] and all(r["person"].startswith("S-") for r in p["rows"])
    assert all(set(r) <= {"person", "day", "fatigue.survey", "heart_rate.daily"} for r in p["rows"])


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
    c.post("/api/reset?ledger=mock")
    web._state["w"].robot_buyer.propose = capable_needs
    assert c.post("/api/study/goal", json={"goal": "back to 80% power"}).json()["spec_status"] == "draft"
    assert c.post("/api/study/approve", json={"signers": ["owner"]}).json()["engine_result"] == "tefBAD_QUORUM"
    assert c.post("/api/study/approve", json={"signers": ["owner", "compliance"]}).json()["ok"]
    c.post("/api/study/send")
    p = c.get(f"/api/p/{HERO}").json()
    rid = p["requests"][0]["id"]
    assert c.get(f"/api/p/{HERO}/preview", params={"request": rid}).json()["rows"]
    c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey"]})
    seen = c.get("/api/study").json()["contributions"]
    assert any(x["person"] == HERO and x["weeks"] == [3] for x in seen)     # the console sees it
    assert c.get("/api/events", params={"after": 0}).json()["last"] > 0
    oid = next(x["order_id"] for x in seen if x["status"] == "delivered")
    assert c.get(f"/api/study/bundle/{oid}").json()["hash_matches"]
    r = c.post(f"/api/p/{HERO}/revoke").json()
    assert r["clawback"] and r["refunds"]
