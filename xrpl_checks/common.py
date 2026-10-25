"""Shared helpers for the Testnet feature checks.

Synthetic faucet accounts only. Seeds go to xrpl_checks/wallets.local.json (git-ignored);
results/*.json hold public tx hashes and addresses only."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AGENTRAIL_WALLETS", os.path.join(HERE, "wallets.local.json"))

from xrpl.clients import JsonRpcClient  # noqa: E402
from xrpl.models.requests import GenericRequest, ServerInfo  # noqa: E402

RPC = os.environ.get("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234/")
EXPLORER = "https://testnet.xrpl.org/transactions/"
TESTNET_NETWORK_ID = 1
os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
AMENDMENTS_INDEX = "7DB0788C020F02780A673DC74757F23823FA3014C1866E72CC4CD8B226CD6EF4"


def client() -> JsonRpcClient:
    c = JsonRpcClient(RPC)
    info = c.request(ServerInfo()).result.get("info", {})
    if info.get("network_id") != TESTNET_NETWORK_ID:
        raise SystemExit(f"refusing to run: {RPC} is not XRPL Testnet (network_id={info.get('network_id')})")
    return c


def ledger(rail: str = "direct"):
    os.environ["PAYMENT_RAIL"] = rail
    client()  # network guard
    from agentrail.ledger import make_ledger
    return make_ledger("testnet")


def amendment_id(name: str) -> str:
    return hashlib.sha512(name.encode()).hexdigest()[:64].upper()


def amendment_status(c, names: list[str]) -> dict[str, str]:
    """enabled / voting (majority since <time>) / not enabled, from the Amendments ledger entry."""
    r = c.request(GenericRequest(method="ledger_entry", index=AMENDMENTS_INDEX, ledger_index="validated")).result
    node = r.get("node", {})
    enabled = set(node.get("Amendments", []))
    majorities = {m["Majority"]["Amendment"]: m["Majority"]["CloseTime"] for m in node.get("Majorities", [])}
    out = {}
    for n in names:
        a = amendment_id(n)
        out[n] = "enabled" if a in enabled else (f"majority (since {majorities[a]})" if a in majorities
                                                 else "not enabled")
    return out


class Check:
    """Records each step: what we sent, what we expected, what the ledger said."""

    def __init__(self, key: str, title: str, amendments: list[str]):
        self.key, self.title, self.t0 = key, title, time.time()
        self.steps: list[dict] = []
        self.notes: list[str] = []
        self.accounts: dict[str, str] = {}
        self.amendments = amendment_status(client(), amendments) if amendments else {}
        print(f"\n=== {title} ===  amendments: {self.amendments}")

    def account(self, role: str, addr: str) -> str:
        self.accounts[role] = addr
        return addr

    def step(self, label: str, tx_hash: str | None, result: str | None, expect: str | None,
             started: float, kind: str = "success", note: str = ""):
        ok = expect is None or result == expect
        s = {"label": label, "kind": kind, "tx": tx_hash, "result": result, "expect": expect, "ok": ok,
             "seconds": round(time.time() - started, 1), "explorer": EXPLORER + tx_hash if tx_hash else None,
             "note": note}
        self.steps.append(s)
        print(f"  [{'OK ' if ok else 'BAD'}] {label}: {result} (expect {expect}) {s['seconds']}s "
              f"{s['explorer'] or ''} {note}")
        return s

    def note(self, text: str):
        self.notes.append(text)
        print("  note:", text)

    def save(self, conclusion: str, blocker: str | None = None, alternative: str | None = None):
        status = "pass" if self.steps and all(s["ok"] for s in self.steps) and not blocker else (
            "blocked" if blocker else "fail")
        out = {"key": self.key, "title": self.title, "status": status, "amendments": self.amendments,
               "accounts": self.accounts, "steps": self.steps, "notes": self.notes,
               "conclusion": conclusion, "blocker": blocker, "alternative": alternative,
               "total_seconds": round(time.time() - self.t0, 1),
               "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with open(os.path.join(HERE, "results", f"{self.key}.json"), "w") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        print(f"  => {status}: {conclusion}")
        return out


def run(key: str, title: str, amendments: list[str], main, rail: str = "direct"):
    """Create the ledger + Check, run main(c, L); an exception becomes a recorded blocker
    so the steps that did run (and their tx hashes) are kept."""
    L = ledger(rail)
    c = Check(key, title, amendments)
    try:
        return main(c, L)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return c.save(conclusion="stopped on error", blocker=f"{type(e).__name__}: {e}")
