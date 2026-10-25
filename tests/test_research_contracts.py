"""A research contract posted over HTTP, joined by people with their own keys, traded by their agents."""
import pytest
from fastapi.testclient import TestClient

from agentrail import web
from agentrail.security.devices import Device
from agentrail.security.http import reset_rate_limits

TERMS = {"title": "Sleep and fatigue, 4 weeks", "institution": "Test Sleep Lab", "irb_approval": "IRB-TEST-001",
         "purpose": "sleep_research", "items": ["sleep.daily", "fatigue.survey", "blood_pressure.daily"],
         "weeks": [1, 4], "price_per_item_drops": 200_000, "budget_drops": 50_000_000, "capacity": 10}


@pytest.fixture
def c():
    reset_rate_limits()
    web._state.pop("lane", None)
    web.reset()
    return TestClient(web.app)


def token(c, dev: Device) -> dict:
    n = c.post("/api/auth/challenge", json={"sub": dev.sub}).json()["nonce"]
    r = c.post("/api/auth/token", json={"sub": dev.sub, "nonce": n, "signature": dev.sign_challenge(n)})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def post(c, terms=TERMS):
    researcher = Device("researcher-key")
    r = c.post("/api/contracts", json={"terms": terms, "researcher_key": researcher.public_hex})
    assert r.status_code == 200, r.text
    out = r.json()
    researcher.sub = out["researcher_sub"]
    return out["contract"]["id"], out["invite_code"], researcher


def join(c, cid, code, automation, name):
    d = Device(name)
    s = c.post(f"/api/contracts/{cid}/join/start",
               json={"invite_code": code, "public_key": d.public_hex, "automation": automation}).json()
    d.sub = s["pid"]
    r = c.post(f"/api/contracts/{cid}/join/complete", json={"pid": s["pid"], "signature": d.sign_consent(s["consent_hash"])})
    assert r.status_code == 200, r.text
    h = token(c, d)
    assert c.post(f"/api/p/{d.sub}/contracts/records", json={"generate_test_weeks": [1, 2]}, headers=h).json()["stored"] > 0
    return d, h


def test_nothing_is_in_the_code_terms_come_from_the_posting(c):
    cid, code, _ = post(c)
    pub = c.get(f"/api/contracts/{cid}").json()
    assert pub["terms"]["institution"] == "Test Sleep Lab" and pub["terms"]["irb_approval"] == "IRB-TEST-001"
    assert pub["terms"]["institution_id"] != "org_sleeplab" and pub["members"] == 0
    assert code not in str(c.get("/api/contracts").json())             # the invite code is shown once, never listed


def test_posting_rejects_t3_and_unknown_items(c):
    r = c.post("/api/contracts", json={"terms": {**TERMS, "items": ["imaging.mri"]}, "researcher_key": "a" * 64})
    assert r.status_code == 422 and "T3" in r.json()["detail"]
    r = c.post("/api/contracts", json={"terms": {**TERMS, "items": ["diagnosis.rare"]}, "researcher_key": "a" * 64})
    assert r.status_code == 422


def test_join_needs_the_invite_and_the_joiners_own_signature(c):
    cid, code, _ = post(c)
    d = Device("x")
    assert c.post(f"/api/contracts/{cid}/join/start", json={"invite_code": "wrong-code-1", "public_key": d.public_hex}).status_code == 403
    s = c.post(f"/api/contracts/{cid}/join/start", json={"invite_code": code, "public_key": d.public_hex}).json()
    other = Device("y")
    other.sub = s["pid"]
    r = c.post(f"/api/contracts/{cid}/join/complete", json={"pid": s["pid"], "signature": other.sign_consent(s["consent_hash"])})
    assert r.status_code == 403
    assert s["consent"]["contract"]["id"] == cid and s["consent"]["synthetic_demo"] is False


