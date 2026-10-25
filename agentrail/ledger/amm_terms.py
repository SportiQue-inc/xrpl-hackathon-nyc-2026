"""Which stablecoin a participant can choose, and the swap's price protection (no xrpl imports)."""
import os

# Ripple's Testnet RLUSD issuer and currency code ("RLUSD" as 160 bits); override for another coin.
STABLE_ISSUER = os.environ.get("PAYOUT_STABLE_ISSUER", "rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV")
STABLE_CODE = os.environ.get("PAYOUT_STABLE_CODE", "524C555344000000000000000000000000000000")
STABLE_LABEL = os.environ.get("PAYOUT_STABLE_LABEL", "RLUSD (Testnet issuer)")
SLIPPAGE = 0.03          # DeliverMin this far under the pool's spot price
