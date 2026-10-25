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
        return "test USD" if self.asset == "USD" else "XRP"     # ledger key stored with each contract

    def label(self) -> str:
        return self.symbol()   # Display identity must match the asset actually settled, including old receipts.

    # ---- the test USD token (stands in for RLUSD) ----
    def _usd(self, micro: int):
        from xrpl.models.amounts import IssuedCurrencyAmount
        return IssuedCurrencyAmount(currency="USD", issuer=self.issuer, value=f"{micro / 1e6:.6f}".rstrip("0").rstrip("."))

    def _send(self, cls, account: str, **kw) -> dict:
        """Sign and submit one transaction from `account`, using the ledger's local sequence counter so it
        never collides with escrows the same account has in flight."""
        p = self.led._sign(cls(account=account, sequence=self.led._next_sequence(account), **kw), account)
        return self._submit(p)

    def _issuer_wallet(self, funder: str) -> str:
        """The issuer is a fresh wallet funded by a Payment from an already-funded account, not by the
        faucet (which rate-limits right after 50 wallets reconnect). Its seed is kept with the others."""
        from xrpl.wallet import Wallet
        label = "vm/issuer"
        if label in self.led._labels:
            w = Wallet.from_seed(self.led._labels[label])
            self.led.wallets[w.classic_address] = w
            return w.classic_address
        w = Wallet.create()
        r = self._submit(self.led.prepare_payment(funder, w.classic_address, 30_000_000, "0" * 64, "vaultmarket/issuer"))
        if not r["ok"]:
            raise RuntimeError(f"funding the issuer: {r['result']}")
        self.led._labels[label] = w.seed
        self.led._save()
        self.led.wallets[w.classic_address] = w
        return w.classic_address

    def setup_token(self, holders: dict[str, float], funder: str) -> None:
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
            self.issuer = self._issuer_wallet(funder)
            if st.get("issuer") != self.issuer:      # a different issuer means new flags and new lines
                st = {"issuer": self.issuer, "lines": []}
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

    def ensure_token_holder(self, addr: str):
        """Onboard a member without changing the market asset if their trust line fails."""
        if not self.token or self._lines.get(addr):
            return
        from xrpl.models.transactions import TrustSet, Payment
        state_file=os.path.join(config.DATA_DIR,"token.local.json")
        st=json.load(open(state_file))
        if addr not in st["lines"]:
            r=self._send(TrustSet,addr,limit_amount=self._usd(10**15))
            if not r["ok"]:
                raise RuntimeError("The test USD trust line is not validated yet")
            if not (self.balance(addr) or 0)>0:
                r=self._send(Payment,self.issuer,destination=addr,amount=self._usd(300000000))
                if not r["ok"]:
                    raise RuntimeError("The test USD starting balance is not validated yet")
            st["lines"].append(addr)
            with open(state_file,"w") as f:
                json.dump(st,f)
            os.chmod(state_file,0o600)
        self._lines[addr]=True

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

    def escrow_lot(self, buyer_addr: str, legs: list[dict], memo: str, record=None) -> list[dict]:
        """legs: [{seller_addr, drops, K}] -> per leg {create, finish} results. Creates run in parallel from the
        buyer (local sequence counter), then each seller's agent finishes its own escrow, revealing K.
        record(i, sequence, create_hash, cancel_after) runs for each leg before anything is submitted."""
        cancel_after = self.led.now() + 3600
        prepared = []
        for leg in legs:
            dst = leg.get("dst_addr") or leg["seller_addr"]
            if self.token:
                p = self.led._sign(self._escrow_create(buyer_addr, dst, leg["drops"], condition_hex(leg["K"]), cancel_after, memo), buyer_addr)
            else:
                p = self.led.prepare_escrow_create(buyer_addr, dst, leg["drops"], condition_hex(leg["K"]), cancel_after, memo)
            prepared.append(p)
        if record:
            for i, p in enumerate(prepared):
                record(i, self._seq_of(p), p.tx_hash, cancel_after, p.blob)
        creates = list(_POOL.map(self._submit, prepared))
        def finish(i):
            leg, c, p = legs[i], creates[i], prepared[i]
            if not c["ok"]:
                return {"hash": None, "result": "not created", "ok": False}
            return self.finish_escrow(leg["seller_addr"], buyer_addr, self._seq_of(p), leg["K"], memo)
        finishes = list(_POOL.map(finish, range(len(legs))))
        return [{"create": c, "finish": f} for c, f in zip(creates, finishes)]


    @staticmethod
    def _seq_of(p) -> int:
        return p.sequence if p.sequence is not None else json.loads(p.blob).get("Sequence")

    def finish_escrow(self, seller_addr: str, owner: str, seq: int, K: bytes, memo: str) -> dict:
        f = self.led.prepare_escrow_finish(seller_addr, owner, seq, condition_hex(K), fulfillment_hex(K), memo)
        return self._submit(f)

    def cancel_escrow(self, owner: str, seq: int) -> dict:
        return self._submit(self.led.prepare_escrow_cancel(owner, owner, seq))

    def created_ok(self, tx_hash: str, blob: str | None = None) -> bool | None:
        """True: validated tesSUCCESS. False: failed or never reached the ledger. None: cannot tell yet."""
        try:
            st = self.led.lookup(tx_hash)
        except Exception:
            return None
        if not st.found:
            if not blob:
                return None
            if self.led.is_expired(blob):
                return False
            from agentrail.ledger.base import Prepared
            try:
                return True if self._submit(Prepared(tx_hash=tx_hash,blob=blob))["ok"] else None
            except Exception:
                return None
        return bool(st.success) if st.validated else None

    def escrow_outcome(self, owner: str, seq: int) -> tuple[str, str | None]:
        """Read the validated closing transaction; a missing escrow alone proves neither payment nor refund."""
        if self.name == "mock":
            pages = [list(self.led.txs.values())]
        else:
            from xrpl.models.requests import AccountTx, LedgerEntry
            from xrpl.models.requests.ledger_entry import Escrow as EscrowLookup
            current=self.led.client.request(LedgerEntry(escrow=EscrowLookup(owner=owner,seq=seq),ledger_index="validated")).result
            if current.get("node",{}).get("LedgerEntryType")=="Escrow":
                return "open",None
            if current.get("error")!="entryNotFound":
                return "unknown",None
            pages, marker = [], None
            while True:
                r = self.led.client.request(AccountTx(account=owner, limit=200, marker=marker)).result
                if "error" in r:
                    return "unknown", None
                pages.append(r.get("transactions", []))
                marker = r.get("marker")
                if not marker:
                    break
        for page in pages:
            for item in page:
                tx = item if self.name == "mock" else item.get("tx_json", item.get("tx", {}))
                ok = item.get("result") == "tesSUCCESS" if self.name == "mock" else item.get("validated") and item.get("meta", {}).get("TransactionResult") == "tesSUCCESS"
                if ok and tx.get("Owner") == owner and tx.get("OfferSequence") == seq:
                    state = {"EscrowFinish": "finished", "EscrowCancel": "refunded"}.get(tx.get("TransactionType"))
                    if state:
                        h = item.get("hash", tx.get("hash"))
                        if self.name == "mock":
                            h = next(k for k, v in self.led.txs.items() if v is item)
                        return state, h
        return ("open" if self.name=="mock" else "unknown"), None

    def receipt(self, tx_hash: str, result: dict | None = None) -> dict:
        from decimal import Decimal
        if result is not None:
            r=result;tx=r.get("tx_json",r)
        elif self.name == "mock":
            tx = self.led.txs.get(tx_hash, {})
            r = {"validated": bool(tx), "ledger_index": tx.get("ledger_index"), "meta": {"TransactionResult": tx.get("result")}}
        else:
            from xrpl.models.requests import Tx
            r = self.led.client.request(Tx(transaction=tx_hash)).result
            tx = r.get("tx_json", r)
        meta = r.get("meta", {})
        fields = next((n["DeletedNode"].get("FinalFields", {}) for n in meta.get("AffectedNodes", []) if n.get("DeletedNode", {}).get("LedgerEntryType")=="Escrow"), {})
        gross = tx.get("Amount", fields.get("Amount"))
        if tx.get("TransactionType")=="Payment":
            gross=meta.get("delivered_amount")
            if gross=="unavailable":
                gross=None
        if not r.get("validated") or meta.get("TransactionResult")!="tesSUCCESS":
            gross=None
        if gross is None and self.name == "mock" and tx.get("TransactionType") in ("EscrowFinish","EscrowCancel"):
            original = next((t for t in self.led.txs.values() if t.get("TransactionType")=="EscrowCreate" and t.get("Account")==tx.get("Owner") and t.get("Sequence")==tx.get("OfferSequence")), {})
            gross = original.get("Amount")
        value = gross.get("value") if isinstance(gross, dict) else str(Decimal(gross)/1000000) if gross is not None else None
        currency = gross.get("currency") if isinstance(gross, dict) else "XRP"
        memos = []
        for m in tx.get("Memos", []):
            try:
                memos.append(bytes.fromhex(m.get("Memo", {}).get("MemoData", "")).decode())
            except (ValueError, UnicodeError):
                pass
        return {"hash":tx_hash,"validated":r.get("validated") is True,"result":meta.get("TransactionResult"),"ledger_index":r.get("ledger_index"),
                "type":tx.get("TransactionType"),"account":tx.get("Account"),"destination":(tx.get("Owner") or fields.get("Account")) if tx.get("TransactionType")=="EscrowCancel" else tx.get("Destination",fields.get("Destination")),
                "owner":tx.get("Owner",fields.get("Account")),"sequence":tx.get("Sequence"),"offer_sequence":tx.get("OfferSequence"),
                "gross_amount":value,"currency":currency,"issuer":gross.get("issuer") if isinstance(gross,dict) else None,
                "fee_xrp":str(Decimal(tx.get("Fee",0))/1000000),"memos":memos}

    def wallet_activity(self, address: str) -> list[dict]:
        from xrpl.models.requests import AccountTx
        if self.name=="mock":
            return []
        result=self.led.client.request(AccountTx(account=address,ledger_index_min=-1,ledger_index_max=-1,limit=200)).result
        if "error" in result:
            raise RuntimeError("Wallet history is temporarily unavailable")
        rows=[]
        for item in result.get("transactions",[]):
            tx=item.get("tx_json",item.get("tx",{}));h=item.get("hash",tx.get("hash"))
            raw={"tx_json":tx,"meta":item.get("meta",{}),"validated":item.get("validated"),"ledger_index":item.get("ledger_index",tx.get("ledger_index"))}
            rec=self.receipt(h,raw)
            if not rec["validated"] or rec["result"]!="tesSUCCESS" or rec["gross_amount"] is None:
                continue
            if rec["type"]=="EscrowFinish" and rec["destination"]!=address:
                continue
            if rec["type"]=="EscrowCreate" and rec["account"]!=address:
                continue
            if rec["type"]=="EscrowCancel" and rec["owner"]!=address:
                continue
            if rec["type"]=="EscrowCancel" and rec["owner"]==address:
                direction="in"
            else:
                direction="in" if rec["destination"]==address else "out"
            rows.append({"id":h,"contract":None,"created":(tx.get("date",0)+946684800),"type":rec["type"],"asset":"XRP" if rec["currency"]=="XRP" else "test USD" if rec["currency"]=="USD" and rec["issuer"]==self.issuer else f"{rec['currency']} · {rec['issuer']}","amount":rec["gross_amount"],"direction":direction,"hash":h,"url":self.explorer(h),"result":rec["result"],"fee_xrp":rec["fee_xrp"]})
        return rows

    def escrow_create_info(self, tx_hash: str) -> dict:
        if self.name == "mock":
            return self.led.txs.get(tx_hash, {})
        from xrpl.models.requests import Tx
        r = self.led.client.request(Tx(transaction=tx_hash)).result
        return r.get("tx_json", r) if r.get("validated") else {}


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
