from .base import Ledger, LostResponse, Prepared, TxStatus
from .mock import MockLedger


def make_ledger(kind: str = "mock") -> Ledger:
    if kind == "testnet":
        from .xrpl_extras import XrplExtrasMixin
        from .xrpl_ledger import XrplLedger

        class TestnetLedger(XrplExtrasMixin, XrplLedger):
            pass
        return TestnetLedger()
    return MockLedger()


__all__ = ["Ledger", "LostResponse", "Prepared", "TxStatus", "MockLedger", "make_ledger"]
