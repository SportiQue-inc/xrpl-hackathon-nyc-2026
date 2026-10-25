"""Two-part pay, integrity review and the limits on penalties (mock ledger, synthetic data)."""
import pytest

from agentrail import payout, scenario, study
from agentrail.cohort import HERO
from tests.llm_doubles import capable_needs

LAB = study.LAB


@pytest.fixture
def w():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    return w


def holdbacks(w, pid=None, kind="round"):
    return [h for h in payout.view(w, LAB, pid)["holdbacks"] if h["kind"] == kind]


def honest(w):
    fx = w.integrity_fixture["person"]
    return next(r for r in w.study.requests.values()
                if r["status"] == "contributed" and r["person"] not in (HERO, fx))


def test_round_pays_on_the_continuity_curve_and_releases_the_held_part_by_default(w):
    req = honest(w)
    paid = []
    for i, x in enumerate(req["orders"]):
        o = w.store.one("SELECT price_drops FROM orders WHERE id=?", x["order_id"])
        assert o["price_drops"] == len(x["items"]) * study.CELL_PRICE * min(90, 50 + 10 * i) // 100
        paid.append(o["price_drops"])
    hb = holdbacks(w, req["person"])[0]
    assert hb["status"] == "held" and hb["review"] == "pass" and hb["create"]["tx"]
    full = sum(len(x["items"]) * study.CELL_PRICE for x in req["orders"])
    assert hb["amount_xrp"] == pytest.approx((full - sum(paid)) / 1e6)
    before = w.ledger.balance_drops(w.engine.party(req["person"])["address"])
    r = payout.release_due(w)
    assert any(x["person"] == req["person"] for x in r["released"])
    assert w.ledger.balance_drops(w.engine.party(req["person"])["address"]) == before + int(hb["amount_xrp"] * 1e6)


def test_held_share_cannot_be_released_before_review_ends(w):
    req = honest(w)
    h = w.store.one("SELECT * FROM holdbacks WHERE person=? AND kind='round'", req["person"])
    assert payout._finish(w, h) is False          # FinishAfter not reached: the ledger refuses


def test_fraud_needs_a_named_reviewer_and_the_response_period(w):
    case = payout.view(w, LAB)["cases"][0]
    assert case["person"] == w.integrity_fixture["person"] and case["signals"][0]["code"] == "impossible_value"
    assert holdbacks(w, case["person"])[0]["status"] == "suspected"
    assert "named reviewer" in payout.decide(w, LAB, case["id"], "", True)["message"]
    assert "can still respond" in payout.decide(w, LAB, case["id"], "reviewer-1", True)["message"]
    w.ledger.clock = case["respond_by"]
    paid_before = w.ledger.balance_drops(w.engine.party(case["person"])["address"])
    r = payout.decide(w, LAB, case["id"], "reviewer-1", True)
    assert r["ok"] and r["repayment_claim_xrp"] > 0
    out = payout.release_due(w)
    assert any(x["person"] == case["person"] and x["kind"] == "round" for x in out["returned"])
    # paid money is never taken back on chain; only a claim is recorded
    assert w.ledger.balance_drops(w.engine.party(case["person"])["address"]) == paid_before
    assert payout.view(w, LAB)["repayment_claims"][0]["status"] == "recorded"
    assert payout.may_request(w, LAB, case["person"])[0] is False
    audit = w.store.one("SELECT * FROM sanctions_audit WHERE person=? AND action='exclude'", case["person"])
    assert audit["reviewer_id"] == "reviewer-1" and audit["notified_at"] and audit["reason_code"]


def test_undecided_case_is_paid_when_the_extension_runs_out(w):
    case = payout.view(w, LAB)["cases"][0]
    h = w.store.one("SELECT * FROM holdbacks WHERE person=? AND kind='round'", case["person"])
    w.ledger.clock = h["review_until"]
    r = payout.release_due(w)
    assert any(x["person"] == case["person"] for x in r["released"])


def test_confirming_after_a_default_payment_never_marks_the_paid_part_withheld(w):
    case = payout.view(w, LAB)["cases"][0]
    h = w.store.one("SELECT * FROM holdbacks WHERE person=? AND kind='round'", case["person"])
    w.ledger.clock = max(h["review_until"], case["respond_by"])
    assert any(x["person"] == case["person"] for x in payout.release_due(w)["released"])
    r = payout.decide(w, LAB, case["id"], "reviewer-1", True)
    assert r["ok"]
    after = w.store.one("SELECT * FROM holdbacks WHERE id=?", h["id"])
    assert after["status"] == "released" and after["cancel_tx"] is None
    paid = sum(o["price_drops"] for o in w.store.q(
        "SELECT price_drops FROM orders WHERE buyer_id=? AND seller_id=? AND status='delivered'", LAB, case["person"]))
    assert r["repayment_claim_xrp"] * 1e6 == pytest.approx(paid + h["amount_drops"])
    assert not any(x["person"] == case["person"] and x["kind"] == "round" for x in payout.release_due(w)["returned"])


