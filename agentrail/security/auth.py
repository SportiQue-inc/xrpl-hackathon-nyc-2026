"""Login by device signature, then short-lived access tokens.

1. POST /api/auth/challenge {sub}            -> single-use nonce, valid 120 s
2. the device signs "agentrail-login|aud|sub|nonce" with its enrolled Ed25519 key
3. POST /api/auth/token {sub, nonce, signature} -> HS256 JWT, 15 minutes, with role and scope

No passwords and no shared secrets on the client. The token carries role and scope (a participant id,
or a study id) and a jti that logout puts on a deny list. Algorithm is fixed to HS256: tokens with
another `alg` (including "none") are refused.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets as pysecrets
import threading
import time
from dataclasses import dataclass, field

from .devices import challenge_message, verify_ed25519
from .secrets import get_secret

ISS, AUD = "agentrail", "agentrail-api"
TOKEN_TTL_S = int(os.environ.get("AGENTRAIL_TOKEN_TTL_S", "900"))
CHALLENGE_TTL_S = 120
ROLES = ("participant", "researcher", "approver", "reviewer", "operator")


class AuthError(Exception):
    pass


@dataclass
class Identity:
    sub: str                 # e.g. "P-017", "researcher@org_sleeplab", "approver:owner@org_sleeplab"
    role: str
    scope: str               # participant id, or study / institution id; "*" for the operator
    public_hex: str          # enrolled device key (Ed25519)
    attrs: dict = field(default_factory=dict)   # e.g. {"signer": "owner"} for approvers

    def __post_init__(self):
        if self.role not in ROLES:
            raise ValueError(f"unknown role {self.role}")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


_PROCESS_SECRET = os.urandom(32)     # dev only: tokens die with the process


class Authority:
    def __init__(self, secret: bytes | None = None):
        s = get_secret("AGENTRAIL_JWT_SECRET")
        self.secret = secret or (s.encode() if s else _PROCESS_SECRET)
        if len(self.secret) < 32:
            raise RuntimeError("AGENTRAIL_JWT_SECRET must be at least 32 bytes")
        self.identities: dict[str, Identity] = {}
        self._challenges: dict[str, tuple[str, float]] = {}   # nonce -> (sub, expires)
        self._denied: dict[str, float] = {}                    # jti -> exp
        self._lock = threading.Lock()

    # ---- enrolment ----
    def enrol(self, ident: Identity) -> Identity:
        with self._lock:
            old = self.identities.get(ident.sub)
            if old and old.public_hex != ident.public_hex:
                raise AuthError(f"{ident.sub} is already enrolled with another device key")
            self.identities[ident.sub] = ident
        return ident

    # ---- login ----
    def challenge(self, sub: str) -> dict:
        nonce = pysecrets.token_urlsafe(24)
        with self._lock:
            now = time.time()
            self._challenges = {n: v for n, v in self._challenges.items() if v[1] > now}
            self._challenges[nonce] = (sub, now + CHALLENGE_TTL_S)
        # Same answer for unknown subjects: the endpoint does not reveal who is enrolled.
        return {"nonce": nonce, "expires_in": CHALLENGE_TTL_S, "aud": AUD}

    def token_for_signature(self, sub: str, nonce: str, signature: str) -> dict:
        with self._lock:
            entry = self._challenges.pop(nonce, None)       # single use, whatever the outcome
        ident = self.identities.get(sub)
        if not entry or entry[0] != sub or entry[1] < time.time() or ident is None:
            raise AuthError("invalid or expired challenge")
        if not verify_ed25519(ident.public_hex, challenge_message(sub, nonce, AUD), signature):
            raise AuthError("signature does not match the enrolled device")
        return self.issue(ident)

    # ---- tokens ----
    def issue(self, ident: Identity, ttl: int = TOKEN_TTL_S) -> dict:
        now = int(time.time())
        claims = {"iss": ISS, "aud": AUD, "sub": ident.sub, "role": ident.role, "scope": ident.scope,
                  "attrs": ident.attrs, "iat": now, "nbf": now, "exp": now + ttl,
                  "jti": pysecrets.token_urlsafe(12)}
        head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
        body = _b64(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
        sig = _b64(hmac.new(self.secret, f"{head}.{body}".encode(), hashlib.sha256).digest())
        return {"access_token": f"{head}.{body}.{sig}", "token_type": "Bearer", "expires_in": ttl,
                "role": ident.role, "scope": ident.scope}

    def verify(self, token: str) -> dict:
        try:
            head, body, sig = token.split(".")
            h = json.loads(_b64d(head))
        except Exception:
            raise AuthError("malformed token")
        if h.get("alg") != "HS256" or h.get("typ") != "JWT":
            raise AuthError("unsupported token algorithm")
        want = hmac.new(self.secret, f"{head}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(want, _b64d(sig)):
            raise AuthError("bad token signature")
        c = json.loads(_b64d(body))
        now = time.time()
        if c.get("iss") != ISS or c.get("aud") != AUD:
            raise AuthError("token not for this API")
        if c.get("exp", 0) < now or c.get("nbf", 0) > now + 5:
            raise AuthError("token expired")
        with self._lock:
            if c.get("jti") in self._denied:
                raise AuthError("token revoked")
        ident = self.identities.get(c.get("sub"))
        if ident is None or ident.role != c.get("role") or ident.scope != c.get("scope"):
            raise AuthError("identity changed since the token was issued")
        return c

    def revoke(self, claims: dict):
        with self._lock:
            now = time.time()
            self._denied = {j: e for j, e in self._denied.items() if e > now}
            self._denied[claims["jti"]] = claims["exp"]
