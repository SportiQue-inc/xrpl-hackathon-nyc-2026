"""Genomic protection: regions, least-revealing ladder, compute-only enclave, Crypt4GH-style
container, recipient watermark, strictest consent, ledger hygiene."""
import pytest
from nacl.public import PrivateKey

from agentrail.catalog.columns import synth_vcf
from agentrail.catalog.scope import TouchID, verify_assertion
from agentrail.vault import genomic as G
from agentrail.vault.keys import SoftPasskey

ROOT = SoftPasskey(b"g" * 32).root("P-1")
VCF = synth_vcf("P-1")


def test_wrong_region_key_fails():
    enc = G.encrypt_regions(ROOT, VCF, "S1")
    assert G.decrypt_region(G.region_key(ROOT, "CYP1A2", "S1"), "CYP1A2", enc["CYP1A2"])
    with pytest.raises(Exception):
        G.decrypt_region(G.region_key(ROOT, "BRCA1", "S1"), "CYP1A2", enc["CYP1A2"])
    with pytest.raises(Exception):
        G.decrypt_region(G.region_key(ROOT, "CYP1A2", "S2"), "CYP1A2", enc["CYP1A2"])


def cohort(n):
    keys, sealed = {}, {}
    for i in range(n):
        pid = f"P-{i}"
        root = SoftPasskey(bytes([i % 256]) * 32).root(pid)
        sealed[pid] = G.encrypt_regions(root, synth_vcf(pid, ("CYP1A2", "MCM6")), "S1")
        keys[pid] = {g: G.region_key(root, g, "S1") for g in ("CYP1A2", "MCM6")}
    return keys, sealed


def test_enclave_runs_only_signed_computations_on_k_people():
    now = [100.0]
    keys, sealed = cohort(25)
    e = G.Enclave("S1", "org_genomics", ["CYP1A2"], until=200, keys=keys, clock=lambda: now[0])
    r = e.run("allele_count", ["CYP1A2"], sealed)
    assert r["ok"] and r["n"] == 25 and set(r["result"]) == {"CYP1A2"}
    assert "never leave" in e.run("raw", ["CYP1A2"], sealed)["why"]
    assert e.run("export_vcf", ["CYP1A2"], sealed)["ok"] is False
    assert "not a computation you signed" in e.run("genotype_list", ["CYP1A2"], sealed)["why"]
    assert "outside the signed scope" in e.run("allele_count", ["MCM6"], sealed)["why"]
    small = {k: sealed[k] for k in list(sealed)[:10]}
    assert "below k=20" in e.run("allele_count", ["CYP1A2"], small)["why"]
    now[0] = 300
    assert not e.holds_keys and "keys destroyed" in e.run("allele_count", ["CYP1A2"], sealed)["why"]


def test_aggregate_cannot_be_turned_into_raw():
    keys, sealed = cohort(20)
    e = G.Enclave("S1", "org_genomics", ["CYP1A2"], until=10**12, keys=keys)
    r = e.run("allele_count", ["CYP1A2"], sealed)
    assert set(r["result"]) == {"CYP1A2"} and isinstance(r["result"]["CYP1A2"], int)
    assert not any(k in str(r) for k in ("pos", "ref", "alt", "gt"))


def test_ladder_least_revealing_first():
    lad = G.Ladder("org_genomics", beacon_limit=2)
    assert lad.ask("raw", "need per-person genotype for phenotype linkage")[0] is False
    assert lad.ask("aggregate")[0] and lad.ask("beacon")[0]
    assert lad.ask("raw", "short")[0] is False
    ok, why = lad.ask("raw", "need per-person genotype for phenotype linkage")
    assert ok and "raw accepted" in why
    lad.ask("beacon")
    assert lad.ask("beacon") == (False, "beacon rate limit reached for this buyer")


def test_crypt4gh_style_roundtrip_and_wrong_recipient():
    r = PrivateKey.generate()
    data = b"x" * 70000 + b"tail"
    blob = G.c4gh_encrypt(data, bytes(r.public_key))
    assert blob[:8] == b"crypt4gh" and G.c4gh_decrypt(blob, r) == data
    with pytest.raises(Exception):
        G.c4gh_decrypt(blob, PrivateKey.generate())


def test_watermark_identifies_recipient():
    key = b"w" * 32
    a = G.watermark(VCF, "org_a", key)
    b = G.watermark(VCF, "org_b", key)
    assert a != b
    assert G.trace(a, ["org_b", "org_a", "org_c"], key) == "org_a"
    assert G.trace(b, ["org_a", "org_b"], key) == "org_b"
    assert G.trace(sorted(a, key=lambda v: v["pos"]), ["org_a", "org_b"], key) is None   # marks stripped


REC = {"id": "org_genomics", "country": "SG", "irb": {"valid": True, "expires": 10**10},
       "duo": ["DUO:0000006", "DUO:0000016"]}


def test_t3_consent_rules():
    dev = TouchID()
    v = lambda a, h: verify_assertion(dev.public, a, h, now=1000)
    pkg = G.consent_package("P-1", "KR", REC, ["CYP1A2"], "genomics_research")
    assert pkg["transfer_abroad"] and len(pkg["warnings"]) == 2
    fresh = dev.assert_(pkg["hash"], now=1000)
    assert G.check_t3(pkg, fresh, v, 1000) == "delivery abroad needs the separate transfer-abroad consent"
    assert G.check_t3(pkg, None, v, 1000, True) == "T3 needs a fresh Touch ID for this package"
    assert G.check_t3(pkg, dev.assert_(pkg["hash"], now=500), v, 1000, True) == "T3 needs a fresh Touch ID for this package"
    assert G.check_t3(pkg, fresh, v, 1000, True) is None
    nogso = G.consent_package("P-1", "KR", {**REC, "duo": ["DUO:0000006"]}, ["CYP1A2"], "g")
    assert "genetic-studies-only" in G.check_t3(nogso, dev.assert_(nogso["hash"], now=1000), v, 1000, True)
    expired = G.consent_package("P-1", "KR", {**REC, "irb": {"valid": True, "expires": 10}}, ["CYP1A2"], "g")
    assert "IRB" in G.check_t3(expired, dev.assert_(expired["hash"], now=1000), v, 1000, True)


def test_ledger_hash_is_salted_per_round():
    b = b'{"variants":[]}'
    assert G.ledger_hash(b"r1", b) != G.ledger_hash(b"r2", b)
    assert "CYP" not in G.ledger_hash(b"r1", b)
