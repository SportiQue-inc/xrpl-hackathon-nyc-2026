"""RPC failures and incomplete history cannot be interpreted as absent rights/money."""
from types import SimpleNamespace

import pytest

from agentrail.ledger.licence import XrplLicenceMixin
from agentrail.ledger.xrpl_ledger import XrplLedger


def response(data, success=True):
    return SimpleNamespace(result=data, is_successful=lambda: success)


@pytest.mark.parametrize("data,success", [({"error": "lgrNotFound"}, False),
                                        ({"account_objects": [], "validated": False}, True)])
def test_licence_rpc_failure_is_not_proof_of_clawback(data, success):
    ledger = XrplLicenceMixin()
    ledger.client = SimpleNamespace(request=lambda _: response(data, success))
    with pytest.raises(RuntimeError):
        ledger.licence_held("holder", "A" * 48)


def test_licence_lookup_follows_empty_pages_on_the_same_validated_ledger():
    pages = iter([
        response({"validated": True, "account": "holder", "ledger_index": 100, "account_objects": [], "marker": "next"}),
        response({"validated": True, "account": "holder", "ledger_index": 100,
                  "account_objects": [{"MPTokenIssuanceID": "A" * 48, "MPTAmount": "1"}]}),
    ])
    queries = []
    def request(query):
        queries.append(query.to_dict())
        return next(pages)
    ledger = XrplLicenceMixin()
    ledger.client = SimpleNamespace(request=request)
    assert ledger.licence_held("holder", "A" * 48)
    assert queries[1]["marker"] == "next" and queries[1]["ledger_index"] == 100


def test_transaction_rpc_failure_remains_unknown(tmp_path):
    ledger = XrplLedger(wallet_file=str(tmp_path / "wallets.json"))
    ledger.client = SimpleNamespace(request=lambda _: response({"error": "notSynced"}, False))
    with pytest.raises(RuntimeError):
        ledger.lookup("A" * 64)
    with pytest.raises(RuntimeError):
        ledger.wait_validated("A" * 64, timeout=0)


@pytest.mark.parametrize("sequence,validated,index,expected", [(5, True, 21, True), (6, True, 21, False),
                                                              (5, False, 21, False), (5, True, 20, False)])
def test_replacement_needs_an_unconsumed_sequence_after_expiry(tmp_path, monkeypatch, sequence, validated, index, expected):
    from agentrail.ledger import xrpl_ledger
    ledger = XrplLedger(wallet_file=str(tmp_path / "wallets.json"))
    monkeypatch.setattr(xrpl_ledger, "decode", lambda _: {"Account": "payer", "Sequence": 5, "LastLedgerSequence": 20})
    ledger.client = SimpleNamespace(request=lambda _: response({"validated": validated, "ledger_index": index,
                                                               "account_data": {"Account": "payer", "Sequence": sequence}}))
    assert ledger.can_replace("synthetic-blob") is expected
