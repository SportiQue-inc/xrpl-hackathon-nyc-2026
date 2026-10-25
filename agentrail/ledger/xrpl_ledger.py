"""XRPL Testnet settlement via xrpl-py.

Wallet secrets live only in memory and in `wallets.local.json` (git-ignored).
The engine stores signed blobs and hashes, never secrets."""
from __future__ import annotations

import json
import os
import threading
import time

from xrpl.clients import JsonRpcClient
from xrpl.core.binarycodec import decode, encode
from xrpl.ledger import get_latest_validated_ledger_sequence
from xrpl.models.requests import AccountInfo, GenericRequest, Ledger as LedgerReq, SubmitOnly, Tx
from xrpl.models.transactions import EscrowCancel, EscrowCreate, EscrowFinish, Memo, Payment
from xrpl.transaction import autofill_and_sign
from xrpl.wallet import Wallet, generate_faucet_wallet

from .base import Ledger, LostResponse, Prepared, TxStatus

TESTNET_RPC = os.environ.get("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234/")
WALLET_FILE = os.environ.get("AGENTRAIL_WALLETS", "wallets.local.json")
LSF_DISABLE_MASTER = 0x00100000


def _hex(s: str) -> str:
    return s.encode().hex().upper()


def _retry(fn, tries: int = 4):
    """Public Testnet nodes drop or stall requests under parallel load: retry read-only calls."""
    for i in range(tries):
        try:
            return fn()
        except Exception:  # httpx connect/read timeouts and similar transport errors
            if i == tries - 1:
                raise
            time.sleep(0.5 * 2 ** i)


