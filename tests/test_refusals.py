from agentrail import boundaries, refusals, scenario, study
from agentrail.cohort import HERO
from tests.llm_doubles import capable_needs


def world():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    w.boundary_evidence = {}
    return w


def test_agent_refuses_expired_approval_outside_consent_and_planted_instruction():
    w = world()
    rows = refusals.run(w, lambda i, l, **k: boundaries._ev(w, i, l, **k), propose=refusals.hijacked)
    steps = [r for r in rows if r["label"][:2] in ("1.", "2.", "3.")]
    assert len(steps) == 3
    assert all(r["ledger_writes"] == 0 for r in steps)
    assert steps[0]["result"] != "allow" and "expired" in steps[0]["label"]
    assert steps[2]["result"] == "refused" and "diagnosis.codes" in steps[2]["label"]
    # the approval is valid again afterwards
    from agentrail.scenario import ETHICS_CREDENTIAL
    lab, board = w.engine.party("org_sleeplab")["address"], w.engine.party("org_ethics")["address"]
    assert w.ledger.has_credential(lab, board, ETHICS_CREDENTIAL)


def test_llm_that_stays_inside_consent_is_accepted():
    w = world()
    r = refusals.bundle_fields(w.store, HERO, ["sleep.daily", "fatigue.survey"], ["sleep.daily"],
                               refusals.CLINIC_RECORD, lambda s, i: {"fields": ["sleep.daily"]})
    assert not r["refused"] and r["final"] == ["sleep.daily"]
