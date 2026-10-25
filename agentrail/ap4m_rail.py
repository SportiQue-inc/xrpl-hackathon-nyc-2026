"""Client for the AP4M payment rail (`ap4m/rail-server.mjs`), shared by the vault market and the research contracts.

pay() asks the rail to pay `amount_micro` millionths of RLUSD on AP4M (XRPL EVM Testnet): an EIP-712 Voucher on
the team's open Channel, redeemed on-chain (VoucherRedeemed), settled by the AP4M service to the team's Merchant
payout wallet, and, with `forward_to`, forwarded on-chain to that address as a second hop.

The rail is idempotent on `ref`: the same ref returns the stored receipt and never pays twice. Every refusal
(per-payment cap 0.10, pool budget, rail not configured) comes back as {"ok": False, "reason": ...}; nothing
here raises for a refused or failed payment, so a caller can mark the order unpaid with the reason.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

PER_PAYMENT_CAP_MICRO = 100_000          # 0.10 RLUSD


def _url() -> str | None:
    return os.environ.get("AP4M_RAIL_URL") or None


def _post(path: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(_url().rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {os.environ.get('AP4M_RAIL_TOKEN', '')}"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read())


def configured() -> bool:
    return bool(_url())


def pay(ref: str, amount_micro: int, memo: dict | None = None, content: dict | None = None,
        forward_to: str | None = None, pool: str = "research", timeout: float = 180.0) -> dict:
    """Pay once for `ref`. Returns the rail's receipt: ok, amount_rlusd, claim_id, voucher_redeemed_tx, voucher_url,
    settlement_tx, payout_tx, receipt_url, forward_tx, forward_url, verified, content; or ok=False with reason."""
    amount_micro = int(amount_micro)
    if not 1 <= amount_micro <= PER_PAYMENT_CAP_MICRO:
        return {"ok": False, "ref": ref, "reason": f"amount must be 0.000001 to 0.10 RLUSD, got {amount_micro / 1e6}"}
    if not configured():
        return {"ok": False, "ref": ref, "reason": "ap4m rail not configured"}
    body = {"ref": ref, "amount_micro": amount_micro, "pool": pool, "memo": memo, "content": content, "forward_to": forward_to}
    try:
        return _post("/pay", body, timeout)
    except urllib.error.HTTPError as e:
        try:
            return {"ok": False, "ref": ref, **json.loads(e.read()), "status": e.code}
        except ValueError:
            return {"ok": False, "ref": ref, "reason": f"rail HTTP {e.code}", "retry": True}
    except (OSError, ValueError) as e:   # timeout or rail down: the rail keeps the job pending; retry the same ref
        return {"ok": False, "ref": ref, "reason": f"rail unreachable: {type(e).__name__}", "retry": True}
