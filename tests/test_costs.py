"""Running cost per participant-week (mock ledger, synthetic data)."""
from agentrail import costs, scenario, study
from tests.llm_doubles import capable_needs


def test_cost_summary_counts_ledger_and_llm_per_side():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    c = costs.summarize(w)
    assert set(c["llm"]) >= {"research", "participant", "model"}
    assert c["ledger"]["txs"] == len(w.ledger.txs) and c["ledger"]["fee_drops"] == 10 * c["ledger"]["txs"]
    assert c["ledger"]["reserve_tied_xrp"] == len(w.ledger.escrows) * 0.2
    assert c["participant_weeks"] > 0
    assert c["per_participant_week"]["ledger_txs"] == round(c["ledger"]["txs"] / c["participant_weeks"], 2)
    assert "Per participant-week" in costs.line(c)
