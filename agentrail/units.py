"""The settlement unit. Amounts are integers of one millionth everywhere in the engine ("drops"):
with SETTLE_ASSET=XRP they are XRP drops; with a token (default) they are millionths of a test USD
token that settles through TokenEscrow (XLS-85) with the same SHA-256(K) condition.

On Testnet the token is our own test USD IOU, issued with the allow-escrow flag (Testnet RLUSD is
Ripple's to issue, so 50 wallets cannot be funded with it). It stands in for RLUSD: in production
only SETTLE_ISSUER and SETTLE_CODE change.
"""
from __future__ import annotations

import os

ASSET = os.environ.get("SETTLE_ASSET", "USD").upper()
TOKEN = ASSET != "XRP"
UNIT = ASSET if TOKEN else "XRP"
# The unit people see; the pages name it once in apps/shared/ui.js (DISPLAY_UNIT). Swap both together.
DISPLAY = os.environ.get("DISPLAY_UNIT", "RLUSD")
LABEL = (f"{UNIT} (test token, stands in for {DISPLAY})" if TOKEN else "XRP")


def fmt(micro) -> str:
    return f"{(micro or 0) / 1e6:g} {UNIT}"