def test_round_follows_each_members_own_choice_then_approve_and_withdraw(c):
    cid, code, researcher = post(c)
    a, ha = join(c, cid, code, "auto_all", "a")
    b, hb = join(c, cid, code, "confirm_each", "b")
    w, hw = join(c, cid, code, "auto_standard", "w")
    rh = token(c, researcher)
    assert c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=ha).status_code == 403   # not a researcher
    r = c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=rh).json()
    by = {x["person"]: x for x in r["results"]}
    assert by[a.sub]["status"] == "delivered" and by[a.sub]["escrow_finish"]["tx"]
    assert by[b.sub]["status"] == "needs_approval"
    assert "blood_pressure.daily" not in by[w.sub]["granted"]          # sensitive item waits for the person

    # b approves week 1 with a fresh signature; a replayed or missing one is refused
    mine = c.get(f"/api/p/{b.sub}/contracts", headers=hb).json()
    ask = mine["contracts"][0]["pending_approvals"][0]
    items = ask["items"]
    path = f"/api/p/{b.sub}/contracts/{cid}/requests/{ask['request_id']}/approve"
    bad = c.post(path, json={"items": items, "signature": b.sign_consent("0" * 64)}, headers=hb)
    assert bad.status_code == 403
    lane = web.lane()
    sig = b.sign(lane.action_message(b.sub, cid, f"approve:{ask['request_id']}:{','.join(sorted(items))}"))
    ok = c.post(path, json={"items": items, "signature": sig}, headers=hb).json()
    assert ok["order"]["status"] == "delivered"
    assert c.get(f"/api/p/{a.sub}/contracts", headers=hb).status_code == 403    # only your own record

    view = c.get(f"/api/p/{b.sub}/contracts", headers=hb).json()
    assert view["settled_drops"] == len(items) * TERMS["price_per_item_drops"] and view["active_institutions"] == 1
    assert view["history"][0]["escrow_finish"]["tx"] and view["display_unit"]

    sig = w.sign(lane.action_message(w.sub, cid, "withdraw"))
    out = c.post(f"/api/p/{w.sub}/contracts/{cid}/withdraw", json={"signature": sig}, headers=hw).json()
    assert out["contracts"][0]["status"] == "withdrawn"
    r2 = c.post(f"/api/contracts/{cid}/rounds", json={"week": 2}, headers=rh).json()
    assert w.sub not in {x["person"] for x in r2["results"]}
    con = c.get(f"/api/contracts/{cid}/console", headers=rh).json()
    assert con["members"] == 2 and con["spent_drops"] > 0


def test_contracts_survive_a_demo_reset(c):
    cid, code, researcher = post(c)
    a, _ = join(c, cid, code, "auto_all", "a")
    web.reset()
    assert c.get(f"/api/contracts/{cid}").json()["members"] == 1
    assert c.get(f"/api/p/{a.sub}/contracts", headers=token(c, a)).status_code == 200
    assert c.get(f"/api/contracts/{cid}/console", headers=token(c, researcher)).status_code == 200


def test_payments_reach_the_members_uniqdata_account_once_per_order(c, monkeypatch):
    cid, code, researcher = post(c)
    lane = web.lane()
    sent = []

    class FakeUniQdata:
        def report_settlements(self, records):
            sent.append(records)
            return {"written": len(records)}

    lane.uniqdata["P-001"] = FakeUniQdata()
    d = Device("u")
    s = c.post(f"/api/contracts/{cid}/join/start", json={"invite_code": code, "public_key": d.public_hex,
                                                         "automation": "auto_all", "uniqdata_account": "P-001"}).json()
    d.sub = s["pid"]
    # the vault reads that UniQdata account: give it stored rows for the test instead
    from agentrail.research_contracts import StoredSource
    monkeypatch.setattr(lane, "_agent", lambda pid, src, _orig=lane._agent: _orig(pid, "stored"))
    assert c.post(f"/api/contracts/{cid}/join/complete",
                  json={"pid": d.sub, "signature": d.sign_consent(s["consent_hash"])}).status_code == 200
    assert isinstance(lane.people[d.sub].vault.sources[0], StoredSource)
    lane.store_records(d.sub, generate_weeks=[1])
    monkeypatch.setattr(lane.ledger, "name", "testnet")
    c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=token(c, researcher))
    assert len(sent) == 1 and len(sent[0]) == 1
    r = sent[0][0]
    assert r["status"] == "settled" and r["period"] == "week 1" and r["display_unit"] and r["escrow_finish_tx"]
    assert r["consent_hash"] == s["consent_hash"] and r["contract_status"] == "active"


def test_contract_pages_are_served(c):
    for f in ("post.html", "post.js", "join.html", "join.js", "contracts.js", "contracts.css"):
        assert c.get(f"/apps/contracts/{f}").status_code == 200


AP4M_TERMS = {**TERMS, "items": ["sleep.daily", "fatigue.survey"], "price_per_item_drops": 10_000,
              "budget_drops": 5_000_000}


