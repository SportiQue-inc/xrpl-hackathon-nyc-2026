"""Act 1 node-network replay: built only from the engine's logs (mock ledger, synthetic data)."""
from agentrail import network_view
from agentrail.market import acts


def test_network_replays_every_trade_and_the_path_to_one_settled_and_one_refused():
    ex = acts.act1()["exchange"]
    d = network_view.build(ex)
    assert len(d["nodes"]) == len(ex.accounts) and len(d["events"]) == len(ex.trades)
    assert d["book"]["listings"] > 100 and d["book"]["tx"]
    ok, no = d["spotlight"]
    keys = [s["k"] for s in ok["steps"]]
    assert keys[:5] == ["1. Need formed", "2. Offer book queried", "3. Fan-out: sample checks", "4. Compared",
                        "5. Negotiated"]
    assert keys[-2:] == ["6. Seller's agent decides", "7. Escrow and key reveal"]
    assert len(ok["sampled"]) >= 5 and ok["top"][0]["s"] == ok["s"]
    assert len({t["score"] for t in ok["top"]}) >= 2          # a real choice, not a tie
    assert next(s for s in ok["steps"] if s["k"].startswith("6"))["v"].startswith("SELL")
    assert next(s for s in no["steps"] if s["k"].startswith("6"))["v"].startswith("BLOCK")
    assert no["steps"][-1]["v"] == "nothing created, nothing paid"
    assert all(s["by"] in ("engine rule", "LLM", "ledger", "ledger + engine") for s in ok["steps"])
    html = network_view.render(d)
    assert "/*DATA*/null" not in html and "synthetic data" in html
