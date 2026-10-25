"""Decryption and expiry, split by tier.

T0-T2: a copy is pushed and decrypted in the buyer's own store (vault/delivery.py). Expiry is
contractual: the contract carries a retention period; at its end the engine sends a deletion
request; the buyer's agent must answer with a signed deletion confirmation; a missing answer is an
audit flag and a penalty case. A decrypted copy cannot be force-deleted.

T3 (genomic, imaging): the plaintext stays in the buyer's controlled workspace (UniQLab tenant).
The encrypted bundle is still pushed into that tenant (no inbound access to the person's store).
The decryption keys are not handed over as a file; they sit in one keyring per grant:

  keyring     one per (owner, institution, study): a versioned manifest the owner signed at consent
              time, holding each granted chunk key wrapped for the grant. When the owner later agrees
              to more columns or regions, the new wrapped keys are appended and the version bumps:
              keys are added, never minted as separate view keys. The wrap comes from what the owner
              signed (the root never leaves the owner's page), not from a server-held root.
  session     a short-lived token bound to the researcher's credential, the IRB credential, the
              purpose code and the contract. One fetch per session returns the whole current keyring;
              the workspace indexes it by chunk id, so opening a chunk is a local lookup. A scope
              added mid-session arrives as a small delta.
  workspace   decrypts only inside the session; computations and aggregate export are allowed, raw
              export is refused
  expiry      per entry and per manifest; an expired or removed entry is dropped from the next keyring
              and the delta, wiped from the cache, and the wipe is logged

Expiry is technically enforced only where the plaintext stays in the controlled workspace. For
copies it is contract plus audit (docs/SECURITY.md).
"""
from __future__ import annotations

import hashlib
import json
import os
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from nacl.signing import SigningKey, VerifyKey


def _canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


class Keyring:
    """The owner's side of one grant: chunk keys wrapped for the grant, versioned and signed."""

    def __init__(self, owner: str, institution: str, study: str, owner_key: SigningKey):
        self.owner, self.institution, self.study = owner, institution, study
        self._sk = owner_key
        self.grant_key = os.urandom(32)        # wraps chunk keys for this grant only
        self.version = 0
        self.entries: dict[str, dict] = {}     # chunk id -> {wrapped, expires}
        self.manifest = None

    def add(self, chunks: dict, expires: float) -> dict:
        """chunks: {chunk_id: chunk key}. Appends, bumps the version, re-signs."""
        for cid, k in chunks.items():
            n = os.urandom(12)
            self.entries[cid] = {"wrapped": (n + AESGCM(self.grant_key).encrypt(n, k, cid.encode())).hex(),
                                 "expires": expires}
        return self._sign()

    def remove(self, cid: str) -> dict:
        self.entries.pop(cid, None)
        return self._sign()

    def _sign(self) -> dict:
        self.version += 1
        body = {"owner": self.owner, "institution": self.institution, "study": self.study,
                "version": self.version, "entries": {c: e["expires"] for c, e in self.entries.items()}}
        self.manifest = {**body, "sig": self._sk.sign(_canon(body)).signature.hex()}
        return self.manifest


class KeyService:
    """Issues sessions and serves the current keyring. It holds wrapped keys and the grant key the
    owner's consent released to it for this grant; it never holds the owner's root."""

    def __init__(self, clock=time.time, session_s: int = 900):
        self.clock, self.session_s = clock, session_s
        self.rings: dict[tuple, Keyring] = {}
        self.owner_pub: dict[str, str] = {}
        self.sessions: dict[str, dict] = {}
        self.audit: list[dict] = []
        self.fetches = 0

    def register(self, ring: Keyring, owner_pub: str):
        self.rings[(ring.owner, ring.institution, ring.study)] = ring
        self.owner_pub[ring.owner] = owner_pub

    def open_session(self, researcher: dict, owner: str, institution: str, study: str, contract: str) -> dict:
        if not researcher.get("credential") or not researcher.get("irb_valid"):
            return {"ok": False, "why": "researcher credential or IRB credential not valid"}
        if researcher.get("institution") != institution:
            return {"ok": False, "why": "researcher is not from the granted institution"}
        tok = os.urandom(16).hex()
        self.sessions[tok] = {"owner": owner, "institution": institution, "study": study, "contract": contract,
                              "researcher": researcher["id"], "purpose": researcher.get("purpose"),
                              "expires": self.clock() + self.session_s}
        return {"ok": True, "token": tok}

    def _live(self, ring: Keyring) -> dict:
        now = self.clock()
        return {c: e for c, e in ring.entries.items() if e["expires"] > now}

    def fetch(self, token: str) -> dict:
        s = self.sessions.get(token)
        if not s or s["expires"] < self.clock():
            return {"ok": False, "why": "session expired"}
        ring = self.rings[(s["owner"], s["institution"], s["study"])]
        m = ring.manifest
        body = {k: v for k, v in m.items() if k != "sig"}
        try:
            VerifyKey(bytes.fromhex(self.owner_pub[ring.owner])).verify(_canon(body), bytes.fromhex(m["sig"]))
        except Exception:
            return {"ok": False, "why": "manifest not signed by the owner"}
        self.fetches += 1
        return {"ok": True, "version": m["version"], "grant_key": ring.grant_key.hex(),
                "entries": {c: e["wrapped"] for c, e in self._live(ring).items()}}

    def delta(self, token: str, since: int) -> dict:
        r = self.fetch(token)
        if not r["ok"]:
            return r
        r["since"] = since
        return r


