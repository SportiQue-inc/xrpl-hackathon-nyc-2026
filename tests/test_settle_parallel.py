"""Settling people in parallel after the payouts (live ledgers) gives the same result as one at a time,
and COHORT_N sets the cohort size."""
from agentrail import scenario, study
from agentrail.cohort import HERO
from tests.llm_doubles import capable_needs


def _run(monkeypatch, workers):
    monkeypatch.setenv("SETTLE_WORKERS", str(workers))
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    v = study.send(w)
    hb = w.store.q("SELECT person, kind, amount_drops, status FROM holdbacks ORDER BY person, kind")
    orders = w.store.q("SELECT seller_id, status FROM orders ORDER BY seller_id, id")
    return ([dict(r) for r in hb], [dict(r) for r in orders], sorted(w.study.licences),
            v["heatmap"]["power"] if "heatmap" in v else None)


def test_parallel_settle_matches_sequential(monkeypatch):
    assert _run(monkeypatch, 1) == _run(monkeypatch, 8)


def test_cohort_n_sets_the_cohort_and_keeps_the_followed_participant(monkeypatch):
    monkeypatch.setenv("COHORT_N", "10")
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    assert len(w.cohort_people) == 11 and HERO in w.cohort_people
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    assert all(r["seller_id"] in w.cohort_people for r in w.store.q("SELECT seller_id FROM orders WHERE product_id='cohort.fill'"))
