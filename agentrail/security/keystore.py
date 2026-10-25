"""Key stores, one per owner. Nothing here is shared between owners: the study's box key, a
participant's escrow keys and an approver's signing key each live in their owner's store.

LocalKeyStore is the demo: in memory, or files under AGENTRAIL_KEYSTORE/<owner>/ (0700 / 0600,
git-ignored). KmsKeyStore is the production seam: the same calls backed by a KMS or HSM, where
private keys never leave the device or the service (sign / decrypt operations instead of raw keys).
"""
from __future__ import annotations

import os
import re
import threading

from nacl.public import PrivateKey
from nacl.signing import SigningKey


class KeyStore:
    owner: str

    def get_or_create(self, name: str, make) -> bytes:
        raise NotImplementedError

    def get(self, name: str) -> bytes | None:
        raise NotImplementedError

    def delete(self, name: str) -> None:
        raise NotImplementedError

    # Typed helpers on top of raw material.
    def secret(self, name: str) -> bytes:
        return self.get_or_create(f"secret.{name}", lambda: os.urandom(32))

    def signing_key(self) -> SigningKey:
        return SigningKey(self.get_or_create("ed25519", lambda: bytes(SigningKey.generate())))

    def box_key(self) -> PrivateKey:
        return PrivateKey(self.get_or_create("x25519", lambda: bytes(PrivateKey.generate())))


class LocalKeyStore(KeyStore):
    def __init__(self, owner: str, root: str | None = None):
        self.owner = owner
        self.root = root if root is not None else os.environ.get("AGENTRAIL_KEYSTORE") or None
        self._mem: dict[str, bytes] = {}
        self._lock = threading.Lock()
        if self.root:
            self.dir = os.path.join(self.root, re.sub(r"[^A-Za-z0-9_.-]", "_", owner))
            os.makedirs(self.dir, mode=0o700, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.dir, re.sub(r"[^A-Za-z0-9_.-]", "_", name))

    def get(self, name: str) -> bytes | None:
        if not self.root:
            return self._mem.get(name)
        p = self._path(name)
        if not os.path.exists(p):
            return None
        with open(p, "rb") as f:
            return f.read()

    def get_or_create(self, name: str, make) -> bytes:
        with self._lock:
            v = self.get(name)
            if v is not None:
                return v
            v = make()
            if not self.root:
                self._mem[name] = v
            else:
                fd = os.open(self._path(name), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(v)
            return v

    def delete(self, name: str) -> None:
        with self._lock:
            if not self.root:
                self._mem.pop(name, None)
            elif os.path.exists(self._path(name)):
                os.remove(self._path(name))


class KmsKeyStore(KeyStore):
    """Production seam. Implement with the KMS / HSM of the deployment (AWS KMS, GCP KMS, Azure Key
    Vault, or the phone's secure enclave for participants): keys are created inside it and only
    sign / decrypt / HMAC operations cross the boundary. Not used in the demo."""

    def __init__(self, owner: str, key_ring: str):
        self.owner, self.key_ring = owner, key_ring

    def get_or_create(self, name, make):
        raise NotImplementedError("bind to the deployment's KMS; raw key export is not allowed there")

    def get(self, name):
        raise NotImplementedError("bind to the deployment's KMS")

    def delete(self, name):
        raise NotImplementedError("bind to the deployment's KMS")
