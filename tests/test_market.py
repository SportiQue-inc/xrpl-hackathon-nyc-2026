"""The open market (Act 1) and healthcare research (Act 2): one pipeline, different policies."""
import json

import pytest
from nacl.signing import VerifyKey

from agentrail import deid
from agentrail.market import acts, imaging, policies, quality
from agentrail.market.exchange import Exchange


@pytest.fixture(scope="module")
def a1():
    return acts.act1(rounds=2)


@pytest.fixture(scope="module")
def a2():
    return acts.act2()


def test_act1_agents_trade_among_themselves(a1):
    act = a1["activity"]
    assert act["by_status"].get("settled", 0) >= 50 and act["volume_xrp"] > 0
    sensor = [t for t in a1["exchange"].trades if t["status"] == "settled"
              and t["columns"][0].startswith(("robot.", "fleet.", "smarthome."))]
    assert sensor, "non-health data trades in the same market"
    for t in a1["exchange"].trades:
        if t["status"] == "settled":
            assert t["txs"]["escrow_create"] and t["txs"]["escrow_finish"] and t["txs"]["holdback"]


def test_act1_shows_sold_queued_and_blocked_with_reasons(a1):
    st = {t["status"] for t in a1["exchange"].trades}
    assert {"settled", "refused"} <= st and st & {"declined", "awaiting_owner"}
    assert all(t.get("why") for t in a1["exchange"].trades)


def test_unfit_delivery_withholds_the_holdback(a1):
    unfit = [t for t in a1["exchange"].trades if t["status"] == "settled_unfit"]
    assert unfit and all(t["withheld_drops"] > 0 and t["signals"] for t in unfit)


def test_reverse_direction_genetic_report(a1):
    ok = [r for r in a1["reports"] if r["status"] == "delivered"]
    assert len(ok) == 2
    for r in ok:
        assert r["variants_sent"] < r["variants_held"]                  # only the loci the report needs
        assert "not a diagnosis" in r["report_received"]["note"] and r["txs"]["escrow_finish"]
        d = r["deletion"]
        VerifyKey(bytes.fromhex(d["key"])).verify(d["body"].encode(), bytes.fromhex(d["sig"]))
    bad = [r for r in a1["reports"] if r["status"] == "refused"]
    assert bad and "wellness" in bad[0]["why"]


def test_act2_is_act1_plus_a_policy(a1, a2):
    assert type(a1["exchange"]) is type(a2["exchange"]) is Exchange
    pol1 = {type(a.policy).__name__ for a in a1["exchange"].accounts.values() if a.policy}
    pol2 = {type(a.policy).__name__ for a in a2["exchange"].accounts.values() if a.policy}
    assert pol1 == {"AutonomyPolicy"} and pol2 == {"SensitivityPolicy"}
    assert issubclass(policies.SensitivityPolicy, policies.AutonomyPolicy)


def test_same_mri_sold_to_grade_a_and_not_on_its_own_to_grade_c(a2):
    g = a2["buyer_grades"]
    assert g["org_neuroimg"]["grade"] == "A" and g["org_genomics"]["grade"] == "C"
    assert "a past deletion was never confirmed" in g["org_genomics"]["reasons"]
    mri = [t for t in a2["exchange"].trades if t["need"].endswith("-mri")]
    auto_a = [t for t in mri if t["buyer"] == "org_neuroimg" and t["why"].startswith("sold on its own")]
    auto_c = [t for t in mri if t["buyer"] == "org_genomics" and t["why"].startswith("sold on its own")]
    assert auto_a and not auto_c
    assert any("needs grade A+, buyer is C" in t["why"] for t in mri if t["buyer"] == "org_genomics")


def test_budget_needs_two_researchers(a2):
    for b in a2["budgets"].values():
        assert not b["one_signature"][0] and b["two_signatures"][0]


def test_manual_approver_answers_with_touch_id(a2):
    ex = a2["exchange"]
    i = next(i for i, p in enumerate(ex.pending) if p["seller"] == acts.MANUAL)
    p = ex.pending[i]
    owner = ex.accounts[p["seller"]].policy.owner
    inst = p["trade"]["buyer_attrs"]["institution"]
    pkg = owner.package(inst)
    assert ex.approve_pending(i, {"package": "x", "ts": 0, "sig": "00"})["ok"] is False
    r = ex.approve_pending(i, owner.device.assert_(pkg["hash"], owner.clock()) if pkg else None)
    assert r["status"] in ("settled", "settled_unfit")


