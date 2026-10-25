"""Provenance from the source to the delivered bundle.

1. Source attestation. The issuer of a column (device vendor, survey app, clinic, robot fleet) signs,
   for each export: the column, the slots it covers (in the issuer's own enrolment-relative slot
   numbers), a hash of the native values, and the holder key the export was made for. The holder key
   is the provider's study-specific key, so an export made for one person cannot be passed off as
   another's. An issuer counts only if a registry has issued it a DATA_SOURCE Credential on the ledger
   and its signing key is the one registered with that registry.
2. Normalization. The steps from native fields to the contract's column (rename, unit factor) are
   listed; the bundle carries the native values too, so the buyer re-runs the steps and compares.
3. The manifest: contract hash, consent version hash, attestations, normalization steps, the
   provider's own QC counts; signed by the holder key. The manifest sits inside the bundle, so the
   bundle hash in the EscrowCreate memo covers it.

A file hash alone proves only that the bytes did not change, not where they came from; the checks
here are what the provenance claim rests on.
"""
from __future__ import annotations

import hashlib

from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .terms import canonical

DATA_SOURCE = "DATA_SOURCE"
CONVERSIONS = {("h/day", "min/day"): 60.0, ("min/day", "min/day"): 1.0, ("bpm", "bpm"): 1.0,
               ("score", "score"): 1.0, ("mmHg", "mmHg"): 1.0, ("points", "points"): 1.0,
               ("m/s2", "m/s2"): 1.0}


def values_hash(values: list) -> str:
    return hashlib.sha256(canonical(values).encode()).hexdigest()


class SourceIssuer:
    def __init__(self, name: str, seed: bytes | None = None):
        self.name = name
        self._key = SigningKey(seed) if seed else SigningKey.generate()
        self.verify_hex = self._key.verify_key.encode(HexEncoder).decode()

    def attest(self, holder: str, column: str, slots: list[int], native: list) -> dict:
        body = {"issuer": self.name, "holder": holder, "column": column, "slots": slots,
                "values": values_hash(native)}
        return {**body, "sig": self._key.sign(canonical(body).encode()).signature.hex()}

    def seal(self, holder: str, column: str, slots: list[int], native: list, key: bytes) -> tuple[dict, bytes]:
        """Provenance stamped at intake: when the record enters the person's store (FHIR export, device
        sync), the source encrypts it with an intake key kept in the person's vault and signs the
        sealed bytes. At sale time there is no round trip to the source: the bundle carries the sealed
        records as stamped, and the buyer checks the signatures before paying. A value changed after
        intake would need the source's signature again."""
        sealed = seal_values(native, key, column)
        body = {"issuer": self.name, "holder": holder, "column": column, "slots": slots,
                "values": values_hash(native), "sealed": hashlib.sha256(sealed).hexdigest()}
        return {**body, "sig": self._key.sign(canonical(body).encode()).signature.hex()}, sealed


def seal_values(native: list, key: bytes, column: str) -> bytes:
    n = hashlib.sha256(f"seal|{column}".encode()).digest()[:12]     # one K per window and column set
    return n + AESGCM(key).encrypt(n, canonical(native).encode(), column.encode())


def open_values(sealed: bytes, key: bytes, column: str) -> list:
    import json
    return json.loads(AESGCM(key).decrypt(sealed[:12], sealed[12:], column.encode()))


class Registry:
    """Which issuers are accepted sources: signing key here, DATA_SOURCE Credential on the ledger."""

    def __init__(self, ledger, registry_addr: str):
        self.ledger, self.addr = ledger, registry_addr
        self.keys: dict[str, str] = {}          # issuer name -> verify key hex
        self.accounts: dict[str, str] = {}      # issuer name -> XRPL account
        self.txs: dict[str, list[str]] = {}

    def register(self, issuer: SourceIssuer, account: str) -> list[str]:
        self.keys[issuer.name], self.accounts[issuer.name] = issuer.verify_hex, account
        self.txs[issuer.name] = self.ledger.issue_credential(self.addr, account, DATA_SOURCE)
        return self.txs[issuer.name]

    def accepted(self, issuer: str) -> bool:
        acc = self.accounts.get(issuer)
        return bool(acc) and self.ledger.has_credential(acc, self.addr, DATA_SOURCE)


def verify_attestation(a: dict, registry: Registry) -> str | None:
    """None if valid, else the failure code."""
    if a.get("issuer") not in registry.keys:
        return "unregistered_source"
    body = {k: a[k] for k in ("issuer", "holder", "column", "slots", "values", "sealed") if k in a}
    try:
        VerifyKey(registry.keys[a["issuer"]], encoder=HexEncoder).verify(canonical(body).encode(),
                                                                       bytes.fromhex(a["sig"]))
    except (BadSignatureError, ValueError):
        return "bad_signature"
    if not registry.accepted(a["issuer"]):
        return "source_not_credentialed"
    return None


class Holder:
    """The provider's study-specific signing key (one per provider and buyer)."""

    def __init__(self, seed: bytes | None = None):
        self._key = SigningKey(seed) if seed else SigningKey.generate()
        self.pub = self._key.verify_key.encode(HexEncoder).decode()

    def sign(self, body: dict) -> str:
        return self._key.sign(canonical(body).encode()).signature.hex()


