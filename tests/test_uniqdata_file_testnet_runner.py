"""Only synthetic Core and MockLedger; no faucet, user account or live approval."""

import json

import pytest

from agentrail.ledger import MockLedger
from scripts.uniqdata_file_testnet import FileCase
from test_uniqdata_contribution import CoreFixture


def test_case_reuses_budget_keys_order_and_original_withdrawal(tmp_path):
    ledger = MockLedger()
    case = FileCase(tmp_path, ledger)
    info = case.prepare()
    core = CoreFixture(info["payer_address"], info["payee_address"], case.recipient.public_hex)
    core.state["settlement"]["request_ref"] = info["request_ref"]
    case.settle(core)
    before = len(ledger.txs)
    restarted = FileCase(tmp_path, ledger)
    assert restarted.prepare() == info
    result = restarted.settle(core)
    assert result["status"] == "delivered" and result["ledger"] == "mock"
    assert result["opened_package_sha256"] == core.state["package_sha256"]
    assert len(ledger.txs) == before and core.exports == 1
    assert restarted.store.one("SELECT COUNT(*) n FROM approvals")["n"] == 1
    assert restarted.store.one("SELECT COUNT(*) n FROM approval_signatures")["n"] == 2
    assert restarted.store.one("SELECT total_drops FROM mandates")["total_drops"] == 1_000_000
    core.state.update(active=False, status="withdrawn")
    assert FileCase(tmp_path, ledger).withdraw(core)["future_access_denied"] is True
    assert "synthetic reviewed file" not in json.dumps(result)


def test_unrelated_contribution_or_recipient_cannot_spend_case_budget(tmp_path):
    ledger = MockLedger()
    case = FileCase(tmp_path, ledger)
    info = case.prepare()
    core = CoreFixture(info["payer_address"], info["payee_address"], case.recipient.public_hex)
    core.state["settlement"]["request_ref"] = "different-request"
    with pytest.raises(PermissionError):
        case.settle(core)
    assert case.store.one("SELECT COUNT(*) n FROM approvals")["n"] == 0


def test_ambiguous_budget_transfer_is_not_signed_again(tmp_path, monkeypatch):
    from agentrail.security import cosign

    case = FileCase(tmp_path, MockLedger())
    info = case.prepare()
    core = CoreFixture(info["payer_address"], info["payee_address"], case.recipient.public_hex)
    core.state["settlement"]["request_ref"] = info["request_ref"]
    monkeypatch.setattr(cosign, "_submit", lambda *_: (_ for _ in ()).throw(TimeoutError("lost response")))
    with pytest.raises(RuntimeError):
        case.settle(core)
    with pytest.raises(RuntimeError, match="Reconcile"):
        FileCase(tmp_path, case.ledger).settle(core)
    assert case.store.one("SELECT COUNT(*) n FROM approval_signatures")["n"] == 2
