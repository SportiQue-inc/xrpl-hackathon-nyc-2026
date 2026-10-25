"""A participant approves a research request with their own passkey (WebAuthn).

The engine writes an approval statement: who asks, the purpose, the items and weeks, the price, and
the consent document it rests on. The person's authenticator signs a challenge derived from that
statement, so the signature covers exactly what was shown. Once a person has a passkey, approving
without a valid assertion is refused. The verified statement hash then goes into:
- the EscrowCreate memo of every order it approves (`consent:<hash16>`);
- the hash-chained event log (`passkey_signed`, then `approval_bound`);
- the participant view (`approvals`).

Two places can hold the passkey:
- UniQdata (`UniQdataBackend`). The statement goes into a pending UniQdata consent. UniQdata issues
  the challenge from that consent's hash, verifies the assertion and anchors it. The engine only
  relays. The calls are the ones in /mnt/project-files/passkey-approval-contract.md ("UniQdata answers").
- Here (`LocalBackend`), when no UniQdata account is connected. The engine checks the challenge, the
  RP ID, the origin, user verification and the ES256 signature itself.

The browser calls are the same either way. WebAuthn binary fields travel as base64url, and
the field names follow UniQdata's (clientDataJson, attestationObject, authenticatorData).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from ..engine import canonical, sha256_hex

SCHEMA = """
CREATE TABLE IF NOT EXISTS passkeys (
  person_id TEXT NOT NULL, credential_id TEXT NOT NULL PRIMARY KEY, public_key TEXT NOT NULL,
  rp_id TEXT NOT NULL, sign_count INTEGER NOT NULL, source TEXT NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS passkey_challenges (
  id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL, purpose TEXT NOT NULL,
  request_id INTEGER, statement TEXT, statement_hash TEXT NOT NULL, challenge TEXT NOT NULL,
  status TEXT NOT NULL, backend TEXT NOT NULL, uniqdata_consent_id TEXT, consent_hash TEXT,
  credential_id TEXT, orders TEXT, expires_at REAL NOT NULL, ts REAL NOT NULL, signed_at REAL
);
"""

TTL_S = 300


def rp_id() -> str:
    return os.environ.get("AGENTRAIL_PASSKEY_RP_ID", "localhost")


def origins() -> set[str]:
    raw = os.environ.get("AGENTRAIL_PASSKEY_ORIGINS", "http://localhost:8000")
    return {o.strip().rstrip("/") for o in raw.split(",") if o.strip()}


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---------- where the passkey lives ----------

class LocalBackend:
    """The engine verifies the passkey itself (no UniQdata account connected)."""
    name = "engine"

    def __init__(self, store):
        self.store = store

    def registered(self, pid: str) -> list[str]:
        return [r["credential_id"] for r in self.store.q("SELECT credential_id FROM passkeys WHERE person_id=?", pid)]

    def register_options(self, pid: str, pseudonym: str) -> dict:
        ch = secrets.token_bytes(32)
        _open(self.store, pid, "register", None, None, ch.hex(), b64u(ch), self.name)
        return {"challenge": b64u(ch), "rp": {"id": rp_id(), "name": "UniQdata research contribution (synthetic)"},
                "user": {"id": b64u(hashlib.sha256(pid.encode()).digest()[:16]), "name": pseudonym,
                         "displayName": pseudonym},
                "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
                "authenticatorSelection": {"residentKey": "preferred", "userVerification": "required"},
                "attestation": "none", "timeout": TTL_S * 1000,
                "excludeCredentials": [{"type": "public-key", "id": c} for c in self.registered(pid)]}

    def register_complete(self, pid: str, body: dict) -> str:
        cd = _client_data(body["clientDataJson"], "webauthn.create")
        row = _take(self.store, pid, "register", challenge=cd["challenge"])
        att = _cbor_decode(unb64u(body["attestationObject"]))
        auth = att["authData"]
        _check_auth(auth)
        if not auth[32] & 0x40:
            raise PermissionError("the authenticator did not return a credential")
        n = int.from_bytes(auth[53:55], "big")
        cred, cose = auth[55:55 + n], _cbor_decode(auth[55 + n:])
        if b64u(cred) != body["credentialId"]:
            raise PermissionError("the authenticator data does not carry this credential")
        if cose.get(3) != -7 or cose.get(-1) != 1:
            raise PermissionError("only ES256 (P-256) passkeys are accepted")
        pub = ec.EllipticCurvePublicNumbers(int.from_bytes(cose[-2], "big"), int.from_bytes(cose[-3], "big"),
                                            ec.SECP256R1()).public_key()
        pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        with self.store.tx() as c:
            c.execute("INSERT INTO passkeys VALUES (?,?,?,?,?,?,?)",
                      (pid, body["credentialId"], pem, rp_id(), int.from_bytes(auth[33:37], "big"), self.name,
                       time.time()))
            c.execute("UPDATE passkey_challenges SET status='used', credential_id=?, signed_at=? WHERE id=?",
                      (body["credentialId"], time.time(), row["id"]))
        return body["credentialId"]

    def approval_options(self, pid: str, stmt: dict, sh: str) -> dict:
        return {"challenge": b64u(bytes.fromhex(sh)), "rpId": rp_id(), "timeout": TTL_S * 1000,
                "userVerification": "required",
                "allowCredentials": [{"type": "public-key", "id": c} for c in self.registered(pid)]}, None, None

    def approve(self, pid: str, row, assertion: dict) -> str:
        cd = _client_data(assertion["clientDataJson"], "webauthn.get")
        if cd["challenge"] != row["challenge"]:
            raise PermissionError("the signature is for another statement")
        key = self.store.one("SELECT * FROM passkeys WHERE person_id=? AND credential_id=?", pid,
                             assertion["credentialId"])
        if key is None:
            raise PermissionError("this passkey is not registered for this participant")
        auth = unb64u(assertion["authenticatorData"])
        _check_auth(auth)
        count = int.from_bytes(auth[33:37], "big")
        if count and count <= key["sign_count"]:
            raise PermissionError("the signature counter went backwards (a copied authenticator?)")
        pub = serialization.load_pem_public_key(key["public_key"].encode())
        try:
            pub.verify(unb64u(assertion["signature"]),
                       auth + hashlib.sha256(unb64u(assertion["clientDataJson"])).digest(), ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            raise PermissionError("the passkey signature does not verify")
        with self.store.tx() as c:
            c.execute("UPDATE passkeys SET sign_count=? WHERE credential_id=?", (count, assertion["credentialId"]))
        return assertion["credentialId"]


class UniQdataBackend:
    """UniQdata holds the passkey and verifies it. `client` is the person's UniQdata session
    (uniqdata_live.UniQdataClient) and must offer: passkey_register_options(), passkey_register_complete(body),
    passkey_registered(), consent_create_pending(statement, statement_hash) -> {id, consent_hash},
    consent_attestation_options(id) -> PublicKeyCredentialRequestOptions, and consent_approve(id, assertion)
    -> {status}."""
    name = "uniqdata"

    def __init__(self, store, client):
        self.store, self.client = store, client

    def registered(self, pid: str) -> list[str]:
        """Only passkeys the person registered on this page count. The same UniQdata account also
        holds the agent's key, and a signature by that key must not pass for the person's own."""
        return [r["credential_id"] for r in self.store.q(
            "SELECT credential_id FROM passkeys WHERE person_id=? AND source=?", pid, self.name)]

    def register_options(self, pid: str, pseudonym: str) -> dict:
        return self.client.passkey_register_options()

    def register_complete(self, pid: str, body: dict) -> str:
        cred = self.client.passkey_register_complete(body)["credential_id"]
        with self.store.tx() as c:
            c.execute("INSERT OR REPLACE INTO passkeys VALUES (?,?,?,?,?,?,?)",
                      (pid, cred, "", rp_id(), 0, self.name, time.time()))
        return cred

    def approval_options(self, pid: str, stmt: dict, sh: str):
        c = self.client.consent_create_pending(stmt, sh)
        return self.client.consent_attestation_options(c["id"]), c["id"], c["consent_hash"]

    def approve(self, pid: str, row, assertion: dict) -> str:
        if assertion["credentialId"] not in self.registered(pid):
            raise PermissionError("this is not the passkey the participant registered for approvals")
        r = self.client.consent_approve(row["uniqdata_consent_id"], assertion)
        if r.get("status") != "APPROVED":
            raise PermissionError(f"UniQdata did not approve the consent ({r.get('status')})")
        return assertion["credentialId"]


def backend(w, pid: str):
    client = getattr(w, "uniqdata_clients", {}).get(pid)
    return UniQdataBackend(w.store, client) if client else LocalBackend(w.store)


# ---------- the flow ----------

def has_passkey(w, pid: str) -> bool:
    return bool(backend(w, pid).registered(pid))


def register_options(w, pid: str, pseudonym: str) -> dict:
    return {"publicKey": backend(w, pid).register_options(pid, pseudonym)}


def register_complete(w, pid: str, body: dict) -> dict:
    b = backend(w, pid)
    cred = b.register_complete(pid, body)
    w.store.log(pid, "passkey_registered", f"{pid} registered a passkey for research approvals ({b.name})",
                {"credential": cred[:16], "rp_id": rp_id(), "held_by": b.name})
    return {"credential_id": cred}


def statement(w, pid: str, req: dict, items: list[str], price_drops: int, pseudonym: str, study: str,
              destination: str) -> dict:
    weeks = {str(wk): sorted(i for i in its if i in items) for wk, its in sorted(req["weeks"].items())}
    weeks = {k: v for k, v in weeks.items() if v}
    c = w.store.one("SELECT version, doc_hash FROM consents WHERE person_id=? AND buyer_id=?", pid, study)
    return {"kind": "research_contribution_approval", "participant": pseudonym, "study": study,
            "request": req["id"], "purpose": req["purpose"], "items": sorted({i for v in weeks.values() for i in v}),
            "weeks": weeks, "price_drops": price_drops, "escrow_destination": destination, "ledger": w.ledger.name,
            "consent": {"version": c["version"], "doc_hash": c["doc_hash"]} if c else None,
            "nonce": secrets.token_hex(8), "issued_at": int(time.time())}


def begin_approval(w, pid: str, rid: int, stmt: dict) -> dict:
    sh = sha256_hex(canonical(stmt))
    b = backend(w, pid)
    opts, consent_id, consent_hash = b.approval_options(pid, stmt, sh)
    _open(w.store, pid, "approve", rid, stmt, sh, opts["challenge"], b.name, consent_id, consent_hash)
    return {"statement": stmt, "statement_hash": sh, "uniqdata_consent_id": consent_id,
            "consent_hash": consent_hash, "held_by": b.name, "publicKey": opts}


def verify_approval(w, pid: str, rid: int, items: list[str], assertion: dict) -> dict:
    """Checks the assertion for the open statement of this request. Refuses a different request or
    other items, a stale, replaced or reused challenge, another person's passkey, or a bad signature."""
    row = w.store.one("SELECT * FROM passkey_challenges WHERE person_id=? AND purpose='approve' AND request_id=? "
                      "AND status='open' ORDER BY id DESC LIMIT 1", pid, rid)
    if row is None:
        raise PermissionError("no open challenge for this request; ask for a new one")
    row = _take(w.store, pid, "approve", challenge=row["challenge"])
    stmt = json.loads(row["statement"])
    if sorted(items) != stmt["items"]:
        raise PermissionError("the signed statement covers other items")
    cred = backend(w, pid).approve(pid, row, assertion)
    with w.store.tx() as c:
        c.execute("UPDATE passkey_challenges SET status='verified', credential_id=?, signed_at=? WHERE id=?",
                  (cred, time.time(), row["id"]))
    w.store.log(pid, "passkey_signed", f"{pid} signed request {rid} with their passkey (statement "
                f"{row['statement_hash'][:12]})", {"request": rid, "statement_hash": row["statement_hash"],
                                                   "consent_hash": row["consent_hash"], "credential": cred[:16],
                                                   "items": stmt["items"], "verified_by": row["backend"]})
    return {"uniqdata_consent_id": row["uniqdata_consent_id"], "consent_hash": row["consent_hash"],
            "statement_hash": row["statement_hash"], "credential_id": cred}


def withdrawal_statement(w, pid: str, pseudonym: str, study: str, licence: str | None, held: list[dict]) -> dict:
    return {"kind": "research_withdrawal", "participant": pseudonym, "study": study, "licence": licence,
            "held_rounds": held, "ledger": w.ledger.name, "nonce": secrets.token_hex(8), "issued_at": int(time.time())}


def begin_withdrawal(w, pid: str, stmt: dict) -> dict:
    sh = sha256_hex(canonical(stmt))
    b = backend(w, pid)
    opts, consent_id, consent_hash = b.approval_options(pid, stmt, sh)
    _open(w.store, pid, "revoke", None, stmt, sh, opts["challenge"], b.name, consent_id, consent_hash)
    return {"statement": stmt, "statement_hash": sh, "uniqdata_consent_id": consent_id,
            "consent_hash": consent_hash, "held_by": b.name, "publicKey": opts}


def verify_withdrawal(w, pid: str, assertion: dict) -> dict:
    """The same checks as an approval, for the open withdrawal statement."""
    row = w.store.one("SELECT * FROM passkey_challenges WHERE person_id=? AND purpose='revoke' AND status='open' "
                      "ORDER BY id DESC LIMIT 1", pid)
    if row is None:
        raise PermissionError("no open withdrawal challenge; ask for a new one")
    row = _take(w.store, pid, "revoke", challenge=row["challenge"])
    cred = backend(w, pid).approve(pid, row, assertion)
    with w.store.tx() as c:
        c.execute("UPDATE passkey_challenges SET status='verified', credential_id=?, signed_at=? WHERE id=?",
                  (cred, time.time(), row["id"]))
    w.store.log(pid, "passkey_signed", f"{pid} signed their withdrawal with their passkey (statement "
                f"{row['statement_hash'][:12]})", {"purpose": "revoke", "statement_hash": row["statement_hash"],
                                                   "consent_hash": row["consent_hash"], "credential": cred[:16],
                                                   "verified_by": row["backend"]})
    return {"uniqdata_consent_id": row["uniqdata_consent_id"], "consent_hash": row["consent_hash"],
            "statement_hash": row["statement_hash"], "credential_id": cred}


def begin_batch(w, pid: str, entries: list[tuple[int, dict]]) -> dict:
    """Several requests, each with its own statement and separate consents, signed by one passkey prompt.
    The challenge is the hash of the batch; each request keeps its own statement and statement hash."""
    batch = {"kind": "research_consent_batch", "statements": [s for _, s in entries],
             "nonce": secrets.token_hex(8), "issued_at": int(time.time())}
    bh = sha256_hex(canonical(batch))
    b = backend(w, pid)
    opts, consent_id, consent_hash = b.approval_options(pid, batch, bh)
    out = []
    for rid, stmt in entries:
        sh = sha256_hex(canonical(stmt))
        _open(w.store, pid, "approve", rid, {**stmt, "batch_hash": bh}, sh, opts["challenge"], b.name,
              consent_id, consent_hash)
        out.append({"request": rid, "statement": stmt, "statement_hash": sh})
    return {"batch_hash": bh, "statements": out, "uniqdata_consent_id": consent_id, "consent_hash": consent_hash,
            "held_by": b.name, "publicKey": opts}


def verify_batch(w, pid: str, items_by_request: dict[int, list[str]], assertion: dict) -> dict[int, dict]:
    """One assertion over the open batch. Every request of the batch must be answered with exactly the
    items it was signed for. Rows end 'signed'; each is set 'verified' just before its approval is applied."""
    challenge = _client_data(assertion["clientDataJson"], "webauthn.get")["challenge"]
    rows = w.store.q("SELECT * FROM passkey_challenges WHERE person_id=? AND purpose='approve' AND challenge=? "
                     "AND status='open'", pid, challenge)
    if not rows:
        raise PermissionError("no open challenge matches this signature (used, replaced or never issued)")
    if any(r["expires_at"] < time.time() for r in rows):
        raise PermissionError("the challenge expired; ask for a new one")
    if {r["request_id"] for r in rows} != set(items_by_request):
        raise PermissionError("the signature covers other requests")
    for r in rows:
        if sorted(items_by_request[r["request_id"]]) != json.loads(r["statement"])["items"]:
            raise PermissionError("the signed statement covers other items")
    cred = backend(w, pid).approve(pid, rows[0], assertion)
    now = time.time()
    with w.store.tx() as c:
        c.execute("UPDATE passkey_challenges SET status='signed', credential_id=?, signed_at=? WHERE person_id=? AND "
                  "purpose='approve' AND challenge=? AND status='open'", (cred, now, pid, challenge))
    out = {}
    for r in rows:
        stmt = json.loads(r["statement"])
        w.store.log(pid, "passkey_signed", f"{pid} signed request {r['request_id']} with their passkey (statement "
                    f"{r['statement_hash'][:12]}, batch {stmt.get('batch_hash', '')[:12]})",
                    {"request": r["request_id"], "statement_hash": r["statement_hash"], "batch_hash": stmt.get("batch_hash"),
                     "consent_hash": r["consent_hash"], "credential": cred[:16], "items": stmt["items"],
                     "consents": [c["kind"] for c in stmt.get("consents") or []], "verified_by": r["backend"]})
        out[r["request_id"]] = {"uniqdata_consent_id": r["uniqdata_consent_id"], "consent_hash": r["consent_hash"],
                                "statement_hash": r["statement_hash"], "batch_hash": stmt.get("batch_hash"),
                                "credential_id": cred}
    return out


def mark_verified(store, pid: str, statement_hash: str):
    with store.tx() as c:
        c.execute("UPDATE passkey_challenges SET status='verified' WHERE person_id=? AND statement_hash=? AND "
                  "status='signed'", (pid, statement_hash))


def memo_tag(store, seller: str) -> str:
    """`|consent:<hash16>` for an order created while its seller's signed approval is being applied."""
    r = store.one("SELECT statement_hash FROM passkey_challenges WHERE person_id=? AND purpose='approve' AND "
                  "status='verified' ORDER BY id DESC LIMIT 1", seller)
    return f"|consent:{r['statement_hash'][:16]}" if r else ""


def bind(store, pid: str, statement_hash: str, orders: list[dict], failed: bool = False):
    with store.tx() as c:
        c.execute("UPDATE passkey_challenges SET status=?, orders=? WHERE person_id=? AND statement_hash=? AND "
                  "status='verified'", ("failed" if failed else "bound", json.dumps(orders), pid, statement_hash))
    if not failed:
        store.log(pid, "approval_bound", f"signed statement {statement_hash[:12]} bound to {len(orders)} escrow(s)",
                  {"statement_hash": statement_hash, "orders": orders})


def approvals(store, pid: str) -> list[dict]:
    return [{"request": r["request_id"], "statement": json.loads(r["statement"]), "statement_hash": r["statement_hash"],
             "uniqdata_consent_id": r["uniqdata_consent_id"], "consent_hash": r["consent_hash"],
             "status": r["status"], "verified_by": r["backend"], "credential": (r["credential_id"] or "")[:16],
             "orders": json.loads(r["orders"] or "[]"), "signed_at": r["signed_at"]}
            for r in store.q("SELECT * FROM passkey_challenges WHERE person_id=? AND purpose='approve' AND "
                             "status IN ('signed','verified','bound') ORDER BY id", pid)]


# ---------- checks ----------

def _open(store, pid, purpose, rid, stmt, sh, challenge, backend_name, consent_id=None, consent_hash=None):
    now = time.time()
    with store.tx() as c:
        c.execute("UPDATE passkey_challenges SET status='replaced' WHERE person_id=? AND purpose=? AND status='open' "
                  "AND request_id IS ?", (pid, purpose, rid))
        c.execute("INSERT INTO passkey_challenges (person_id, purpose, request_id, statement, statement_hash, challenge, "
                  "status, backend, uniqdata_consent_id, consent_hash, expires_at, ts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (pid, purpose, rid, json.dumps(stmt) if stmt else None, sh, challenge, "open", backend_name,
                   consent_id, consent_hash, now + TTL_S, now))


