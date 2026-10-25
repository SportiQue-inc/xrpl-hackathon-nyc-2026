"""Act 1 node-network replay: built only from the trade log (mock ledger, synthetic data)."""
from agentrail import network_view
from agentrail.market import acts


def test_network_replays_every_trade_and_traces_one_settled_and_one_refused():
    ex = acts.act1()["exchange"]
    d = network_view.build(ex)
    assert len(d["nodes"]) == len(ex.accounts) and len(d["events"]) == len(ex.trades)
    ok, no = d["spotlight"]
    assert [s["k"] for s in ok["steps"]][:6] == ["Need", "Match", "Quality", "Provenance", "Scope and price", "Decision"]
    assert ok["steps"][5]["v"].startswith("SELL") and ok["steps"][6]["k"] == "Escrow and key reveal"
    assert no["steps"][5]["v"].startswith("BLOCK") and no["steps"][6]["v"] == "nothing created, nothing paid"
    html = network_view.render(d)
    assert "/*DATA*/null" not in html and "synthetic data" in html
