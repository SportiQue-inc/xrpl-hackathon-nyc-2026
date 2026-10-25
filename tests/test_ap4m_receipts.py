"""AP4M rail: run records become public receipts, and each VoucherRedeemed is checked against the chain."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentrail import ap4m_receipts as ap, web

LOG = json.loads((Path(__file__).parent.parent / "ap4m" / "test" / "fixtures" / "voucher-redeemed-log.json")
                 .read_text())["log"]
TX = LOG["transactionHash"]
CHANNEL, CLAIM = LOG["topics"][1], LOG["topics"][2]


def record(mode="live", amount="0.01"):
    return {"schema": "agentrail.ap4m-run.v1", "run_id": "r1", "mode": mode, "finished_at": "2026-10-25T15:00:00Z",
            "agent": "0xagent", "channel": {"channel_id": CHANNEL, "cap_rlusd": "0.2", "opened_by_this_run": True},
            "calls": [{"paid": True, "decision": "pay", "reason": "within cap", "claim_id": CLAIM,
                       "voucher_redeemed_tx": TX, "package_sha256": "ab" * 32, "package_hash_ok": True,
                       "offer": {"package_id": "P-017-w3", "week": 3, "price_rlusd": amount},
                       "voucher_redeemed_event": {"amount_rlusd": amount}},
                      {"paid": False, "decision": "refuse", "reason": "price 0.5 RLUSD exceeds per-call cap 0.1 RLUSD",
                       "offer": {"package_id": "P-017-w6", "price_rlusd": "0.5"}}],
            "total_paid_rlusd": amount, "settlement": {"payout_tx": "0x" + "1" * 64, "receipt_url": "https://x/r"}}


def receipt(status="0x1"):
    return {"status": status, "blockNumber": LOG["blockNumber"], "logs": [LOG]}


def test_decodes_the_deployed_voucher_redeemed_log():
    e = ap.decode_voucher_redeemed(LOG)
    assert e["ledger"] == ap.PAYMENT_LEDGER and e["channel_id"] == CHANNEL and e["claim_id"] == CLAIM
    assert e["amount_rlusd"] == "0.01" and e["cumulative_rlusd"] == "0.04"
    assert e["payout"] == "0xc46d99faae8482f3876f49cae56b9f09057ce2b8"


def test_match_and_mismatch():
    want = {"channel_id": CHANNEL, "claim_id": CLAIM, "amount_rlusd": "0.010"}
    assert ap.check_receipt(receipt(), want)["status"] == "verified"
    assert ap.check_receipt(receipt(), {**want, "amount_rlusd": "0.05"})["status"] == "mismatch"
    assert ap.check_receipt(receipt("0x0"), want)["status"] == "failed"
    assert ap.check_receipt(None, want)["status"] == "not_found"
    other = {**LOG, "address": "0x" + "9" * 40}
    assert ap.check_receipt({"status": "0x1", "logs": [other]}, want)["status"] == "mismatch"


def test_view_lists_live_runs_only_and_verifies(tmp_path):
    (tmp_path / "run-a.json").write_text(json.dumps(record()))
    (tmp_path / "run-b.json").write_text(json.dumps(record(mode="DRY_RUN (no network)")))
    v = ap.view(directory=tmp_path)
    assert len(v["runs"]) == 1 and v["chain_id"] == 1449000
    r = v["runs"][0]
    assert [p["week"] for p in r["paid"]] == [3] and "onchain" not in r["paid"][0]
    assert r["refused"][0]["reason"].startswith("price 0.5")
    ap._verified.clear()
    v = ap.view(check=True, directory=tmp_path, rpc=lambda m, p: receipt())
    assert v["runs"][0]["paid"][0]["onchain"]["status"] == "verified"


def test_unreachable_rpc_is_never_a_pass(tmp_path):
    ap._verified.clear()
    def down(m, p):
        raise OSError("no route")
    assert ap.verify(TX, {"channel_id": CHANNEL}, down)["status"] == "unreachable"
    assert TX not in ap._verified


def test_public_endpoint_needs_no_token(monkeypatch, tmp_path):
    (tmp_path / "run-a.json").write_text(json.dumps(record()))
    monkeypatch.setattr(ap, "RECEIPTS", tmp_path)
    res = TestClient(web.app).get("/api/public/ap4m")
    assert res.status_code == 200 and res.json()["runs"][0]["channel"]["channel_id"] == CHANNEL
