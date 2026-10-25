"""Safety properties of the trade engine, on MockLedger (real sealing, real SQLite)."""
import json
import threading

import pytest

from agentrail.engine import BudgetExceeded, Engine, NeedsHumanApproval, OrderConflict, OrderRequest
from agentrail.policy import ALLOW, Decision
from agentrail.scenario import STANDARD_ITEMS, XRP, build_world, scene_a

LAB = "org_sleeplab"


@pytest.fixture
def w(tmp_path):
    w = build_world("mock", str(tmp_path / "t.db"))
    for pid in ("P017", "P023", "P031"):
        w.people[pid].set_consent(LAB, "sleep_research", STANDARD_ITEMS, automation="auto_all")
    return w


def request(w, pid="P017", week=1, items=None, price=None):
    pa = w.people[pid]
    items = items or STANDARD_ITEMS
    d = pa.handle_request(LAB, "sleep_research", items, week, 1 * XRP)
    return OrderRequest(LAB, pid, pid, "personal.weekly", f"{pid}|week{week}", "sleep_research",
                        d.granted, price or len(d.granted) * XRP, pa.vault.extract(d.granted, week), d)


def mandate(w, buyer=LAB):
    return dict(w.store.one("SELECT * FROM mandates WHERE buyer_id=?", buyer))


def paid_count(w):
    return w.ledger.payment_count()


# 1
def test_same_order_twice_creates_one_order_and_one_payment(w):
    req = request(w)
    a = w.engine.place_order(req)
    w.engine.process(a)
    b = w.engine.place_order(req)
    w.engine.process(b)
    assert a == b
    assert w.store.one("SELECT COUNT(*) n FROM orders")["n"] == 1
    assert paid_count(w) == 1
    assert mandate(w)["spent_drops"] == 3 * XRP


# 2
def test_same_key_different_content_is_a_conflict(w):
    w.engine.place_order(request(w))
    with pytest.raises(OrderConflict):
        w.engine.place_order(request(w, price=5 * XRP))
    assert w.store.one("SELECT COUNT(*) n FROM orders")["n"] == 1


# 3
def test_concurrent_orders_reserve_budget_without_loss_or_overspend(w):
    from agentrail.policy import BuyerMandate
    w.engine.set_mandate(BuyerMandate(LAB, 7 * XRP, 6 * XRP, ["sleep_research"]))
    reqs = [request(w, pid) for pid in ("P017", "P023", "P031")]  # 3 XRP each, budget 7
    results, errors = [], []

    def go(r):
        try:
            results.append(w.engine.place_order(r))
        except BudgetExceeded as e:
            errors.append(e)

    ts = [threading.Thread(target=go, args=(r,)) for r in reqs]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(results) == 2 and len(errors) == 1
    m = mandate(w)
    assert m["reserved_drops"] == 6 * XRP
    for oid in results:
        w.engine.process(oid)
    m = mandate(w)
    assert m["spent_drops"] == 6 * XRP and m["reserved_drops"] == 0


# 4
def test_restart_after_payment_recovers_pending_delivery(w):
    oid = w.engine.place_order(request(w))
    w.engine.inbox.lose_next_ack = True
    assert w.engine.process(oid) == "paid"            # paid, delivery not acknowledged
    e2 = Engine(w.store, w.ledger, w.engine.inbox)     # "restart"
    e2.policies, e2.box_keys = w.engine.policies, w.engine.box_keys
    assert e2.recover() == [oid]
    assert w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "delivered"
    assert paid_count(w) == 1


# 5
def test_lost_delivery_resends_same_bundle_without_extra_payment(w):
    oid = w.engine.place_order(request(w))
    w.engine.inbox.lose_next_ack = True
    w.engine.process(oid)
    w.engine.process(oid)
    rows = w.store.q("SELECT bundle_hash, acked FROM deliveries WHERE order_id=?", oid)
    assert len(rows) == 2 and rows[0]["bundle_hash"] == rows[1]["bundle_hash"]
    assert [r["acked"] for r in rows] == [0, 1]
    assert paid_count(w) == 1
    data = w.engine.open_bundle(LAB, oid)
    assert len(data) == 7 and set(STANDARD_ITEMS) <= set(data[0])


