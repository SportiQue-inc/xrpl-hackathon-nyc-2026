"""Requests, one-to-one trades and recovery use the real store and mock ledger."""
import json
import os
import random
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prototypes/data-vault-market/server"))
os.environ.setdefault("VM_DATA_DIR", tempfile.mkdtemp(prefix="vault-tests-"))
from vaultmarket import config, data, rail
from vaultmarket.market import Market


@pytest.fixture
def market(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LEDGER", "mock")
    monkeypatch.setattr(config, "LLM_PROVIDER", "none")
    monkeypatch.setattr(config, "ASSET", "XRP")
    monkeypatch.setattr(config, "MICRO_PER_UNIT", 10000)
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "market.db"))
    monkeypatch.setattr(rail, "KEYS_FILE", str(tmp_path / "keys.json"))
    m = Market()
    for aid, typ in (("buyer", "org"), ("seller", "person")):
        m.s.insert("accounts", id=aid, name=aid, type=typ, trust=.95, verified=1,
                   sell_agent={"mode": "ask", "min": {"sleep_log": 7}, "blocks": ["insurance pricing"]},
                   buy_agent={"auto_limit": 100, "min_trust": .7, "max_overlap": .3})
        m.addr[aid] = m.rail.ensure_account(aid)
    body = data.make_record("sleep_log", random.Random(1), "Synthetic", 0, (0, 0))
    m.test_file = m.add_file("seller", "sleep_log", "sleep.json", body, listed=False, source="synthetic")
    m.test_post = m.s.insert("postings", buyer="buyer", kind="sleep_log", offer=8, max=20,
                           purpose="sleep research", lot=5, min_trust=.7, status="open", once=1)
    return m


def journal(m, state="open", finished=False):
    from agentrail.ledger.conditions import condition_hex, new_key
    key = new_key()
    cid = m.s.insert("contracts", posting=m.test_post, buyer="buyer", kind="sleep_log", status="settling", trace={"protocol": [], "tx": []})
    p = m.rail.led.prepare_escrow_create(m.addr["buyer"], m.addr["seller"], 80000,
                                      condition_hex(key), m.rail.led.now() + 3600, f"vaultmarket/contract/{cid}")
    m.rail._submit(p)
    seq = m.rail._seq_of(p)
    fh = m.rail.finish_escrow(m.addr["seller"], m.addr["buyer"], seq, key, f"vaultmarket/contract/{cid}")["hash"] if finished else None
    m.s.insert("escrows", contract=cid, buyer="buyer", seller="seller", owner=m.addr["buyer"], seq=seq,
               create_hash=p.tx_hash, finish_hash=fh if state == "finished" else None, k=key.hex(),
               cancel_after=m.rail.led.now() + 3600, drops=80000, price=8, files=[m.test_file], state=state)
    return cid


def test_recovery_preserves_the_actual_file_record(market):
    cid = journal(market)
    expected = json.loads(market.s.one("SELECT clean FROM files WHERE id=?", (market.test_file,))["clean"])
    market.recover()
    assert market.s.one("SELECT status FROM contracts WHERE id=?", (cid,))["status"] == "settled"
    bought = market.s.one("SELECT raw FROM files WHERE source=?", (f"contract {cid}",))
    assert json.loads(bought["raw"])["records"] == [expected]


def test_recovery_closes_a_contract_with_all_legs_finished_before_crash(market):
    cid = journal(market, state="finished", finished=True)
    market.recover()
    assert market.s.one("SELECT status FROM contracts WHERE id=?", (cid,))["status"] == "settled"


def test_recovery_recognizes_finish_validated_before_database_write(market):
    cid = journal(market, finished=True)
    market.recover()
    assert market.s.one("SELECT status FROM contracts WHERE id=?", (cid,))["status"] == "settled"
    assert market.s.one("SELECT state FROM escrows WHERE contract=?", (cid,))["state"] == "finished"


def test_recovery_is_idempotent(market):
    cid = journal(market)
    market.recover()
    market.recover()
    assert market.s.one("SELECT count(*) n FROM files WHERE source=?", (f"contract {cid}",))["n"] == 1
    assert market.s.stat("settled") == 1


