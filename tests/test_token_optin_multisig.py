"""A saved multisig account (master key disabled by an earlier run) still gets its token trust line."""
from agentrail.ledger import token_settle
from agentrail.ledger.token_settle import TokenSettleMixin


class _Client:
    def request(self, req):
        class R:
            result = {"lines": []}
        return R()


class _Led(TokenSettleMixin):
    def __init__(self):
        self.issuer, self.code, self.client = "rIssuer", "USD", _Client()
        self.wallets = {"rTreasury": object()}
        self.multisigned = []

    def can_sign(self, addr):
        return False

    def _multisigned(self, tx, account):
        self.multisigned.append((tx.transaction_type.value, account))
        return "tesSUCCESS"


def test_trustset_falls_back_to_cosigners_when_master_is_disabled(monkeypatch):
    monkeypatch.setattr(token_settle, "submit_capture", lambda c, tx, w: ("h", "tefMASTER_DISABLED", {}))
    led = _Led()
    led.token_optin("rTreasury", "org_treasury")
    assert led.multisigned == [("TrustSet", "rTreasury")]


def test_other_failures_still_raise(monkeypatch):
    monkeypatch.setattr(token_settle, "submit_capture", lambda c, tx, w: ("h", "tecNO_LINE", {}))
    led = _Led()
    try:
        led.token_optin("rTreasury", "org_treasury")
    except RuntimeError as e:
        assert "tecNO_LINE" in str(e)
    else:
        raise AssertionError("expected a failure")
    assert led.multisigned == []