# 6
def test_pause_blocks_new_orders_but_keeps_history(w):
    oid = w.engine.place_order(request(w, week=1))
    w.engine.process(oid)
    w.people["P017"].pause(LAB)
    d = w.people["P017"].handle_request(LAB, "sleep_research", STANDARD_ITEMS, 2, XRP)
    assert not d.ok and "paused" in d.reason
    assert w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "delivered"


def test_pause_between_order_and_payment_blocks_payment_and_releases_budget(w):
    oid = w.engine.place_order(request(w))
    w.people["P017"].pause(LAB)
    assert w.engine.process(oid) == "blocked"
    assert paid_count(w) == 0
    assert mandate(w)["reserved_drops"] == 0


# 7
def test_revoke_withholds_undelivered_bundle_keeps_payment_and_records_exception(w):
    oid = w.engine.place_order(request(w))
    w.engine.inbox.lose_next_ack = True
    w.engine.process(oid)                              # paid, delivery not done
    w.engine.inbox.received.clear()
    w.people["P017"].revoke(LAB)
    w.engine.process(oid)
    assert w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "withheld"
    assert w.store.one("SELECT status FROM payments WHERE order_id=?", oid)["status"] == "validated"
    ex = w.store.one("SELECT * FROM exceptions WHERE order_id=?", oid)
    assert ex["kind"] == "delivery_withheld" and ex["cost_bearer"] == LAB
    assert oid not in w.engine.inbox.received


# 8
def test_over_limit_or_over_budget_stops_before_any_payment(w):
    with pytest.raises(NeedsHumanApproval):
        w.engine.place_order(request(w, price=7 * XRP))   # per-order limit 6
    res = scene_a(w, budget_xrp=30)                       # full coverage needs 35
    assert res["status"] == "not_purchased" and "+5 XRP" in res["reason"]
    assert paid_count(w) == 0


# 9
def test_lost_payment_response_recovered_by_tx_hash(w):
    oid = w.engine.place_order(request(w))
    w.ledger.lose_next_response = True
    assert w.engine.process(oid) == "delivered"
    assert w.ledger.submit_calls == 1 and paid_count(w) == 1


def test_dropped_submit_resubmits_same_signed_blob(w):
    oid = w.engine.place_order(request(w))
    w.ledger.drop_next_submit = True
    w.engine.process(oid)
    assert paid_count(w) == 1
    p = w.store.one("SELECT * FROM payments WHERE order_id=?", oid)
    assert p["status"] == "validated" and w.ledger.lookup(p["tx_hash"]).invoice_id == p["invoice_id"]


# consent scope, sensitivity, automation, compliance
def test_items_outside_consent_wait_for_person_even_at_higher_price(w):
    pa = w.people["P017"]
    d = pa.handle_request(LAB, "sleep_research", STANDARD_ITEMS + ["fatigue.survey", "blood_pressure.daily"],
                          2, XRP, extra_price_drops=5 * XRP)
    assert sorted(d.granted) == sorted(STANDARD_ITEMS)
    assert sorted(d.pending) == ["blood_pressure.daily", "fatigue.survey"]
    req = pa.open_requests()[0]
    pa.approve(req["id"], ["fatigue.survey"])
    d = pa.handle_request(LAB, "sleep_research", STANDARD_ITEMS + ["fatigue.survey", "blood_pressure.daily"], 3, XRP)
    assert "fatigue.survey" in d.granted and "blood_pressure.daily" not in d.granted


def test_auto_standard_still_confirms_sensitive_items_each_round(w):
    pa = w.people["P023"]
    pa.set_consent(LAB, "sleep_research", STANDARD_ITEMS + ["blood_pressure.daily"], automation="auto_standard")
    d = pa.handle_request(LAB, "sleep_research", STANDARD_ITEMS + ["blood_pressure.daily"], 1, XRP)
    assert d.round_confirm == ["blood_pressure.daily"] and "blood_pressure.daily" not in d.granted
    r = [r for r in pa.open_requests() if r["kind"] == "round"][0]
    pa.approve(r["id"], ["blood_pressure.daily"])
    assert "blood_pressure.daily" in pa.handle_request(LAB, "sleep_research",
                                                       ["blood_pressure.daily"], 1, XRP).granted
    assert "blood_pressure.daily" not in pa.handle_request(LAB, "sleep_research",
                                                           ["blood_pressure.daily"], 2, XRP).granted


