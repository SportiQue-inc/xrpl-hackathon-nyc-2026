"""The person's agent: everyday data supply-first, sensitive data demand-first; de-identified; sealed push."""
from agentrail.market import products


def test_everyday_supply_first_sensitive_only_from_postings():
    r = products.scene("P-017")
    sup = [c for c in r["candidates"] if c["direction"] == "supply"]
    dem = [c for c in r["candidates"] if c["direction"] == "demand"]
    assert sup and all(c["tier"] in ("T0", "T1") for c in sup)
    assert all(c["tier"] in ("T2", "T3") for c in dem)
    matched = {x["posting"] for x in r["postings_searched"] if x["matched"]}
    assert dem and all(c["posting"] in matched for c in dem)
    assert any(c["collected"] for c in r["collected"])


def test_sold_as_sealed_push_without_the_person_id():
    r = products.scene("P-017")
    sold = [c["sale"] for c in r["candidates"] if c.get("sale", {}).get("sold")]
    assert sold and all(s["pushed"] and s["escrow_finish"] and not s["carries_person_id"] for s in sold)


def test_review_waits_for_a_tap_and_never_lists_raw_genomic_or_never_tiers():
    r = products.scene("P-017", tap=False)
    waiting = [c for c in r["candidates"] if not c["review"]["listed"]]
    assert waiting and all(c["review"]["how"] in ("tap", "passkey") and "sale" not in c for c in waiting)
    for x in r["postings_searched"]:
        assert not (x["matched"] and any(c.startswith("genome") for c in x["matched"]))


def test_collect_rules_by_tier():
    cols, log = products.collect("P-x", [], {"spo2.night": "w", "lab.glucose": "emr", "genome.vcf": "lab"})
    got = {x["column"]: x["collected"] for x in log}
    assert got == {"spo2.night": True, "lab.glucose": False, "genome.vcf": False}


def test_k_anonymity_generalizes_then_refuses():
    me = {"age_group": "<40", "sex": "F", "region": "A", "country": "KR"}
    cohort = [{**me, "region": "B"}] * 5 + [me]
    out, steps = products.k_anonymize(me, cohort)
    assert out == {"age_group": "<40", "sex": "F", "country": "KR"} and "region removed" in steps[0]
    assert products.k_anonymize(me, [me])[0] is None


def test_mongolia_sensitive_stays_and_small_class_not_released():
    r = products.scene("P-050")
    assert r["home"] == "MN" and not any(c["direction"] == "demand" for c in r["candidates"])
    assert r["sold"] == 0
