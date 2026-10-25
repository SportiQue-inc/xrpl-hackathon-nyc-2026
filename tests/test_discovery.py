"""Need formation, the shared offer book anchored on the ledger, scoring and negotiation (mock ledger,
synthetic data)."""
from agentrail.ledger.mock import MockLedger
from agentrail.market import acts, discovery
from agentrail.market.exchange import quote


def _need(propose=None, budget=2_000_000):
    return discovery.form_need("P-024", ["sleep.daily"], ["sleep.daily", "spo2.night", "mood.score"], "spo2.night",
                               1, 3, budget, 3, quote, propose)


def test_need_comes_from_the_gap_and_the_budget_by_rule():
    n = _need()
    assert n["source"] == "rules" and n["columns"] == ["spo2.night"]
    assert n["gap"] == ["spo2.night", "mood.score"] and "sleep.daily" in n["holds"]
    assert n["max_price_drops"] <= n["budget_per_item_drops"]


def test_llm_need_is_used_only_inside_the_gap_and_the_budget():
    ok = _need(lambda s, p: {"columns": ["spo2.night"], "weeks": 2, "min_grade": "B", "max_price_drops": 9000,
                             "why": "night oxygen is the gap for my sleep model"})
    assert ok["source"] == "llm" and ok["weeks"] == 2 and ok["min_grade"] == "B"
    assert ok["max_price_drops"] == 9000 and ok["why"].startswith("night oxygen")
    bad = _need(lambda s, p: {"columns": ["sleep.daily"], "weeks": 40, "max_price_drops": 10 ** 9, "why": "x"},
                budget=100_000)
    assert bad["columns"] == ["spo2.night"] and bad["weeks"] == 1
    assert bad["max_price_drops"] <= bad["budget_per_item_drops"] and len(bad["checks"]) == 3


def test_offer_book_root_is_on_the_ledger_and_unlisted_offers_are_ignored():
    led = MockLedger()

    class DS:
        def __init__(self, i):
            self.id, self.columns, self.weeks = f"d{i}", ["sleep.daily"], 2

    offers = [{"seller": f"S{i}", "dataset": DS(i), "cert": {"root": f"r{i}"}} for i in range(5)]
    book = discovery.OfferBook(led, led.new_account("reg"), led.new_account("sink"))
    r = book.publish(offers[:4])
    assert r["listings"] == 4 and led.lookup(r["tx"]).invoice_id == r["root"].upper()
    assert all(book.anchored(o) for o in offers[:4]) and not book.anchored(offers[4])
    ids = sorted(book.anchored_ids)
    assert all(discovery.verify(i, discovery.proof(ids, i), book.root) for i in ids)
    assert not discovery.verify("f" * 64, discovery.proof(ids, ids[0]), book.root)


def test_scoring_prefers_quality_price_and_track_record():
    class DS:
        id = "d"
    need = {"max_price_drops": 12000}
    a = discovery.score({"seller": "A", "dataset": DS, "grade": "A"}, 10000, need, (5, 0))
    c = discovery.score({"seller": "C", "dataset": DS, "grade": "C"}, 6000, need, (0, 3))
    assert a["score"] > c["score"] and a["parts"]["track"] > c["parts"]["track"]
    over = discovery.score({"seller": "X", "dataset": DS, "grade": "A"}, 20000, need, (0, 0))
    assert over["over_ceiling"] and over["parts"]["price"] == 0


def test_negotiation_meets_between_bid_and_ask_or_walks_away():
    d = discovery.negotiate(10000, 12000, (3, 0))
    assert d["deal"] and 9000 <= d["price_drops"] <= 10000 and len(d["rounds"]) >= 2
    assert d["rounds"][0]["bid"] == 8000 and d["rounds"][0]["counter"] == 10000
    no = discovery.negotiate(10000, 5000, (0, 0))
    assert not no["deal"] and "floor" in no["why"]


def test_act1_logs_the_whole_path_from_need_to_one_trade():
    r = acts.act1()
    assert r["offer_book"]["tx"] and r["offer_book"]["listings"] > 100
    n = next(x for x in r["needs"] if x["fills"])
    d = n["discovery"]
    assert n["plan"]["gap"] and n["plan"]["source"] in ("rules", "llm")
    assert d["anchored_root"] == r["offer_book"]["root"] and d["listed"] >= len(d["ranked"])
    assert sum(d["dropped"].values()) > 0 and len(d["sampled"]) >= len(d["ranked"]) >= 1
    top = d["ranked"][0]
    assert top["negotiation"]["deal"] and top["outcome"] in ("settled", "settled_unfit")
    t = next(f for f in n["fills"] if f["seller"] == top["seller"])
    assert t["price_drops"] == top["negotiation"]["price_drops"] <= top["ask_drops"]
    assert d["explanation"]["why"] and d["explanation"]["source"] in ("rules", "llm")


def test_llm_explains_but_cannot_invent_candidates():
    ranked = [{"seller": "S1", "grade": "A", "ask_drops": 1, "score": 0.9, "parts": {"quality": 1, "price": 1, "track": 1},
               "over_ceiling": False}]
    need = {"columns": ["c"], "weeks": 1, "max_price_drops": 2}
    ok = discovery.explain("n", need, ranked, ["S1"], lambda s, p: {"why": "best grade", "others": {}})
    assert ok["source"] == "llm" and ok["why"] == "best grade"
    bad = discovery.explain("n", need, ranked, ["S1"], lambda s, p: {"why": "x", "others": {"S9": "made up"}})
    assert bad["source"] == "rules"
