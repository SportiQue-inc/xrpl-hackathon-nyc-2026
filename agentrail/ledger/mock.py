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
        self.credentials: set[tuple[str, str, str]] = set()
        self.signer_lists: dict[str, tuple[list[str], int]] = {}
        self.master_disabled: set[str] = set()

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

    def invoice_field_of(self, blob: str) -> str | None:
        return json.loads(blob)["InvoiceID"]

    def balance_drops(self, address: str) -> int:
        return self.balances.get(address, 0)

    def account_settings(self, address: str) -> dict:
        return {"network": "mock", "multisig": address in self.signer_lists,
                "master_disabled": address in self.master_disabled}

    def _fake_tx(self, kind: str, **fields) -> str:
        self.ledger_index += 1
        h = hashlib.sha256(json.dumps([kind, fields, self.ledger_index], sort_keys=True).encode()).hexdigest().upper()
        self.txs[h] = {"TransactionType": kind, **fields, "result": "tesSUCCESS", "ledger_index": self.ledger_index,
                       "Destination": fields.get("Destination"), "Amount": fields.get("Amount", "0"),
                       "InvoiceID": None}
        return h

    def new_keypair(self, label: str) -> str:
        return "r" + hashlib.sha256(("key:" + label).encode()).hexdigest()[:24]

    def issue_credential(self, issuer, subject, cred_type):
        self.credentials.add((subject, issuer, cred_type))
        return [self._fake_tx("CredentialCreate", Account=issuer, Subject=subject),
                self._fake_tx("CredentialAccept", Account=subject, Issuer=issuer)]

    def has_credential(self, subject, issuer, cred_type):
        return (subject, issuer, cred_type) in self.credentials

    def setup_multisig(self, account, signers, quorum):
        self.signer_lists[account] = (list(signers), quorum)
        self.master_disabled.add(account)
        return [self._fake_tx("SignerListSet", Account=account), self._fake_tx("AccountSet", Account=account)]

    def multisig_payment(self, source, destination, amount_drops, signers, memo=""):
        listed, quorum = self.signer_lists[source]
        if len(set(signers) & set(listed)) < quorum:
            raise RuntimeError("tefBAD_QUORUM: not enough valid signers")
        self.balances[source] -= amount_drops
        self.balances[destination] = self.balances.get(destination, 0) + amount_drops
        return self._fake_tx("Payment", Account=source, Destination=destination, Amount=str(amount_drops))

    def payment_count(self) -> int:
        return sum(1 for t in self.txs.values() if t["result"] == "tesSUCCESS" and t.get("InvoiceID"))
