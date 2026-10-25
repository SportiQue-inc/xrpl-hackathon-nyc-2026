"""Owner-signed delegation (Verifiable Intent L1 -> L2 -> L3) checked right before money moves."""
import time

import pytest

from agentrail import mandate, scenario, study
from agentrail.cohort import HERO
from tests.llm_doubles import capable, capable_needs

ORDER = {"content_hash": "c" * 64, "invoice_id": "I" * 64, "amount_drops": 2_000_000, "payee_id": "P-1",
         "order_id": 1, "purpose": "sleep_research"}


@pytest.fixture
def chain():
    c = mandate.MandateChain("org_lab")
    c.issue(100_000_000, 3_000_000, 30_000_000, ["sleep_research"], ["P-1"])
    return c


def test_valid_chain_passes(chain):
    l3 = chain.sign_order(ORDER)
    assert mandate.verify(chain.l1, chain.l2, l3, chain.issuer_pub, ORDER, 0) == (True, "ok")


def test_agent_signed_order_above_the_owners_limit_is_refused(chain):
    big = {**ORDER, "amount_drops": 5_000_000}          # e.g. an LLM proposal; the agent key signs it anyway
    ok, why = mandate.verify(chain.l1, chain.l2, chain.sign_order(big), chain.issuer_pub, big, 0)
    assert not ok and "per-transaction max" in why
    ok, why = mandate.verify(chain.l1, chain.l2, chain.sign_order(ORDER), chain.issuer_pub, ORDER, 29_000_000)
    assert not ok and "total" in why


def test_forged_delegation_is_refused(chain):
    forger = mandate.MandateChain("org_lab")            # different owner key, generous limits
    forger.l1 = chain.l1
    forger.issue(100_000_000, 99_000_000, 99_000_000, ["sleep_research"], None)
    forger.l1 = chain.l1                                  # keep the real institution credential
    from x402_xrpl.vi import sign_l2_delegation
    forger.l2 = sign_l2_delegation(owner_private_jwk=forger.owner_key, agent_public_jwk=forger.agent_pub,
                                   agent_kid=forger.agent_key["kid"], l1_presentation=chain.l1, audience="agentrail",
                                   constraints={"per_transaction_max": 99_000_000, "total_max": 99_000_000,
                                                "allowed_purposes": ["sleep_research"], "allowed_payees": ["*"]})
    ok, why = mandate.verify(chain.l1, forger.l2, forger.sign_order(ORDER), chain.issuer_pub, ORDER, 0)
    assert not ok and "owner key" in why


def test_expired_delegation_is_refused(chain):
    old = mandate.MandateChain("org_lab")
    old.issue(100_000_000, 3_000_000, 30_000_000, ["sleep_research"], ["P-1"], ttl_s=60, now=int(time.time()) - 3600)
    ok, why = mandate.verify(old.l1, old.l2, old.sign_order(ORDER), old.issuer_pub, ORDER, 0)
    assert not ok and "expired" in why


def test_signed_order_must_match_the_payment(chain):
    l3 = chain.sign_order(ORDER)
    ok, why = mandate.verify(chain.l1, chain.l2, l3, chain.issuer_pub, {**ORDER, "payee_id": "P-2"}, 0)
    assert not ok


def test_raised_budget_row_without_owner_signature_is_refused_by_the_engine():
    w = scenario.build_world("mock", ":memory:")
    w.robot_buyer.propose = capable
    # The mandates row is raised behind the owner's back (bug, or a hostile agent with DB access).
    with w.store.tx() as c:
        c.execute("UPDATE mandates SET per_order_limit_drops=99000000, total_drops=999000000 "
                  "WHERE buyer_id='org_robodev'")
    w.engine.mandate_chains["org_robodev"].issue(100_000_000, 15_000_000, 50_000_000, ["commercial_training"],
                                                 w.engine.mandate_chains["org_robodev"].payees)
    r = scenario.scene_a(w)
    blocked = w.store.q("SELECT note FROM orders WHERE buyer_id='org_robodev' AND status='blocked'")
    assert blocked and "mandate check failed" in blocked[0]["note"] and "per-transaction max" in blocked[0]["note"]


def test_payments_carry_the_signed_order_hash():
    w = scenario.build_world("mock", ":memory:")
    w.robot_buyer.propose = capable
    scenario.scene_a(w)
    memos = [t.get("Memo", "") for t in w.ledger.txs.values() if t.get("TransactionType") in ("Payment", "EscrowCreate")
             and "order:" in (t.get("Memo") or "")]
    assert memos and all("|mandate:" in m for m in memos)


def test_study_escrows_need_the_pi_signature():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    v = study.send(w)
    assert v["settlement"]["paid_xrp"] > 0
    rows = w.store.q("SELECT verdict FROM mandate_actions")
    assert rows and all(r["verdict"] == "ok" for r in rows)
