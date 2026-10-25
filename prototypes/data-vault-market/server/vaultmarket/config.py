"""Settings, all from the environment (see .env.example)."""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv():
    for path in (os.path.join(ROOT, ".env"), os.path.join(ROOT, "..", "..", "..", ".env")):
        if os.path.exists(path):
            for line in open(path):
                line = line.split("#", 1)[0].strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

DATA_DIR = os.environ.get("VM_DATA_DIR", ROOT)                  # where the DB, wallets and keys live (a disk on a host)
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.environ.get("VM_DB", os.path.join(DATA_DIR, "vaultmarket.db"))
LEDGER = os.environ.get("VM_LEDGER", "testnet")            # testnet | devnet | mock (tests only; the UI says so)
WALLETS = os.environ.get("VM_WALLETS", os.path.join(DATA_DIR, "wallets.local.json"))
AGENTS = int(os.environ.get("VM_AGENTS", "50"))
TICK_SECONDS = float(os.environ.get("VM_TICK_SECONDS", "30"))   # one negotiation round per tick
# Settlement asset. USD: a test USD token (IOU) on the ledger, issued by this application, settled by token
# escrow; XRP: the fallback. Amounts are kept in millionths of the asset (drops for XRP).
ASSET = os.environ.get("VM_ASSET", "USD").upper()
USD_PER_UNIT = float(os.environ.get("VM_USD_PER_UNIT", "1"))         # 1 price unit = 1 test USD, all display values use the actual test asset
# How the token is shown to people. The ledger key stays "test USD"; swap the name and footnote here
# (or in env) when the market's own registered token replaces the stand-in.
ASSET_LABEL = os.environ.get("VM_ASSET_LABEL", "test USD")
ASSET_FOOTNOTE = os.environ.get("VM_ASSET_FOOTNOTE", "XRPL Testnet: application-issued test USD; this is not official RLUSD.")
XRP_DROPS_PER_UNIT = int(os.environ.get("VM_DROPS_PER_UNIT", "10000"))  # fallback: 1 price unit = 0.01 XRP
MICRO_PER_UNIT = int(USD_PER_UNIT * 1_000_000) if ASSET == "USD" else XRP_DROPS_PER_UNIT
DROPS_PER_XRP_UNIT = MICRO_PER_UNIT    # older name, same meaning: millionths of the asset per price unit
K_MIN = 1

LLM_PROVIDER = os.environ.get("VM_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER") or (
    "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai" if os.environ.get("OPENAI_API_KEY") else "none")
ANTHROPIC_MODEL = os.environ.get("VM_ANTHROPIC_MODEL", "claude-haiku-5-5")
# one model, or a comma list tried in order: a model that answers 429 rests until its limit resets.
# On OpenAI's lowest tier every model has its own 50 requests/day, so a chain of seven gives about 350.
_SMALL = ["gpt-5-nano", "gpt-4o-mini", "gpt-5.4-nano", "gpt-5-mini", "gpt-5.4-mini", "gpt-4.1-mini", "o4-mini"]
_chosen = [m.strip() for m in (os.environ.get("VM_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL") or "").split(",") if m.strip()]
OPENAI_MODELS = _chosen + [m for m in _SMALL if m not in _chosen]   # the chosen model first, the small ones behind it
OPENAI_MODEL = OPENAI_MODELS[0]
OPENAI_REASONING = os.environ.get("VM_OPENAI_REASONING", "minimal")   # reasoning models only; short turns don't need more
LLM_RPM = int(os.environ.get("VM_LLM_RPM", "4"))                 # calls per minute, all agents together
LLM_DAILY_CALLS = int(os.environ.get("VM_LLM_DAILY_CALLS", "320"))   # spread evenly over the day (llm.free_slots)

# Membership. VM_PUBLIC=1 when the site is reachable from the internet: the demo accounts become
# read-only and only signed-in members act, each on their own account.
PUBLIC = os.environ.get("VM_PUBLIC", "0") == "1"
DEMO_CHAT_DAILY = int(os.environ.get("VM_DEMO_CHAT_DAILY", "200"))   # the shared demo vault, all visitors together
CHAT_RESERVE = int(os.environ.get("VM_CHAT_RESERVE", "150"))    # chat can use this much ahead of pacing, within the same hard daily cap
CHAT_DAILY = int(os.environ.get("VM_CHAT_DAILY", "30"))         # agent chat messages per member per day
SIGNUPS_PER_HOUR = int(os.environ.get("VM_SIGNUPS_PER_HOUR", "5"))  # per IP address

# Read-only engine demonstration, linked from the marketplace navigation.
ENGINE_URL = os.environ.get("VM_ENGINE_URL", "https://agentrail-try-production.up.railway.app/try")
