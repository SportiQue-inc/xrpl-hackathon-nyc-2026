"""Payout in the stablecoin the participant picks, through an XRPL AMM pool.

The study always pays XRP (escrow). If the participant chose a stablecoin, their own agent then
swaps exactly what it received: a Payment to itself with Amount in the stablecoin, SendMax in XRP,
tfPartialPayment and a DeliverMin a few percent under the pool's spot price, so a thin or moving
pool fails the swap instead of delivering less than the participant expects. The participant opts
in once with a TrustSet. The service never holds the funds.
"""
from __future__ import annotations

from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.currencies import XRP, IssuedCurrency
from xrpl.models.requests import AMMInfo, GenericRequest
from xrpl.models.transactions import Payment, PaymentFlag, TrustSet

from .xrpl_extras import submit_capture

from .amm_terms import SLIPPAGE


def _fmt(v: float) -> str:
    return f"{v:.6f}".rstrip("0").rstrip(".")


class XrplAmmMixin:
    def stable_price(self, code: str, issuer: str) -> float | None:
        """Stablecoin per XRP at the pool's spot price, or None if there is no pool."""
        try:
            a = self.client.request(AMMInfo(asset=XRP(), asset2=IssuedCurrency(currency=code, issuer=issuer))).result["amm"]
        except Exception:
            return None
        return float(a["amount2"]["value"]) / (int(a["amount"]) / 1e6)

    def ensure_trustline(self, account: str, code: str, issuer: str) -> str | None:
        r = self.client.request(GenericRequest(method="account_lines", account=account, peer=issuer,
                                               ledger_index="validated")).result
        if any(l.get("currency") == code for l in r.get("lines", [])):
            return None
        h, code_, _ = submit_capture(self.client, TrustSet(account=account, limit_amount=IssuedCurrencyAmount(
            currency=code, issuer=issuer, value="1000000")), self.wallets[account])
        if code_ != "tesSUCCESS":
            raise RuntimeError(f"TrustSet {code_}")
        return h

    def swap_to_stable(self, account: str, drops: int, code: str, issuer: str) -> dict:
        price = self.stable_price(code, issuer)
        if price is None:
            return {"ok": False, "result": "no_pool"}
        want = drops / 1e6 * price
        cur = lambda v: IssuedCurrencyAmount(currency=code, issuer=issuer, value=_fmt(v))
        h, res, r = submit_capture(self.client, Payment(
            account=account, destination=account, amount=cur(want * 1.5), send_max=str(drops),
            deliver_min=cur(want * (1 - SLIPPAGE)), flags=PaymentFlag.TF_PARTIAL_PAYMENT), self.wallets[account])
        got = (r.get("meta", {}).get("delivered_amount") or {}).get("value") if isinstance(
            r.get("meta", {}).get("delivered_amount"), dict) else None
        return {"ok": res == "tesSUCCESS", "result": res, "tx": h, "delivered": got, "spot": price}
