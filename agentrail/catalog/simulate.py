"""The approval bottleneck, with and without the agent. Synthetic owners, studies and response times.

Manual: the owner approves every column of every study every week (one sitting per study-week,
each column a separate tick). Agent: requests inside a standing grant run at once; the rest go to
one consent package per institution, approved with one Touch ID; T3 asks every time.

Owner response time is drawn from an exponential with a mean of 18 hours (a plausible figure, not a
measured one). Payment follows delivery within seconds; the clock that matters is request -> paid.
"""
from __future__ import annotations

import random
import statistics

from .scope import Grant, Owner, Request, TouchID

STUDIES = [
    # id, institution, class, country, purpose, columns, weeks
    ("S1", "org_sleeplab", "academic", "KR", "sleep_research",
     ["sleep.daily", "sleep.efficiency", "heart_rate.daily", "hrv.daily", "steps.daily"], list(range(1, 13))),
    ("S2", "org_cardio_hosp", "hospital", "KR", "cardio_research",
     ["heart_rate.daily", "hrv.daily", "weight", "meal.sugar", "med.adherence", "blood_pressure.daily", "lab.ldl"],
     list(range(1, 13))),
    ("S3", "org_nutrition_us", "academic", "US", "nutrition_research",
     ["meal.kcal", "meal.protein", "meal.carbs", "meal.sugar", "caffeine", "weight"], list(range(1, 9))),
    ("S4", "org_cardio_hosp", "hospital", "KR", "pharmacogenomics_research", ["genome.pgx", "rx.list"], [1]),
    ("S5", "org_imaging_lab", "academic", "KR", "imaging_research", ["imaging.mri", "dx.codes"], [1]),
    ("S6", "org_wellness_co", "commercial", "KR", "product_development",
     ["steps.daily", "sleep.daily", "active_energy.daily"], list(range(1, 13))),
]
MEAN_RESPONSE_H = 18.0
AUTO_H = 10 / 3600            # agent decision plus ledger settlement, seconds
DEADLINE_H = 48


def studies():
    from .columns import duo_for
    out = []
    for sid, inst, cls, country, purpose, cols, weeks in STUDIES:
        extra = ["DUO:0000016"] if any(c.startswith("genome.") for c in cols) else []
        out.append(dict(id=sid, institution=inst, inst_class=cls, country=country, purpose=purpose, columns=cols,
                        weeks=weeks, duo=sorted(set(duo_for(cols)) | set(extra)), irb=cls != "commercial"))
    return out


def owners(n=50, seed=7):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        if rng.random() < 0.7:
            g = Grant("T2" if rng.random() < 0.4 else "T1", frozenset({"sleep_research", "cardio_research"}),
                      frozenset({"academic", "hospital"}), abroad=rng.random() < 0.3)
        else:
            g = Grant("T0", frozenset({"sleep_research"}), frozenset({"academic"}))
        out.append(Owner(f"U-{i + 1:03d}", grants=[g], device=TouchID(bytes([i + 1]) * 32)))
    return out


def run(n=50, seed=7) -> dict:
    rng = random.Random(seed + 1)
    st = studies()
    manual_ticks = sum(len(s["columns"]) * len(s["weeks"]) for s in st) * n
    manual_sittings = sum(len(s["weeks"]) for s in st) * n
    manual_lat, agent_lat = [], []
    touches = autos = refused = declined = 0
    offers = {}
    for o in owners(n, seed):
        accepts = rng.random() < 0.8          # how this owner answers packages
        t3_ok = rng.random() < 0.5
        for s in st:
            for wk in s["weeks"]:
                manual_lat.append(rng.expovariate(1 / MEAN_RESPONSE_H))
                r = Request(f"{s['id']}-w{wk}-{o.pid}", s["institution"], s["inst_class"], s["country"], s["id"],
                            s["purpose"], s["columns"], [wk], why=f"{s['purpose']} week {wk}", duo=s["duo"],
                            irb=s["irb"])
                e = o.request(r)
                if e["decision"] == "auto":
                    autos += 1
                    agent_lat.append(AUTO_H)
                elif e["decision"] == "refused":
                    refused += 1
                    continue
                else:
                    ok = t3_ok if r.tier == "T3" else accepts
                    touches += 1
                    if not ok:
                        o.decline(r.institution)
                        declined += 1
                        continue
                    pkg = o.package(r.institution)
                    res = o.approve(r.institution, o.device.assert_(pkg["hash"], o.clock()), remember=True)
                    assert res["ok"], res
                    agent_lat.append(rng.expovariate(1 / MEAN_RESPONSE_H))
                if agent_lat[-1] <= DEADLINE_H:
                    offers[(s["id"], wk)] = offers.get((s["id"], wk), 0) + 1

    def q(xs, p):
        return round(sorted(xs)[int(p * (len(xs) - 1))], 3) if xs else None
    return {
        "owners": n, "studies": len(st),
        "manual": {"approvals": manual_ticks, "sittings": manual_sittings,
                   "median_hours_to_paid": q(manual_lat, 0.5), "p90_hours_to_paid": q(manual_lat, 0.9),
                   "within_48h": round(sum(x <= DEADLINE_H for x in manual_lat) / len(manual_lat), 3)},
        "agent": {"touch_id": touches, "auto": autos, "declined": declined, "refused": refused,
                  "median_hours_to_paid": q(agent_lat, 0.5), "p90_hours_to_paid": q(agent_lat, 0.9),
                  "within_48h": round(sum(x <= DEADLINE_H for x in agent_lat) / max(1, len(agent_lat)), 3)},
        "reduction": round(manual_ticks / max(1, touches), 1),
        "offers_per_study_week": round(statistics.mean(offers.values()), 1) if offers else 0,
    }
