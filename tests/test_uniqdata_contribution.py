"""Synthetic Core boundary; real SQLite, encryption, mandates and mock escrow."""
import base64
import copy
import hashlib
import json
import sys
import uuid

import pytest

from agentrail.db import Store
from agentrail.engine import Engine, canonical
from agentrail.ledger import MockLedger
from agentrail.mandate import MandateChain
from agentrail.policy import BuyerMandate
from agentrail.security.devices import InstitutionVault, ParticipantKeyring
from agentrail.uniqdata_contribution import ContributionBridge, ResidentCore


class CoreFixture:
    def __init__(self, payer, payee, public_key):
        self.exports = 0
        self.delivered = False
        self.calls = []
        self.state = {
            "version": "uniqdata.agentrail.file-contribution.v1", "active": True, "status": "packaged",
            "submission_ref": str(uuid.uuid4()), "consent_ref": str(uuid.uuid4()),
            "participant_ref": "RF-synthetic", "binding_sha256": "a" * 64,
            "package_sha256": hashlib.sha256(b"synthetic reviewed file").hexdigest(),
            "settlement": {"network": "xrpl-testnet", "currency": "XRP", "amount_drops": 1_000_000,
                           "payer_address": payer, "payee_address": payee,
                           "recipient_key_sha256": hashlib.sha256(bytes.fromhex(public_key)).hexdigest(),
                           "request_ref": "synthetic-request"},
        }
        self.payload = canonical({"contract": "uniqdata.agentrail.file-delivery.v1", "salt": "b" * 32,
                                  "binding_sha256": self.state["binding_sha256"],
                                  "package_sha256": self.state["package_sha256"],
                                  "package_b64": base64.b64encode(b"synthetic reviewed file").decode()}).encode()
        self.state["bundle_sha256"] = hashlib.sha256(self.payload).hexdigest()

    def call(self, action, **body):
        self.calls.append(action)
        if action == "inspect":
            return copy.deepcopy(self.state)
        if action == "receipt":
            return {"network": "xrpl-testnet", "finish_tx_hash": body["finish_hash"], "simulation": True}
        if not self.state["active"]:
            raise PermissionError("Original Core consent is inactive")
        if action == "export":
            self.exports += 1
            return {"state": copy.deepcopy(self.state), "payload_b64": base64.b64encode(self.payload).decode()}
        assert body["binding_sha256"] == self.state["binding_sha256"]
        if action == "delivered":
            self.delivered = True
            return {"create_tx_hash": body["create_hash"]}
        if action == "check":
            if body["phase"] == "key" and not self.delivered:
                raise PermissionError("Encrypted handoff is missing")
            return copy.deepcopy(self.state)
        raise AssertionError(action)


@pytest.fixture
def connected(tmp_path):
    ledger = MockLedger()
    engine = Engine(Store(str(tmp_path / "bridge.db")), ledger)
    payer, payee = ledger.new_account("payer"), ledger.new_account("person")
    engine.add_party("buyer", "Test institution", "organization", payer)
    vault = InstitutionVault("recipient")
    engine.register_public_key("buyer", vault.public_hex)
    engine.set_mandate(BuyerMandate("buyer", 5_000_000, 1_000_000, ["research_file_delivery"]))
    chain = MandateChain("buyer")
    chain.issue(5_000_000, 1_000_000, 5_000_000, ["research_file_delivery"], ["RF-synthetic"])
    engine.mandate_chains["buyer"] = chain
    source = CoreFixture(payer, payee, vault.public_hex)
    keyring = ParticipantKeyring("RF-synthetic")
    bridge = ContributionBridge(engine, source, buyer_id="buyer", keyring=keyring, recipient=vault)
    return bridge, source, engine


