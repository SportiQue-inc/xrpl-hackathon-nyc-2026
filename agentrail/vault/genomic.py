"""Genomic data (T3): a separate protection layer on top of the passkey root and push delivery.

Threat model (docs/GENOMIC.md):
  - a genome identifies its owner by itself; we never claim otherwise
  - it says something about blood relatives who never consented
  - it is permanent: a leak cannot be undone, so withdrawal cannot fully protect it
  - small slices can still link (rare variants)

Design:
  regions     the synthetic VCF is cut by gene region; each region has its own key,
              HKDF(passkey root, "region|<region>|<study>"), so a trade releases only the loci asked for
  ladder      the buyer's agent must try the least revealing answer first: a cohort aggregate (computed
              on the provider side, k >= 20), then a yes/no presence answer (Beacon style, rate-limited
              per buyer), and only then raw variants for named loci, with the reason recorded
  enclave     inside a study the person signed, a compute-only process holds the signed loci's keys,
              runs only whitelisted computations, returns outputs (never raw), refuses cohorts below k,
              and destroys its keys when the period ends
  delivery    raw loci go in a Crypt4GH-style container: a header encrypted to the recipient's X25519
              key carrying the data key, then 64 KiB ChaCha20-Poly1305 segments. It follows the GA4GH
              Crypt4GH structure; byte compatibility with the reference tool is not tested here.
  watermark   each recipient's copy orders its records by a recipient-keyed permutation and carries a
              recipient-keyed record id; a leaked copy with those marks intact points to one recipient
  consent     never automatic: a fresh Touch ID every time; the package shows the relatives and
              permanence warnings, the exact loci, the recipient and country, the IRB credential (valid,
              with the genetic-studies-only DUO code); delivery abroad needs the separate transfer consent
  ledger      only a salted, per-round hash goes on the ledger, never a variant id or anything derived
              from genotypes
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import struct
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from nacl.bindings import (crypto_aead_chacha20poly1305_ietf_decrypt, crypto_aead_chacha20poly1305_ietf_encrypt,
                           crypto_scalarmult)
from nacl.public import PrivateKey

from ..catalog.columns import GENES
from .keys import hkdf

K_MIN = 20
FRESH_S = 120
GSO = "DUO:0000016"


def _canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


# ---------------- region-level encryption ----------------

def region_key(root: bytes, region: str, study: str) -> bytes:
    return hkdf(root, f"region|{region}|{study}")


def encrypt_regions(root: bytes, vcf: list[dict], study: str) -> dict:
    out = {}
    for g in sorted({v["gene"] for v in vcf}):
        n = os.urandom(12)
        out[g] = {"nonce": n.hex(), "ct": AESGCM(region_key(root, g, study)).encrypt(
            n, _canon([v for v in vcf if v["gene"] == g]), g.encode()).hex()}
    return out


def decrypt_region(key: bytes, region: str, blob: dict) -> list[dict]:
    return json.loads(AESGCM(key).decrypt(bytes.fromhex(blob["nonce"]), bytes.fromhex(blob["ct"]), region.encode()))


# ---------------- least revealing answer first ----------------

LEVELS = ("aggregate", "beacon", "raw")


class Ladder:
    """One buyer's negotiation for one study. Raw needs both lower levels tried and a stated reason."""

    def __init__(self, buyer: str, beacon_limit: int = 10):
        self.buyer, self.limit = buyer, beacon_limit
        self.tried: list[dict] = []
        self.beacon_calls = 0

    def ask(self, level: str, why: str = "") -> tuple[bool, str]:
        if level not in LEVELS:
            return False, "unknown level"
        if level == "beacon":
            if self.beacon_calls >= self.limit:
                return False, "beacon rate limit reached for this buyer"
            self.beacon_calls += 1
        if level == "raw":
            done = {t["level"] for t in self.tried}
            if not {"aggregate", "beacon"} <= done:
                return False, "try the aggregate and the presence answer first"
            if len(why) < 20:
                return False, "raw loci need a stated reason the lower levels cannot answer"
        self.tried.append({"level": level, "why": why})
        return True, f"{level} accepted" + (f": {why}" if why else "")


def beacon(vcf: list[dict], gene: str, pos: int, alt: str) -> bool:
    return any(v["gene"] == gene and v["pos"] == pos and v["alt"] == alt and v["gt"] != "0/0" for v in vcf)


# ---------------- compute-only enclave ----------------

WHITELIST = {
    "allele_count": lambda rows, loci: {g: sum({"0/0": 0, "0/1": 1, "1/1": 2}[v["gt"]] for r in rows for v in r
                                               if v["gene"] == g) for g in loci},
    "carrier_count": lambda rows, loci: {g: sum(1 for r in rows if any(v["gene"] == g and v["gt"] != "0/0" for v in r))
                                         for g in loci},
}


