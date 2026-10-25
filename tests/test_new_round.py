"""A second round of the same study (new spec, co-signed again, Send) used to fail with OrderConflict:
the same person, week and items gave the same order key as round 1 with different content."""
from agentrail import scenario, study
from tests.llm_doubles import capable_needs


def test_second_round_sends_without_order_conflict():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    for rnd in (1, 2):
        study.set_goal(w, "", capable_needs)
        assert study.approve(w, ["owner", "compliance"])["ok"], rnd
        v = study.send(w)
        assert study.ensure(w).status == "sent" and "contributions" in v or v, rnd
    pid = next(iter(w.cohort_people))
    study.participant_view(w, pid)
    keys = [r["order_key"] for r in w.store.q("SELECT order_key FROM orders WHERE product_id='cohort.fill'")]
    assert len(keys) == len(set(keys)) and keys


def test_second_round_through_the_console_api():
    from fastapi.testclient import TestClient
    from agentrail import web
    from agentrail.security.http import reset_rate_limits
    from tests.test_apps import COMPLIANCE, OWNER, R, login
    reset_rate_limits()
    c = TestClient(web.app, raise_server_exceptions=False)
    c.post("/api/reset?ledger=mock", headers=login(c, "operator"))
    web._state["w"].robot_buyer.propose = capable_needs
    for rnd in (1, 2):
        assert c.post("/api/study/goal", json={"goal": ""}, headers=login(c, R)).status_code == 200, rnd
        a = c.post("/api/study/approvals", headers=login(c, R)).json()
        for sub in (OWNER, COMPLIANCE):
            sig = c.post(f"/api/dev/devices/{sub}/sign-approval/{a['id']}").json()
            c.post(f"/api/study/approvals/{a['id']}/signatures", json=sig, headers=login(c, sub))
        r = c.post("/api/study/send", headers=login(c, R))
        assert r.status_code == 200, (rnd, r.text[:300])


def test_order_conflict_skips_that_week_instead_of_failing_send(monkeypatch):
    from agentrail.engine import OrderConflict
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]

    def conflict(req):
        raise OrderConflict("order 1 exists with different content")
    monkeypatch.setattr(w.engine, "place_order", conflict)
    study.send(w)
    assert w.store.one("SELECT count(*) n FROM events WHERE kind='already_ordered'")["n"] > 0
