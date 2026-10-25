"""The phone is off; the hosted agent executes only what the person signed."""
import pytest

from agentrail.vault.delegation import HostedAgent, Phone
from agentrail.vault.keys import SoftPasskey

S = [{"tier": "T1", "purpose": "sleep_research", "inst_class": "academic"}]


def setup(**k):
    now = [1000.0]
    phone = Phone("P-1", SoftPasskey(b"x" * 32).root("P-1"))
    agent = HostedAgent(phone.public, clock=lambda: now[0])
    g, wrapped = phone.delegate(agent.public, k.pop("scopes", S), until=5000, budget_drops=100, **k)
    assert agent.install(g, wrapped) is None
    return phone, agent, now


def req(tier="T0", purpose="sleep_research", cls="academic", price=10, t="t1"):
    return {"trade": t, "tier": tier, "purpose": purpose, "inst_class": cls, "price_drops": price}


def test_offline_trade_within_grant():
    _, a, _ = setup()
    r = a.handle(req("T1"))
    assert r["status"] == "executed" and "within the grant you signed" in r["why"]


def test_out_of_scope_is_queued():
    _, a, _ = setup()
    assert a.handle(req(purpose="product_development"))["status"] == "needs_owner"
    assert a.handle(req("T2"))["status"] == "needs_owner"
    assert len(a.queue) == 2


def test_t3_never_delegated():
    with pytest.raises(ValueError):
        setup(scopes=[{"tier": "T3", "purpose": "x", "inst_class": "academic"}])
    _, a, _ = setup()
    assert a.handle(req("T3"))["why"] == "T3 needs a fresh Touch ID every time"


def test_t2_needs_opt_in():
    with pytest.raises(ValueError):
        setup(scopes=[{"tier": "T2", "purpose": "x", "inst_class": "academic"}])
    _, a, _ = setup(scopes=[{"tier": "T2", "purpose": "x", "inst_class": "academic"}], t2_opt_in=True)
    assert a.handle(req("T2", purpose="x"))["status"] == "executed"


def test_budget_and_time():
    _, a, now = setup()
    for i in range(10):
        assert a.handle(req(t=f"t{i}"))["status"] == "executed"
    assert a.handle(req(t="t11"))["why"] == "delegated budget reached"
    _, a, now = setup()
    now[0] = 6000
    assert a.handle(req())["why"] == "delegation expired"


def test_revocation_stops_it_and_old_grant_rejected():
    phone, a, _ = setup()
    old_g, old_w = phone.delegate(a.public, S, until=5000, budget_drops=100)
    assert a.install(old_g, old_w) is None
    assert a.apply_revocation(phone.revoke()) is None
    assert a.handle(req())["status"] == "needs_owner"
    assert a.install(old_g, old_w) == "stale grant version"


def test_forged_grant_rejected():
    phone, a, _ = setup()
    g, w = Phone("P-1", b"y" * 32).delegate(a.public, S, until=9999, budget_drops=10**9)
    g.version = 99
    assert a.install(g, w) == "grant not signed by the owner's device"