def test_withdrawal_history_is_never_an_input(w):
    req = honest(w)
    pid = req["person"]
    before = payout.decision_inputs(w.store, LAB, pid)
    study.participant_pause(w, pid)
    study.participant_pause(w, pid, resume=True)
    study.participant_revoke(w, pid)
    assert payout.decision_inputs(w.store, LAB, pid) == before
    assert payout.may_request(w, LAB, pid) == (True, "")
    assert w.store.one("SELECT trust FROM standing WHERE person=?", pid)["trust"] == "normal"
    r = payout.release_due(w)
    assert any(x["person"] == pid for x in r["released"])     # held share still paid


def test_withdrawal_still_pays_reviewed_share_and_returns_the_bonus(w):
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    study.participant_approve(w, HERO, rid, ["fatigue.survey", "heart_rate.daily"])
    assert holdbacks(w, HERO, "bonus")[0]["status"] == "held"
    study.participant_revoke(w, HERO)
    assert any(h["review"].startswith("pass: data destroyed") for h in holdbacks(w, HERO))
    assert holdbacks(w, HERO, "bonus")[0]["status"] == "returning"
    r = payout.release_due(w)
    assert any(x["person"] == HERO and x["kind"] == "round" for x in r["released"])
    # the mock clock never jumps past an open case's payment on its own; move it for the bonus deadline
    w.ledger.clock = w.store.one("SELECT cancel_after FROM holdbacks WHERE person=? AND kind='bonus'", HERO)[0]
    r = payout.release_due(w)
    assert any(x["person"] == HERO and x["kind"] == "bonus" for x in r["returned"])


def test_completed_request_earns_the_bonus(w):
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    req = w.study.requests[rid]
    study.participant_approve(w, HERO, rid, sorted({i for its in req["weeks"].values() for i in its}))
    study.close_round(w)
    assert holdbacks(w, HERO, "bonus")[0]["status"] == "earned"
    r = payout.release_due(w)
    assert any(x["person"] == HERO and x["kind"] == "bonus" for x in r["released"])


def test_two_missed_accepted_rounds_pause_automatic_requests_only(w):
    req = honest(w)
    pid = req["person"]
    payout.round_missed(w, LAB, pid, req["id"])
    assert payout.auto_paused(w, LAB, pid) is False
    payout.round_missed(w, LAB, pid, req["id"])
    assert payout.auto_paused(w, LAB, pid) is True
    assert payout.may_request(w, LAB, pid) == (True, "")          # not excluded, not blocked
    assert w.store.one("SELECT trust FROM standing WHERE person=?", pid)["trust"] == "normal"
    payout.resume_requests(w, LAB, pid)
    assert payout.auto_paused(w, LAB, pid) is False


def test_trust_and_case_details_never_reach_the_ledger(w):
    case = payout.view(w, LAB)["cases"][0]
    w.ledger.clock = case["respond_by"]
    payout.decide(w, LAB, case["id"], "reviewer-1", True)
    payout.release_due(w)
    import json
    memos = " ".join(json.dumps({k: v for k, v in t.items() if k != "TransactionType"})
                     for t in w.ledger.txs.values()).lower()
    for word in ("trust", "fraud", "restricted", "impossible", "reviewer"):
        assert word not in memos
    assert "trust" not in payout.view(w, LAB, case["person"])


def test_round_escrow_refused_because_finish_after_passed_is_retried_with_fresh_times(w, monkeypatch):
    """With parallel settle a round EscrowCreate can queue past its FinishAfter; the ledger then answers
    tecNO_PERMISSION. One retry with the times moved forward creates it."""
    from types import SimpleNamespace
    real, calls = payout._send, []

    def send(w_, prep):
        calls.append(prep)
        if len(calls) == 1:
            w_.ledger.clock = w_.ledger.now() + 60           # the queue took a minute
            return SimpleNamespace(validated=True, success=False, result="tecNO_PERMISSION")
        return real(w_, prep)
    monkeypatch.setattr(payout, "_send", send)
    now = w.ledger.now()
    req = honest(w)
    hid = payout._create(w, "bonus", LAB, req["person"], 999, 1, 1000, now + 20, now + 620, now + 680, "held")
    assert hid and len(calls) == 2
    h = w.store.one("SELECT * FROM holdbacks WHERE id=?", hid)
    assert h["finish_after"] > w.ledger.now() and h["create_tx"] == calls[1].tx_hash