def test_existing_core_consent_to_delivery_payment_and_original_withdrawal(connected):
    bridge, core, engine = connected
    oid = bridge.prepare()
    assert engine.store.one("SELECT COUNT(*) n FROM payments")["n"] == 1
    assert bridge.deliver()["status"] == "escrowed"
    assert engine.ledger.balance_drops(core.state["settlement"]["payee_address"]) > 0
    result = bridge.finish()
    assert result["status"] == "delivered" and result["ledger"] == "mock"
    assert bridge.open_package() == b"synthetic reviewed file"
    assert core.calls.index("delivered") < core.calls.index("receipt")
    count = len(engine.ledger.txs)
    assert bridge.prepare() == oid
    bridge.finish()
    assert len(engine.ledger.txs) == count and core.exports == 1
    core.state.update(active=False, status="withdrawn")
    revoked = bridge.sync_withdrawal()
    assert revoked["status"] == "withdrawn" and revoked["clawback_tx"]
    assert engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "delivered"
    with pytest.raises(PermissionError):
        bridge.open_package()
    assert "approve" not in core.calls and "register" not in core.calls


def test_revoked_before_key_release_does_not_pay(connected):
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge.deliver()
    core.state.update(active=False, status="withdrawn")
    bridge.sync_withdrawal()
    assert engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)["finish_tx"] is None
    with pytest.raises(PermissionError):
        bridge.finish()


@pytest.mark.parametrize("field,value", [("payee_address", "other-wallet"), ("payer_address", "other-payer"),
                                         ("recipient_key_sha256", "0" * 64), ("network", "xrpl-mainnet")])
def test_changed_payment_or_recipient_is_refused_before_any_order(connected, field, value):
    bridge, core, engine = connected
    if field == "payee_address":
        engine.add_party("RF-synthetic", "Existing participant", "person", "original-wallet")
    core.state["settlement"][field] = value
    with pytest.raises((ValueError, PermissionError)):
        bridge.prepare()
    assert engine.store.one("SELECT COUNT(*) n FROM orders")["n"] == 0


def test_no_owner_mandate_does_not_create_an_unlimited_budget(connected):
    bridge, core, engine = connected
    engine.mandate_chains.clear()
    with pytest.raises(PermissionError):
        bridge.prepare()
    assert engine.store.one("SELECT COUNT(*) n FROM orders")["n"] == 0


def test_changed_payload_or_original_binding_is_rejected(connected):
    bridge, core, engine = connected
    core.payload += b"tampered"
    with pytest.raises(ValueError):
        bridge.prepare()
    assert engine.store.one("SELECT COUNT(*) n FROM orders")["n"] == 0


def test_restart_reuses_the_order_and_redelivers_the_same_ciphertext(connected):
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge.deliver()
    restarted = Engine(Store(engine.store.path), engine.ledger)
    restarted.mandate_chains = engine.mandate_chains
    resumed = ContributionBridge(restarted, core, buyer_id="buyer", keyring=bridge.keyring,
                                 recipient=bridge.recipient)
    assert resumed.prepare() == oid
    resumed.deliver()
    assert resumed.finish()["status"] == "delivered"
    assert resumed.open_package() == b"synthetic reviewed file"
    assert core.exports == 1
    assert restarted.store.one("SELECT COUNT(*) n FROM orders")["n"] == 1


def test_restart_can_reconcile_original_withdrawal_without_another_export(connected):
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge.deliver()
    bridge.finish()
    core.state.update(active=False, status="withdrawn")
    restarted = Engine(Store(engine.store.path), engine.ledger)
    restarted.mandate_chains = engine.mandate_chains
    resumed = ContributionBridge(restarted, core, buyer_id="buyer", keyring=bridge.keyring,
                                 recipient=bridge.recipient)
    assert resumed.resume() == oid
    assert resumed.sync_withdrawal()["clawback_tx"]
    assert core.exports == 1
    assert restarted.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "delivered"
    with pytest.raises(PermissionError):
        resumed.open_package()


def test_resume_never_adopts_a_different_original_contribution(connected):
    bridge, core, engine = connected
    bridge.prepare()
    core.state["binding_sha256"] = "c" * 64
    with pytest.raises(PermissionError):
        bridge.resume()