def test_sensitive_items_filtered_for_buyer_without_ethics_approval(w):
    pa = w.people["P017"]
    pa.set_consent("org_adtech", "sleep_research", STANDARD_ITEMS + ["blood_pressure.daily"], automation="auto_all")
    d = pa.policy.evaluate("org_adtech", "sleep_research", STANDARD_ITEMS + ["blood_pressure.daily"], 4 * XRP, week=1)
    assert d.refused == ["blood_pressure.daily"] and "blood_pressure.daily" not in d.granted


def test_prohibited_purpose_refused_even_with_consent(w):
    pa = w.people["P017"]
    pa.set_consent("org_adtech", "marketing_profiling", STANDARD_ITEMS, automation="auto_all")
    d = pa.policy.evaluate("org_adtech", "marketing_profiling", STANDARD_ITEMS, 3 * XRP, week=1)
    assert not d.ok and "prohibited" in d.reason


def test_unreadable_consent_store_holds_the_trade(w):
    w.people["P017"].policy.fail_reads = True
    d = w.people["P017"].handle_request(LAB, "sleep_research", STANDARD_ITEMS, 1, XRP)
    assert d.status == "hold" and not d.ok


def test_payment_memo_carries_consent_version_hash(w):
    oid = w.engine.place_order(request(w))
    w.engine.process(oid)
    p = w.store.one("SELECT * FROM payments WHERE order_id=?", oid)
    memo = json.loads(p["tx_blob"])["Memo"]
    doc_hash = w.store.one("SELECT doc_hash FROM consents WHERE person_id='P017' AND buyer_id=?", LAB)["doc_hash"]
    assert doc_hash[:16] in memo


def test_scene_a_selects_b_and_c_within_budget(w):
    res = scene_a(w)
    assert res["status"] == "purchased" and sorted(res["selected"]) == ["B1", "C1"]
    excluded = {c["product"]: c["excluded"] for c in res["candidates"]}
    assert "lidar" in excluded["A1"] and "licence" in excluded["C2"] and "missing rate" in excluded["D1"]
    assert res["spent_xrp"] == 35 and res["remaining_xrp"] == 15
    b1 = [c for c in res["candidates"] if c["product"] == "B1"][0]
    assert b1["refused_fields"] == ["raw_video"]


# XRPL-native controls
def test_sensitive_items_follow_the_ledger_credential(w):
    from agentrail.scenario import ETHICS_CREDENTIAL
    pa = w.people["P017"]
    pa.set_consent("org_adtech", "sleep_research", STANDARD_ITEMS + ["blood_pressure.daily"], automation="auto_all")
    d = pa.policy.evaluate("org_adtech", "sleep_research", ["blood_pressure.daily"], XRP, week=1)
    assert not d.ok
    w.ledger.issue_credential(w.engine.party("org_ethics")["address"], w.engine.party("org_adtech")["address"],
                              ETHICS_CREDENTIAL)
    d = pa.policy.evaluate("org_adtech", "sleep_research", ["blood_pressure.daily"], XRP, week=1)
    assert d.granted == ["blood_pressure.daily"]


def test_agent_cannot_raise_its_own_budget_but_cosigned_top_up_can(w):
    from agentrail.scenario import scene_a_guarded
    res = scene_a_guarded(w)
    assert res["status"] == "purchased" and res["spent_xrp"] == 35
    kinds = [r["kind"] for r in w.store.q("SELECT kind FROM events WHERE scene='A'")]
    assert "refused" in kinds and "top_up" in kinds
    assert mandate(w, "org_robodev")["total_drops"] == 35 * XRP
    assert w.ledger.account_settings(w.treasury) == {"network": "mock", "multisig": True, "master_disabled": True}


def test_cohort_round_pays_fifty_people_once_each_in_parallel(w):
    from agentrail.scenario import scene_d
    res = scene_d(w, n=50, workers=10)
    assert res == {"orders": 50, "delivered": 50, "seconds": res["seconds"]}
    assert w.store.one("SELECT COUNT(DISTINCT payee_id) n FROM orders WHERE buyer_id='org_cohort'")["n"] == 50
    assert mandate(w, "org_cohort")["spent_drops"] == 50 * XRP
