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
TICK_SECONDS = float(os.environ.get("VM_TICK_SECONDS", "15"))   # one negotiation round per tick
DROPS_PER_XRP_UNIT = int(os.environ.get("VM_DROPS_PER_UNIT", "10000"))  # 1 price unit = 0.01 XRP on the ledger
K_MIN = 5

LLM_PROVIDER = os.environ.get("VM_LLM_PROVIDER") or os.environ.get("LLM_PROVIDER") or (
    "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai" if os.environ.get("OPENAI_API_KEY") else "none")
ANTHROPIC_MODEL = os.environ.get("VM_ANTHROPIC_MODEL", "claude-haiku-5-5")
OPENAI_MODEL = os.environ.get("VM_OPENAI_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
LLM_RPM = int(os.environ.get("VM_LLM_RPM", "4"))                 # calls per minute, all agents together
LLM_DAILY_CALLS = int(os.environ.get("VM_LLM_DAILY_CALLS", "600"))

# Membership. VM_PUBLIC=1 when the site is reachable from the internet: the demo accounts become
# read-only and only signed-in members act, each on their own account.
PUBLIC = os.environ.get("VM_PUBLIC", "0") == "1"
CHAT_DAILY = int(os.environ.get("VM_CHAT_DAILY", "30"))         # agent chat messages per member per day
SIGNUPS_PER_HOUR = int(os.environ.get("VM_SIGNUPS_PER_HOUR", "5"))  # per IP address
