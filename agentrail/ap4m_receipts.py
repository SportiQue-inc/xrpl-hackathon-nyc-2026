"""AP4M receipts: the agent's RLUSD payments on the Mastercard AP4M rail, checked against XRPL EVM Testnet.

AP4M is an extra rail next to the XRPL escrow and key reveal: the participant's agent opens a Channel with
requestChannel(), pays each export call with an EIP-712 Voucher, the merchant redeems it on the PaymentLedger
(VoucherRedeemed) and the AP4M service settles RLUSD to the merchant payout wallet.

`ap4m/agent.mjs` writes one run record per live run. Records copied to `ap4m/receipts/` (no keys in them,
only addresses and transaction hashes) are what this module reads. `verify` asks an XRPL EVM RPC node for
each VoucherRedeemed transaction and checks it against the record: status, ledger, event, Channel, claim, amount.
"""
from __future__ import annotations

import json
import os
import urllib.request
from decimal import Decimal
from pathlib import Path

RECEIPTS = Path(__file__).resolve().parent.parent / "ap4m" / "receipts"
CHAIN_ID = 1449000
RPC_URL = "https://rpc.testnet.xrplevm.org"
EXPLORER = "https://explorer.testnet.xrplevm.org"
PAYMENT_LEDGER = "0xcab42800a5ecf0d253fa2581bb3334b4daefae91"
# keccak256 of VoucherRedeemed(bytes32,bytes32,bytes32,bytes32,address,bytes32,address,address,uint256,uint256,uint256);
# ap4m/lib/ledger-events.mjs computes it and ap4m/test/ledger-events.test.mjs checks it against a deployed log.
VOUCHER_REDEEMED_TOPIC = "0xe3de5c3755abd99a01530fd79b85708f309453f6d26eb9bb5dde4c14cd5f7175"
WEI = Decimal(10) ** 18

_verified: dict[str, dict] = {}   # a confirmed transaction does not change, so a passing check is kept


def _rpc_url() -> str:
    return os.environ.get("AP4M_RPC_URL", RPC_URL)


def _rpc(method: str, params: list, timeout: float = 6.0):
    req = urllib.request.Request(_rpc_url(), data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                                                               "params": params}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.loads(res.read())
    if "error" in body:
        raise RuntimeError(body["error"].get("message", "rpc error"))
    return body["result"]


def _rlusd(wei: int) -> str:
    return format((Decimal(wei) / WEI).normalize(), "f")


def decode_voucher_redeemed(log: dict) -> dict | None:
    """One raw log -> the VoucherRedeemed fields this page checks, or None for any other log."""
    topics = [t.lower() for t in log.get("topics") or []]
    if len(topics) != 4 or topics[0] != VOUCHER_REDEEMED_TOPIC:
        return None
    data = str(log.get("data", "")).removeprefix("0x")
    if len(data) != 8 * 64:
        return None
    word = lambda i: data[i * 64:(i + 1) * 64]   # noqa: E731
    return {"ledger": str(log.get("address", "")).lower(), "channel_id": topics[1], "claim_id": topics[2],
            "agent": "0x" + word(1)[24:], "payout": "0x" + word(4)[24:],
            "amount_rlusd": _rlusd(int(word(7), 16)), "cumulative_rlusd": _rlusd(int(word(6), 16))}


def check_receipt(receipt: dict | None, expect: dict) -> dict:
    """Compare one transaction receipt with what the run record says was paid."""
    if not receipt:
        return {"status": "not_found", "why": "the RPC node has no receipt for this transaction"}
    if receipt.get("status") != "0x1":
        return {"status": "failed", "why": f"transaction status {receipt.get('status')}"}
    events = [e for e in map(decode_voucher_redeemed, receipt.get("logs") or []) if e]
    events = [e for e in events if e["ledger"] == PAYMENT_LEDGER]
    if not events:
        return {"status": "mismatch", "why": "no VoucherRedeemed event from the AP4M PaymentLedger"}
    want = {k: str(v).lower() for k, v in expect.items() if v}
    for e in events:
        if all(e.get(k) == v if k != "amount_rlusd" else Decimal(e[k]) == Decimal(v) for k, v in want.items()):
            return {"status": "verified", "block": int(receipt.get("blockNumber", "0x0"), 16), "event": e}
    return {"status": "mismatch", "why": "VoucherRedeemed does not match the record (Channel, claim or amount)",
            "event": events[0]}


