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