class Enclave:
    """Holds the signed loci's region keys for one study; returns computed outputs only."""

    def __init__(self, study: str, recipient: str, loci: list, until: float, keys: dict, clock=time.time,
                 computations=("allele_count", "carrier_count")):
        self.study, self.recipient, self.loci, self.until = study, recipient, list(loci), until
        self.computations = set(computations)
        self._keys = dict(keys)                 # per person: {pid: {region: key}}
        self.clock = clock
        self.log: list[dict] = []

    def _expire(self):
        if self.clock() > self.until and self._keys:
            self._keys.clear()
            self.log.append({"event": "keys destroyed", "at": self.clock()})

    @property
    def holds_keys(self) -> bool:
        self._expire()
        return bool(self._keys)

    def run(self, computation: str, loci: list, sealed: dict) -> dict:
        self._expire()
        if computation == "raw" or computation.startswith("export"):
            return self._refuse(computation, "raw variants never leave the enclave")
        if computation not in self.computations or computation not in WHITELIST:
            return self._refuse(computation, "not a computation you signed")
        if not set(loci) <= set(self.loci):
            return self._refuse(computation, "loci outside the signed scope")
        if not self._keys:
            return self._refuse(computation, "the signed period has ended; keys destroyed")
        people = [p for p in sealed if p in self._keys]
        if len(people) < K_MIN:
            return self._refuse(computation, f"cohort of {len(people)} is below k={K_MIN}")
        rows = [sum((decrypt_region(self._keys[p][g], g, sealed[p][g]) for g in loci if g in sealed[p]), [])
                for p in people]
        out = WHITELIST[computation](rows, loci)
        self.log.append({"event": "computed", "computation": computation, "loci": loci, "n": len(people)})
        return {"ok": True, "computation": computation, "n": len(people), "result": out}

    def _refuse(self, c, why):
        self.log.append({"event": "refused", "computation": c, "why": why})
        return {"ok": False, "why": why}


# ---------------- Crypt4GH-style container ----------------

MAGIC, SEG = b"crypt4gh", 65536


def _shared(priv: bytes, pub: bytes, ours: bytes, recipient_is_reader: bool) -> bytes:
    dh = crypto_scalarmult(priv, pub)
    a, b = (pub, ours) if recipient_is_reader else (ours, pub)
    return hashlib.blake2b(dh + a + b, digest_size=64).digest()[:32]


def c4gh_encrypt(data: bytes, recipient_pub: bytes) -> bytes:
    writer = PrivateKey.generate()
    wpub = bytes(writer.public_key)
    k = _shared(bytes(writer), recipient_pub, wpub, recipient_is_reader=False)
    dk = os.urandom(32)
    n = os.urandom(12)
    packet = struct.pack("<I", 0) + struct.pack("<I", 0) + dk          # data_encryption_parameters, chacha20poly1305
    enc = crypto_aead_chacha20poly1305_ietf_encrypt(packet, None, n, k)
    header = MAGIC + struct.pack("<I", 1) + struct.pack("<I", 1) + struct.pack("<I", 4 + 32 + 12 + len(enc)) + \
        struct.pack("<I", 0) + wpub + n + enc
    body = b""
    for i in range(0, len(data) or 1, SEG):
        sn = os.urandom(12)
        body += sn + crypto_aead_chacha20poly1305_ietf_encrypt(data[i:i + SEG], None, sn, dk)
    return header + body


def c4gh_decrypt(blob: bytes, recipient: PrivateKey) -> bytes:
    assert blob[:8] == MAGIC
    plen = struct.unpack("<I", blob[16:20])[0]
    p = blob[20:20 + plen]
    wpub, n, enc = p[4:36], p[36:48], p[48:]
    k = _shared(bytes(recipient), wpub, bytes(recipient.public_key), recipient_is_reader=True)
    packet = crypto_aead_chacha20poly1305_ietf_decrypt(enc, None, n, k)
    dk = packet[8:40]
    body, out = blob[20 + plen:], b""
    while body:
        seg = body[:12 + SEG + 16]
        out += crypto_aead_chacha20poly1305_ietf_decrypt(seg[12:], None, seg[:12], dk)
        body = body[len(seg):]
    return out


# ---------------- per-recipient fingerprint ----------------

def watermark(variants: list[dict], recipient: str, key: bytes) -> list[dict]:
    tag = lambda v: hmac.new(key, f"{recipient}|{v['gene']}|{v['pos']}".encode(), hashlib.sha256).hexdigest()
    marked = [{**v, "id": "rec_" + tag(v)[:10]} for v in variants]
    return sorted(marked, key=lambda v: tag(v))


def trace(leaked: list[dict], recipients: list[str], key: bytes) -> str | None:
    for r in recipients:
        mine = watermark([{k: v for k, v in x.items() if k != "id"} for x in leaked], r, key)
        if [x["id"] for x in mine] == [x.get("id") for x in leaked]:
            return r
    return None


# ---------------- strictest consent ----------------

def consent_package(pid: str, home: str, recipient: dict, loci: list, purpose: str) -> dict:
    body = {"owner": pid, "recipient": recipient["id"], "country": recipient["country"], "loci": loci,
            "purpose": purpose, "irb": recipient.get("irb"), "duo": recipient.get("duo", []),
            "transfer_abroad": recipient["country"] != home,
            "warnings": ["your genome says something about blood relatives who did not consent",
                         "genomic data is permanent: a copy already delivered cannot be taken back technically, "
                         "only by contract (deletion request and confirmation)"]}
    body["hash"] = hashlib.sha256(_canon(body)).hexdigest()
    return body


def check_t3(pkg: dict, assertion: dict | None, verify, now: float, transfer_consent: bool = False) -> str | None:
    """verify(assertion, package_hash) -> error or None (the owner's device key)."""
    irb = pkg.get("irb") or {}
    if not irb.get("valid") or irb.get("expires", 0) < now:
        return "recipient has no valid IRB credential"
    if GSO not in pkg.get("duo", []):
        return f"request lacks the genetic-studies-only code {GSO}"
    if pkg["transfer_abroad"] and not transfer_consent:
        return "delivery abroad needs the separate transfer-abroad consent"
    if not assertion or now - assertion.get("ts", 0) > FRESH_S:
        return "T3 needs a fresh Touch ID for this package"
    return verify(assertion, pkg["hash"])


def ledger_hash(round_salt: bytes, bundle: bytes) -> str:
    """What goes on the ledger: salted per round, so it cannot be matched by guessing genotypes."""
    return hashlib.sha256(round_salt + hashlib.sha256(bundle).digest()).hexdigest()
