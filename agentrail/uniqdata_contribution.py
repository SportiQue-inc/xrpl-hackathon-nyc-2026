"""Owner-agent settlement of an existing, Core-verified file contribution.

The resident Core command is a trusted operator channel, never a browser body or
an arbitrary receipt file. The owner agent receives only the reviewed export,
seals it to the registered institution, and retains its own per-order key. Main
UniQdata owns the original account, existing passkey, consent and withdrawal.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess

from nacl.public import PublicKey, SealedBox

from .engine import OrderRequest, canonical, sha256_hex
from .ledger import MockLedger
from .ledger.licence import licence_metadata
from .policy import ALLOW, DENY, Decision

PURPOSE = "research_file_delivery"
SCHEMA = """
CREATE TABLE IF NOT EXISTS uniqdata_file_transfers (
  submission_ref TEXT PRIMARY KEY, binding_sha256 TEXT NOT NULL UNIQUE,
  state_json TEXT NOT NULL, buyer_id TEXT NOT NULL, seller_id TEXT NOT NULL,
  order_id INTEGER, licence_id TEXT, licence_status TEXT NOT NULL DEFAULT 'new',
  licence_txs TEXT, clawback_tx TEXT
);
"""


class ResidentCore:
    """A resident-local Core argv, e.g. docker exec -i on that same host.

    No shell, secret printing, passkey simulation, arbitrary URL, or bearer
    forwarding. The command's stdout is private and must never be logged.
    """
    def __init__(self, command: list[str], *, country: str, lane: str):
        if not isinstance(command, list) or not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("A resident Core command is required")
        if country not in {"KR", "MN"} or lane not in {"prod", "dev"}:
            raise ValueError("An explicit resident country and database lane are required")
        self.command = tuple(command)
        self.country, self.lane = country, lane

    def call(self, action: str, **body) -> dict:
        try:
            result = subprocess.run(self.command, input=json.dumps({"action": action, **body}),
                                    text=True, capture_output=True, timeout=90, check=False)
            if result.returncode or len(result.stdout) > 470_000_000:
                raise ValueError("Resident Core refused the operation")
            value = json.loads(result.stdout)
            if not isinstance(value, dict):
                raise ValueError("Resident Core returned no object")
            context = value.get("_core")
            if not isinstance(context, dict) or context.get("country") != self.country or context.get("lane") != self.lane:
                raise ValueError("Resident Core country or database lane differs")
            return value
        except (OSError, subprocess.SubprocessError, ValueError):
            raise PermissionError("Resident Core authority is unavailable; no operation authorized") from None


class _Recipient:
    def __init__(self, vault):
        self.vault = vault

    def open(self, sealed, fulfillment):
        record = json.loads(sealed)
        if record.get("format") != "uniqdata.sealed-file.v1":
            raise ValueError("Unknown file envelope")
        return self.vault.open(base64.b64decode(record["sealed_b64"], validate=True), fulfillment)


class _Authority:
    def __init__(self, bridge):
        self.bridge = bridge

    def evaluate(self, buyer_id, purpose, fields, price_drops, week=None, for_delivery=False):
        b = self.bridge
        try:
            b._check("delivery")
            if (buyer_id != b.buyer_id or purpose != PURPOSE or fields != ["reviewed_file_package"]
                    or price_drops != b.state["settlement"]["amount_drops"] or not b._licence_held()):
                raise PermissionError("Contribution scope differs")
        except (PermissionError, ValueError):
            return Decision(DENY, reason="Core contribution authority is unavailable or changed")
        return Decision(ALLOW, granted=fields, policy_version="core-consent:" + b.state["consent_ref"])


class _KeyRelease:
    def __init__(self, bridge):
        self.bridge = bridge

    def fulfillment(self, order_key):
        try:
            self.bridge._check("key")
        except (PermissionError, ValueError):
            return None
        return self.bridge.keyring.fulfillment(order_key)


class ContributionBridge:
    def __init__(self, engine, source, *, buyer_id, keyring, recipient):
        self.engine, self.source, self.buyer_id = engine, source, buyer_id
        self.keyring, self.recipient = keyring, recipient
        self.state = None
        self.engine.store.conn.executescript(SCHEMA)

    def _row(self):
        return self.engine.store.one("SELECT * FROM uniqdata_file_transfers WHERE submission_ref=?",
                                     self.state["submission_ref"])

    def _same(self, state):
        for key in ("submission_ref", "consent_ref", "participant_ref", "binding_sha256", "settlement"):
            if state.get(key) != self.state[key]:
                raise PermissionError("Original Core contribution binding changed")

    def _check(self, phase):
        state = self.source.call("check", binding_sha256=self.state["binding_sha256"], phase=phase)
        self._same(state)
        if state.get("active") is not True or state.get("bundle_sha256") != self.state["bundle_sha256"]:
            raise PermissionError("Original Core consent is inactive or its package changed")
        return state

    def _network(self):
        if isinstance(self.engine.ledger, MockLedger):
            return
        from .ledger.xrpl_ledger import XrplLedger
        from .ledger.token_settle import TokenSettleMixin

        ledger = self.engine.ledger
        if (not isinstance(ledger, XrplLedger) or isinstance(ledger, TokenSettleMixin)
                or ledger.client.url.rstrip("/") != "https://s.altnet.rippletest.net:51234"):
            raise PermissionError("Use the public native-XRP Testnet ledger (SETTLE_ASSET=XRP)")

    def _configure(self):
        terms = self.state["settlement"]
        if (self.state.get("version") != "uniqdata.agentrail.file-contribution.v1"
                or terms.get("network") != "xrpl-testnet" or terms.get("currency") != "XRP"
                or type(terms.get("amount_drops")) is not int or not 0 < terms["amount_drops"] <= 10**9
                or self.keyring.pid != self.state["participant_ref"]
                or self.keyring.ks is self.recipient.ks):
            raise PermissionError("Exact Testnet contribution and separate owner keys are required")
        self._network()
        buyer = self.engine.party(self.buyer_id)
        if (buyer is None or buyer["address"] != terms["payer_address"]
                or buyer["box_pubkey"] != self.recipient.public_hex
                or hashlib.sha256(bytes.fromhex(buyer["box_pubkey"])).hexdigest() != terms["recipient_key_sha256"]):
            raise PermissionError("Payer or recipient encryption key differs from consent")
        chain = self.engine.mandate_chains.get(self.buyer_id)
        if chain is None or not chain.l1 or not chain.l2:
            raise PermissionError("An existing owner-signed spending mandate is required")
        pid = self.state["participant_ref"]
        person = self.engine.party(pid)
        if person is not None and person["address"] != terms["payee_address"]:
            raise PermissionError("Participant payout address differs from consent")
        if person is None:
            self.engine.add_party(pid, "UniQdata participant", "person", terms["payee_address"])
        if not isinstance(self.engine.ledger, MockLedger) and not self.engine.ledger.can_sign(terms["payee_address"]):
            raise PermissionError("The configured participant Testnet licence signer is unavailable")
        self.engine.policies[pid] = _Authority(self)
        self.engine.key_holders[pid] = _KeyRelease(self)
        self.engine.openers[self.buyer_id] = _Recipient(self.recipient)

    def _order_key(self):
        return sha256_hex(f"{self.buyer_id}|{self.state['participant_ref']}|contract:{self.state['binding_sha256']}|"
                          f"{self.state['submission_ref']}|{PURPOSE}")

    def resume(self):
        """Restore an existing transfer for reconciliation, including after withdrawal."""
        current = self.source.call("inspect")
        previous = self.engine.store.one("SELECT * FROM uniqdata_file_transfers WHERE submission_ref=?",
                                         current["submission_ref"])
        if previous is None or previous["buyer_id"] != self.buyer_id or previous["order_id"] is None:
            raise PermissionError("No existing contribution transfer is available")
        self.state = json.loads(previous["state_json"])
        self._same(current)
        if any(current.get(key) != self.state[key] for key in ("package_sha256", "bundle_sha256")):
            raise PermissionError("Original contribution package changed")
        self._configure()
        return previous["order_id"]

    def prepare(self):
        current = self.source.call("inspect")
        if self.state is not None:
            self._same(current)
        self.state = current
        if self.state.get("active") is not True:
            raise PermissionError("Original Core consent is inactive")
        self._configure()
        previous = self._row()
        if previous is not None:
            if previous["binding_sha256"] != self.state["binding_sha256"] or previous["buyer_id"] != self.buyer_id:
                raise PermissionError("Submission was already bound to another contract")
            self.state = json.loads(previous["state_json"])
            existing = self.engine.store.one("SELECT id FROM orders WHERE order_key=?", self._order_key())
            if existing:
                with self.engine.store.tx() as db:
                    db.execute("UPDATE uniqdata_file_transfers SET order_id=? WHERE submission_ref=?",
                               (existing["id"], self.state["submission_ref"]))
                return existing["id"]
        export = self.source.call("export")
        self._same(export["state"])
        self.state = export["state"]
        payload = base64.b64decode(export["payload_b64"], validate=True)
        body = json.loads(payload)
        if (sha256_hex(payload) != self.state["bundle_sha256"]
                or body.get("binding_sha256") != self.state["binding_sha256"]
                or body.get("package_sha256") != self.state["package_sha256"]
                or body.get("contract") != "uniqdata.agentrail.file-delivery.v1"
                or sha256_hex(base64.b64decode(body["package_b64"], validate=True)) != self.state["package_sha256"]):
            raise ValueError("Resident export does not match its approved commitments")
        sealed, condition = self.keyring.lock(self._order_key(),
            SealedBox(PublicKey(bytes.fromhex(self.recipient.public_hex))).encrypt(payload))
        record = {"format": "uniqdata.sealed-file.v1", "bundle_hash": self.state["bundle_sha256"],
                  "sealed_b64": base64.b64encode(sealed).decode()}
        with self.engine.store.tx() as db:
            db.execute("INSERT OR IGNORE INTO uniqdata_file_transfers "
                       "(submission_ref,binding_sha256,state_json,buyer_id,seller_id) VALUES (?,?,?,?,?)",
                       (self.state["submission_ref"], self.state["binding_sha256"], canonical(self.state),
                        self.buyer_id, self.state["participant_ref"]))
        oid = self.engine.place_order(OrderRequest(
            self.buyer_id, self.state["participant_ref"], self.state["participant_ref"],
            "contract:" + self.state["binding_sha256"], self.state["submission_ref"], PURPOSE,
            ["reviewed_file_package"], self.state["settlement"]["amount_drops"],
            [{"binding_sha256": self.state["binding_sha256"], "package_sha256": self.state["package_sha256"]}],
            Decision(ALLOW, granted=["reviewed_file_package"], policy_version="core-file-v1"),
            settle="escrow", presealed={"record": record, "condition": condition}))
        with self.engine.store.tx() as db:
            db.execute("UPDATE uniqdata_file_transfers SET order_id=? WHERE submission_ref=?", (oid, self.state["submission_ref"]))
        return oid

    def _licence_held(self):
        row = self._row()
        return bool(row and row["licence_id"] and self.engine.ledger.licence_held(
            self.state["settlement"]["payer_address"], row["licence_id"]))

    def _ensure_licence(self):
        self._check("delivery")
        row = self._row()
        if row["licence_id"]:
            if not self._licence_held():
                raise PermissionError("The contribution licence is no longer held")
            return
        with self.engine.store.tx() as db:
            changed = db.execute("UPDATE uniqdata_file_transfers SET licence_status='issuing' "
                                 "WHERE submission_ref=? AND licence_status='new'",
                                 (self.state["submission_ref"],)).rowcount
        if changed != 1:
            raise RuntimeError("Reconcile the pending licence issuance before retrying; no second issuance sent")
        terms = self.state["settlement"]
        mpt, txs = self.engine.ledger.issue_licence(terms["payee_address"], terms["payer_address"],
            licence_metadata(PURPOSE, ["file_delivery"], self.state["binding_sha256"]))
        with self.engine.store.tx() as db:
            db.execute("UPDATE uniqdata_file_transfers SET licence_id=?,licence_txs=?,licence_status='issued' "
                       "WHERE submission_ref=?", (mpt, canonical(txs), self.state["submission_ref"]))

    def deliver(self):
        self._ensure_licence()
        oid = self._row()["order_id"]
        status = self.engine.process(oid, until="finish")
        acknowledged = self.engine.store.one("SELECT 1 FROM deliveries WHERE order_id=? AND acked=1", oid)
        if status in {"escrowed", "delivered"} and acknowledged:
            if oid not in self.engine.inbox.received:
                # Restart may lose the receiver handle, never the committed ciphertext/order.
                self._check("delivery")
                bundle = self.engine.store.one("SELECT bundle_hash,sealed FROM bundles WHERE order_id=?", oid)
                self.engine.inbox.deliver(self.buyer_id, oid, bundle["bundle_hash"], bundle["sealed"])
            payment = self.engine.store.one("SELECT tx_hash FROM payments WHERE order_id=?", oid)
            self.source.call("delivered", binding_sha256=self.state["binding_sha256"], create_hash=payment["tx_hash"])
        return {"order_id": oid, "status": status, "ledger": self.engine.ledger.name}

    def finish(self):
        oid = self._row()["order_id"]
        status = self.engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"]
        if status != "delivered":
            self._check("key")
            status = self.engine.process(oid)
        receipt = None
        if status == "delivered":
            payment = self.engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)
            receipt = self.source.call("receipt", binding_sha256=self.state["binding_sha256"], finish_hash=payment["finish_tx"])
        return {"order_id": oid, "status": status, "ledger": self.engine.ledger.name, "receipt": receipt}

    def open_package(self):
        self._check("delivery")
        if not self._licence_held():
            raise PermissionError("The contribution licence is no longer held")
        payload = self.engine.open_payload(self.buyer_id, self._row()["order_id"])
        content = base64.b64decode(payload["package_b64"], validate=True)
        if sha256_hex(content) != self.state["package_sha256"]:
            raise ValueError("Received package differs from the approved export")
        return content

    def sync_withdrawal(self):
        state = self.source.call("inspect")
        self._same(state)
        if state.get("active") is not False or state.get("status") not in {"withdrawn", "expired"}:
            raise PermissionError("The original Core consent has not been withdrawn or expired")
        row = self._row()
        terms = self.state["settlement"]
        oid = row["order_id"]
        status = self.engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"]
        if status != "delivered":
            self.engine.process(oid)
        pending_finish = self.engine.store.one(
            "SELECT 1 FROM outbox WHERE order_id=? AND kind='finish' AND status='pending'", oid)
        if pending_finish:
            # Finish and clawback share the payee signer; resolve its reserved sequence first.
            raise RuntimeError("Reconcile the pending finish before sending a licence clawback")
        if row["licence_status"] in {"issuing", "revoking"}:
            raise RuntimeError("Reconcile the pending licence transaction before completing withdrawal")
        if self._licence_held():
            if row["clawback_tx"]:
                raise RuntimeError("Reconcile the saved clawback and current licence balance")
            with self.engine.store.tx() as db:
                db.execute("UPDATE uniqdata_file_transfers SET licence_status='revoking' WHERE submission_ref=?",
                           (self.state["submission_ref"],))
            tx = self.engine.ledger.clawback_licence(terms["payee_address"], terms["payer_address"], row["licence_id"])
            with self.engine.store.tx() as db:
                db.execute("UPDATE uniqdata_file_transfers SET clawback_tx=?,licence_status='revoked' WHERE submission_ref=?",
                           (tx, self.state["submission_ref"]))
            if self._licence_held():
                raise RuntimeError("Reconcile the clawback before completing withdrawal")
        elif row["licence_id"] and not row["clawback_tx"]:
            raise RuntimeError("Reconcile the absent licence without a saved clawback receipt")
        status = self.engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"]
        receipt = self.finish()["receipt"] if status == "delivered" else None
        return {"status": "withdrawn", "clawback_tx": self._row()["clawback_tx"], "ledger": self.engine.ledger.name,
                "settlement_status": status, "receipt": receipt}