@pytest.mark.parametrize("override_default", [False, True])
def test_a_mainnet_client_named_testnet_is_refused(connected, tmp_path, monkeypatch, override_default):
    from agentrail.ledger import xrpl_ledger
    from agentrail.ledger.xrpl_ledger import XrplLedger
    bridge, core, engine = connected
    if override_default:
        monkeypatch.setattr(xrpl_ledger, "TESTNET_RPC", "https://s1.ripple.com:51234/")
    engine.ledger = XrplLedger("https://s1.ripple.com:51234/", str(tmp_path / "no-wallets.json"))
    with pytest.raises(PermissionError, match="native-XRP Testnet"):
        bridge.prepare()
    assert engine.store.one("SELECT COUNT(*) n FROM orders")["n"] == 0


def test_ambiguous_licence_creation_is_not_reissued(connected, monkeypatch):
    bridge, core, engine = connected
    bridge.prepare()
    calls = []
    def lost(*args):
        calls.append(args)
        raise TimeoutError("Synthetic ambiguous response")
    monkeypatch.setattr(engine.ledger, "issue_licence", lost)
    with pytest.raises(TimeoutError):
        bridge.deliver()
    with pytest.raises(RuntimeError, match="Reconcile"):
        bridge.deliver()
    assert len(calls) == 1


def test_resident_transport_rejects_the_wrong_country_or_dev_database():
    for context in ({"country": "MN", "lane": "prod"}, {"country": "KR", "lane": "dev"}):
        command = [sys.executable, "-c", "import json; print(json.dumps(" + repr({"_core": context}) + "))"]
        source = ResidentCore(command, country="KR", lane="prod")
        with pytest.raises(PermissionError):
            source.call("inspect")


def test_resident_failure_never_exposes_the_private_pipe_or_diagnostics():
    source = ResidentCore([sys.executable, "-c", "import sys; print('synthetic-private-payload'); "
                           "print('synthetic-secret', file=sys.stderr); sys.exit(1)"], country="KR", lane="prod")
    with pytest.raises(PermissionError) as error:
        source.call("export")
    assert "synthetic" not in str(error.value)


def test_resident_transport_accepts_only_the_configured_context():
    command = [sys.executable, "-c", "import json; print(json.dumps({'_core': {'country': 'KR', 'lane': 'prod'}}))"]
    assert ResidentCore(command, country="KR", lane="prod").call("inspect")["_core"]["lane"] == "prod"


@pytest.mark.parametrize("command", ["python script.py", {"python": "script.py"}, ["python", None]])
def test_resident_transport_requires_an_explicit_argument_vector(command):
    with pytest.raises(ValueError):
        ResidentCore(command, country="KR", lane="prod")


@pytest.mark.parametrize("already_submitted", [False, True])
def test_withdrawal_recovery_never_first_publishes_a_saved_finish(connected, monkeypatch, already_submitted):
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge.deliver()
    original = engine._submit
    def crash(order_id, prepared):
        if already_submitted:
            original(order_id, prepared)
        raise RuntimeError("crash after finish persistence")
    monkeypatch.setattr(engine, "_submit", crash)
    with pytest.raises(RuntimeError):
        bridge.finish()
    payment = engine.store.one("SELECT * FROM payments WHERE order_id=?", oid)
    assert payment["finish_tx"]
    monkeypatch.setattr(engine, "_submit", original)
    core.state.update(active=False, status="withdrawn")
    calls = engine.ledger.submit_calls
    if already_submitted:
        bridge.sync_withdrawal()
    else:
        with pytest.raises(RuntimeError, match="Reconcile"):
            bridge.sync_withdrawal()
    engine.recover()
    assert engine.ledger.submit_calls == calls
    assert engine.ledger.lookup(payment["finish_tx"]).found is already_submitted
    if already_submitted:
        assert engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "delivered"
        assert "receipt" in core.calls
    else:
        monkeypatch.setattr(engine.ledger, "is_expired", lambda _: True)
        monkeypatch.setattr(engine.ledger, "can_replace", lambda _: True)
        engine.ledger.clock = payment["cancel_after"] + 1
        bridge.sync_withdrawal()
        engine.recover()
        assert not engine.ledger.lookup(payment["finish_tx"]).found
        assert engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "refunded"


