"""Data contracts: column profiles, negotiation, provenance, per-contribution fitness and holdback,
delivery reliability forecast. Synthetic data, mock ledger."""
import json
import random

import pytest

from agentrail import payout, scenario, study
from agentrail.contract import fitness, forecast, market, measure, onledger, provenance
from agentrail.contract.profile import ColumnMeta, profile
from agentrail.contract.round import Round, as_asked, requirements
from agentrail.contract.terms import ColumnReq, Requirements, negotiate

BUYER = "org_sleeplab"


def _rows(comp_by_window, slots=7, col="x", seed=1):
    rng = random.Random(seed)
    rows = []
    for w, c in enumerate(comp_by_window, start=1):
        for i in range(slots):
            rows.append({"slot": (w - 1) * slots + i + 1, col: rng.uniform(10, 20) if i < round(c * slots) else None})
    return rows


@pytest.mark.parametrize("series,expected", [([1, 1, 1, 1, 1, 1], "holding"),
                                              ([1, .86, .71, .57, .43, .29], "declining"),
                                              ([1, .57, .29, .43, .71, 1], "recovering")])
def test_profile_reads_how_a_column_behaves_over_time(series, expected):
    meta = ColumnMeta("x", "src", "u", None, 0, 100)
    p = profile([meta], _rows(series), lambda r: (r["slot"] - 1) // 7 + 1)["columns"]["x"]
    assert p["behaviour"]["completeness"] == expected
    fc = p["forecast"]["completeness"]
    assert all(f["lo"] <= f["mean"] <= f["hi"] for f in fc)
    if expected == "declining":
        assert fc[0]["mean"] < series[-1]


def test_profile_shares_statistics_only_and_works_on_robot_columns():
    rows = [{"slot": i + 1, "lidar_points": 30000 + i} for i in range(28)]
    out = profile([ColumnMeta("lidar_points", "robot_fleet", "points", None, 1000, 100000)], rows,
                  lambda r: (r["slot"] - 1) // 7 + 1)
    p = out["columns"]["lidar_points"]
    assert out["rows_shared"] == 0 and p["completeness"] == 1.0 and p["distribution"]["n"] == 28
    flat = json.dumps(out)
    assert "30005" not in flat                     # individual values do not leave, only aggregates


def test_agents_agree_on_a_substitute_and_a_shorter_period_instead_of_failing():
    p = market.scripted_decliner()
    reg, iss = measure.world()
    rnd = Round(requirements(), [p], reg, iss, None, target=2)
    prof = rnd.profiles[p.id]
    assert prof["columns"]["resting_hr"]["behaviour"]["completeness"] == "declining"
    holder = fitness.holder_for(p.id, BUYER).pub
    k, log = negotiate(requirements(), p.id, prof, p.price_drops, holder=holder)
    kinds = [m["kind"] for m in log]
    assert k.status == "agreed" and "accept_substitute" in kinds and "shorter_period" in kinds
    assert {t["column"] for t in k.terms} == {"sleep_minutes", "resting_hr_b"}
    assert k.windows == [5, 6]
    # negotiated: each window passes; as asked: the chest band's later windows fail
    for w in k.windows:
        pl = fitness.deliver(p, k, w, iss, "c")
        assert not fitness.precheck(pl["manifest"], k, reg) and not fitness.check_values(pl, k, prof, {}, p.id)
    fixed = as_asked(requirements(), p.id, p.price_drops, prof, holder)
    codes = [{s["code"] for s in fitness.check_values(fitness.deliver(p, fixed, w, iss, "c"), fixed, prof, {}, p.id)}
             for w in fixed.windows]
    assert sum(c == {"incomplete"} for c in codes) >= 2


def test_a_column_outside_consent_or_a_sensitive_column_goes_to_the_owner():
    p = market.scripted_decliner()
    reg, iss = measure.world()
    prof = Round(requirements(), [p], reg, iss).profiles[p.id]
    k, _ = negotiate(requirements(), p.id, prof, p.price_drops, owner_allows={"sleep_minutes"})
    assert k.status == "needs_owner" and "consent" in k.reason
    req = requirements()
    req.columns.append(ColumnReq("diagnosis_codes", "code", sensitive=True))
    k, _ = negotiate(req, p.id, prof, p.price_drops)
    assert k.status == "needs_owner" and "sensitive" in k.reason


def test_price_is_a_fixed_quote_per_tier_and_never_imputed():
    p = market.scripted_decliner()
    reg, iss = measure.world()
    prof = Round(requirements(), [p], reg, iss).profiles[p.id]
    k, log = negotiate(requirements(tier="A", lowest="B"), p.id, prof, p.price_drops)
    from agentrail.contract.terms import TIERS
    assert k.price_drops_per_window == int(p.price_drops * TIERS[k.tier]["price_share"])
    assert not any("imput" in json.dumps(m) for m in log)


@pytest.mark.parametrize("fault,stage,code", [("wrong_source", "pre", "wrong_source"),
                                              ("wrong_period", "pre", "wrong_period"),
                                              ("different_person", "pre", "different_person"),
                                              ("wrong_unit", "post", "wrong_unit"),
                                              ("drift", "post", "drift"),
                                              ("duplicate", "post", "duplicate")])
def test_each_bad_record_is_caught_at_the_right_stage(fault, stage, code):
    reg, iss = measure.world()
    good = market.Provider("good", 60_000, 1.0, {"sleep_minutes": market.ColSim("wearable_a", 1.0),
                                                 "resting_hr": market.ColSim("chest_band_a", 1.0, native_unit="bpm")})
    bad = market.Provider("bad", 60_000, 1.0, {"sleep_minutes": market.ColSim("wearable_a", 1.0),
                                               "resting_hr": market.ColSim("chest_band_a", 1.0, native_unit="bpm")},
                          faults={6: fault})
    rnd = Round(requirements(), [good, bad], reg, iss)
    seen = {}
    kg, _ = negotiate(requirements(), "good", rnd.profiles["good"], 60_000, holder=fitness.holder_for("good", BUYER).pub)
    kb, _ = negotiate(requirements(), "bad", rnd.profiles["bad"], 60_000, holder=fitness.holder_for("bad", BUYER).pub)
    fitness.check_values(fitness.deliver(good, kg, 6, iss, "c"), kg, rnd.profiles["good"], seen, "good")
    ok = fitness.deliver(bad, kb, 5, iss, "c")                    # before the fault: passes
    assert not fitness.precheck(ok["manifest"], kb, reg)
    assert not fitness.check_values(ok, kb, rnd.profiles["bad"], seen, "bad")
    pl = fitness.deliver(bad, kb, 6, iss, "c", twins=good)
    pre = {s["code"] for s in fitness.precheck(pl["manifest"], kb, reg)}
    if stage == "pre":
        assert code in pre
    else:
        assert not pre
        assert code in {s["code"] for s in fitness.check_values(pl, kb, rnd.profiles["bad"], seen, "bad")}


def test_values_changed_after_the_source_signed_them_are_caught():
    reg, iss = measure.world()
    p = market.Provider("p", 60_000, 1.0, {"sleep_minutes": market.ColSim("wearable_a", 1.0),
                                           "resting_hr": market.ColSim("chest_band_a", 1.0, native_unit="bpm")})
    rnd = Round(requirements(), [p], reg, iss)
    k, _ = negotiate(requirements(), "p", rnd.profiles["p"], 60_000, holder=fitness.holder_for("p", BUYER).pub)
    pl = fitness.deliver(p, k, 5, iss, "c")
    pl["native"]["sleep_minutes"][0] = 999
    assert "tampered" in {s["code"] for s in fitness.check_values(pl, k, rnd.profiles["p"], {}, "p")}


def test_a_source_whose_credential_is_deleted_no_longer_counts():
    reg, iss = measure.world()
    p = market.Provider("p", 60_000, 1.0, {"sleep_minutes": market.ColSim("wearable_a", 1.0),
                                           "resting_hr": market.ColSim("chest_band_a", 1.0, native_unit="bpm")})
    rnd = Round(requirements(), [p], reg, iss)
    k, _ = negotiate(requirements(), "p", rnd.profiles["p"], 60_000, holder=fitness.holder_for("p", BUYER).pub)
    pl = fitness.deliver(p, k, 5, iss, "c")
    assert not fitness.precheck(pl["manifest"], k, reg)
    reg.ledger.delete_credential(reg.addr, reg.accounts["wearable_a"], provenance.DATA_SOURCE)
    assert any(s.get("detail") == "source_not_credentialed" for s in fitness.precheck(pl["manifest"], k, reg))


def test_forecast_uses_only_delivery_behaviour():
    for banned in ("declined", "withdrew", "age", "heart_rate", "diagnosis"):
        with pytest.raises(ValueError):
            forecast.features(**{banned: 1})
    assert set(forecast.ALLOWED).isdisjoint(forecast.BANNED)


def test_forecast_is_calibrated_better_than_the_base_rate_on_synthetic_histories():
    m, info = measure.train()
    assert info["brier"] < info["brier_base_rate"]
    assert all(abs(r["predicted"] - r["observed"]) < 0.35 for r in info["reliability"] if r["n"] >= 20)


@pytest.mark.parametrize("method", ["platt", "isotonic"])
def test_calibration_on_held_out_data_lowers_brier_and_calibration_error(method):
    _, info = measure.train(calibration=method)
    assert info["brier"] <= info["brier_before"] and info["ece"] < info["ece_before"]
    assert info["train"] > info["calibration_set"] and info["calibration_set"] == info["test"]


def test_isotonic_map_is_monotone():
    iso = forecast.Isotonic().fit([.1, .2, .3, .4, .5, .6, .7, .8], [0, 1, 0, 0, 1, 1, 0, 1])
    xs = [i / 20 for i in range(21)]
    assert all(iso(a) <= iso(b) for a, b in zip(xs, xs[1:]))


def test_contract_checks_and_the_forecast_cut_unfit_purchases_on_a_stream_with_bad_records():
    m, _ = measure.train()
    out = measure.compare(m, seeds=(21, 22, 23))["runs"]
    assert out["checks"]["xrp_paid_for_unfit"] < out["manual"]["xrp_paid_for_unfit"]
    assert out["checks"]["usable"] > out["manual"]["usable"]
    assert out["forecast"]["unfit_rate"] <= out["checks"]["unfit_rate"]
    assert out["forecast"]["usable"] >= out["checks"]["usable"]


def test_projection_has_a_band_and_names_the_windows_at_risk():
    m, _ = measure.train()
    reg, iss = measure.world()
    r = Round(requirements(), market.make_market(40, seed=7), reg, iss, m, target=12)
    r.run()
    for pr in r.projections:
        assert pr["band_90"][0] <= pr["expected_usable"] <= pr["band_90"][1]
        assert pr["power"]["lo"] <= pr["power"]["mean"] <= pr["power"]["hi"]
        assert all("at risk of missing window" in x for x in pr["risks"])
    assert r.projections[-1]["usable"] == sum(o["verdict"] == "pass" for o in r.outcomes)


@pytest.fixture
def lw():
    w = scenario.build_world("mock", ":memory:")
    study.set_goal(w, "back to 80% power")
    assert study.approve(w, ["owner", "compliance"])["ok"]
    return w


def test_on_the_ledger_the_contract_hash_rides_in_the_escrow_memo_and_the_bundle(lw):
    m, _ = measure.train()
    s = onledger.run(lw, model=m)
    assert s["contributions"] > 0
    paid = [o for o in lw.contract_round.outcomes if o["paid_drops"]]
    o = paid[0]
    create = lw.ledger.txs[o["txs"]["escrow_create"]]
    memo = " ".join(json.dumps(x) for x in create.get("Memos", [])) + json.dumps(create)
    assert o["contract"][:16] in memo
    oid = lw.store.one("SELECT order_id FROM payments WHERE tx_hash=?", o["txs"]["escrow_create"])["order_id"]
    payload = lw.engine.open_payload(BUYER, oid)
    k = lw.contract_round.contracts[o["provider"]]
    assert payload["manifest"]["contract"] == k.hash == o["contract"]
    assert payload["contract"]["holder"] == k.holder


def test_held_part_per_contribution_is_released_on_pass_and_an_unfit_one_is_withheld_without_sanction(lw):
    m, _ = measure.train()
    onledger.run(lw, model=m)
    hb = lw.store.q("SELECT * FROM holdbacks WHERE kind='contribution'")
    outcomes = {payout_ref: o for o in lw.contract_round.outcomes if o["stage"] == "after_reveal"
                for payout_ref in [o["txs"].get("holdback_create")]}
    assert hb and all(h["create_tx"] in outcomes for h in hb)
    for h in hb:
        o = outcomes[h["create_tx"]]
        if o["verdict"] == "pass":
            assert h["status"] == "released" and h["finish_tx"]
        else:
            assert h["status"] in ("withheld", "returned")
            assert payout.decision_inputs(lw.store, BUYER, h["person"])["excluded"] is False
            assert not lw.store.q("SELECT * FROM repayment_claims WHERE person=?", h["person"])


def test_contract_api_projection(lw):
    from fastapi.testclient import TestClient
    from agentrail import web
    c = TestClient(web.app)
    tok = lambda sub: {"Authorization": "Bearer " + c.post(f"/api/dev/login/{sub}").json()["access_token"]}
    c.post("/api/reset?ledger=mock", headers=tok("operator"))
    R = tok(f"researcher@{BUYER}")
    assert c.get("/api/contract/projection", headers=R).json()["projections"] == []
    c.post("/api/study/goal", json={"goal": "x"}, headers=R)
    c.post("/api/study/approve", json={"signers": ["owner", "compliance"]}, headers=tok("operator"))
    r = c.post("/api/contract/round", headers=R).json()
    v = c.get("/api/contract/projection", headers=R).json()
    assert v["status"] == "done" and v["latest"]["usable"] == r["usable"]
    assert v["contracts"] and all(x["transcript"] for x in v["contracts"])
    assert c.get("/api/contract/projection", headers=tok("P-017")).status_code == 403
