"""Live: the followed person's records go into a running UniQdata (local sandbox) and come back out
through the engine to a settled trade. Skipped unless UNIQDATA_PERSON names a person file made by
scripts/uniqdata_sandbox_person.py and that sandbox is up. Use a fresh person per run."""
import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("UNIQDATA_PERSON"), reason="no UniQdata sandbox person")


def test_uploaded_records_flow_from_uniqdata_to_a_settled_trade():
    from agentrail import scenario, study
    from agentrail.cohort import HERO
    from tests.llm_doubles import capable_needs

    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    before = study.my_data(w, HERO)
    up = study.upload_data(w, HERO, list(range(1, 9)), ["heart_rate.daily", "fatigue.survey", "sleep.daily",
                                                        "activity.daily", "blood_pressure.daily"])
    assert up["written"] > 0 and up["records"] > before["records"]
    held = {i["item"]: i for s in up["sources"] for i in s["items"]}
    assert {3, 4, 5} <= set(held["fatigue.survey"]["weeks"])

    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    pv = study.preview(w, HERO, rid)
    assert pv["from"]["system"] == "UniQdata" and pv["from"]["records"] > 0
    v = study.participant_approve(w, HERO, rid, ["fatigue.survey"])
    assert any(c["status"] == "delivered" for c in v["contributions"])
    kinds = [e["kind"] for e in w.store.q("SELECT kind FROM events")]
    assert "uniqdata_upload" in kinds and "uniqdata_read" in kinds
