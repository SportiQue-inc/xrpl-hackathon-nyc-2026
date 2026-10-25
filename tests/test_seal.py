"""Provenance stamped at intake and checked before payment, and the payout schedules."""
from agentrail import payout_schedule as ps
from agentrail.contract import fitness, market, measure
from agentrail.contract.round import Accounting, Round, requirements
from agentrail.contract.terms import negotiate

BUYER = requirements().buyer


def _setup(fault=None):
    reg, iss = measure.world()
    cols = {"sleep_minutes": market.ColSim("wearable_a", 1.0),
            "resting_hr": market.ColSim("chest_band_a", 1.0, native_unit="bpm")}
    p = market.Provider("p", 60_000, 1.0, cols, faults={6: fault} if fault else {})
    rnd = Round(requirements(), [p], reg, iss)
    k, _ = negotiate(requirements(), "p", rnd.profiles["p"], 60_000, holder=fitness.holder_for("p", BUYER).pub)
    return reg, iss, p, k, rnd


def test_sealed_contribution_passes_and_opens_with_the_escrow_key():
    reg, iss, p, k, _ = _setup()
    key = b"\x07" * 32
    pl = fitness.deliver(p, k, 5, iss, "c", key=key)
    assert not fitness.precheck(pl["manifest"], k, reg, pl)
    from agentrail.contract.provenance import open_sealed
    assert not open_sealed(pl["manifest"], pl, key)
    assert {s["code"] for s in open_sealed(pl["manifest"], pl, b"\x08" * 32)} == {"unopenable"}


def test_tampered_after_sealing_fails_before_payment():
    reg, iss, p, k, _ = _setup("tampered")
    key = b"\x07" * 32
    pl = fitness.deliver(p, k, 6, iss, "c", key=key)
    codes = {s["code"] for s in fitness.precheck(pl["manifest"], k, reg, pl)}
    assert "tampered" in codes


def test_a_stamp_from_a_source_without_credential_is_refused():
    reg, iss, p, k, _ = _setup("wrong_source")
    pl = fitness.deliver(p, k, 6, iss, "c", key=b"\x07" * 32)
    assert "wrong_source" in {s["code"] for s in fitness.precheck(pl["manifest"], k, reg, pl)}


def test_round_pays_a_tampered_week_nothing():
    reg, iss, p, k, rnd = _setup("tampered")
    rnd.contracts["p"] = k
    rnd.settle = Accounting()
    o5 = rnd.contribute("p", 5)
    o6 = rnd.contribute("p", 6)
    assert o5["verdict"] == "pass" and o5["paid_drops"] > 0
    assert o6["stage"] == "before_payment" and o6["paid_drops"] == 0 and o6["held_drops"] == 0


def test_continuity_curve_pays_more_the_longer_the_streak_and_resets_on_a_gap():
    w = ps.simulate(100_000, [True] * 5 + [False] + [True] * 3)
    assert [x["upfront_pct"] for x in w[:5]] == [50, 60, 70, 80, 90]
    assert w[4]["week_drops"] > w[0]["week_drops"]
    assert w[5]["paid_drops"] == 0 and w[6]["upfront_pct"] == 50 and w[6]["rate_multiplier"] == 1.0


def test_retrospective_is_one_shot_and_hybrid_has_two_parts():
    r = ps.retrospective(500_000)
    assert r["upfront_pct"] == 100 and r["held_drops"] == 0
    h = ps.hybrid(500_000, 50_000, [True, True])
    assert h["baseline"]["schedule"] == "retrospective" and h["follow_up"]["rate_multiplier"] == 1.1