def test_sell_button_and_chat_both_create_durable_requests(market, monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, "M", market)
    monkeypatch.setattr(config, "PUBLIC", False)
    c = TestClient(web.app)
    assert c.post(f"/api/account/seller/sell-now/{market.test_post}").status_code == 200
    account = c.get("/api/account/seller").json()
    assert account.get("agent_queue"), "A sale must be persisted and visible beside the agent"
    assert account["agent_queue"][0]["status"] == "queued"
    assert account["chat"][-1]["role"] == "agent"
    assert c.post("/api/account/seller/chat", json={"text": "sell my sleep logs"}).status_code == 200
    assert len(c.get("/api/account/seller").json()["agent_queue"]) == 1, "Repeated instructions must not duplicate an active sale"


def test_one_seller_can_trade_without_an_unrequested_group_vote(market):
    market.s.x("UPDATE files SET status='listed' WHERE id=?", (market.test_file,))
    market.s.insert("interests", account="seller", posting=market.test_post)
    cid = market.negotiate(market.s.one("SELECT * FROM postings WHERE id=?", (market.test_post,)))
    c = market.s.one("SELECT * FROM contracts WHERE id=?", (cid,))
    assert c["status"] == "settled", (c["reason"], c["trace"])
    assert json.loads(c["sellers"]) == ["seller"]


def test_public_demo_cannot_modify_somebody_elses_vault(market, monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, "M", market)
    monkeypatch.setattr(config, "PUBLIC", True)
    assert TestClient(web.app).post(f"/api/account/seller/sell-now/{market.test_post}").status_code == 403


def test_all_finished_recovery_also_restores_receipt_links(market):
    cid = journal(market, state="finished", finished=True)
    market.recover()
    assert len(market.s.q("SELECT * FROM txs WHERE contract=?", (cid,))) == 2


def test_sale_queue_is_actually_processed_one_to_one(market):
    q = market.enqueue_sale("seller", "sleep_log", market.test_post)
    assert market.process_sale_queue()
    q = market.s.one("SELECT * FROM sale_queue WHERE id=?", (q["id"],))
    assert q["status"] == "settled"
    assert json.loads(market.s.one("SELECT sellers FROM contracts WHERE id=?", (q["contract"],))["sellers"]) == ["seller"]


def test_blocked_sale_keeps_the_file_private(market):
    market.s.x("UPDATE postings SET purpose='insurance pricing' WHERE id=?", (market.test_post,))
    q = market.enqueue_sale("seller", "sleep_log", market.test_post)
    assert q["status"] == "blocked"
    assert market.s.one("SELECT status FROM files WHERE id=?", (market.test_file,))["status"] == "private"


def test_old_xrp_history_uses_paid_amount_not_current_usd_conversion(market, monkeypatch):
    from fastapi.testclient import TestClient
    from vaultmarket import app as web
    monkeypatch.setattr(web, "M", market)
    cid = market.s.insert("contracts", posting=market.test_post, buyer="buyer", kind="sleep_log", status="settled", total=13.7, sellers=["seller"], asset="XRP", unit_micro=10000)
    market.s.insert("txs", contract=cid, type="EscrowFinish (key released)", drops=137000, result="tesSUCCESS", src="seller", dst="buyer", asset="XRP")
    c = TestClient(web.app).get("/api/market").json()["contracts"][0]
    assert (c["drops"], c["asset"]) == (137000, "XRP")


def test_crash_during_accounting_cannot_duplicate_delivery_or_proceeds(market, monkeypatch):
    market.s.x("UPDATE files SET status='listed' WHERE id=?", (market.test_file,))
    market.s.insert("interests", account="seller", posting=market.test_post)
    real_bump = market.s.bump
    def crash(k, by=1):
        if k == "settled":
            raise RuntimeError("simulated process stop during accounting")
        return real_bump(k, by)
    monkeypatch.setattr(market.s, "bump", crash)
    with pytest.raises(RuntimeError):
        market.negotiate(market.s.one("SELECT * FROM postings WHERE id=?", (market.test_post,)))
    assert market.s.one("SELECT status FROM contracts ORDER BY id DESC LIMIT 1")["status"] == "settling"
    monkeypatch.setattr(market.s, "bump", real_bump)
    market.recover()
    market.recover()
    assert market.s.one("SELECT sold FROM files WHERE id=?", (market.test_file,))["sold"] == 1
    assert market.s.one("SELECT count(*) n FROM files WHERE status='bought'")["n"] == 1
    assert market.s.stat("settled") == 1
