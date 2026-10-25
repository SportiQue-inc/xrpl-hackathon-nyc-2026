"""Settle in an issued token instead of XRP (TokenEscrow, XLS-85).

The engine keeps integer millionths; this mixin turns them into token amounts on the wire and back.
Setup per account: a TrustSet to the issuer, then the issuer funds it. The issuer is our own Testnet
account with DefaultRipple (holders pay each other) and AllowTrustLineLocking (its token may sit in
an escrow); without that flag EscrowCreate fails with tecNO_PERMISSION. XRP is still needed for fees
and reserves, so faucet funding stays.
"""
from __future__ import annotations

import os

from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountInfo, GenericRequest
from xrpl.models.transactions import AccountSet, AccountSetAsfFlag, Payment, TrustSet

from .. import units
from .xrpl_extras import submit_capture

LSF_DEFAULT_RIPPLE = 0x00800000
LSF_ALLOW_TRUSTLINE_LOCKING = 0x40000000
ISSUER_LABEL = "settle_issuer"
FUND = os.environ.get("SETTLE_FUND", "5000")          # token units each account starts with


def _fmt(micro: int) -> str:
    return f"{micro / 1e6:.6f}".rstrip("0").rstrip(".")


def code_of(unit: str) -> str:
    """3-letter codes go as is; longer ones (RLUSD) as 160-bit hex."""
    return unit if len(unit) == 3 else unit.encode().hex().upper().ljust(40, "0")


class TokenSettleMixin:
    def _token_setup(self):
        if getattr(self, "issuer", None):
            return
        self.code = os.environ.get("SETTLE_CODE") or code_of(units.UNIT)
        given = os.environ.get("SETTLE_ISSUER")
        self.issuer = given or super().new_account(ISSUER_LABEL)
        self.setup_txs: list[dict] = []
        if self.can_sign(self.issuer):
            flags = int(self.client.request(AccountInfo(account=self.issuer, ledger_index="validated"))
                        .result["account_data"]["Flags"])
            for bit, asf in ((LSF_DEFAULT_RIPPLE, AccountSetAsfFlag.ASF_DEFAULT_RIPPLE),
                             (LSF_ALLOW_TRUSTLINE_LOCKING, AccountSetAsfFlag.ASF_ALLOW_TRUSTLINE_LOCKING)):
                if not flags & bit:
                    h, res, _ = submit_capture(self.client, AccountSet(account=self.issuer, set_flag=asf),
                                               self.wallets[self.issuer])
                    if res != "tesSUCCESS":
                        raise RuntimeError(f"AccountSet {asf.name} on the token issuer: {res}")
                    self.setup_txs.append({"what": f"issuer {asf.name}", "tx": h})

    def new_account(self, label: str) -> str:
        self._token_setup()
        addr = super().new_account(label)
        if addr != self.issuer:
            self.token_optin(addr, label)
        return addr

    def token_optin(self, addr: str, label: str = "") -> None:
        """Trust line to the issuer, then funds from it (once; re-runs top up when half is spent)."""
        self._token_setup()
        r = self.client.request(GenericRequest(method="account_lines", account=addr, peer=self.issuer,
                                               ledger_index="validated")).result
        line = next((l for l in r.get("lines", []) if l.get("currency") == self.code), None)
        if line is None:
            h, res, _ = submit_capture(self.client, TrustSet(account=addr, limit_amount=IssuedCurrencyAmount(
                currency=self.code, issuer=self.issuer, value="100000000")), self.wallets[addr])
            if res != "tesSUCCESS":
                raise RuntimeError(f"TrustSet for {label or addr}: {res}")
            bal = 0.0
        else:
            bal = float(line.get("balance", 0))
        if bal < float(FUND) / 2 and self.can_sign(self.issuer):
            h, res, _ = submit_capture(self.client, Payment(
                account=self.issuer, destination=addr,
                amount=IssuedCurrencyAmount(currency=self.code, issuer=self.issuer, value=FUND)),
                self.wallets[self.issuer])
            if res != "tesSUCCESS":
                raise RuntimeError(f"funding {label or addr} with {units.UNIT}: {res}")

    def _amount(self, drops: int):
        self._token_setup()
        return IssuedCurrencyAmount(currency=self.code, issuer=self.issuer, value=_fmt(int(drops)))

    def _parse_amount(self, a) -> int | None:
        if isinstance(a, dict) and a.get("currency") == self.code and a.get("issuer") == self.issuer:
            return round(float(a["value"]) * 1e6)
        return None              # XRP or another token never counts as this payment

    def balance_drops(self, address: str) -> int:
        self._token_setup()
        r = self.client.request(GenericRequest(method="account_lines", account=address, peer=self.issuer,
                                               ledger_index="validated")).result
        return sum(round(float(l["balance"]) * 1e6) for l in r.get("lines", []) if l.get("currency") == self.code)
