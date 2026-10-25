from fastapi.testclient import TestClient

from agentrail.catalog import explain
from agentrail.web import app


def _run(preset):
    return explain.explain(explain.PRESETS[preset])


def test_routine_data_inside_her_grant_is_handled_by_the_agent():
    r = _run("steps_hospital")
    assert r["decision"] == "auto" and r["tier"] == "T0"
    assert [s["state"] for s in r["steps"]] == ["pass", "pass", "pass", "pass"]


def test_same_data_for_a_new_purpose_comes_back_to_her():
    r = _run("same_new_purpose")
    assert r["decision"] == "gate"
    assert {s["name"]: s["state"] for s in r["steps"]}["Her standing scope"] == "ask"


def test_mri_always_asks_even_from_a_trusted_hospital():
    r = _run("mri_irb")
    assert r["decision"] == "gate" and r["tier"] == "T3"
    assert {s["name"]: s["state"] for s in r["steps"]}["Sensitivity tier"] == "ask"


def test_mri_without_ethics_approval_is_refused_before_asking():
    r = _run("mri_no_irb")
    assert r["decision"] == "refused"
    assert r["steps"][0]["state"] == "fail" and all(s["state"] == "skip" for s in r["steps"][1:])


def test_payout_curve_runs_from_50_to_90():
    assert [w["at_delivery_pct"] for w in explain.payout_curve(6)] == [50, 60, 70, 80, 90, 90]


def test_routes_are_public_and_validate():
    c = TestClient(app)
    assert c.get("/api/agent/explain/presets").status_code == 200
    body = {k: v for k, v in explain.PRESETS["genome_abroad"].items() if k != "label"}
    ok = c.post("/api/agent/explain", json=body)
    assert ok.status_code == 200 and ok.json()["decision"] in ("gate", "refused")
    assert c.post("/api/agent/explain", json={"columns": ["nope"]}).status_code == 400