def manifest(holder: Holder, contract_hash: str, consent_hash: str, window: int, attestations: list[dict],
             steps: list[dict], qc: dict) -> dict:
    body = {"contract": contract_hash, "consent": consent_hash, "window": window, "holder": holder.pub,
            "attestations": attestations, "normalization": steps, "qc": qc}
    return {**body, "holder_sig": holder.sign(body)}


def verify_manifest(m: dict, registry: Registry, contract, expected_holder: str | None,
                    slots_for_window) -> list[dict]:
    """Checks that need no values: done before the escrow is created. Returns failure signals."""
    out = []
    body = {k: m[k] for k in ("contract", "consent", "window", "holder", "attestations", "normalization", "qc")}
    try:
        VerifyKey(m["holder"], encoder=HexEncoder).verify(canonical(body).encode(), bytes.fromhex(m["holder_sig"]))
    except (BadSignatureError, ValueError, KeyError):
        out.append({"code": "bad_signature", "where": "manifest"})
    if m["contract"] != contract.hash:
        out.append({"code": "wrong_contract"})
    if expected_holder and m["holder"] != expected_holder:
        out.append({"code": "different_person", "where": "manifest holder"})
    want = {(t["column"], t["source"]) for t in contract.terms if m["window"] in t["windows"]}
    got = {(a["column"], a["issuer"]) for a in m["attestations"]}
    for a in m["attestations"]:
        bad = verify_attestation(a, registry)
        if bad:
            out.append({"code": "wrong_source", "detail": bad, "column": a["column"], "issuer": a["issuer"]})
        if a["holder"] != m["holder"]:
            out.append({"code": "different_person", "column": a["column"],
                        "detail": "export was made for another holder key"})
        lo, hi = slots_for_window(m["window"])
        if not a["slots"] or min(a["slots"]) < lo or max(a["slots"]) > hi:
            out.append({"code": "wrong_period", "column": a["column"], "window": m["window"],
                        "slots": [min(a["slots"]), max(a["slots"])] if a["slots"] else []})
    for col, src in sorted(want - got):
        if not any(x["column"] == col for x in out):
            out.append({"code": "wrong_source", "column": col, "detail": f"no attestation from {src}"})
    return out


def wrap_key(intake_key: bytes, escrow_key: bytes, column: str) -> str:
    """The intake key travels inside the bundle wrapped with the escrow's K: it opens only once the
    escrow is finished."""
    n = hashlib.sha256(f"wrap|{column}".encode()).digest()[:12]
    return (n + AESGCM(escrow_key).encrypt(n, intake_key, column.encode())).hex()


def unwrap_key(wrapped: str, escrow_key: bytes, column: str) -> bytes:
    b = bytes.fromhex(wrapped)
    return AESGCM(escrow_key).decrypt(b[:12], b[12:], column.encode())


def verify_seals(m: dict, payload: dict) -> list[dict]:
    """Before payment: every column carries the source's intake stamp, and the sealed bytes delivered
    are exactly the ones the source signed (issuer key and DATA_SOURCE credential are checked with
    the attestation)."""
    out = []
    for a in m["attestations"]:
        if "sealed" not in a:
            out.append({"code": "unsealed", "column": a["column"], "detail": "the source did not seal this column"})
            continue
        blob = (payload.get("sealed") or {}).get(a["column"])
        if blob is None or hashlib.sha256(bytes.fromhex(blob)).hexdigest() != a["sealed"]:
            out.append({"code": "tampered", "column": a["column"],
                        "detail": "sealed records differ from what the source signed at intake: refused before payment"})
    return out


def open_sealed(m: dict, payload: dict, escrow_key: bytes) -> list[dict]:
    """After the key reveal: unwrap each intake key with K and open the stamped records; they must be
    the values the bundle's rows were built from."""
    out = []
    for a in m["attestations"]:
        col = a["column"]
        if col not in (payload.get("sealed") or {}):
            continue
        try:
            vals = open_values(bytes.fromhex(payload["sealed"][col]), unwrap_key(payload["wrapped"][col], escrow_key, col), col)
        except Exception:
            out.append({"code": "unopenable", "column": col, "detail": "the stamped records do not open with the released key"})
            continue
        if values_hash(vals) != a["values"] or vals != payload["native"].get(col):
            out.append({"code": "tampered", "column": col, "detail": "rows differ from the stamped records"})
    return out


def verify_values(m: dict, payload: dict) -> list[dict]:
    """After the key is revealed: native values match the attestation, and the normalization steps,
    re-run by the buyer, give exactly the delivered column."""
    out = []
    steps = {s["column"]: s for s in m["normalization"]}
    for a in m["attestations"]:
        native = payload["native"].get(a["column"])
        if native is None or values_hash(native) != a["values"]:
            out.append({"code": "tampered", "column": a["column"], "detail": "native values differ from the attested hash"})
            continue
        s = steps.get(a["column"], {"factor": 1.0})
        expect = [None if v is None else round(v * s["factor"], 3) for v in native]
        got = [r.get(a["column"]) for r in payload["rows"]]
        if expect != got:
            out.append({"code": "tampered", "column": a["column"], "detail": "normalization does not reproduce the rows"})
    return out
