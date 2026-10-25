"""The catalog, tiered consent and the approval bottleneck."""
from agentrail.catalog import columns as C
from agentrail.catalog import simulate as S
from agentrail.catalog.scope import Grant, Owner, Request, TouchID, verify_assertion


def req(cols, rid="r1", inst="org_a", cls="academic", country="KR", purpose="sleep_research", irb=True, duo=None):
    return Request(rid, inst, cls, country, "S1", purpose, cols, [1], why="test",
                   duo=duo if duo is not None else C.duo_for(cols) + (["DUO:0000016"] if any(c.startswith("genome") for c in cols) else []),
                   irb=irb)


def test_catalog_has_every_tier_with_rules():
    assert len(C.CATALOG) >= 40
    for t in C.TIERS:
        assert len(C.by_tier(t)) >= 6
    g = C.CATALOG["genome.vcf"]
    assert g.tier == "T3" and "DUO:0000016" in g.duo and g.retention_days == 90 and g.source == "engine"
    assert all(c.card()["deletion"] for c in C.CATALOG.values())


def test_synthetic_values_every_column():
    for cid, c in C.CATALOG.items():
        v = C.synth(cid, "U-001", 3)
        assert v is not None
        if c.kind == "numeric":
            assert c.lo <= v <= c.hi
    assert C.synth("sleep.daily", "U-001", 3) == C.synth("sleep.daily", "U-001", 3)
    img = C.synth("imaging.ct", "U-001")
    assert img["Modality"] == "CT" and len(img["pixels"]) == 16


def test_preconsented_scope_runs_at_once_and_is_logged():
    o = Owner("U-1", grants=[Grant("T1")])
    e = o.request(req(["sleep.daily", "mood.score"]))
    assert e["decision"] == "auto" and o.log[-1]["id"] == e["id"]


def test_above_grant_or_new_scope_goes_to_gate():
    o = Owner("U-1", grants=[Grant("T1")])
    assert o.request(req(["lab.hba1c"]))["decision"] == "gate"                     # higher tier
    assert o.request(req(["sleep.daily"], "r2", purpose="product_development"))["decision"] == "gate"
    assert o.request(req(["sleep.daily"], "r3", inst="org_us", country="US"))["decision"] == "gate"


def test_t3_always_asks_even_with_a_wide_grant():
    o = Owner("U-1", grants=[Grant("T3", frozenset({"genomics"}), frozenset({"academic"}), abroad=True)])
    assert o.request(req(["genome.pgx"], purpose="genomics"))["decision"] == "gate"


def test_restrictions_travel_with_the_data():
    o = Owner("U-1", grants=[Grant("T2")])
    assert o.request(req(["lab.ldl"], irb=False))["decision"] == "refused"
    e = o.request(req(["genome.vcf"], duo=C.duo_for(["genome.vcf"])[:-1]))
    assert e["decision"] == "refused" and "data use codes" in e["why"]


def test_package_bundles_per_institution_and_needs_fresh_touch():
    now = [1000.0]
    o = Owner("U-1", grants=[Grant("T1")], clock=lambda: now[0])
    o.request(req(["sleep.daily"]))                                   # auto: shared before
    o.request(req(["lab.ldl"], "r2"))
    o.request(req(["genome.pgx"], "r3", purpose="sleep_research"))
    pkg = o.package("org_a")
    assert len(pkg["studies"]) == 2 and not pkg["first_time"] and pkg["already_shared"] == ["sleep.daily"]
    assert pkg["risks"]["reidentification"]["T3"] == "identifying by itself" and pkg["warnings"]
    stale = o.device.assert_(pkg["hash"], now=800)
    assert o.approve("org_a", stale)["reason"] == "assertion is not fresh"
    other = TouchID().assert_(pkg["hash"], now=1000)
    assert o.approve("org_a", other)["reason"] == "bad assertion signature"
    assert o.approve("org_a", o.device.assert_(pkg["hash"], now=1000), remember=True)["ok"]
    # the non-T3 part widened the grant; T3 did not
    assert o.request(req(["lab.ldl"], "r4"))["decision"] == "auto"
    assert o.request(req(["genome.pgx"], "r5"))["decision"] == "gate"


def test_cross_border_package_flags_transfer():
    o = Owner("U-1", grants=[Grant("T1")])
    o.request(req(["sleep.daily"], inst="org_us", country="US"))
    p = o.package("org_us")
    assert p["first_time"] and p["risks"]["transfer_abroad"]


def test_revoke_stops_future_auto_approvals():
    o = Owner("U-1", grants=[Grant("T1")])
    e = o.request(req(["sleep.daily"]))
    assert o.revoke(e["id"])["ok"]
    assert o.request(req(["sleep.daily"], "r2"))["decision"] == "gate"


def test_decline_is_remembered():
    o = Owner("U-1", grants=[Grant("T0")])
    o.request(req(["lab.ldl"]))
    o.decline("org_a")
    assert o.request(req(["lab.ldl"], "r2"))["decision"] == "refused"


def test_bottleneck_and_outcome():
    r = S.run(n=20)
    assert r["manual"]["approvals"] > 20 * r["agent"]["touch_id"]
    assert r["agent"]["median_hours_to_paid"] < r["manual"]["median_hours_to_paid"]
    assert r["agent"]["within_48h"] >= r["manual"]["within_48h"]


def test_assertion_bound_to_package():
    d = TouchID()
    a = d.assert_("h1", now=10)
    assert verify_assertion(d.public, a, "h2", now=10) == "assertion is for another package"
