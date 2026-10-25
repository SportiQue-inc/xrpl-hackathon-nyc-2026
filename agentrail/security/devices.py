"""The client side of every key. Each object here stands for something the server does not run in
production: a participant's phone (keyring), the institution's decryption service (vault), an
approver's or a participant's login device. Each holds its own KeyStore; the engine and the ledger
see only public keys, conditions and signatures.

In the demo all of them run in the same Python process as simulated devices, but nothing in the
engine, the ledger or the HTTP API can reach their private keys: the engine asks a keyring for a
fulfillment, asks a vault to open a bundle, and receives approver signatures as data.
"""
from __future__ import annotations

import json

from nacl.public import SealedBox
from nacl.secret import SecretBox
from nacl.signing import VerifyKey

from ..ledger.conditions import condition_hex, fulfillment_hex, key_from_fulfillment, new_key
from .keystore import KeyStore, LocalKeyStore


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def verify_ed25519(public_hex: str, message: bytes, signature_hex: str) -> bool:
    try:
        VerifyKey(bytes.fromhex(public_hex)).verify(message, bytes.fromhex(signature_hex))
        return True
    except Exception:
        return False


class Device:
    """A login device: an Ed25519 key that signs login challenges and consent documents."""

    def __init__(self, sub: str, keystore: KeyStore | None = None):
        self.sub = sub
        self.ks = keystore or LocalKeyStore(f"device.{sub}")

    @property
    def public_hex(self) -> str:
        return bytes(self.ks.signing_key().verify_key).hex()

    def sign(self, message: bytes) -> str:
        return self.ks.signing_key().sign(message).signature.hex()

    def sign_challenge(self, nonce: str, aud: str = "agentrail-api") -> str:
        return self.sign(f"agentrail-login|{aud}|{self.sub}|{nonce}".encode())

    def sign_consent(self, doc_hash: str) -> str:
        return self.sign(f"agentrail-consent|{self.sub}|{doc_hash}".encode())


def challenge_message(sub: str, nonce: str, aud: str = "agentrail-api") -> bytes:
    return f"agentrail-login|{aud}|{sub}|{nonce}".encode()


def consent_message(sub: str, doc_hash: str) -> bytes:
    return f"agentrail-consent|{sub}|{doc_hash}".encode()


class ParticipantKeyring:
    """On the participant's phone: the escrow key K of every round and the vault secret behind the
    per-study pseudonym and date shift. K is created here, never stored by the engine, and released
    only as an EscrowFinish fulfillment once the personal agent decides to publish it."""

    def __init__(self, pid: str, keystore: KeyStore | None = None):
        self.pid = pid
        self.ks = keystore or LocalKeyStore(f"participant.{pid}")

    def vault_secret(self) -> bytes:
        return self.ks.secret("vault")

    def lock(self, order_key: str, inner: bytes) -> tuple[bytes, str]:
        """Second lock on an already sealed bundle. Same order key -> same K (idempotent orders)."""
        k = self.ks.get_or_create(f"escrow.{order_key}", new_key)
        return SecretBox(k).encrypt(inner), condition_hex(k)

    def key(self, order_key: str) -> bytes:
        """K for an order before it is placed: the agent hands it to the source issuer, which seals its
        export with it (provenance seal); the escrow is then created with the same K's condition."""
        return self.ks.get_or_create(f"escrow.{order_key}", new_key)

    def fulfillment(self, order_key: str) -> str | None:
        k = self.ks.get(f"escrow.{order_key}")
        return fulfillment_hex(k) if k else None

    def forget(self, order_key: str):
        self.ks.delete(f"escrow.{order_key}")


class InstitutionVault:
    """At the institution: the box key bundles are sealed to. Opening needs the institution's key
    and, for escrowed rounds, K read from the validated ledger."""

    def __init__(self, org: str, keystore: KeyStore | None = None):
        self.org = org
        self.ks = keystore or LocalKeyStore(f"institution.{org}")

    @property
    def public_hex(self) -> str:
        return bytes(self.ks.box_key().public_key).hex()

    def open(self, sealed: bytes, fulfillment: str | None) -> dict:
        if fulfillment:
            sealed = SecretBox(key_from_fulfillment(fulfillment)).decrypt(sealed)
        return json.loads(SealedBox(self.ks.box_key()).decrypt(sealed))


class ApproverDevice(Device):
    """A treasury approver's device. Holds the key that is on the treasury's SignerList and signs one
    approval at a time. On XRPL it is an XRPL key (multisign); on the mock ledger an Ed25519 key."""

    def __init__(self, sub: str, ledger_kind: str, keystore: KeyStore | None = None):
        super().__init__(sub, keystore)
        self.ledger_kind = ledger_kind

    def _wallet(self):
        from xrpl.wallet import Wallet
        seed = self.ks.get_or_create("xrpl.seed", lambda: Wallet.create().seed.encode()).decode()
        return Wallet.from_seed(seed)

    @property
    def address(self) -> str:
        if self.ledger_kind == "testnet":
            return self._wallet().classic_address
        return mock_address(self.public_hex)

    def cosign(self, approval: dict) -> dict:
        """Sign what the approval asks for, after showing it to the person (amount, destination,
        spec hash, expiry). Returns the signature as data for the server."""
        if self.ledger_kind == "testnet":
            from xrpl.models.transactions.transaction import Transaction
            from xrpl.transaction import sign
            tx = Transaction.from_xrpl(approval["tx_json"])
            signed = sign(tx, self._wallet(), multisign=True)
            return {"signer": self.address, "signed_tx": signed.to_xrpl()}
        return {"signer": self.address, "public_key": self.public_hex,
                "signature": self.sign(approval_message(approval))}


class ParticipantWalletDevice(Device):
    """A participant's agent device whose key is the participant's own XRPL wallet (Ed25519). The
    same seed signs consent documents and logins and receives the rewards on XRPL, so a consent
    signature verifies against the wallet the money goes to. The seed stays in the keystore."""

    def _seed(self) -> str:
        from xrpl.constants import CryptoAlgorithm
        from xrpl.wallet import Wallet
        return self.ks.get_or_create("xrpl.seed", lambda: Wallet.create(CryptoAlgorithm.ED25519).seed.encode()).decode()

    def wallet(self):
        from xrpl.wallet import Wallet
        return Wallet.from_seed(self._seed())

    @property
    def address(self) -> str:
        return self.wallet().classic_address

    def _signing(self):
        if getattr(self, "_sk", None) is None:
            from nacl.signing import SigningKey
            from xrpl.core.keypairs import derive_keypair
            _, private = derive_keypair(self._seed())
            self._sk = SigningKey(bytes.fromhex(private[2:]))   # "ED" + 32-byte Ed25519 private key
        return self._sk

    @property
    def public_hex(self) -> str:
        return bytes(self._signing().verify_key).hex()

    def sign(self, message: bytes) -> str:
        return self._signing().sign(message).signature.hex()


def mock_address(public_hex: str) -> str:
    import hashlib
    return "r" + hashlib.sha256(("ed25519:" + public_hex).encode()).hexdigest()[:24]


def approval_message(approval: dict) -> bytes:
    keys = ("id", "study", "treasury", "destination", "amount_drops", "spec_hash", "nonce", "expires_at")
    return b"agentrail-approval|" + canonical({k: approval[k] for k in keys})
