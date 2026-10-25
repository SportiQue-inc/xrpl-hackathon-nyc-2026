"""Pseudonymization, reimplemented here after the interfaces of the people's store (UniQdata), plus
the imaging steps that store does not have. Nothing is imported from those repositories.

Same interfaces:
  research_ref(person, secret)       HMAC-SHA256 over a purpose string and the person id ("rmr_v1_...")
  participant_number(study, seq)     per-study sequence ("UQ-0007"); only the store can re-link it
  deidentify(payload)                suppress direct and quasi identifiers anywhere in the payload,
                                     pseudonymize stable keys with a per-request salted HMAC, truncate
                                     timestamps to the day, bucket age into <40 / 40-64 / 65+,
                                     drop coded clinical items carried by fewer than k=5 subjects

New for imaging (DICOM):
  remap_uid(uid, secret)             HMAC with its own secret into the 2.25.<integer> UID form
  date_shift_days(person, secret)    one consistent shift per subject, so intervals survive
  burned_in_gate(dicom)              an image that says or looks like it has burned-in text is
                                     blocked, not guessed at

Secrets: each purpose has its own secret, read from its own environment variable or generated per
process. There is no default secret and no reuse of another key (the store's weak fallbacks are not
carried over). This lowers the risk that a record is linked back to a person; it does not remove it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

_SECRETS: dict[str, bytes] = {}


def secret(purpose: str) -> bytes:
    if purpose not in _SECRETS:
        env = os.environ.get(f"AGENTRAIL_DEID_{purpose.upper()}_SECRET")
        _SECRETS[purpose] = env.encode() if env else os.urandom(32)
    return _SECRETS[purpose]


def research_ref(person_id: str, key: bytes | None = None) -> str:
    mac = hmac.new(key or secret("research_ref"), b"agentrail/research-membership/v1\x00" + person_id.encode(),
                   hashlib.sha256).digest()
    return "rmr_v1_" + base64.urlsafe_b64encode(mac).decode().rstrip("=")


def participant_number(prefix: str, seq: int) -> str:
    return f"{prefix}-{seq:04d}"


NEVER = {"person_id", "wallet_address", "email", "phone", "name", "dob", "birth_date", "year_of_birth",
         "national_id", "rrn", "ssn", "passport", "address", "postal_code", "zip", "ip", "device_id", "user_id",
         "account_id", "PatientName", "PatientID", "PatientBirthDate", "PatientAddress", "OtherPatientIDs",
         "ReferringPhysicianName", "InstitutionName"}
K_MIN = 5


def age_group(age) -> str:
    try:
        a = int(age)
    except (TypeError, ValueError):
        return "unknown"
    return "<40" if a < 40 else "40-64" if a < 65 else "65+"


def deidentify(payload, prevalence: dict | None = None, salt: bytes | None = None) -> tuple[object, dict]:
    salt = salt or os.urandom(16)
    ledger = {"dropped": [], "pseudonymized": [], "coarsened": []}

    def walk(x, path):
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                p = f"{path}.{k}" if path else k
                if k in NEVER:
                    ledger["dropped"].append(p)
                elif k == "stable_key":
                    out[k] = "pseudo_" + hmac.new(salt, str(v).encode(), hashlib.sha256).hexdigest()[:24]
                    ledger["pseudonymized"].append(p)
                elif k == "age":
                    out["age_group"] = age_group(v)
                    ledger["coarsened"].append(p)
                elif k == "code" and prevalence is not None and prevalence.get(v, 0) < K_MIN:
                    return None
                elif isinstance(v, str) and len(v) >= 19 and v[4] == "-" and v[10] in "T ":
                    out[k] = v[:10]
                    ledger["coarsened"].append(p)
                else:
                    w = walk(v, p)
                    if w is not None or v is None:
                        out[k] = w
            return out
        if isinstance(x, list):
            return [y for y in (walk(v, f"{path}[{i}]") for i, v in enumerate(x)) if y is not None]
        return x
    return walk(payload, ""), ledger


# ---------------- imaging ----------------

def remap_uid(uid: str, key: bytes | None = None) -> str:
    return "2.25." + str(int(hmac.new(key or secret("dicom_uid"), uid.encode(), hashlib.sha256).hexdigest()[:30], 16))


def date_shift_days(person: str, key: bytes | None = None) -> int:
    return int(hmac.new(key or secret("date_shift"), person.encode(), hashlib.sha256).hexdigest()[:6], 16) % 335 + 30


def burned_in_gate(d: dict) -> str | None:
    if str(d.get("BurnedInAnnotation", "")).upper() == "YES":
        return "image declares burned-in annotation"
    px = d.get("pixels") or []
    if px and len(px) > 4:
        top = [v for row in px[:2] for v in row]
        if top and sum(v >= 250 for v in top) / len(top) > 0.3:
            return "bright text-like band in the top rows"
    return None
