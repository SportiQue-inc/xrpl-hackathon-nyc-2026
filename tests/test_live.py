from fastapi.testclient import TestClient

from agentrail import live, scenario, study
from agentrail.cohort import HERO
from tests.llm_doubles import capable_needs


def test_clawback_and_escrow_cancel_reach_the_live_feed_with_the_person():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    assert live.feed(w).since()["events"] == [] or all(e["person"] != HERO for e in live.feed(w).since()["events"])
    study.participant_revoke(w, HERO)
    ev = live.feed(w).since()["events"]
    claw = [e for e in ev if e["type"] == "Clawback"]
    assert claw and claw[-1]["person"] == HERO and claw[-1]["tx"]
    later = live.feed(w).since(ev[-1]["id"])["events"]
    assert later == []


def test_live_route_needs_the_study_team(monkeypatch):
    from agentrail import web
    c = TestClient(web.app)
    assert c.get("/api/study/live").status_code == 401
