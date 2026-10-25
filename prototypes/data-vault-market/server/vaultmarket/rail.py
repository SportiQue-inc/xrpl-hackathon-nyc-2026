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
            self.led = MockLedger(start_balance_drops=10 ** 13)
        else:
            from agentrail.ledger.xrpl_ledger import XrplLedger
            rpc = {"devnet": "https://s.devnet.rippletest.net:51234/"}.get(config.LEDGER, "https://s.altnet.rippletest.net:51234/")
            self.led = XrplLedger(rpc_url=rpc, wallet_file=config.WALLETS)
        self.name = "mock" if config.LEDGER == "mock" else config.LEDGER
        self._keys = json.load(open(KEYS_FILE)) if os.path.exists(KEYS_FILE) else {}
        self._lock = threading.Lock()
        # settlement asset: the test USD token when the ledger supports token escrow, else XRP
        self.asset = config.ASSET
        self.issuer: str | None = None
        self.asset_note = ""
        self._lines: dict[str, bool] = {}

    @property
    def token(self) -> bool:
        return self.asset == "USD" and self.name != "mock" and self.issuer is not None

    def symbol(self) -> str:
        return "test USD" if self.asset == "USD" else "XRP"

    # ---- the test USD token (stands in for RLUSD) ----
    def _usd(self, micro: int):
        from xrpl.models.amounts import IssuedCurrencyAmount
        return IssuedCurrencyAmount(currency="USD", issuer=self.issuer, value=f"{micro / 1e6:.6f}".rstrip("0").rstrip("."))

    def _send(self, cls, account: str, **kw) -> dict:
        """Sign and submit one transaction from `account`, using the ledger's local sequence counter so it
        never collides with escrows the same account has in flight."""
        p = self.led._sign(cls(account=account, sequence=self.led._next_sequence(account), **kw), account)
        return self._submit(p)

    def setup_token(self, holders: dict[str, float]) -> None:
        """Issuer wallet with DefaultRipple + AllowTrustLineLocking (needed for token escrow), a trust line
        from every account, and a starting balance. Then one probe escrow; if the ledger refuses it, the
        market settles in XRP and says why. holders: address -> starting test USD."""
        if self.asset != "USD":
            return
        if self.name == "mock":
            self.asset_note = "test ledger: amounts are simulated"
            return
        from xrpl.models.transactions import AccountSet, Payment, TrustSet
        from xrpl.models.transactions.account_set import AccountSetAsfFlag
        state_file = os.path.join(config.DATA_DIR, "token.local.json")
        st = json.load(open(state_file)) if os.path.exists(state_file) else {"lines": []}
        try:
            self.issuer = self.ensure_account("issuer")
            if not st.get("flags"):
                for flag in (AccountSetAsfFlag.ASF_DEFAULT_RIPPLE, AccountSetAsfFlag.ASF_ALLOW_TRUSTLINE_LOCKING):
                    r = self._send(AccountSet, self.issuer, set_flag=flag)
                    if not r["ok"]:
                        raise RuntimeError(f"AccountSet {flag.name}: {r['result']}")
                st["flags"] = True
            todo = [a for a in holders if a not in st["lines"]]
            # trust lines in parallel (each from its own account), then the issuer pays one at a time
            lined = [a for a, r in zip(todo, _POOL.map(lambda a: self._send(TrustSet, a, limit_amount=self._usd(10 ** 15)), todo)) if r["ok"]]
            done = [a for a in lined if self._send(Payment, self.issuer, destination=a, amount=self._usd(int(holders[a] * 1e6)))["ok"]]
            st["lines"] = sorted(set(st["lines"]) | set(done))
            with open(state_file, "w") as f:
                json.dump(st, f)
            self._lines.update({a: True for a in st["lines"]})
            # probe: one tiny token escrow between two holders, created and finished
            a, b = st["lines"][0], st["lines"][1]
            K = new_key()
            p = self.led._sign(self._escrow_create(a, b, 1000, condition_hex(K), self.led.now() + 3600, "vaultmarket/probe"), a)
            c = self._submit(p)
            if not c["ok"]:
                raise RuntimeError(f"token escrow refused by the ledger: {c['result']}")
            f = self._submit(self.led.prepare_escrow_finish(b, a, p.sequence, condition_hex(K), fulfillment_hex(K), "vaultmarket/probe"))
            if not f["ok"]:
                raise RuntimeError(f"token escrow finish refused: {f['result']}")
            self.asset_note = f"issuer {self.issuer}; token escrow verified on the ledger"
        except Exception as e:
            self.asset, self.issuer = "XRP", None
            self.asset_note = f"settling in XRP: {e}"
            config.MICRO_PER_UNIT = config.DROPS_PER_XRP_UNIT = config.XRP_DROPS_PER_UNIT

    def has_line(self, addr: str) -> bool:
        if not self.token:
            return True
        if addr not in self._lines:
            from xrpl.models.requests import AccountLines
            try:
                r = self.led.client.request(AccountLines(account=addr, peer=self.issuer)).result
                self._lines[addr] = any(l.get("currency") == "USD" for l in r.get("lines", []))
            except Exception:
                return False
        return self._lines[addr]

    def _escrow_create(self, src, dst, micro, condition, cancel_after, memo):
        from xrpl.models.transactions import EscrowCreate, Memo
        hx = lambda t: t.encode().hex()
        return EscrowCreate(account=src, destination=dst, amount=self._usd(micro), condition=condition, cancel_after=cancel_after,
                            sequence=self.led._next_sequence(src), memos=[Memo(memo_type=hx("agentrail/order"), memo_data=hx(memo))])

    def pay(self, src: str, dst: str, micro: int, memo: str) -> dict:
        """A plain payment in the settlement asset (cleaning fees, wallet checks)."""
        if self.token:
            from xrpl.models.transactions import Memo, Payment
            hx = lambda t: t.encode().hex()
            return self._send(Payment, src, destination=dst, amount=self._usd(micro),
                              memos=[Memo(memo_type=hx("agentrail/order"), memo_data=hx(memo))])
        return self._submit(self.led.prepare_payment(src, dst, micro, "0" * 64, memo))

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

    def balance(self, address: str) -> float | None:
        """Balance in the settlement asset."""
        if not self.token:
            return self.balance_xrp(address)
        from xrpl.models.requests import AccountLines
        try:
            r = self.led.client.request(AccountLines(account=address, peer=self.issuer)).result
            return sum(float(l["balance"]) for l in r.get("lines", []) if l.get("currency") == "USD")
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
            dst = leg.get("dst_addr") or leg["seller_addr"]
            if self.token:
                p = self.led._sign(self._escrow_create(buyer_addr, dst, leg["drops"], condition_hex(leg["K"]), cancel_after, memo), buyer_addr)
            else:
                p = self.led.prepare_escrow_create(buyer_addr, dst, leg["drops"], condition_hex(leg["K"]), cancel_after, memo)
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