class Workspace:
    """The controlled workspace: one fetch per session, local O(1) opens, no raw export."""

    def __init__(self, service: KeyService, clock=time.time):
        self.svc, self.clock = service, clock
        self.token, self.version = None, 0
        self._grant, self._cache = None, {}

    def start(self, token: str) -> dict:
        r = self.svc.fetch(token)
        if not r["ok"]:
            return r
        self.token = token
        self._load(r)
        return {"ok": True, "version": self.version, "chunks": len(self._cache)}

    def _load(self, r: dict):
        if r["version"] < self.version:
            raise ValueError("stale manifest version")
        gone = set(self._cache) - set(r["entries"])
        for c in gone:
            self._cache.pop(c)
            self.svc.audit.append({"event": "wiped from workspace cache", "chunk": c, "at": self.clock()})
        self._grant = AESGCM(bytes.fromhex(r["grant_key"]))
        for c, w in r["entries"].items():
            if c not in self._cache:
                b = bytes.fromhex(w)
                self._cache[c] = self._grant.decrypt(b[:12], b[12:], c.encode())
        self.version = r["version"]

    def apply_delta(self, r: dict):
        if not r.get("ok"):
            raise PermissionError(r.get("why"))
        self._load(r)

    def open(self, chunk_id: str, blob: dict) -> bytes:
        k = self._cache.get(chunk_id)
        if k is None:
            raise PermissionError(f"no key for {chunk_id} in this session")
        return AESGCM(k).decrypt(bytes.fromhex(blob["nonce"]), bytes.fromhex(blob["ct"]), chunk_id.encode())

    def export(self, kind: str, data) -> dict:
        if kind != "aggregate":
            return {"ok": False, "why": "raw export from a T3 workspace is refused"}
        return {"ok": True, "data": data}

    def end(self):
        self._cache.clear()
        self._grant = None
        self.svc.audit.append({"event": "session ended; keys wiped", "at": self.clock()})


def seal_chunk(key: bytes, cid: str, data: bytes) -> dict:
    n = os.urandom(12)
    return {"nonce": n.hex(), "ct": AESGCM(key).encrypt(n, data, cid.encode()).hex()}


# ---------------- T0-T2 copies: retention and deletion confirmation ----------------

class CopyLedger:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.copies: dict[str, dict] = {}
        self.flags: list[dict] = []

    def delivered(self, cid: str, institution: str, retention_s: float, buyer_pub: str):
        self.copies[cid] = {"institution": institution, "expires": self.clock() + retention_s, "buyer_pub": buyer_pub,
                            "requested": False, "confirmed": False}

    def sweep(self, grace_s: float = 0) -> list[dict]:
        now = self.clock()
        out = []
        for cid, c in self.copies.items():
            if now >= c["expires"] and not c["requested"]:
                c["requested"] = True
                out.append({"event": "deletion requested", "copy": cid, "institution": c["institution"]})
            if c["requested"] and not c["confirmed"] and now >= c["expires"] + grace_s and \
                    not any(f["copy"] == cid for f in self.flags):
                f = {"event": "audit flag: no deletion confirmation", "copy": cid, "institution": c["institution"],
                     "penalty_case": True}
                self.flags.append(f)
                out.append(f)
        return out

    def confirm(self, cid: str, sig_hex: str) -> bool:
        c = self.copies[cid]
        try:
            VerifyKey(bytes.fromhex(c["buyer_pub"])).verify(f"deleted|{cid}".encode(), bytes.fromhex(sig_hex))
        except Exception:
            return False
        c["confirmed"] = True
        return True


def benchmark(n_chunks: int = 200, expansions: int = 5, seed: int = 1) -> dict:
    """Open N chunks after M scope expansions: one keyring fetch per session vs a key fetch per request."""
    owner = SigningKey.generate()
    ring = Keyring("P-1", "org_neuroimg", "S", owner)
    svc = KeyService()
    keys = {f"c{i}": os.urandom(32) for i in range(n_chunks)}
    per = n_chunks // (expansions + 1)
    groups = [list(keys)[i * per:(i + 1) * per] for i in range(expansions + 1)]
    ring.add({c: keys[c] for c in groups[0]}, time.time() + 3600)
    svc.register(ring, bytes(owner.verify_key).hex())
    blobs = {c: seal_chunk(keys[c], c, b"x" * 256) for c in keys}
    res = {"researcher": {"id": "R-1", "credential": True, "irb_valid": True, "institution": "org_neuroimg"}}
    tok = svc.open_session(res["researcher"], "P-1", "org_neuroimg", "S", "k")["token"]
    ws = Workspace(svc)
    t0 = time.perf_counter()
    ws.start(tok)
    opened = 0
    for g in groups[1:]:
        ring.add({c: keys[c] for c in g}, time.time() + 3600)
        ws.apply_delta(svc.delta(tok, ws.version))
    for c in [c for g in groups for c in g]:
        ws.open(c, blobs[c])
        opened += 1
    t_ring = time.perf_counter() - t0
    fetch_ring = svc.fetches
    # key per request: every open is its own key issue (a signed manifest check and an unwrap each)
    svc2 = KeyService()
    svc2.register(ring, bytes(owner.verify_key).hex())
    tok2 = svc2.open_session(res["researcher"], "P-1", "org_neuroimg", "S", "k")["token"]
    t0 = time.perf_counter()
    for c in [c for g in groups for c in g]:
        r = svc2.fetch(tok2)
        b = bytes.fromhex(r["entries"][c])
        k = AESGCM(bytes.fromhex(r["grant_key"])).decrypt(b[:12], b[12:], c.encode())
        AESGCM(k).decrypt(bytes.fromhex(blobs[c]["nonce"]), bytes.fromhex(blobs[c]["ct"]), c.encode())
    t_per = time.perf_counter() - t0
    return {"chunks": opened, "expansions": expansions, "keyring": {"fetches": fetch_ring, "seconds": round(t_ring, 4)},
            "key_per_request": {"fetches": svc2.fetches, "seconds": round(t_per, 4)}}
