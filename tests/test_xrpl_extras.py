"""Re-run lookups in the XRPL extras, against a fake JSON-RPC client (no network)."""
from types import SimpleNamespace

from agentrail.ledger.xrpl_extras import XrplExtrasMixin


def _tx(ty, h, ok=True, **fields):
    return {"hash": h, "tx_json": {"TransactionType": ty, **fields},
            "meta": {"TransactionResult": "tesSUCCESS" if ok else "tecNO_PERMISSION"}}


class PagedClient:
    """account_tx in pages of `size`, oldest first when forward=True, with a marker."""

    def __init__(self, txs, size=200):
        self.txs, self.size, self.calls = txs, size, []

    def request(self, req):
        self.calls.append(req)
        order = self.txs if req.forward else list(reversed(self.txs))
        start = req.marker or 0
        page = order[start:start + self.size]
        nxt = start + self.size
        return SimpleNamespace(result={"transactions": page,
                                       **({"marker": nxt} if nxt < len(order) else {})})


class Extras(XrplExtrasMixin):
    def __init__(self, client):
        self.client = client


def test_setup_txs_found_after_hundreds_of_later_payments():
    # Credential setup first, then 450 payments: the newest-200 window would miss the setup.
    txs = [_tx("CredentialCreate", "C1", CredentialType="AB"), _tx("CredentialAccept", "A1", CredentialType="AB")]
    txs += [_tx("Payment", f"P{i}") for i in range(450)]
    x = Extras(PagedClient(txs))
    assert x._past_hashes("rLab", ["CredentialCreate", "CredentialAccept"],
                          lambda tx: tx.get("CredentialType") == "AB") == ["C1", "A1"]
    assert len(x.client.calls) == 1   # oldest first: found on the first page


def test_pages_until_found_and_skips_failed_or_other_types():
    txs = [_tx("Payment", f"P{i}") for i in range(250)]
    txs += [_tx("CredentialCreate", "BAD", ok=False, CredentialType="AB"),
            _tx("CredentialCreate", "OTHER", CredentialType="CD"),
            _tx("CredentialCreate", "C2", CredentialType="AB")]
    x = Extras(PagedClient(txs))
    assert x._past_hashes("rLab", ["CredentialCreate"], lambda tx: tx.get("CredentialType") == "AB") == ["C2"]
    assert len(x.client.calls) == 2
