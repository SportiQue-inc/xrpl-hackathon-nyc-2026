"""Passkey-rooted keys, browser sealing and push delivery."""
import pytest

from agentrail.db import Store
from agentrail.engine import Engine
from agentrail.ledger.conditions import condition_hex
from agentrail.ledger.mock import MockLedger
from agentrail.vault import keys as K
from agentrail.vault.delivery import PushDelivery


@pytest.fixture
def d():
    e = Engine(Store(":memory:"), MockLedger())
    pd = PushDelivery(e)
    inst = K.InstitutionKey()
    pd.register_institution("org_neuroimg", "US", inst)
    pd.consent("P-1", "org_neuroimg", ["sleep.daily"], "sleep_research")
    return pd, inst


ROWS = [{"day": i, "sleep.daily": 400 + i, "heart_rate.daily": 60} for i in range(7)]


def test_root_is_per_person_and_never_needs_the_server():
    pk = K.SoftPasskey(b"s" * 32)
    assert pk.root("P-1") == pk.root("P-1") != pk.root("P-2")
    assert K.trade_key(pk.root("P-1"), "t1", "h") != K.trade_key(pk.root("P-1"), "t2", "h")


def test_push_then_reveal_end_to_end(d):
    pd, inst = d
    prep = pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 100_000)
    bundle = K.unb64u(prep["bundle_b64u"])
    assert b"heart_rate" not in bundle                               # only the agreed columns
    root = K.SoftPasskey(b"s" * 32).root("P-1")
    rec, k = K.seal(root, prep["order_id"], bundle, prep["institution_jwk"])
    r = pd.accept_sealed("P-1", rec, condition_hex(k))
    assert r["ok"] and r["country"] == "US" and r["escrow_create"]
    with pytest.raises(Exception):
        inst.open(rec, b"\0" * 32)                                     # pushed, but closed until K is public
    assert pd.reveal("P-1", prep["order_id"], b"\1" * 32)["ok"] is False
    out = pd.reveal("P-1", prep["order_id"], k)
    assert out["ok"] and out["escrow_finish"]
    payload = pd.engine.open_payload("org_neuroimg", r["order_id"])
    assert [x["sleep.daily"] for x in payload["rows"]] == [400 + i for i in range(7)]


def test_engine_never_holds_k_or_clear_bundle(d):
    pd, _ = d
    prep = pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 100_000)
    rec, k = K.seal(K.SoftPasskey().root("P-1"), prep["order_id"], K.unb64u(prep["bundle_b64u"]), prep["institution_jwk"])
    r = pd.accept_sealed("P-1", rec, condition_hex(k))
    sealed = pd.engine.store.one("SELECT sealed FROM bundles WHERE order_id=?", r["order_id"])["sealed"]
    assert b"sleep.daily" not in bytes(sealed) and k.hex() not in bytes(sealed).decode()
    assert pd.engine.store.one("SELECT * FROM escrow_keys WHERE order_id=?", r["order_id"]) is None


def test_tampered_or_foreign_bundle_refused(d):
    pd, _ = d
    prep = pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 100_000)
    rec, k = K.seal(K.SoftPasskey().root("P-1"), prep["order_id"], b'{"other":1}', prep["institution_jwk"])
    assert pd.accept_sealed("P-1", rec, condition_hex(k))["reason"] == "sealed bundle is not the prepared one"


def test_other_institution_cannot_open(d):
    pd, _ = d
    prep = pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 1)
    rec, k = K.seal(K.SoftPasskey().root("P-1"), prep["order_id"], K.unb64u(prep["bundle_b64u"]), prep["institution_jwk"])
    with pytest.raises(Exception):
        K.InstitutionKey().open(rec, k)


def test_revoke_stops_pushes_and_requests_deletion(d):
    pd, _ = d
    prep = pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 100_000)
    rec, k = K.seal(K.SoftPasskey().root("P-1"), prep["order_id"], K.unb64u(prep["bundle_b64u"]), prep["institution_jwk"])
    pd.accept_sealed("P-1", rec, condition_hex(k))
    pd.reveal("P-1", prep["order_id"], k)
    r = pd.revoke("P-1", "org_neuroimg")
    assert r["ok"] and len(r["deletion_request"]["copies"]) == 1
    with pytest.raises(PermissionError):
        pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 1)


def test_revoke_before_reveal_keeps_the_key_back(d):
    pd, _ = d
    prep = pd.prepare("P-1", "org_neuroimg", ROWS, ["sleep.daily"], "c" * 64, 100_000)
    rec, k = K.seal(K.SoftPasskey().root("P-1"), prep["order_id"], K.unb64u(prep["bundle_b64u"]), prep["institution_jwk"])
    pd.accept_sealed("P-1", rec, condition_hex(k))
    pd.revoke("P-1", "org_neuroimg")
    assert pd.reveal("P-1", prep["order_id"], k)["ok"] is False      # engine re-checks consent before the key goes out


def test_http_flow_participant_only():
    from fastapi.testclient import TestClient
    from agentrail import web
    from agentrail.cohort import HERO
    from tests.test_security import login
    c = TestClient(web.app)
    c.post("/api/reset?ledger=mock", headers=login(c, "operator"))
    h = login(c, HERO)
    body = {"institution": "org_cardio", "columns": ["sleep.daily"], "purpose": "cardiometabolic_research",
            "contract": "ab" * 16, "price_drops": 50_000}
    assert c.post("/api/p/P-999/push/prepare", json=body, headers=h).status_code == 403
    prep = c.post(f"/api/p/{HERO}/push/prepare", json=body, headers=h).json()
    rec, k = K.seal(K.SoftPasskey().root(HERO), prep["order_id"], K.unb64u(prep["bundle_b64u"]), prep["institution_jwk"])
    r = c.post(f"/api/p/{HERO}/push/sealed", json={"record": rec, "condition": condition_hex(k)}, headers=h).json()
    assert r["ok"], r
    r = c.post(f"/api/p/{HERO}/push/reveal", json={"order_id": prep["order_id"], "key_b64u": K.b64u(k)}, headers=h).json()
    assert r["ok"], r
