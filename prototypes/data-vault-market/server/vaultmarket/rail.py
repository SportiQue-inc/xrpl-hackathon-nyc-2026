"""Settlement: sealed delivery plus XRPL escrow where payment releases the key.

For each seller in a lot:
  1. the seller's agent encrypts its share under a fresh key K and wraps it to the buyer's X25519 key;
  2. the buyer's agent locks the price in an EscrowCreate whose condition is SHA-256(K);
  3. the seller's agent submits EscrowFinish with K as the fulfillment: it is paid, and K is now on the
     ledger, so the buyer opens what it already holds.
The ledger is AgentRail's XrplLedger (Testnet) from this repository, used as is. VM_LEDGER=mock swaps in
AgentRail's in-memory ledger for tests only; the site then says "test ledger" on every page.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from . import config

sys.path.insert(0, os.path.abspath(os.path.join(config.ROOT, "..", "..", "..")))
from agentrail.ledger.conditions import condition_hex, fulfillment_hex, new_key  # noqa: E402

KEYS_FILE = os.environ.get("VM_KEYS", os.path.join(config.DATA_DIR, "keys.local.json"))
_POOL = ThreadPoolExecutor(max_workers=8)


class Rail:
    def __init__(self):
        if config.LEDGER == "mock":
            from agentrail.ledger.mock import MockLedger
            self.led = MockLedger(start_balance_drops=100_000_000)
        else:
            from agentrail.ledger.xrpl_ledger import XrplLedger
            rpc = {"devnet": "https://s.devnet.rippletest.net:51234/"}.get(config.LEDGER, "https://s.altnet.rippletest.net:51234/")
            self.led = XrplLedger(rpc_url=rpc, wallet_file=config.WALLETS)
        self.name = "mock" if config.LEDGER == "mock" else config.LEDGER
        self._keys = json.load(open(KEYS_FILE)) if os.path.exists(KEYS_FILE) else {}
        self._lock = threading.Lock()

    # ---- accounts ----
    def ensure_account(self, label: str) -> str:
        addr = self.led.new_account("vm/" + label)
        with self._lock:
            if label not in self._keys:
                k = X25519PrivateKey.generate()
                self._keys[label] = base64.b64encode(k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                                                     serialization.NoEncryption())).decode()
                with open(KEYS_FILE, "w") as f:
                    json.dump(self._keys, f)
                os.chmod(KEYS_FILE, 0o600)
        return addr

    def _priv(self, label: str) -> X25519PrivateKey:
        return X25519PrivateKey.from_private_bytes(base64.b64decode(self._keys[label]))

    def balance_xrp(self, address: str) -> float | None:
        try:
            return self.led.balance_drops(address) / 1e6
        except Exception:
            return None

    def explorer(self, tx_hash: str) -> str | None:
        return f"https://{self.name}.xrpl.org/transactions/{tx_hash}" if self.name in ("testnet", "devnet") else None

    def find_link_payment(self, src: str, dst: str, tag: int) -> str | None:
        """Hash of a validated, successful Payment src -> dst carrying DestinationTag == tag: proof that
        whoever linked src controls it. On the mock ledger there is nothing to check."""
        if self.name == "mock":
            return "mock-" + hashlib.sha256(f"{src}{tag}".encode()).hexdigest()[:16]
        from xrpl.models.requests import AccountTx
        r = self.led.client.request(AccountTx(account=dst, limit=100)).result
        for t in r.get("transactions", []):
            tx = t.get("tx_json") or t.get("tx") or {}
            ok = (t.get("meta") or {}).get("TransactionResult") == "tesSUCCESS"
            if t.get("validated") and ok and tx.get("TransactionType") == "Payment" and tx.get("Account") == src and tx.get("DestinationTag") == tag:
                return t.get("hash") or tx.get("hash")
        return None

    # ---- sealing ----
    def seal(self, buyer_label: str, clear: bytes) -> tuple[bytes, bytes]:
        """Encrypt under a fresh K, then wrap to the buyer's key. Returns (sealed envelope, K)."""
        K = new_key()
        n1 = os.urandom(12)
        inner = n1 + AESGCM(K).encrypt(n1, clear, None)
        eph = X25519PrivateKey.generate()
        shared = eph.exchange(self._priv(buyer_label).public_key())
        wrap = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"vaultmarket/seal").derive(shared)
        n2 = os.urandom(12)
        epub = eph.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return epub + n2 + AESGCM(wrap).encrypt(n2, inner, None), K

    def open(self, buyer_label: str, sealed: bytes, K: bytes) -> bytes:
        epub, n2, body = sealed[:32], sealed[32:44], sealed[44:]
        shared = self._priv(buyer_label).exchange(X25519PublicKey.from_public_bytes(epub))
        wrap = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"vaultmarket/seal").derive(shared)
        inner = AESGCM(wrap).decrypt(n2, body, None)
        return AESGCM(K).decrypt(inner[:12], inner[12:], None)

    # ---- escrow ----
    def _submit(self, prepared) -> dict:
        self.led.submit(prepared)
        st = self.led.wait_validated(prepared.tx_hash, timeout=40) if hasattr(self.led, "wait_validated") else self.led.lookup(prepared.tx_hash)
        return {"hash": prepared.tx_hash, "result": st.result or ("tesSUCCESS" if st.success else "unknown"), "ok": bool(st.success)}

    def escrow_lot(self, buyer_addr: str, legs: list[dict], memo: str) -> list[dict]:
        """legs: [{seller_addr, drops, K}] -> per leg {create, finish} results. Creates run in parallel from the
        buyer (local sequence counter), then each seller's agent finishes its own escrow, revealing K."""
        cancel_after = self.led.now() + 3600
        prepared = []
        for leg in legs:
            p = self.led.prepare_escrow_create(buyer_addr, leg.get("dst_addr") or leg["seller_addr"], leg["drops"], condition_hex(leg["K"]), cancel_after, memo)
            prepared.append(p)
        creates = list(_POOL.map(self._submit, prepared))
        def finish(i):
            leg, c, p = legs[i], creates[i], prepared[i]
            if not c["ok"]:
                return {"hash": None, "result": "not created", "ok": False}
            seq = p.sequence if p.sequence is not None else json.loads(p.blob).get("Sequence")
            f = self.led.prepare_escrow_finish(leg["seller_addr"], buyer_addr, seq, condition_hex(leg["K"]), fulfillment_hex(leg["K"]), memo)
            return self._submit(f)
        finishes = list(_POOL.map(finish, range(len(legs))))
        return [{"create": c, "finish": f} for c, f in zip(creates, finishes)]


def merkle_root(leaves: list[str]) -> str:
    level = [hashlib.sha256(l.encode()).digest() for l in leaves] or [hashlib.sha256(b"").digest()]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def merkle_proof(leaves: list[str], idx: int) -> list[tuple[str, bool]]:
    level = [hashlib.sha256(l.encode()).digest() for l in leaves]
    proof = []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = idx ^ 1
        proof.append((level[sib].hex(), sib < idx))
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
        idx //= 2
    return proof


def merkle_verify(leaf: str, proof: list[tuple[str, bool]], root: str) -> bool:
    h = hashlib.sha256(leaf.encode()).digest()
    for sib, left in proof:
        s = bytes.fromhex(sib)
        h = hashlib.sha256(s + h).digest() if left else hashlib.sha256(h + s).digest()
    return h.hex() == root