def verify(tx: str, expect: dict, rpc=_rpc) -> dict:
    if tx in _verified:
        return _verified[tx]
    try:
        result = check_receipt(rpc("eth_getTransactionReceipt", [tx]), expect)
    except Exception as exc:   # network or node trouble is reported, never mistaken for a pass
        return {"status": "unreachable", "why": f"{type(exc).__name__}: {exc}"[:200]}
    if result["status"] == "verified":
        _verified[tx] = result
    return result


def _tx(h: str | None) -> dict | None:
    return {"tx": h, "url": f"{EXPLORER}/tx/{h}"} if h else None


def summarize(rec: dict) -> dict:
    """Public view of one run record: what was paid, what was refused, the settlement and its receipt."""
    ch = rec.get("channel") or {}
    paid, refused = [], []
    for c in rec.get("calls") or []:
        offer = c.get("offer") or {}
        if c.get("paid"):
            ev = c.get("voucher_redeemed_event") or {}
            paid.append({"package": offer.get("package_id"), "week": offer.get("week"),
                         "price_rlusd": offer.get("price_rlusd"), "reason": c.get("reason"),
                         "claim_id": c.get("claim_id"), "package_sha256": c.get("package_sha256"),
                         "package_hash_ok": c.get("package_hash_ok"), **(_tx(c.get("voucher_redeemed_tx")) or {}),
                         "expect": {"channel_id": ch.get("channel_id"), "claim_id": c.get("claim_id"),
                                    "amount_rlusd": ev.get("amount_rlusd") or offer.get("price_rlusd")}})
        elif c.get("decision") == "refuse":
            refused.append({"package": offer.get("package_id"), "price_rlusd": offer.get("price_rlusd"),
                            "reason": c.get("reason")})
    st = rec.get("settlement") or {}
    return {"run_id": rec.get("run_id"), "finished_at": rec.get("finished_at"), "task": rec.get("task"),
            "agent": rec.get("agent"), "policy": rec.get("policy"),
            "channel": {"channel_id": ch.get("channel_id"), "cap_rlusd": ch.get("cap_rlusd"),
                        "opened_by_this_run": ch.get("opened_by_this_run")},
            "paid": paid, "refused": refused, "total_paid_rlusd": rec.get("total_paid_rlusd"),
            "settlement": {"payout": _tx(st.get("payout_tx")), "settlement": _tx(st.get("settlement_tx")),
                           "receipt_url": st.get("receipt_url")} if st else None,
            "payout_balance": rec.get("payout_balance")}


def runs(directory: Path | None = None) -> list[dict]:
    """Live run records, newest first. DRY_RUN records are never shown as payments."""
    directory = directory or RECEIPTS
    out = []
    for f in sorted(directory.glob("run-*.json")) if directory.is_dir() else []:
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rec.get("schema") == "agentrail.ap4m-run.v1" and rec.get("mode") == "live":
            out.append(summarize(rec))
    return sorted(out, key=lambda r: r.get("finished_at") or "", reverse=True)


def view(check: bool = False, directory: Path | None = None, rpc=_rpc) -> dict:
    rs = runs(directory)
    if check:
        for r in rs:
            for p in r["paid"]:
                p["onchain"] = verify(p["tx"], p["expect"], rpc) if p.get("tx") else {"status": "not_found"}
    return {"rail": "AP4M (Mastercard) on XRPL EVM Testnet", "chain_id": CHAIN_ID, "ledger": PAYMENT_LEDGER,
            "rpc": _rpc_url(), "explorer": EXPLORER, "asset": "RLUSD", "synthetic_data": True, "runs": rs}
