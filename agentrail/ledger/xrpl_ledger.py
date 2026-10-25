"""XRPL Testnet settlement via xrpl-py.

Wallet secrets live only in memory and in `wallets.local.json` (git-ignored).
The engine stores signed blobs and hashes, never secrets."""
from __future__ import annotations

import json
import os
import time

from xrpl.clients import JsonRpcClient
from xrpl.core.binarycodec import decode, encode
from xrpl.ledger import get_latest_validated_ledger_sequence
from xrpl.models.requests import AccountInfo, SubmitOnly, Tx
from xrpl.models.transactions import Memo, Payment
from xrpl.transaction import autofill_and_sign
from xrpl.wallet import Wallet, generate_faucet_wallet

from .base import Ledger, LostResponse, Prepared, TxStatus

TESTNET_RPC = os.environ.get("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234/")
WALLET_FILE = os.environ.get("AGENTRAIL_WALLETS", "wallets.local.json")
LSF_DISABLE_MASTER = 0x00100000


def _hex(s: str) -> str:
    return s.encode().hex().upper()


class XrplLedger(Ledger):
    name = "testnet"

    def __init__(self, rpc_url: str = TESTNET_RPC, wallet_file: str = WALLET_FILE):
        self.client = JsonRpcClient(rpc_url)
        self.wallet_file = wallet_file
        self.wallets: dict[str, Wallet] = {}
        self._labels: dict[str, str] = {}
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
        else:
            w = generate_faucet_wallet(self.client, debug=False)
            self._labels[label] = w.seed
            self._save()
        self.wallets[w.classic_address] = w
        return w.classic_address

    def prepare_payment(self, source, destination, amount_drops, invoice_id, memo):
        tx = Payment(account=source, destination=destination, amount=str(amount_drops),
                     invoice_id=invoice_id,
                     memos=[Memo(memo_type=_hex("agentrail/order"), memo_data=_hex(memo))])
        signed = autofill_and_sign(tx, self.client, self.wallets[source])
        return Prepared(tx_hash=signed.get_hash(), blob=encode(signed.to_xrpl()))

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
        resp = self.client.request(Tx(transaction=tx_hash))
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
            invoice_id=txj.get("InvoiceID"))

    def is_expired(self, blob: str) -> bool:
        lls = decode(blob).get("LastLedgerSequence")
        return lls is not None and get_latest_validated_ledger_sequence(self.client) > lls

    def wait_validated(self, tx_hash: str, timeout: float = 30.0) -> TxStatus:
        end = time.time() + timeout
        st = self.lookup(tx_hash)
        while not st.validated and time.time() < end:
            time.sleep(1.0)
            st = self.lookup(tx_hash)
        return st

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