def test_missing_ledger_history_cannot_replace_a_previously_applied_escrow(connected, monkeypatch):
    from agentrail.ledger.base import TxStatus
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge._ensure_licence()
    original = engine._submit
    def crash(order_id, prepared):
        original(order_id, prepared)
        raise RuntimeError("applied create before local confirmation")
    monkeypatch.setattr(engine, "_submit", crash)
    with pytest.raises(RuntimeError):
        engine.process(oid, until="finish")
    original_create = engine.store.one("SELECT tx_hash FROM payments WHERE order_id=?", oid)["tx_hash"]
    monkeypatch.setattr(engine, "_submit", original)
    lookup = engine.ledger.lookup
    monkeypatch.setattr(engine.ledger, "lookup", lambda h: TxStatus(found=False) if h == original_create else lookup(h))
    monkeypatch.setattr(engine.ledger, "is_expired", lambda _: True)
    with pytest.raises(RuntimeError, match="Reconcile"):
        engine.process(oid, until="finish")
    assert len([tx for tx in engine.ledger.txs.values() if tx["TransactionType"] == "EscrowCreate"]) == 1
    assert engine.store.one("SELECT tx_hash FROM payments WHERE order_id=?", oid)["tx_hash"] == original_create


def test_lost_clawback_receipt_stays_unresolved_without_another_submission(connected, monkeypatch):
    bridge, core, engine = connected
    bridge.prepare()
    bridge.deliver()
    bridge.finish()
    core.state.update(active=False, status="withdrawn")
    original = engine.ledger.clawback_licence
    def lost(*args):
        original(*args)
        raise TimeoutError("lost clawback receipt")
    monkeypatch.setattr(engine.ledger, "clawback_licence", lost)
    with pytest.raises(TimeoutError):
        bridge.sync_withdrawal()
    count = len(engine.ledger.txs)
    with pytest.raises(RuntimeError, match="Reconcile"):
        bridge.sync_withdrawal()
    assert len(engine.ledger.txs) == count
    assert bridge._row()["clawback_tx"] is None


def test_withdrawal_before_encrypted_handoff_returns_the_existing_escrow(connected):
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge._ensure_licence()
    assert engine._escrow_create(oid)
    core.state.update(active=False, status="withdrawn")
    bridge.sync_withdrawal()
    payment = engine.store.one("SELECT * FROM payments WHERE order_id=?", oid)
    engine.ledger.clock = payment["cancel_after"] + 1
    bridge.sync_withdrawal()
    assert engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "refunded"
    assert engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", oid)["finish_tx"] is None


def test_saved_unsubmitted_create_is_not_first_funded_after_withdrawal(connected, monkeypatch):
    bridge, core, engine = connected
    oid = bridge.prepare()
    bridge._ensure_licence()
    original = engine._submit
    monkeypatch.setattr(engine, "_submit", lambda *_: (_ for _ in ()).throw(RuntimeError("crash before create submit")))
    with pytest.raises(RuntimeError):
        engine.process(oid, until="finish")
    monkeypatch.setattr(engine, "_submit", original)
    core.state.update(active=False, status="withdrawn")
    calls = engine.ledger.submit_calls
    engine.recover()
    assert engine.ledger.submit_calls == calls
    monkeypatch.setattr(engine.ledger, "is_expired", lambda _: True)
    monkeypatch.setattr(engine.ledger, "can_replace", lambda _: True)
    engine.recover()
    assert engine.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "blocked"
    assert engine.store.one("SELECT reserved_drops FROM mandates")["reserved_drops"] == 0


def test_withdrawal_reconciles_an_earned_receipt_without_reopening_data(connected, monkeypatch):
    bridge, core, engine = connected
    bridge.prepare()
    bridge.deliver()
    original = core.call
    def unavailable(action, **body):
        if action == "receipt":
            raise PermissionError("receipt service temporarily unavailable")
        return original(action, **body)
    monkeypatch.setattr(core, "call", unavailable)
    with pytest.raises(PermissionError):
        bridge.finish()
    count = engine.ledger.submit_calls
    core.state.update(active=False, status="withdrawn")
    monkeypatch.setattr(core, "call", original)
    result = bridge.sync_withdrawal()
    assert result["receipt"]["finish_tx_hash"]
    assert core.exports == 1 and engine.ledger.submit_calls == count
    with pytest.raises(PermissionError):
        bridge.open_package()
