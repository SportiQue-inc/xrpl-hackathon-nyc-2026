import os

from .base import Ledger, LostResponse, Prepared, TxStatus
from .mock import MockLedger


def make_ledger(kind: str = "mock") -> Ledger:
    if kind == "testnet":
        from .amm import XrplAmmMixin
        from .licence import XrplLicenceMixin
        from .xrpl_extras import XrplExtrasMixin
        from .xrpl_ledger import XrplLedger

        class TestnetLedger(XrplAmmMixin, XrplLicenceMixin, XrplExtrasMixin, XrplLedger):
            pass

        if os.environ.get("PAYMENT_RAIL", "direct") == "x402":
            from .x402_rail import X402Mixin

            class X402TestnetLedger(X402Mixin, TestnetLedger):
                pass
            return X402TestnetLedger()
        return TestnetLedger()
    return MockLedger()


__all__ = ["Ledger", "LostResponse", "Prepared", "TxStatus", "MockLedger", "make_ledger"]
