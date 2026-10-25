"""The settlement engine alone, on the mock ledger: no agents, no LLM (synthetic rows)."""
import pytest

from agentrail.db import Store
from agentrail.engine import BudgetExceeded, Engine, OrderConflict, OrderRequest
from agentrail.ledger import MockLedger
from agentrail.policy import ALLOW, BuyerMandate, Decision

XRP = 1_000_000
ROWS = [{"week": 1, "item": "sleep.daily", "value": 7.1}]


class Allow:
    def evaluate(self, *a, **k):
        return Decision(ALLOW, granted=["sleep.daily"])


@pytest.fixture
def e():
    L = MockLedger()
    e = Engine(Store(":memory:"), L)
    e.add_party("lab", "Lab (synthetic)", "organization", L.new_account("lab"))
    e.add_party("p1", "Participant (synthetic)", "person", L.new_account("p1"))
    e.policies["p1"] = Allow()
    e.set_mandate(BuyerMandate("lab", 5 * XRP, 3 * XRP, ["sleep_research"]))
    return e


def req(price=2 * XRP, settle="direct", slot="p1|w1"):
    return OrderRequest("lab", "p1", "p1", "personal.weekly", slot, "sleep_research", ["sleep.daily"], price, ROWS,
                        Decision(ALLOW, granted=["sleep.daily"]), settle=settle)


def test_order_is_idempotent_and_pays_once(e):
    a = e.place_order(req())
    assert e.process(a) == "delivered"
    assert e.place_order(req()) == a and e.ledger.payment_count() == 1
    with pytest.raises(OrderConflict):
        e.place_order(req(price=1 * XRP))


def test_budget_is_reserved_and_never_overspent(e):
    e.place_order(req(slot="a"))
    e.place_order(req(slot="b"))
    with pytest.raises(BudgetExceeded):
        e.place_order(req(slot="c"))


def test_escrowed_bundle_opens_with_the_key_from_the_ledger(e):
    oid = e.place_order(req(settle="escrow"))
    assert e.process(oid) == "delivered"
    assert e.open_bundle("lab", oid) == ROWS
    p = e.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)
    assert e.ledger.lookup(p["finish_tx"]).fulfillment
