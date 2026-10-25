from __future__ import annotations

from dataclasses import dataclass


class LostResponse(Exception):
    """The submit call may or may not have reached the ledger; the caller must
    look the transaction up by hash instead of paying again."""


@dataclass
class Prepared:
    tx_hash: str
    blob: str  # signed transaction; safe to store, contains no secret


@dataclass
class TxStatus:
    found: bool
    validated: bool = False
    success: bool = False
    ledger_index: int | None = None
    destination: str | None = None
    amount_drops: int | None = None
    invoice_id: str | None = None
    expired: bool = False  # past LastLedgerSequence and not in a validated ledger


class Ledger:
    """What the engine needs from a settlement network."""

    name = "abstract"

    def new_account(self, label: str) -> str:
        raise NotImplementedError

    def prepare_payment(self, source: str, destination: str, amount_drops: int,
                        invoice_id: str, memo: str) -> Prepared:
        raise NotImplementedError

    def submit(self, prepared: Prepared) -> None:
        raise NotImplementedError

    def lookup(self, tx_hash: str) -> TxStatus:
        raise NotImplementedError

    rail = "direct"

    def invoice_field_of(self, blob: str) -> str | None:
        """InvoiceID inside a signed blob we created (compared with the validated tx)."""
        raise NotImplementedError

    def is_expired(self, blob: str) -> bool:
        """True once the tx can no longer be included (past LastLedgerSequence)."""
        return False

    def wait_validated(self, tx_hash: str, timeout: float = 30.0) -> TxStatus:
        return self.lookup(tx_hash)

    def balance_drops(self, address: str) -> int:
        raise NotImplementedError

    def account_settings(self, address: str) -> dict:
        return {}

    def explorer_url(self, tx_hash: str) -> str | None:
        return None

    # XRPL-native controls (see xrpl_extras.py)
    def new_keypair(self, label: str) -> str:
        raise NotImplementedError

    def issue_credential(self, issuer: str, subject: str, cred_type: str) -> list[str]:
        raise NotImplementedError

    def has_credential(self, subject: str, issuer: str, cred_type: str) -> bool:
        raise NotImplementedError

    def setup_multisig(self, account: str, signers: list[str], quorum: int) -> list[str]:
        raise NotImplementedError

    def multisig_payment(self, source: str, destination: str, amount_drops: int,
                         signers: list[str], memo: str = "") -> str:
        raise NotImplementedError