def _take(store, pid, purpose, challenge):
    row = store.one("SELECT * FROM passkey_challenges WHERE person_id=? AND purpose=? AND challenge=? AND status='open'",
                    pid, purpose, challenge)
    if row is None:
        raise PermissionError("no open challenge matches this signature (used, replaced or never issued)")
    if row["expires_at"] < time.time():
        raise PermissionError("the challenge expired; ask for a new one")
    return row


def _client_data(b64: str, kind: str) -> dict:
    cd = json.loads(unb64u(b64))
    if cd.get("type") != kind:
        raise PermissionError(f"client data is not {kind}")
    if cd.get("origin", "").rstrip("/") not in origins():
        raise PermissionError(f"origin {cd.get('origin')} is not allowed for passkeys")
    if cd.get("crossOrigin"):
        raise PermissionError("cross-origin passkey use is not allowed")
    return cd


def _check_auth(auth: bytes):
    if len(auth) < 37 or auth[:32] != hashlib.sha256(rp_id().encode()).digest():
        raise PermissionError(f"the passkey belongs to another site (RP ID is not {rp_id()})")
    if not auth[32] & 0x01 or not auth[32] & 0x04:
        raise PermissionError("the authenticator did not confirm the person (user presence and verification)")


def _cbor_decode(data: bytes):
    """Minimal CBOR reader: unsigned and negative ints, byte and text strings, arrays and maps, which
    is all a WebAuthn attestation object and a COSE key use."""
    def item(i):
        ib = data[i]
        major, ai = ib >> 5, ib & 0x1F
        i += 1
        if ai < 24:
            n = ai
        elif ai in (24, 25, 26, 27):
            size = 1 << (ai - 24)
            n, i = int.from_bytes(data[i:i + size], "big"), i + size
        else:
            raise ValueError("indefinite CBOR lengths are not used by WebAuthn")
        if major == 0:
            return n, i
        if major == 1:
            return -1 - n, i
        if major in (2, 3):
            v = data[i:i + n]
            return (v if major == 2 else v.decode()), i + n
        if major == 4:
            out = []
            for _ in range(n):
                v, i = item(i)
                out.append(v)
            return out, i
        if major == 5:
            out = {}
            for _ in range(n):
                k, i = item(i)
                out[k], i = item(i)
            return out, i
        raise ValueError(f"CBOR major type {major} is not used by WebAuthn")
    return item(0)[0]