@pytest.fixture
def rail(monkeypatch):
    """A fake AP4M rail with the real client's contract: idempotent on ref, never raises, ok=False on a refusal."""
    import sys
    import types
    import agentrail
    paid, state = {}, {"down": False}

    def pay(ref, amount_micro, memo=None, content=None, forward_to=None, pool="research", timeout=180.0):
        if state["down"]:
            return {"ok": False, "ref": ref, "reason": "rail unreachable: URLError", "retry": True}
        if amount_micro > 100_000:
            return {"ok": False, "ref": ref, "reason": "per-payment cap"}
        if ref not in paid:
            h = f"0x{len(paid) + 1:064x}"
            paid[ref] = {"ok": True, "ref": ref, "amount_rlusd": amount_micro / 1e6, "claim_id": h,
                         "voucher_redeemed_tx": h, "voucher_url": f"https://explorer.testnet.xrplevm.org/tx/{h}",
                         "receipt_url": f"https://hackathon.ap4m.build/public/evidence/claims/{h}.json",
                         "verified": True, "pool": pool, "memo": memo}
        return paid[ref]

    def lookup(ref, timeout=10.0):
        return {**paid[ref], "receipt_url": f"https://hackathon.ap4m.build/r/{ref}.json"} if ref in paid else None

    fake = types.SimpleNamespace(pay=pay, lookup=lookup)
    monkeypatch.setitem(sys.modules, "agentrail.ap4m_rail", fake)
    monkeypatch.setattr(agentrail, "ap4m_rail", fake, raising=False)
    monkeypatch.setattr(web.lane(), "rail", "ap4m")
    return paid, state


def test_ap4m_rail_pays_each_delivered_week_once_and_shows_what_was_paid(c, rail):
    paid, state = rail
    over = c.post("/api/contracts", json={"terms": {**AP4M_TERMS, "price_per_item_drops": 60_000}, "researcher_key": "a" * 64})
    assert over.status_code == 422 and "AP4M" in over.json()["detail"]        # 2 x 0.06 > 0.10 per payment
    cid, code, researcher = post(c, AP4M_TERMS)
    a, ha = join(c, cid, code, "auto_all", "a")
    b, hb = join(c, cid, code, "auto_all", "b")
    rh = token(c, researcher)

    state["down"] = True                       # the rail is down for b's payment only
    lane = web.lane()
    r = c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=rh).json()
    assert {x["payment"]["status"] for x in r["results"]} == {"unpaid"} and not paid
    mine = c.get(f"/api/p/{a.sub}/contracts", headers=ha).json()
    assert mine["settled_drops"] == 0 and mine["held_drops"] == 20_000        # delivered, not yet paid: not shown as paid

    state["down"] = False
    r = c.post(f"/api/contracts/{cid}/rounds", json={"week": 2}, headers=rh).json()   # retries week 1, pays week 2
    assert len(paid) == 4 and all(p["pool"] == "research" for p in paid.values())
    assert all(p["amount_rlusd"] == 0.02 for p in paid.values())
    mine = c.get(f"/api/p/{a.sub}/contracts", headers=ha).json()
    assert mine["settled_drops"] == 40_000 and mine["held_drops"] == 0
    pay = mine["history"][0]["payment"]
    assert pay["rail"] == "ap4m" and pay["status"] == "paid" and pay["receipt_url"] and "merchant" in pay["payee"]
    assert mine["contracts"][0]["latest_tx"]["rail"] == "ap4m"
    lane.retry_payments(cid)
    assert len(paid) == 4                      # paid orders are never paid again

    sig = b.sign(lane.action_message(b.sub, cid, "withdraw"))
    c.post(f"/api/p/{b.sub}/contracts/{cid}/withdraw", json={"signature": sig}, headers=hb)
    c.post(f"/api/contracts/{cid}/rounds", json={"week": 3}, headers=rh)
    assert len(paid) == 5 and not any(p["memo"]["member"] == b.sub and p["memo"]["week"] == 3 for p in paid.values())
    con = c.get(f"/api/contracts/{cid}/console", headers=rh).json()
    assert con["payments"] == {"rail": "ap4m", "paid_count": 5, "paid_drops": 100_000, "unpaid_count": 0, "unpaid_drops": 0}