class XrplLedger(Ledger):
    name = "testnet"

    def __init__(self, rpc_url: str = TESTNET_RPC, wallet_file: str = WALLET_FILE):
        self.client = JsonRpcClient(rpc_url)
        self.wallet_file = wallet_file
        self.wallets: dict[str, Wallet] = {}
        self._seq: dict[str, int] = {}
        self._seq_lock = threading.Lock()
        self._labels: dict[str, str] = {}
        self._rules: dict[str, list[tuple[str, str]]] = {}  # destination -> [(issuer, cred type hex)]
        if os.path.exists(wallet_file):
            with open(wallet_file) as f:
                self._labels = json.load(f)

    def _save(self):
        with open(self.wallet_file, "w") as f:
            json.dump(self._labels, f, indent=1)
        os.chmod(self.wallet_file, 0o600)

    def new_account(self, label: str) -> str:
        if label in self._labels:
            w = Wallet.from_seed(self._labels[label])
            try:   # re-runs spend the same wallets; refill from the faucet when low
                bal = int(self.client.request(AccountInfo(account=w.classic_address, ledger_index="validated"))
                          .result["account_data"]["Balance"])
                if bal < 60_000_000:
                    generate_faucet_wallet(self.client, wallet=w, debug=False)
            except Exception:
                pass
        else:
            w = generate_faucet_wallet(self.client, debug=False)
            self._labels[label] = w.seed
            self._save()
        self.wallets[w.classic_address] = w
        return w.classic_address

    def _next_sequence(self, account: str) -> int:
        """Local sequence counter so many payments can be signed and in flight at once."""
        with self._seq_lock:
            if account not in self._seq:
                r = _retry(lambda: self.client.request(AccountInfo(account=account, ledger_index="current"))).result
                self._seq[account] = int(r["account_data"]["Sequence"])
            seq = self._seq[account]
            self._seq[account] = seq + 1
            return seq

    def _deposit_rules(self, destination: str, refresh: bool = False) -> list[tuple[str, str]]:
        """Credential DepositPreauth rules on `destination` (cached)."""
        if refresh or destination not in self._rules:
            r = self.client.request(GenericRequest(method="account_objects", account=destination,
                                                   type="deposit_preauth", ledger_index="validated")).result
            self._rules[destination] = [(c["Credential"]["Issuer"], c["Credential"]["CredentialType"].upper())
                                        for o in r.get("account_objects", [])
                                        for c in o.get("AuthorizeCredentials", [])]
        return self._rules[destination]

    def credential_ids_for(self, source: str, destination: str) -> list[str] | None:
        """CredentialIDs a tx from `source` must carry to get past `destination`'s DepositAuth.
        None if the destination has no credential rule or the source holds no matching credential
        (the ledger then answers tecNO_PERMISSION)."""
        rules = self._deposit_rules(destination)
        if not rules:
            return None
        r = self.client.request(GenericRequest(method="account_objects", account=source,
                                               type="credential", ledger_index="validated")).result
        for o in r.get("account_objects", []):
            if (o.get("Subject") == source and int(o.get("Flags", 0)) & 0x00010000
                    and (o.get("Issuer"), o.get("CredentialType", "").upper()) in rules):
                return [o["index"]]
        return None

    def prepare_payment(self, source, destination, amount_drops, invoice_id, memo):
        tx = Payment(account=source, destination=destination, amount=str(amount_drops),
                     credential_ids=self.credential_ids_for(source, destination),
                     invoice_id=invoice_id, sequence=self._next_sequence(source),
                     memos=[Memo(memo_type=_hex("agentrail/order"), memo_data=_hex(memo))])
        signed = _retry(lambda: autofill_and_sign(tx, self.client, self.wallets[source]))
        return Prepared(tx_hash=signed.get_hash(), blob=encode(signed.to_xrpl()))

    def can_sign(self, address: str) -> bool:
        return address in self.wallets

    def now(self) -> int:
        r = self.client.request(LedgerReq(ledger_index="validated")).result
        return int(r["ledger"]["close_time"])

    def _sign(self, tx, account: str) -> Prepared:
        signed = autofill_and_sign(tx, self.client, self.wallets[account])
        return Prepared(tx_hash=signed.get_hash(), blob=encode(signed.to_xrpl()), sequence=signed.sequence)

    def prepare_escrow_create(self, source, destination, amount_drops, condition, cancel_after, memo):
        return self._sign(EscrowCreate(account=source, destination=destination, amount=str(amount_drops),
                                       condition=condition, cancel_after=cancel_after,
                                       sequence=self._next_sequence(source),
                                       memos=[Memo(memo_type=_hex("agentrail/order"), memo_data=_hex(memo))]), source)

    def prepare_escrow_finish(self, submitter, owner, offer_sequence, condition, fulfillment, memo,
                              destination: str | None = None):
        # DepositAuth gates EscrowFinish (not EscrowCreate) when someone other than the
        # destination submits it; that submitter must then carry CredentialIDs.
        creds = (self.credential_ids_for(submitter, destination)
                 if destination and destination != submitter else None)
        return self._sign(EscrowFinish(account=submitter, owner=owner, offer_sequence=offer_sequence,
                                       condition=condition, fulfillment=fulfillment, credential_ids=creds,
                                       sequence=self._next_sequence(submitter),
                                       memos=[Memo(memo_type=_hex("agentrail/order"), memo_data=_hex(memo))]),
                          submitter)

    def prepare_escrow_cancel(self, submitter, owner, offer_sequence):
        return self._sign(EscrowCancel(account=submitter, owner=owner, offer_sequence=offer_sequence,
                                       sequence=self._next_sequence(submitter)), submitter)

    def submit(self, prepared: Prepared) -> None:
        try:
            resp = self.client.request(SubmitOnly(tx_blob=prepared.blob))
        except Exception as e:  # network error: outcome unknown
            raise LostResponse(str(e)) from e
        engine = resp.result.get("engine_result", "")
        # tef/tem codes mean the tx can never apply; anything else -> check the ledger.
        if engine.startswith(("tem", "tef")) and engine != "tefPAST_SEQ":
            raise RuntimeError(f"payment rejected: {engine}")

    def lookup(self, tx_hash: str) -> TxStatus:
        resp = _retry(lambda: self.client.request(Tx(transaction=tx_hash)))
        r = resp.result
        if not resp.is_successful() or r.get("error") == "txnNotFound":
            return TxStatus(found=False)
        txj = r.get("tx_json", r)
        meta = r.get("meta", {})
        delivered = meta.get("delivered_amount", txj.get("Amount"))
        return TxStatus(
            found=True, validated=bool(r.get("validated")),
            success=meta.get("TransactionResult") == "tesSUCCESS",
            ledger_index=r.get("ledger_index"), destination=txj.get("Destination"),
            amount_drops=int(delivered) if isinstance(delivered, str) else None,
            invoice_id=txj.get("InvoiceID"), tx_type=txj.get("TransactionType"),
            result=meta.get("TransactionResult"), condition=txj.get("Condition"),
            fulfillment=txj.get("Fulfillment"), sequence=txj.get("Sequence"))

    def invoice_field_of(self, blob: str) -> str | None:
        return decode(blob).get("InvoiceID")

    def is_expired(self, blob: str) -> bool:
        tx = decode(blob)
        lls = tx.get("LastLedgerSequence")
        expired = lls is not None and _retry(lambda: get_latest_validated_ledger_sequence(self.client)) > lls
        if expired:
            with self._seq_lock:  # the sequence was never consumed: re-read it from the ledger
                self._seq.pop(tx["Account"], None)
        return expired

    def wait_validated(self, tx_hash: str, timeout: float = 30.0) -> TxStatus:
        end = time.time() + timeout
        st = TxStatus(found=False)
        while True:
            try:
                st = self.lookup(tx_hash)
            except Exception:  # still unreachable after retries: keep polling until the deadline
                pass
            if st.validated or time.time() >= end:
                return st
            time.sleep(1.0)

    def balance_drops(self, address: str) -> int:
        r = self.client.request(AccountInfo(account=address, ledger_index="validated")).result
        return int(r.get("account_data", {}).get("Balance", 0))

    def account_settings(self, address: str) -> dict:
        r = self.client.request(AccountInfo(account=address, ledger_index="validated",
                                            signer_lists=True)).result
        data = r.get("account_data", {})
        signers = r.get("signer_lists") or data.get("signer_lists") or []
        return {"network": "testnet",
                "multisig": bool(signers),
                "master_disabled": bool(int(data.get("Flags", 0)) & LSF_DISABLE_MASTER)}

    def explorer_url(self, tx_hash: str) -> str:
        return f"https://testnet.xrpl.org/transactions/{tx_hash}"
