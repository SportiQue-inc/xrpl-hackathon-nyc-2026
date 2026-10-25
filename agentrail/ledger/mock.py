"""In-memory ledger with XRPL-like semantics for tests:
signed blobs are idempotent (same blob -> same hash -> applied once),
payments land in a validated ledger immediately, and faults can be injected."""
from __future__ import annotations

import hashlib
import json
import threading

from .base import Ledger, LostResponse, Prepared, TxStatus


class MockLedger(Ledger):
    name = "mock"

    def __init__(self, start_balance_drops: int = 1_000_000_000):
        self.balances: dict[str, int] = {}
        self.sequences: dict[str, int] = {}
        self.txs: dict[str, dict] = {}
        self.ledger_index = 1000
        self.start_balance = start_balance_drops
        self.lock = threading.Lock()
        # fault injection
        self.lose_next_response = False   # apply, then raise LostResponse
        self.drop_next_submit = False     # raise LostResponse without applying
        self.submit_calls = 0

    def new_account(self, label: str) -> str:
        addr = "r" + hashlib.sha256(label.encode()).hexdigest()[:24]
        self.balances.setdefault(addr, self.start_balance)
        self.sequences.setdefault(addr, 1)
        return addr

    def prepare_payment(self, source, destination, amount_drops, invoice_id, memo):
        with self.lock:
            seq = self.sequences[source]
            self.sequences[source] = seq + 1
        body = {"TransactionType": "Payment", "Account": source, "Destination": destination,
                "Amount": str(amount_drops), "InvoiceID": invoice_id, "Sequence": seq,
                "Memo": memo}
        blob = json.dumps(body, sort_keys=True)
        return Prepared(tx_hash=hashlib.sha256(blob.encode()).hexdigest().upper(), blob=blob)

    def submit(self, prepared: Prepared) -> None:
        self.submit_calls += 1
        if self.drop_next_submit:
            self.drop_next_submit = False
            raise LostResponse("network dropped the request")
        with self.lock:
            if prepared.tx_hash not in self.txs:  # resubmitting the same blob is a no-op
                body = json.loads(prepared.blob)
                amt = int(body["Amount"])
                if self.balances.get(body["Account"], 0) < amt:
                    self.ledger_index += 1
                    self.txs[prepared.tx_hash] = {**body, "result": "tecUNFUNDED_PAYMENT",
                                                  "ledger_index": self.ledger_index}
                else:
                    self.balances[body["Account"]] -= amt
                    self.balances[body["Destination"]] = self.balances.get(body["Destination"], 0) + amt
                    self.ledger_index += 1
                    self.txs[prepared.tx_hash] = {**body, "result": "tesSUCCESS",
                                                  "ledger_index": self.ledger_index}
        if self.lose_next_response:
            self.lose_next_response = False
            raise LostResponse("response lost after submit")

    def lookup(self, tx_hash: str) -> TxStatus:
        t = self.txs.get(tx_hash)
        if not t:
            return TxStatus(found=False)
        return TxStatus(found=True, validated=True, success=t["result"] == "tesSUCCESS",
                        ledger_index=t["ledger_index"], destination=t["Destination"],
                        amount_drops=int(t["Amount"]), invoice_id=t["InvoiceID"])

    def balance_drops(self, address: str) -> int:
        return self.balances.get(address, 0)

    def account_settings(self, address: str) -> dict:
        return {"network": "mock", "multisig": False, "master_disabled": False}

    def payment_count(self) -> int:
        return sum(1 for t in self.txs.values() if t["result"] == "tesSUCCESS")