def test_a_restart_on_the_mock_ledger_still_trades(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTRAIL_CONTRACTS_DB", str(tmp_path / "contracts.db"))
    monkeypatch.setenv("AGENTRAIL_KEYSTORE", str(tmp_path / "keystore"))
    reset_rate_limits()
    web._state.pop("lane", None)
    web.reset()
    c = TestClient(web.app)
    cid, code, researcher = post(c)
    a, _ = join(c, cid, code, "auto_all", "a")
    web._state.pop("lane", None)               # a redeploy: the lane is rebuilt from its store
    web.reset()
    r = c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=token(c, researcher)).json()
    assert r["results"][0]["status"] == "delivered", r["results"][0]
    assert "blood_pressure.daily" in r["results"][0]["granted"]          # the ethics credential is back too
    web._state.pop("lane", None)


def test_the_researchers_agent_runs_each_week_on_its_own_and_ap4m_forwards_payouts(c, rail):
    paid, _ = rail
    cid, code, researcher = post(c, {**AP4M_TERMS, "weeks": [1, 2], "round_every_s": 60})
    d = Device("p")
    wallet = "0x" + "ab" * 20
    s = c.post(f"/api/contracts/{cid}/join/start", json={"invite_code": code, "public_key": d.public_hex,
                                                         "automation": "auto_all", "payout_address": wallet}).json()
    assert s["consent"]["payment"]["payout"] == wallet           # where the money goes is in what they sign
    d.sub = s["pid"]
    c.post(f"/api/contracts/{cid}/join/complete", json={"pid": d.sub, "signature": d.sign_consent(s["consent_hash"]),
                                                        "generate_test_weeks": [1, 2]})
    lane = web.lane()
    t0 = lane.public(cid)["terms"]["posted_at"]
    assert lane.tick(now=t0 + 10) == []                          # not due yet
    assert [r["week"] for r in lane.tick(now=t0 + 61)] == [1]
    last = lane.store.one("SELECT started_at FROM contract_rounds WHERE contract_id=? ORDER BY id DESC", cid)["started_at"]
    assert lane.tick(now=last + 30) == []                        # a week runs once
    assert [r["week"] for r in lane.tick(now=last + 61)] == [2]
    lane.tick(now=last + 200)
    assert c.get(f"/api/contracts/{cid}").json()["status"] == "closed"
    assert len(paid) == 2
    for p in paid.values():
        assert p["memo"]["member"] == d.sub
    # the fake rail does not forward; a real forward shows the member's wallet as payee
    oid = next(iter(paid.values()))["memo"]["order"]
    view = lane._order_view(oid)["payment"]
    assert view["status"] == "paid" and "merchant" in view["payee"]


def test_receipts_the_rail_settles_later_are_filled_in(c, rail):
    paid, _ = rail
    cid, code, researcher = post(c, AP4M_TERMS)
    a, ha = join(c, cid, code, "auto_all", "a")
    c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=token(c, researcher))
    lane = web.lane()
    with lane.store.tx() as tx:                      # the rail settles in the background: no receipt yet
        tx.execute("UPDATE contract_payments SET result=json_remove(result, '$.receipt_url')")
    assert c.get(f"/api/p/{a.sub}/contracts", headers=ha).json()["history"][0]["payment"]["receipt_url"] is None
    assert lane.backfill_receipts() == 1
    assert lane.backfill_receipts() == 0
    got = c.get(f"/api/p/{a.sub}/contracts", headers=ha).json()["history"][0]["payment"]
    assert got["receipt_url"].startswith("https://hackathon.ap4m.build/r/rc-") and got["status"] == "paid"


def test_unpaid_weeks_are_paid_after_the_contract_closes(c, rail):
    paid, state = rail
    cid, code, researcher = post(c, AP4M_TERMS)
    join(c, cid, code, "auto_all", "a")
    rh = token(c, researcher)
    state["down"] = True
    c.post(f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=rh)
    c.post(f"/api/contracts/{cid}/close", headers=rh)
    state["down"] = False
    lane = web.lane()
    lane.tick(now=lane._retry_at if hasattr(lane, "_retry_at") else 0)
    assert len(paid) == 1                             # the scheduler pays it after the close
    r = c.post(f"/api/contracts/{cid}/payments/retry", headers=rh).json()
    assert r["paid"] == 0 and r["payments"]["unpaid_count"] == 0 and len(paid) == 1
