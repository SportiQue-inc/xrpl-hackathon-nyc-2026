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


def test_escrow_deadline_counts_from_creation_not_from_the_order():
    """A slow ledger between order and EscrowCreate must not eat the window (Testnet runs 1-4:
    EscrowFinish landed after CancelAfter, tecNO_PERMISSION)."""
    L = MockLedger()
    e = Engine(Store(":memory:"), L)
    e.add_party("lab", "Lab (synthetic)", "organization", L.new_account("lab"))
    e.add_party("p1", "Participant (synthetic)", "person", L.new_account("p1"))
    e.policies["p1"] = Allow()
    e.set_mandate(BuyerMandate("lab", 5 * XRP, 3 * XRP, ["sleep_research"]))
    oid = e.place_order(req(settle="escrow"))
    placed = e.store.one("SELECT cancel_after FROM payments WHERE order_id=?", oid)["cancel_after"]
    L.clock += 900                                  # longer than the 600 s window
    assert e.process(oid) == "delivered"
    p = e.store.one("SELECT cancel_after, finish_tx FROM payments WHERE order_id=?", oid)
    assert p["cancel_after"] >= placed + 900 and L.lookup(p["finish_tx"]).success


def test_key_is_not_published_when_the_finish_could_land_after_the_deadline():
    """A late EscrowFinish fails but still puts K on the ledger; the engine must not sign it."""
    L = MockLedger()
    L.finish_margin_s = 60
    e = Engine(Store(":memory:"), L)
    e.add_party("lab", "Lab (synthetic)", "organization", L.new_account("lab"))
    e.add_party("p1", "Participant (synthetic)", "person", L.new_account("p1"))
    e.policies["p1"] = Allow()
    e.set_mandate(BuyerMandate("lab", 5 * XRP, 3 * XRP, ["sleep_research"]))
    oid = e.place_order(req(settle="escrow"))
    create = e._escrow_create

    def slow_create(o):                    # the escrow is created, then the ledger is slow to the finish
        ok = create(o)
        L.clock = e.store.one("SELECT cancel_after FROM payments WHERE order_id=?", o)["cancel_after"] - 30
        return ok
    e._escrow_create = slow_create
    e.process(oid)
    assert e.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)["finish_tx"] is None
    assert e.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "withheld"
    assert not any(t.get("TransactionType") == "EscrowFinish" for t in L.txs.values())


def test_token_settlement_amounts_round_trip():
    from agentrail.ledger.token_settle import TokenSettleMixin, code_of

    class T(TokenSettleMixin):
        issuer, code = "rIssuer", "USD"
    t = T()
    a = t._amount(1_250_000)
    assert (a.currency, a.issuer, a.value) == ("USD", "rIssuer", "1.25")
    assert t._parse_amount({"currency": "USD", "issuer": "rIssuer", "value": "1.25"}) == 1_250_000
    assert t._parse_amount({"currency": "USD", "issuer": "rOther", "value": "1.25"}) is None
    assert t._parse_amount("1250000") is None              # XRP never counts as a token payment
    assert code_of("RLUSD") == "524C555344000000000000000000000000000000"
