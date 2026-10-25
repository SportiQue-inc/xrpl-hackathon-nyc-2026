from .base import Ledger, LostResponse, Prepared, TxStatus
from .mock import MockLedger


def make_ledger(kind: str = "mock") -> Ledger:
    if kind == "testnet":
        from .xrpl_ledger import XrplLedger
        return XrplLedger()
    return MockLedger()


__all__ = ["Ledger", "LostResponse", "Prepared", "TxStatus", "MockLedger", "make_ledger"]
