"""Consent signed on the participant's device. A revoked consent comes back only this way: the
participant's device signs the hash of the new consent document, and the server records the
signature next to the version. Pause / resume, approve and decline are bound to the participant's
token; only a new consent needs the signature, because it is what turns supply back on."""
from __future__ import annotations

import time

from ..agents import consent_document
from ..engine import canonical, sha256_hex
from .devices import consent_message, verify_ed25519

SCHEMA = """
CREATE TABLE IF NOT EXISTS consent_signatures (
  person_id TEXT NOT NULL, buyer_id TEXT NOT NULL, version INTEGER NOT NULL, doc_hash TEXT NOT NULL,
  signature TEXT NOT NULL, ts REAL NOT NULL, PRIMARY KEY (person_id, buyer_id, version)
);
"""


def draft(w, pid: str, buyer: str, purpose: str, items: list[str], weeks: tuple[int, int], automation: str) -> dict:
    cur = w.store.one("SELECT version, min_price_drops FROM consents WHERE person_id=? AND buyer_id=?", pid, buyer)
    v = (cur["version"] + 1) if cur else 1
    doc = consent_document(pid, buyer, purpose, sorted(items), weeks, automation,
                           cur["min_price_drops"] if cur else 0, "active", v)
    return {"version": v, "doc": doc, "doc_hash": sha256_hex(canonical(doc)),
            "min_price_drops": cur["min_price_drops"] if cur else 0}


def sign_and_apply(w, pid: str, buyer: str, purpose: str, items: list[str], weeks: tuple[int, int],
                   automation: str, signature: str, public_hex: str) -> dict:
    d = draft(w, pid, buyer, purpose, items, weeks, automation)
    if not verify_ed25519(public_hex, consent_message(pid, d["doc_hash"]), signature):
        raise PermissionError("consent signature does not match this participant's device and this document")
    pa = w.cohort_people.get(pid) if getattr(w, "cohort_people", None) else None
    pa = pa or w.people[pid]
    pa.set_consent(buyer, purpose, sorted(items), weeks=weeks, automation=automation,
                   min_price_drops=d["min_price_drops"])
    row = w.store.one("SELECT version, doc_hash FROM consents WHERE person_id=? AND buyer_id=?", pid, buyer)
    if row["doc_hash"] != d["doc_hash"]:
        raise RuntimeError("stored consent differs from the signed document")
    with w.store.tx() as c:
        c.execute("INSERT INTO consent_signatures VALUES (?,?,?,?,?,?)",
                  (pid, buyer, row["version"], row["doc_hash"], signature, time.time()))
    s = getattr(w, "study", None)
    if s is not None:
        # Returning participant: a fresh licence is issued with the next contribution.
        if pid in getattr(s, "withdrawn", set()):
            s.withdrawn.discard(pid)
        if pid in s.licences and s.licences[pid].get("clawback"):
            s.licences.pop(pid)
            pa.policy.licence_check = None
    w.store.log(pid, "consent", f"{pid} signed consent v{row['version']} on their device (doc {row['doc_hash'][:12]})",
                {"doc_hash": row["doc_hash"], "signed": True})
    return {"ok": True, "version": row["version"], "doc_hash": row["doc_hash"]}
