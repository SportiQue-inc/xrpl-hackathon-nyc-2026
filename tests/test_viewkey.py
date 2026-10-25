"""T3 view keys: one keyring per grant, one fetch per session, expiry and revocation; T0-T2 copies:
retention and deletion confirmation."""
import time

import pytest
from nacl.signing import SigningKey

from agentrail.vault.viewkey import CopyLedger, Keyring, KeyService, Workspace, benchmark, seal_chunk

R = {"id": "R-neuroimg-1", "credential": True, "irb_valid": True, "institution": "org_neuroimg"}


def setup(now):
    owner = SigningKey.generate()
    ring = Keyring("P-1", "org_neuroimg", "S", owner)
    keys = {c: bytes([i]) * 32 for i, c in enumerate("ABCDE")}
    ring.add({c: keys[c] for c in "ABC"}, expires=1000)
    svc = KeyService(clock=lambda: now[0])
    svc.register(ring, bytes(owner.verify_key).hex())
    blobs = {c: seal_chunk(keys[c], c, f"data {c}".encode()) for c in keys}
    tok = svc.open_session(R, "P-1", "org_neuroimg", "S", "contract")["token"]
    ws = Workspace(svc, clock=lambda: now[0])
    assert ws.start(tok)["chunks"] == 3
    return owner, ring, keys, svc, blobs, tok, ws


def test_expansion_appends_and_opens_without_refetch():
    now = [10.0]
    _, ring, keys, svc, blobs, tok, ws = setup(now)
    assert ws.open("A", blobs["A"]) == b"data A"
    with pytest.raises(PermissionError):
        ws.open("D", blobs["D"])
    v = ring.version
    ring.add({c: keys[c] for c in "DE"}, expires=1000)
    assert ring.version == v + 1
    ws.apply_delta(svc.delta(tok, ws.version))
    before = svc.fetches
    for c in "ABCDE":
        assert ws.open(c, blobs[c]) == f"data {c}".encode()
    assert svc.fetches == before                                     # opens are local lookups


def test_revoked_entry_fails_after_delta_and_is_logged():
    now = [10.0]
    _, ring, _, svc, blobs, tok, ws = setup(now)
    ring.remove("B")
    ws.apply_delta(svc.delta(tok, ws.version))
    with pytest.raises(PermissionError):
        ws.open("B", blobs["B"])
    assert any(a["chunk"] == "B" for a in svc.audit if "chunk" in a)


def test_expired_view_key_fails():
    now = [10.0]
    _, _, _, svc, blobs, tok, ws = setup(now)
    now[0] = 2000
    assert svc.fetch(tok)["ok"] is False                            # session over
    tok2 = svc.open_session(R, "P-1", "org_neuroimg", "S", "contract")["token"]
    ws.apply_delta(svc.delta(tok2, ws.version))                      # entries expired at 1000
    with pytest.raises(PermissionError):
        ws.open("A", blobs["A"])


def test_stale_manifest_version_rejected():
    now = [10.0]
    _, ring, keys, svc, blobs, tok, ws = setup(now)
    old = svc.fetch(tok)
    ring.add({"D": keys["D"]}, expires=1000)
    ws.apply_delta(svc.delta(tok, ws.version))
    with pytest.raises(ValueError):
        ws.apply_delta(old)


def test_forged_manifest_and_wrong_researcher():
    now = [10.0]
    _, ring, _, svc, _, tok, _ = setup(now)
    ring._sk = SigningKey.generate()
    ring.add({}, expires=1000)
    assert svc.fetch(tok)["why"] == "manifest not signed by the owner"
    assert svc.open_session({**R, "irb_valid": False}, "P-1", "org_neuroimg", "S", "c")["ok"] is False
    assert svc.open_session({**R, "institution": "org_genomics"}, "P-1", "org_neuroimg", "S", "c")["ok"] is False


def test_raw_export_refused():
    now = [10.0]
    *_, ws = setup(now)
    assert ws.export("raw", [1])["ok"] is False and ws.export("aggregate", {"n": 30})["ok"]


def test_copy_past_retention_without_confirmation_flags():
    now = [0.0]
    led = CopyLedger(clock=lambda: now[0])
    buyer = SigningKey.generate()
    led.delivered("c1", "org_cardio", 100, bytes(buyer.verify_key).hex())
    led.delivered("c2", "org_cardio", 100, bytes(buyer.verify_key).hex())
    now[0] = 100
    assert {e["event"] for e in led.sweep(grace_s=50)} == {"deletion requested"}
    assert led.confirm("c1", buyer.sign(b"deleted|c1").signature.hex())
    assert not led.confirm("c2", SigningKey.generate().sign(b"deleted|c2").signature.hex())
    now[0] = 151
    flags = led.sweep(grace_s=50)
    assert [f["copy"] for f in flags] == ["c2"] and flags[0]["penalty_case"]


def test_benchmark_keyring_fetches_once_per_expansion():
    b = benchmark(60, 2)
    assert b["keyring"]["fetches"] == 3 and b["key_per_request"]["fetches"] == 60
