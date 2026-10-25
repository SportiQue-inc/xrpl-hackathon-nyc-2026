"""Person -> institution -> sub-project: one consent, many sub-projects, payouts tagged (mock, synthetic)."""
import pytest

from agentrail import scenario, study, subprojects
from tests.llm_doubles import capable_needs


@pytest.fixture(scope="module")
def w():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    return w


def test_in_scope_settles_per_subproject_without_a_new_contract(w):
    rel = subprojects.of(w)
    t = rel.scope["data_types"][0]
    sp = rel.create("Night shift follow-up", rel.scope["purposes"][0], [t, "imaging.mri", "steps.daily"], 50_000_000, 2)
    by = {(r["item"], r["reason"]) for r in sp["routing"] if r["decision"] != "blocked"}
    assert (t, "in_scope") in by and ("imaging.mri", "T3") in by and ("steps.daily", "outside_scope") in by
    out = rel.run(sp["id"])
    assert out["settled"] and all(s["status"] == "delivered" for s in out["settled"])
    o = out["settled"][0]
    assert f"sub:{sp['id']}" in w.ledger.memo_of(o["escrow_create"])
    assert rel.institution()["subprojects"][0]["paid"] > 0


def test_t3_and_outside_scope_wait_for_the_person(w):
    rel = subprojects.of(w)
    sid = rel.institution()["subprojects"][0]["id"]
    pid = next(iter(rel.consents))
    view = rel.relationship(pid)
    assert {p["item"] for p in view["pending"]} >= {"imaging.mri", "steps.daily"}
    rel.decide(pid, sid, "steps.daily", True)
    assert rel.route(rel.subprojects[sid], pid, "steps.daily") == ("auto", "rule")


def test_sensitive_approval_covers_only_one_delivery_round(w, monkeypatch):
    rel = subprojects.of(w)
    pid = next(iter(rel.consents))
    sp = rel.create("Fresh MRI approval", "sleep_research", ["imaging.mri"], 50_000_000, 2)
    monkeypatch.setattr(w.cohort_people[pid].vault, "extract", lambda *args, **kwargs:
                        [{"person": "synthetic-mri-participant", "imaging.mri": "synthetic-image-hash"}])
    monkeypatch.setitem(w.cohort_people[pid].vault.by_item, "imaging.mri",
                        w.cohort_people[pid].vault.by_item["sleep.daily"])
    rel.decide(pid, sp["id"], "imaging.mri", True)
    first = rel.run(sp["id"])
    assert any(row["person"] == pid and row["status"] == "delivered" for row in first["settled"])
    assert rel.route(rel.subprojects[sp["id"]], pid, "imaging.mri") == ("ask", "T3")
    assert not rel.run(sp["id"])["settled"]


def test_no_relationship_means_blocked(w):
    rel = subprojects.of(w)
    sp = rel.subprojects["sp-1"]
    outsider = next(p for p in w.cohort_people if p not in rel.consents)
    assert rel.route(sp, outsider, rel.scope["data_types"][0]) == ("blocked", "rule")
    rel.consent(outsider)
    assert rel.route(sp, outsider, rel.scope["data_types"][0])[0] == "auto"


def test_a_pause_stops_the_next_subproject_delivery(w):
    rel = subprojects.of(w)
    pid = next(p for p in rel.consents if rel.route(rel.subprojects["sp-1"], p, rel.scope["data_types"][0])[0] == "auto")
    study.participant_pause(w, pid)
    assert rel.route(rel.subprojects["sp-1"], pid, rel.scope["data_types"][0]) == ("blocked", "rule")
    out = rel.run("sp-1")
    assert pid not in {s["person"] for s in out["settled"]}


def test_scope_and_relationships_follow_the_study_when_read_before_it_starts():
    w = scenario.build_world("mock", ":memory:")
    rel = subprojects.of(w)                       # the page asks before the study reads its gaps
    assert rel.scope["data_types"] and not rel.consents
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    sp = rel.create("After send", rel.scope["purposes"][0], [rel.scope["data_types"][0]], 50_000_000, 1)
    assert rel.consents and any(r["decision"] == "auto" for r in sp["routing"])


def test_a_subproject_inside_the_agreed_protocol_needs_no_ask_whatever_the_week_gaps(w):
    rel = subprojects.of(w)
    assert set(subprojects.PROTOCOL_ITEMS) <= set(rel.scope["data_types"])
    sp = rel.create("Protocol only", rel.scope["purposes"][0], ["heart_rate.daily", "sleep.daily"], 50_000_000, 2)
    asked = [r for r in sp["routing"] if r["decision"] == "ask"]
    assert not asked and any(r["decision"] == "auto" for r in sp["routing"])


def test_a_narrowed_consent_sends_the_left_out_items_back_to_the_person(w):
    rel = subprojects.of(w)
    pid = sorted(w.cohort_people)[-1]
    keep, left = rel.scope["data_types"][0], rel.scope["data_types"][1]
    rel.consent(pid, [keep])
    sp = rel.subprojects[rel.create("Narrowed", rel.scope["purposes"][0], [keep, left], 50_000_000, 1)["id"]]
    assert rel.route(sp, pid, keep) == ("auto", "in_scope")
    assert rel.route(sp, pid, left) == ("ask", "narrowed")
    with pytest.raises(ValueError):
        rel.consent(pid, ["imaging.mri"])


def test_the_same_items_for_a_new_purpose_go_back_to_the_person(w):
    rel = subprojects.of(w)
    pid = next(p for p in rel.consents if "items" not in rel.consents[p] and not rel._withdrawn(p))
    t = rel.scope["data_types"][0]
    sp = rel.subprojects[rel.create("Marketing reuse", "product_marketing", [t], 50_000_000, 1)["id"]]
    assert rel.route(sp, pid, t) == ("ask", "outside_scope")
