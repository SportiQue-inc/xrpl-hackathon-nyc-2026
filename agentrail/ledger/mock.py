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
        self.cred_expiry: dict[tuple[str, str, str], int | None] = {}
        self.trustlines: set[tuple[str, str, str]] = set()
        self.ious: dict[tuple[str, str, str], float] = {}
        self.signer_lists: dict[str, tuple[list[str], int]] = {}
        self.master_disabled: set[str] = set()
        self.deposit_auth: set[str] = set()
        self.preauth: dict[str, set[tuple[str, str]]] = {}   # account -> {(issuer, cred_type)}
        self.escrows: dict[tuple[str, int], dict] = {}
        self.mpts: dict[str, dict] = {}          # id -> {issuer, meta, holders: {addr: amount}, authorized}
        self.clock = 800_000_000          # Ripple-epoch seconds; tests move it forward

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

    def now(self) -> int:
        return self.clock

    def can_sign(self, address: str) -> bool:
        return True

    def _prep(self, body: dict) -> Prepared:
        with self.lock:
            seq = self.sequences.setdefault(body["Account"], 1)
            self.sequences[body["Account"]] = seq + 1
        body["Sequence"] = seq
        blob = json.dumps(body, sort_keys=True)
        return Prepared(tx_hash=hashlib.sha256(blob.encode()).hexdigest().upper(), blob=blob, sequence=seq)

    def prepare_escrow_create(self, source, destination, amount_drops, condition, cancel_after, memo,
                              finish_after=None):
        body = {"TransactionType": "EscrowCreate", "Account": source, "Destination": destination,
                "Amount": str(amount_drops), "Condition": condition, "CancelAfter": cancel_after, "Memo": memo}
        if finish_after is not None:
            body["FinishAfter"] = finish_after
        return self._prep(body)

    def prepare_escrow_finish(self, submitter, owner, offer_sequence, condition, fulfillment, memo,
                              destination=None):
        return self._prep({"TransactionType": "EscrowFinish", "Account": submitter, "Owner": owner,
                           "OfferSequence": offer_sequence, "Condition": condition, "Fulfillment": fulfillment,
                           "Memo": memo})

    def prepare_escrow_batch(self, source, legs):
        """Batch (ALL_OR_NOTHING) of EscrowCreates from one account. legs: dicts with destination,
        amount_drops, condition, cancel_after, memo. Returns (outer, inner hashes, inner sequences)."""
        with self.lock:
            seq = self.sequences.setdefault(source, 1)
            self.sequences[source] = seq + 1 + len(legs)
        inner = [{"TransactionType": "EscrowCreate", "Account": source, "Destination": l["destination"],
                  "Amount": str(l["amount_drops"]), "Condition": l["condition"], "CancelAfter": l["cancel_after"],
                  "Memo": l["memo"], "Sequence": seq + 1 + i, "InnerBatch": True} for i, l in enumerate(legs)]
        hashes = [hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest().upper() for b in inner]
        blob = json.dumps({"TransactionType": "Batch", "Account": source, "Sequence": seq, "Flags": "ALL_OR_NOTHING",
                           "RawTransactions": inner}, sort_keys=True)
        outer = Prepared(tx_hash=hashlib.sha256(blob.encode()).hexdigest().upper(), blob=blob, sequence=seq)
        return outer, hashes, [b["Sequence"] for b in inner]

    def _apply_batch(self, body: dict) -> str:
        inner = body["RawTransactions"]
        if sum(int(b["Amount"]) for b in inner) > self.balances.get(body["Account"], 0):
            return "tesSUCCESS"          # the outer tx applies; with ALL_OR_NOTHING no inner tx does
        for b in inner:
            self.ledger_index += 1
            h = hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest().upper()
            self.txs[h] = {**b, "result": self._apply_escrow(b), "ledger_index": self.ledger_index}
        return "tesSUCCESS"

    # ---------- stablecoin payout through an AMM (fixed demo pool) ----------

    MOCK_STABLE_PER_XRP = 0.5

    def stable_price(self, code, issuer):
        return self.MOCK_STABLE_PER_XRP

    def ensure_trustline(self, account, code, issuer):
        if (account, code, issuer) in self.trustlines:
            return None
        self.trustlines.add((account, code, issuer))
        return self._fake_tx("TrustSet", Account=account)

    def swap_to_stable(self, account, drops, code, issuer):
        if (account, code, issuer) not in self.trustlines:
            return {"ok": False, "result": "tecPATH_DRY"}
        if self.balances.get(account, 0) < drops:
            return {"ok": False, "result": "tecUNFUNDED_PAYMENT"}
        got = drops / 1e6 * self.MOCK_STABLE_PER_XRP * 0.997          # pool fee
        self.balances[account] -= drops
        self.ious[(account, code, issuer)] = self.ious.get((account, code, issuer), 0.0) + got
        h = self._fake_tx("Payment", Account=account, Destination=account, SendMax=str(drops))
        return {"ok": True, "result": "tesSUCCESS", "tx": h, "delivered": f"{got:.6f}", "spot": self.MOCK_STABLE_PER_XRP}

    def prepare_escrow_cancel(self, submitter, owner, offer_sequence):
        return self._prep({"TransactionType": "EscrowCancel", "Account": submitter, "Owner": owner,
                           "OfferSequence": offer_sequence})

    def _apply_escrow(self, body: dict) -> str:
        t = body["TransactionType"]
        if t == "EscrowCreate":
            amt = int(body["Amount"])
            if self.balances.get(body["Account"], 0) < amt:
                return "tecUNFUNDED"
            # As on XRPL: EscrowCreate is not gated by the destination's DepositAuth (no CredentialIDs field).
            # The escrow route's verified-organization check is the personal agent's, before it publishes the key.
            self.balances[body["Account"]] -= amt
            self.escrows[(body["Account"], body["Sequence"])] = dict(body)
            return "tesSUCCESS"
        key = (body["Owner"], body["OfferSequence"])
        e = self.escrows.get(key)
        if e is None:
            return "tecNO_TARGET"
        if t == "EscrowFinish":
            from .conditions import condition_hex, key_from_fulfillment
            if self.clock >= e["CancelAfter"] or self.clock < e.get("FinishAfter", 0):
                return "tecNO_PERMISSION"
            try:
                ok = condition_hex(key_from_fulfillment(body["Fulfillment"])) == e["Condition"] == body["Condition"]
            except ValueError:
                ok = False
            if not ok:
                return "tecCRYPTOCONDITION_ERROR"
            self.balances[e["Destination"]] = self.balances.get(e["Destination"], 0) + int(e["Amount"])
        else:
            if self.clock < e["CancelAfter"]:
                return "tecNO_PERMISSION"
            self.balances[e["Account"]] += int(e["Amount"])
        del self.escrows[key]
        return "tesSUCCESS"

    def submit(self, prepared: Prepared) -> None:
        self.submit_calls += 1
        if self.drop_next_submit:
            self.drop_next_submit = False
            raise LostResponse("network dropped the request")
        with self.lock:
            if prepared.tx_hash not in self.txs and json.loads(prepared.blob)["TransactionType"] != "Payment":
                body = json.loads(prepared.blob)
                self.ledger_index += 1
                apply = self._apply_batch if body["TransactionType"] == "Batch" else self._apply_escrow
                self.txs[prepared.tx_hash] = {**body, "result": apply(body), "ledger_index": self.ledger_index}
            elif prepared.tx_hash not in self.txs:  # resubmitting the same blob is a no-op
                body = json.loads(prepared.blob)
                amt = int(body["Amount"])
                if body["Destination"] in self.deposit_auth and not self._preauthorized(body):
                    self.ledger_index += 1
                    self.txs[prepared.tx_hash] = {**body, "result": "tecNO_PERMISSION",
                                                  "ledger_index": self.ledger_index}
                elif self.balances.get(body["Account"], 0) < amt:
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
                        ledger_index=t["ledger_index"], destination=t.get("Destination"),
                        amount_drops=int(t["Amount"]) if t.get("Amount") else None, invoice_id=t.get("InvoiceID"),
                        tx_type=t.get("TransactionType"), result=t["result"], condition=t.get("Condition"),
                        fulfillment=t.get("Fulfillment"), sequence=t.get("Sequence"))

    def memo_of(self, tx_hash: str) -> str | None:
        return (self.txs.get(tx_hash) or {}).get("Memo")

    def invoice_field_of(self, blob: str) -> str | None:
        return json.loads(blob).get("InvoiceID")

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

    def issue_credential(self, issuer, subject, cred_type, expiration=None):
        self.credentials.add((subject, issuer, cred_type))
        self.cred_expiry[(subject, issuer, cred_type)] = expiration
        return [self._fake_tx("CredentialCreate", Account=issuer, Subject=subject),
                self._fake_tx("CredentialAccept", Account=subject, Issuer=issuer)]

    def has_credential(self, subject, issuer, cred_type):
        k = (subject, issuer, cred_type)
        exp = self.cred_expiry.get(k)
        return k in self.credentials and (exp is None or exp > self.now())

    def delete_credential(self, issuer, subject, cred_type):
        self.credentials.discard((subject, issuer, cred_type))
        return self._fake_tx("CredentialDelete", Account=issuer, Subject=subject)

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

    def _preauthorized(self, body: dict) -> bool:
        need = self.preauth.get(body["Destination"], set())
        return any((body["Account"], iss, ct) in self.credentials for iss, ct in need)

    def require_credential_deposits(self, account, issuer, cred_type):
        self.deposit_auth.add(account)
        self.preauth.setdefault(account, set()).add((issuer, cred_type))
        return [self._fake_tx("AccountSet", Account=account), self._fake_tx("DepositPreauth", Account=account)]

    # ---------- data licence (MPT) ----------

    def issue_licence(self, issuer, holder, metadata):
        mpt_id = hashlib.sha256(f"{issuer}|{metadata}|{len(self.mpts)}".encode()).hexdigest()[:48].upper()
        self.mpts[mpt_id] = {"issuer": issuer, "meta": metadata, "holders": {holder: 1}, "authorized": {holder}}
        return mpt_id, [self._fake_tx("MPTokenIssuanceCreate", Account=issuer),
                        self._fake_tx("MPTokenAuthorize", Account=holder),
                        self._fake_tx("MPTokenAuthorize", Account=issuer, Holder=holder),
                        self._fake_tx("Payment", Account=issuer, Destination=holder)]

    def licence_held(self, holder, mpt_id):
        return self.mpts.get(mpt_id, {}).get("holders", {}).get(holder, 0) > 0

    def licence_metadata_of(self, mpt_id):
        return self.mpts.get(mpt_id, {}).get("meta")

    def clawback_licence(self, issuer, holder, mpt_id):
        m = self.mpts[mpt_id]
        if m["issuer"] != issuer:
            raise RuntimeError("tecNO_PERMISSION: only the issuer can claw back")
        m["holders"][holder] = 0
        return self._fake_tx("Clawback", Account=issuer, Holder=holder)

    def transfer_licence(self, holder, to, mpt_id):
        # No CanTransfer flag and RequireAuth: a holder cannot pass the licence to a third party.
        self._fake_tx("Payment", Account=holder, Destination=to)
        self.txs[list(self.txs)[-1]]["result"] = "tecNO_AUTH"
        return "tecNO_AUTH"

    def payment_count(self) -> int:
        return sum(1 for t in self.txs.values() if t["result"] == "tesSUCCESS"
                   and (t.get("InvoiceID") or t.get("TransactionType") == "EscrowFinish"))
