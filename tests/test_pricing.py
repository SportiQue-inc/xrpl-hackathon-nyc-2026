"""Who sets the price: settled prices on the ledger, supply and demand, inside owner bounds (mock, synthetic)."""
from agentrail.market import acts
from agentrail.market.exchange import quote, spec
from agentrail.market.pricing import PriceIndex, negotiate


def test_reference_starts_at_the_rate_card_then_follows_settled_prices():
    p = PriceIndex(quote, spec)
    card = quote(["sleep.daily"], 1, "A")
    assert p.reference(["sleep.daily"], 1, "A")["source"] == "rate card (seed)"
    for r in (0.7, 0.8, 0.9):
        p.record(["sleep.daily"], 1, "A", int(card * r))
    ref = p.reference(["sleep.daily"], 2, "A")          # two weeks compare through the ratio
    assert ref["n"] == 3 and abs(ref["price"] - quote(["sleep.daily"], 2, "A") * 0.8) <= 2


def test_ask_rises_with_demand_and_never_goes_under_the_owners_floor():
    p = PriceIndex(quote, spec)
    p.set_supply([{"dataset": type("D", (), {"columns": ["sleep.daily"]})()}] * 4)
    calm = p.ask(["sleep.daily"], 1, "A", 0.9, now_h=1)
    for _ in range(12):
        p.post(["sleep.daily"], 0.5)
    busy = p.ask(["sleep.daily"], 1, "A", 0.9, now_h=1)
    assert busy["ask"] > calm["ask"] and calm["ask"] >= calm["floor"]
    assert "needs in the last day" in busy["why"]


def test_buyer_never_pays_above_its_ceiling_and_seller_never_below_its_floor():
    deal = negotiate(1000, 950, (3, 0), floor=900, opening=800)
    assert deal["deal"] and 900 <= deal["price_drops"] <= 950
    assert not negotiate(1000, 850, (3, 0), floor=900, opening=800)["deal"]


def test_prices_move_with_supply_and_demand_in_the_market():
    from statistics import median
    base = median(h["ratio"] for v in acts.act1()["exchange"].pricing.history.values() for h in v)
    scarce = median(h["ratio"] for v in acts.act1(supply_share=0.5)["exchange"].pricing.history.values() for h in v)
    assert scarce > base


def test_the_conversation_names_the_market_reference():
    ex = acts.act1(rounds=1)["exchange"]
    said = [t for c in ex.contracts for t in c["turns"] if t["speaker"] == "seller" and t["message"].startswith("Listed at")]
    assert said and all("reference" in t["reasoning"] for t in said)
