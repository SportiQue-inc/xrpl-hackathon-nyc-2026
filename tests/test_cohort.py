"""Cohort lots: nothing leaves below k; the agents assemble the lot; one push, one escrow per member."""
from agentrail.market import acts, cohort


def test_one_person_never_passes_and_a_lot_does():
    me = {"qi": {"age_group": "<40", "sex": "F", "region": "Seoul"}}
    assert cohort.k_check([me], 5)[0] is None
    lot = [{"qi": {"age_group": a, "sex": s, "region": "Seoul"}} for a in ("<40", "40-64") for s in "FM" for _ in range(5)]
    assert cohort.k_check(lot, 5)[0] == ["age_group", "sex", "region"]
    mixed = lot[:5] + [{"qi": {"age_group": "65+", "sex": "M", "region": "Busan"}}] * 2
    assert cohort.k_check(mixed, 5)[0] in (["sex"], [])


def test_lots_clear_where_one_at_a_time_cannot():
    r = cohort.run()
    assert r["cleared_one_at_a_time"] == 0 and r["lots_released"] > 0
    for lot in r["lots"]:
        if lot["status"] == "released":
            assert len(lot["members"]) >= lot["k"] and lot["domain"]
            assert len({acts.catalog.CATALOG[c].tier for c in lot["columns"]}) == 1


def test_a_lot_never_spans_two_domains():
    r = cohort.form({"id": "x", "institution": "org_cardio", "columns": ["sleep.daily", "lab.glucose"], "weeks": 8},
                    acts.load())
    assert r["status"] == "refused"


def test_below_k_stays_closed():
    r = cohort.form({"id": "y", "institution": "org_cardio", "columns": ["blood_pressure.daily"], "weeks": 8},
                    acts.load(), k=1000)
    assert r["status"] == "pending"


def test_lot_is_one_push_and_each_member_is_paid():
    prof = acts.load()
    lot = next(x for x in cohort.run(prof)["lots"] if x["status"] == "released")
    d = cohort.deliver(lot, prof)
    assert d["members_paid"] == len(lot["members"]) and d["paid_drops"] == lot["price_per_member_drops"] * len(lot["members"])
