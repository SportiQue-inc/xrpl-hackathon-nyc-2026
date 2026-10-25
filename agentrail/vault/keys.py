"""The person's keys, rooted in their passkey, and the bundle format the browser seals.

  root        the passkey's PRF output for salt SHA-256("agentrail-vault-v1|" + pid). It exists only
              while the passkey is used, in the person's page. The server never sees it; if it did,
              "the key lives in the passkey" would mean nothing. Agent accounts use SoftPasskey, which
              emulates PRF as HMAC-SHA256(credential secret, salt).
  trade key   K = HKDF-SHA256(root, salt = empty, info = "trade|<order id>|<bundle hash>"), 32 bytes.
              K seals the bundle (AES-256-GCM) and is the escrow preimage: the EscrowCreate condition
              is SHA-256(K); publishing K in EscrowFinish pays the person and lets the institution open
              the bundle. No standing master key leaves the device.
  delivery    the sealed bundle is encrypted again to the receiving institution's registered P-256
              key (ECDH with a fresh ephemeral key, HKDF info "seal|<order id>|<bundle hash>",
              AES-256-GCM) and pushed into the institution's own store. Nobody outside reads the
              person's store.

This module is the Python twin of apps/shared/passkey.js (sealBundle): the same bytes either way.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def prf_salt(pid: str) -> bytes:
    return hashlib.sha256(f"agentrail-vault-v1|{pid}".encode()).digest()


class SoftPasskey:
    """An agent account's passkey: PRF emulated as HMAC-SHA256(credential secret, salt)."""

    def __init__(self, secret: bytes | None = None):
        self._secret = secret or os.urandom(32)

    def prf(self, salt: bytes) -> bytes:
        return hmac.new(self._secret, salt, hashlib.sha256).digest()

    def root(self, pid: str) -> bytes:
        return self.prf(prf_salt(pid))


def hkdf(ikm: bytes, info: str, length: int = 32) -> bytes:
    return HKDF(hashes.SHA256(), length, None, info.encode()).derive(ikm)


def trade_key(root: bytes, order_id, bundle_hash: str) -> bytes:
    return hkdf(root, f"trade|{order_id}|{bundle_hash}")


def bundle_bytes(payload: dict) -> bytes:
    """The bytes the page seals: canonical JSON (sorted keys, no spaces, ASCII)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


# ---------------- the receiving institution ----------------

class InstitutionKey:
    """The institution's P-256 key: the public half is registered, the private half stays in its store."""

    def __init__(self, private=None):
        self._priv = private or ec.generate_private_key(ec.SECP256R1())

    def jwk(self) -> dict:
        n = self._priv.public_key().public_numbers()
        return {"kty": "EC", "crv": "P-256", "x": b64u(n.x.to_bytes(32, "big")), "y": b64u(n.y.to_bytes(32, "big")),
                "ext": True}

    def open_outer(self, sealed: dict) -> bytes:
        epk = sealed["epk"]
        pub = ec.EllipticCurvePublicNumbers(int.from_bytes(unb64u(epk["x"]), "big"),
                                            int.from_bytes(unb64u(epk["y"]), "big"), ec.SECP256R1()).public_key()
        shared = self._priv.exchange(ec.ECDH(), pub)
        wrap = hkdf(shared, f"seal|{sealed['order_id']}|{sealed['bundle_hash']}")
        return AESGCM(wrap).decrypt(unb64u(sealed["iv"]), unb64u(sealed["sealed"]), None)

    def open(self, sealed: dict, k: bytes) -> bytes:
        body = self.open_outer(sealed)
        bundle = AESGCM(k).decrypt(body[:12], body[12:], None)
        if hashlib.sha256(bundle).hexdigest() != sealed["bundle_hash"]:
            raise ValueError("bundle does not match its hash")
        return bundle


def jwk_public(jwk: dict):
    return ec.EllipticCurvePublicNumbers(int.from_bytes(unb64u(jwk["x"]), "big"), int.from_bytes(unb64u(jwk["y"]), "big"),
                                         ec.SECP256R1()).public_key()


def seal(root: bytes, order_id, bundle: bytes, institution_jwk: dict) -> tuple[dict, bytes]:
    """What the page does (passkey.js sealBundle). Returns the sealed record and K (kept by the page
    until the reveal)."""
    bh = hashlib.sha256(bundle).hexdigest()
    k = trade_key(root, order_id, bh)
    iv1 = os.urandom(12)
    inner = AESGCM(k).encrypt(iv1, bundle, None)
    eph = ec.generate_private_key(ec.SECP256R1())
    shared = eph.exchange(ec.ECDH(), jwk_public(institution_jwk))
    wrap = hkdf(shared, f"seal|{order_id}|{bh}")
    iv2 = os.urandom(12)
    outer = AESGCM(wrap).encrypt(iv2, iv1 + inner, None)
    n = eph.public_key().public_numbers()
    epk = {"kty": "EC", "crv": "P-256", "x": b64u(n.x.to_bytes(32, "big")), "y": b64u(n.y.to_bytes(32, "big")),
           "ext": True}
    return {"order_id": order_id, "bundle_hash": bh, "epk": epk, "iv": b64u(iv2), "sealed": b64u(outer),
            "root": "passkey"}, k


def private_pem(key: InstitutionKey) -> bytes:
    return key._priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                   serialization.NoEncryption())
