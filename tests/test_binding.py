"""One paid order checked link by link: contract, stamps, escrow memo, K, bundle (mock ledger,
synthetic data)."""
import pytest
from agentrail import binding, scenario, study
from agentrail.contract import onledger
from tests.llm_doubles import capable_needs


@pytest.fixture(scope="module")
def w():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    onledger.run(w, 6, 4)
    return w


def _paid(w):
    o = next(o for o in w.contract_round.outcomes if (o.get("txs") or {}).get("escrow_finish"))
    return w.store.one("SELECT order_id FROM payments WHERE finish_tx=?", o["txs"]["escrow_finish"])["order_id"]


def test_every_link_points_at_the_same_bundle(w):
    c = binding.chain(w.engine, study.LAB, _paid(w))
    names = [s["step"] for s in c["steps"]]
    assert c["ok"], [s for s in c["steps"] if not s["ok"]]
    for n in ("bundle hash in the EscrowCreate memo", "contract hash in the memo", "SHA-256(K) equals the escrow condition",
              "opened bundle hashes to the memo's bundle hash", "manifest names this contract",
              "source stamps match the sealed records", "stamped records open with K and equal the delivered values"):
        assert n in names


def test_a_swapped_bundle_breaks_the_chain(w):
    oid = _paid(w)
    keep = w.store.one("SELECT bundle_hash FROM bundles WHERE order_id=?", oid)["bundle_hash"]
    with w.store.tx() as c:
        c.execute("UPDATE bundles SET bundle_hash=? WHERE order_id=?", ("0" * 64, oid))
    try:
        r = binding.chain(w.engine, study.LAB, oid)
        assert not r["ok"]
        assert not next(s for s in r["steps"] if s["step"] == "bundle hash in the EscrowCreate memo")["ok"]
    finally:
        with w.store.tx() as c:
            c.execute("UPDATE bundles SET bundle_hash=? WHERE order_id=?", (keep, oid))


def test_engine_order_key_alone_does_not_open_the_data():
    from agentrail.db import Store
    from agentrail.engine import Engine, OrderRequest
    from agentrail.ledger import MockLedger
    from agentrail.policy import ALLOW, BuyerMandate, Decision

    class Allow:
        def evaluate(self, *a, **k):
            return Decision(ALLOW, granted=["sleep.daily"])

    L = MockLedger()
    e = Engine(Store(":memory:"), L)
    e.add_party("lab", "Lab (synthetic)", "organization", L.new_account("lab"))
    e.add_party("p1", "Participant (synthetic)", "person", L.new_account("p1"))
    e.policies["p1"] = Allow()
    e.set_mandate(BuyerMandate("lab", 5_000_000, 3_000_000, ["sleep_research"]))
    oid = e.place_order(OrderRequest("lab", "p1", "p1", "personal.weekly", "p1|w1", "sleep_research", ["sleep.daily"],
                                     1_000_000, [{"week": 1, "value": 7.1}], Decision(ALLOW, granted=["sleep.daily"]),
                                     settle="escrow"))
    assert e.process(oid) == "delivered"
    c = binding.chain(e, "lab", oid)
    assert c["ok"] and next(s for s in c["steps"] if s["step"].startswith("K alone"))["ok"]


def test_proof_names_a_paid_trade(w):
    p = binding.proof(w)
    assert p["paid_trade"]["ok"] and "Proof of one trade" in binding.summary(p)


def test_proof_starts_with_the_budget_and_the_consent(w):
    t = binding.proof(w)["paid_trade"]
    budget, consent = t["steps"][:2]
    assert budget["step"] == "budget co-signed by 2 approvers" and budget["ok"] and budget["tx"]
    assert consent["step"] == "person's consent in force" and consent["ok"] and len(t["consent_hash"]) == 64
