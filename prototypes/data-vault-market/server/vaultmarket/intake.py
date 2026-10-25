"""Intake: what happens to a file the moment it is uploaded.

1. Classify it into the domain ontology (which kind of record is this?).
2. Screen it: some data can never be listed (health records with diagnoses, identity documents, data
   about children); raw data with problems can be listed only after cleaning, for a fee.
3. Standardize and clean: one schema per kind, duplicates and impossible values dropped.
4. Attest: the intake service signs what it checked and the Merkle root of the cleaned records, so a
   buyer can verify sampled records against the root before paying.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

from nacl.signing import SigningKey

from . import config, data
from .rail import merkle_root

_KEY_FILE = os.path.join(config.DATA_DIR, "intake_key.local")
if not os.path.exists(_KEY_FILE):
    with open(_KEY_FILE, "wb") as f:
        f.write(bytes(SigningKey.generate()))
    os.chmod(_KEY_FILE, 0o600)
SIGNER = SigningKey(open(_KEY_FILE, "rb").read())
INTAKE_PUBKEY = SIGNER.verify_key.encode().hex()

CLEAN_FEE = {"gps_track": 0.2, "sleep_log": 0.5, "purchase_receipts": 0.2, "audio": 0.3, "air": 0.2}   # price units

SENSITIVE_KEYS = {"diagnosis": "a diagnosis", "icd10": "diagnosis codes", "medications": "medications", "prescription": "prescriptions",
                  "passport_no": "a passport number", "ssn": "a social security number", "mrn": "a medical record number"}


def classify(body: dict) -> str | None:
    if "points" in body:
        return "gps_track"
    if "nights" in body:
        return "sleep_log"
    if "receipts" in body:
        return "purchase_receipts"
    if "clips" in body:
        return "audio"
    if "readings" in body:
        return "air"
    return None


def records(kind: str, body: dict) -> list:
    return {"gps_track": lambda: [body], "sleep_log": lambda: body["nights"], "purchase_receipts": lambda: body["receipts"],
            "audio": lambda: body["clips"], "air": lambda: body["readings"]}[kind]()


def screen(body: dict) -> dict:
    """-> {verdict: ok|clean|block, kind, why, issues, fee}"""
    flat = json.dumps(body).lower()
    for k, what in SENSITIVE_KEYS.items():
        if f'"{k}"' in flat:
            return {"verdict": "block", "kind": classify(body), "why": f"it contains {what}. Records like this cannot be listed on the open market; they need a per-use consent flow", "issues": [k]}
    if body.get("subject_age") is not None and int(body["subject_age"]) < 18 or '"minor": true' in flat:
        return {"verdict": "block", "kind": classify(body), "why": "it is about a child. Data about minors is never sold here", "issues": ["minor"]}
    kind = classify(body)
    if not kind:
        return {"verdict": "block", "kind": None, "why": "I could not tell what kind of data this is, so it stays private", "issues": ["unknown"]}
    issues = []
    if kind == "sleep_log":
        nights = [n.get("night") for n in body["nights"]]
        if len(nights) != len(set(nights)):
            issues.append("duplicate nights")
        if any(not (0 < float(n.get("total_h", n.get("hours", 0)) or 0) < 16) for n in body["nights"]):
            issues.append("impossible sleep durations")
        if any("hours" in n and "total_h" not in n for n in body["nights"]):
            issues.append("non-standard field names")
    if kind == "gps_track":
        if any(not (30 <= p.get("hr", 120) <= 220) for p in body["points"]):
            issues.append("heart-rate spikes from a loose strap")
        if len(body["points"]) < 8:
            issues.append("too few points")
    if kind == "purchase_receipts":
        ids = [r.get("receipt") for r in body["receipts"]]
        if len(ids) != len(set(ids)):
            issues.append("the same receipt twice")
    if kind == "audio" and any(c.get("snr_db", 30) < 10 for c in body["clips"]):
        issues.append("clips too noisy to use")
    if issues:
        return {"verdict": "clean", "kind": kind, "why": "; ".join(issues), "issues": issues, "fee": CLEAN_FEE[kind]}
    return {"verdict": "ok", "kind": kind, "why": "schema, value ranges and duplicates all check out", "issues": []}


def clean(kind: str, body: dict) -> dict:
    b = json.loads(json.dumps(body))
    if kind == "sleep_log":
        seen, out = set(), []
        for n in b["nights"]:
            if "hours" in n and "total_h" not in n:
                n["total_h"] = n.pop("hours")
            if n["night"] in seen or not (0 < float(n["total_h"]) < 16):
                continue
            seen.add(n["night"]); out.append(n)
        b["nights"] = out
        b["_fps"] = list(dict.fromkeys(b.get("_fps", [])))
    if kind == "gps_track":
        b["points"] = [p for p in b["points"] if 30 <= p.get("hr", 120) <= 220]
    if kind == "purchase_receipts":
        seen, out = set(), []
        for r in b["receipts"]:
            if r["receipt"] not in seen:
                seen.add(r["receipt"]); out.append(r)
        b["receipts"] = out
    if kind == "audio":
        b["clips"] = [c for c in b["clips"] if c.get("snr_db", 30) >= 10]
    return b


def leaves(kind: str, clean_body: dict) -> list[str]:
    """The Merkle leaves of a listed file: its records, without the attestation itself."""
    if "_people" in clean_body and "records" in clean_body:          # a bundle of lots
        return [data.dumps(r) for r in clean_body["records"]]
    body = {k: v for k, v in clean_body.items() if k != "_attestation"}
    return [data.dumps(r) for r in records(kind, body)]


def attest(kind: str, clean_body: dict, checks: list[str], cleaned: bool) -> dict:
    lv = leaves(kind, clean_body)
    body = {"issuer": "vaultmarket-intake", "kind": kind, "schema": f"{kind}/v1", "records": len(lv), "merkle_root": merkle_root(lv),
            "checks": checks, "cleaned": cleaned, "identifiers_removed": sorted(data.DIRECT)}
    msg = data.dumps(body).encode()
    body["sig"] = base64.b64encode(SIGNER.sign(msg).signature).decode()
    body["pubkey"] = INTAKE_PUBKEY
    return body


def verify_attestation(att: dict) -> bool:
    from nacl.signing import VerifyKey
    a = {k: v for k, v in att.items() if k not in ("sig", "pubkey")}
    try:
        VerifyKey(bytes.fromhex(att["pubkey"])).verify(data.dumps(a).encode(), base64.b64decode(att["sig"]))
        return att["pubkey"] == INTAKE_PUBKEY
    except Exception:
        return False