def trade(cols, **b):
    return {"columns": cols, "purpose": b.pop("purpose", "x_research"), "buyer": "B", "price_drops": 10,
            "buyer_attrs": b, "pseudonymized": True, "output": b.pop("output", "raw") if "output" in b else "raw"}


GOOD = dict(institution_credential=True, irb=True, workspace="controlled", history=True, country="KR",
            institution="org_g")


def test_policy_rules():
    p = policies.AutonomyPolicy("L4")
    assert p.decide(trade(["sleep.daily"], **GOOD))[0] == "allow"
    assert p.decide(trade(["lab.ldl"], **{**GOOD, "irb": False}))[0] == "refuse"
    v, why = policies.AutonomyPolicy("L1").decide(trade(["imaging.mri"], **GOOD))
    assert v == "gate" and "pseudonymized imaging is not set to sell on its own" in why
    assert p.decide(trade(["imaging.mri"], **{**GOOD, "workspace": "copy"}))[0] == "gate"
    assert p.decide(trade(["sleep.daily"], purpose="insurance_pricing", **GOOD))[0] == "refuse"


def test_genomic_rules():
    signed = [{"institution": "org_g", "purpose": "x_research", "loci": ["CYP1A2"]}]
    p = policies.AutonomyPolicy("L4", signed_genomic=signed)
    raw = trade(["genome.vcf"], **GOOD)
    assert p.decide(raw)[0] == "gate"
    agg = {**raw, "output": "aggregate", "loci": ["CYP1A2"]}
    v, why = p.decide(agg)
    assert v == "allow" and "executing your signed consent" in why
    assert p.decide({**agg, "loci": ["BRCA1"]})[0] == "gate"
    assert policies.AutonomyPolicy("L4", signed_genomic=signed, home="MN").decide(agg)[0] == "refuse"


def test_quality_commitment():
    rows = [{"day": i, "x": i} for i in range(20)]
    c = quality.Committed(rows)
    for o in c.open([0, 7, 19]):
        assert quality.verify_proof(c.root, o["row"], o["salt"], o["i"], o["proof"])
    o = c.open([3])[0]
    assert not quality.verify_proof(c.root, {**o["row"], "x": 99}, o["salt"], 3, o["proof"])
    assert quality.delivery_matches({"root": c.root}, rows, c.salts)
    assert not quality.delivery_matches({"root": c.root}, rows[:-1] + [{"day": 19, "x": 0}], c.salts)
    s = quality.Seller("S")
    cert = s.certify("d", rows, {"x": {"lo": 0, "hi": 100}}, {"x": "dev"}, 0.8, c)
    assert quality.check_certificate(cert) is None
    assert quality.check_certificate({**cert, "grade": "A" if cert["grade"] != "A" else "B"})


def test_deid_and_imaging():
    out, led = deid.deidentify({"person_id": "p", "age": 52, "stable_key": "k",
                                "ts": "2026-09-01T10:00:00", "items": [{"code": "rare"}, {"code": "common"}]},
                               prevalence={"rare": 2, "common": 40})
    assert "person_id" not in out and out["age_group"] == "40-64" and out["ts"] == "2026-09-01"
    assert out["stable_key"].startswith("pseudo_") and out["items"] == [{"code": "common"}]
    from agentrail.catalog.columns import synth
    d = synth("imaging.mri", "P-1")
    a, b = imaging.deidentify(d, "P-1"), imaging.deidentify(synth("imaging.mri", "P-1", 3), "P-1")
    assert "PatientName" not in a and a["StudyInstanceUID"].startswith("2.25.")
    assert a["StudyInstanceUID"] == deid.remap_uid(d["StudyInstanceUID"])
    assert "deface: face region zeroed" in a["pseudonymization"]["steps"]
    assert imaging.deidentify({**d, "BurnedInAnnotation": "YES"}, "P-1") is None
    assert deid.date_shift_days("P-1") == deid.date_shift_days("P-1")
    assert b["StudyDate"] != synth("imaging.mri", "P-1", 3)["StudyDate"]


def test_manual_approver_keeps_generated_rows_with_uniqdata():
    from agentrail.market.acts import MANUAL
    from agentrail.uniqdata_live import feed_market

    class A:
        id, datasets = MANUAL, []
    assert feed_market([A()], {MANUAL: object()}, keep={MANUAL}) == {}
