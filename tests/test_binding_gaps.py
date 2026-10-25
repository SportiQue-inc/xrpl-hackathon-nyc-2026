"""Independent check of bundle binding and key release (GPT review items 1-2).

Tests marked xfail(strict=True) reproduce a gap that is open today: each passes once the gap is fixed,
and strict mode then fails the run so the marker gets removed.
"""
import json
import pytest
from nacl.public import PrivateKey, SealedBox
from nacl.secret import SecretBox

from agentrail.db import Store
from agentrail.engine import Engine
from agentrail.ledger.conditions import condition_hex, key_from_fulfillment
from agentrail.ledger.mock import MockLedger
from agentrail.market import acts
from agentrail.vault import keys as K
from agentrail.vault.delivery import PushDelivery

INST = "org_neuroimg"
ROWS = [{"day": i, "sleep.daily": 400 + i} for i in range(7)]


@pytest.fixture
def d():
    e = Engine(Store(":memory:"), MockLedger())
    pd = PushDelivery(e)
    inst = K.InstitutionKey()
    pd.register_institution(INST, "US", inst)
    pd.consent("P-1", INST, ["sleep.daily"], "sleep_research")
    return pd, inst


def pushed(pd, k_override=None):
    prep = pd.prepare("P-1", INST, ROWS, ["sleep.daily"], "c" * 64, 100_000)
    rec, k = K.seal(K.SoftPasskey(b"s" * 32).root("P-1"), prep["order_id"], K.unb64u(prep["bundle_b64u"]),
                    prep["institution_jwk"])
    cond_key = k_override or k
    r = pd.accept_sealed("P-1", rec, condition_hex(cond_key))
    assert r["ok"]
    return prep, rec, k, cond_key, r["order_id"]


def balance(pd, who):
    return pd.engine.ledger.balance_drops(pd.engine.party(who)["address"])


# ---- 1. K alone does not open a bundle for a third party ----

def test_vault_bundle_needs_the_institution_key_as_well_as_k(d):
    pd, inst = d
    prep, rec, k, _, oid = pushed(pd)
    assert pd.reveal("P-1", prep["order_id"], k)["ok"]
    f = pd.engine.ledger.lookup(pd.engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)["finish_tx"]).fulfillment
    k_public = key_from_fulfillment(f)
    assert k_public == k
    with pytest.raises(Exception):
        K.InstitutionKey().open(rec, k_public)          # anyone else holding K and the record: closed
    assert json.loads(inst.open(rec, k_public))["rows"][0]["sleep.daily"] == 400


def test_engine_bundle_with_k_alone_is_still_sealed_to_the_buyer():
    buyer = PrivateKey.generate()
    k = bytes(range(32))
    inner = SealedBox(buyer.public_key).encrypt(b'{"rows":[1]}')
    locked = SecretBox(k).encrypt(inner)                 # engine.place_order layering
    after_k = SecretBox(k).decrypt(locked)
    with pytest.raises(Exception):
        SealedBox(PrivateKey.generate()).decrypt(after_k)
    assert SealedBox(buyer).decrypt(after_k) == b'{"rows":[1]}'


# ---- 2. A failed or late EscrowFinish must not publish K ----

@pytest.mark.xfail(strict=True, reason="gap: engine._escrow_finish submits after CancelAfter; K lands on the ledger unpaid")
def test_late_finish_does_not_publish_k(d):
    pd, inst = d
    prep, rec, k, _, oid = pushed(pd)
    p = pd.engine.store.one("SELECT cancel_after FROM payments WHERE order_id=?", oid)
    pd.engine.ledger.clock = p["cancel_after"] + 1       # the round is past its deadline
    seller_before = balance(pd, "P-1")
    pd.reveal("P-1", prep["order_id"], k)
    pm = pd.engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)
    leaked = pm["finish_tx"] and pd.engine.ledger.lookup(pm["finish_tx"]).fulfillment
    assert balance(pd, "P-1") == seller_before            # not paid (the ledger refuses)
    assert not leaked, "K is public in a failed EscrowFinish: the buyer opens the bundle and then cancels"


def test_late_finish_today_gives_the_buyer_the_data_and_the_refund(d):
    """What the gap above means, end to end on the mock ledger."""
    pd, inst = d
    prep, rec, k, _, oid = pushed(pd)
    p = pd.engine.store.one("SELECT cancel_after FROM payments WHERE order_id=?", oid)
    pd.engine.ledger.clock = p["cancel_after"] + 1
    pd.reveal("P-1", prep["order_id"], k)
    pm = pd.engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)
    st = pd.engine.ledger.lookup(pm["finish_tx"])
    if not st.fulfillment:
        pytest.skip("gap fixed: no K on the ledger")
    assert st.result == "tecNO_PERMISSION"
    assert json.loads(inst.open(rec, key_from_fulfillment(st.fulfillment)))["rows"]     # buyer reads it
    assert pd.engine.sweep() == [oid]                                                    # and is refunded


# ---- 3. Contract, ciphertext and K point to the same bundle before money moves ----

@pytest.mark.xfail(strict=True, reason="gap: the condition is not bound to the sealed record; the buyer pays for a bundle K cannot open")
def test_condition_for_another_key_is_refused_or_refunded(d):
    pd, inst = d
    other = b"\7" * 32
    prep, rec, k, cond_key, oid = pushed(pd, k_override=other)
    seller_before = balance(pd, "P-1")
    pd.reveal("P-1", prep["order_id"], other)             # matches the escrow condition, not the bundle
    paid = balance(pd, "P-1") > seller_before
    with pytest.raises(Exception):
        pd.engine.open_payload(INST, oid)
    assert not paid, "buyer paid; K does not open what it holds"


def test_bundle_hash_check_is_not_an_assert():
    """python -O removes asserts; the check must stay."""
    import inspect
    from agentrail.engine import Engine
    assert "assert " not in inspect.getsource(Engine.open_payload)


def test_bundle_that_does_not_match_its_hash_is_refused_and_recorded(d):
    from agentrail.engine import BundleMismatch
    pd, inst = d
    prep, rec, k, _, oid = pushed(pd)
    assert pd.reveal("P-1", prep["order_id"], k)["ok"]
    bh, sealed = pd.engine.inbox.received[oid]
    pd.engine.inbox.received[oid] = ("0" * 64, sealed)       # the order says another bundle
    with pytest.raises(BundleMismatch):
        pd.engine.open_payload(INST, oid)
    ex = pd.engine.store.one("SELECT * FROM exceptions WHERE order_id=? AND kind='bundle_mismatch'", oid)
    assert ex and ex["cost_bearer"] == "P-1"


@pytest.fixture(scope="module")
def a1():
    return acts.act1(rounds=2)


def test_seller_who_delivers_other_rows_than_committed_is_not_paid(a1):
    bait = [t for t in a1["exchange"].trades
            if any(s.get("code") == "not_as_committed" for s in t.get("signals", []))]
    assert bait, "Act 1 has sellers whose delivery does not hash to the certified root"
    assert all(t["paid_drops"] == 0 and not t.get("txs", {}).get("escrow_finish") and t["stage"] == "binding" for t in bait)
