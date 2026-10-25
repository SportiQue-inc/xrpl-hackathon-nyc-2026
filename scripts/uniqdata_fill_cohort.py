"""Fill every cohort participant's UniQdata account with eight weeks of synthetic records.

    python scripts/uniqdata_fill_cohort.py [--roster .uniqdata_roster.json] [--skip P-017]

Each person gets a wearable (sleep, resting heart rate, steps every day), a weekly fatigue survey
and clinic visits with blood pressure, with person-level variety so the study's checks have work:
- wear adherence differs per person (some days missing);
- about one in five people wear the device less and less in weeks 5-8 (a declining column);
- about one in ten have bad records: a flat heart-rate week (copied value), a few implausible
  heart-rate readings that are still inside UniQdata's hard range, or a survey answered twice.
Values are generated, not taken from anyone. Records go in through UniQdata's write API.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.connectors import HospitalExportSource, SurveySource, WearableSource  # noqa: E402
from agentrail.uniqdata_live import load_roster, records_for  # noqa: E402

WEEKS = range(1, 9)
CONSENT_TIERS = ["T0-T3", "T0-T2", "T0-T2", "T0-T1", "T0"]     # what each person pre-consents to


def person_profile(pid: str) -> dict:
    rng = random.Random(f"profile-{pid}")
    return {"adherence": round(rng.uniform(0.72, 0.99), 2), "declining": rng.random() < 0.2,
            "bad": rng.choice([None] * 9 + [rng.choice(["flat_hr", "implausible_hr", "double_survey"])]),
            "clinic_days": sorted(rng.sample(range(5, 54), rng.choice([1, 2, 2, 3]))),
            "consent_tiers": rng.choice(CONSENT_TIERS)}


def readings(pid: str, prof: dict) -> list[tuple[str, int, dict]]:
    wear, survey = WearableSource(), SurveySource()
    out = []
    for wk in WEEKS:
        keep = prof["adherence"] - (0.12 * (wk - 4) if prof["declining"] and wk > 4 else 0)
        for day in range((wk - 1) * 7 + 1, wk * 7 + 1):
            rng = random.Random(f"{pid}-{day}")
            if rng.random() < keep:
                for it in WearableSource.items:
                    out.append((it, day, wear.read(pid, it, day, random.Random(f"{pid}-{wk}-{it}-{day}"))))
            v = survey.read(pid, "fatigue.survey", day, random.Random(f"{pid}-{wk}-fatigue.survey-{day}"))
            if v is not None and rng.random() < 0.9:
                out.append(("fatigue.survey", day, v))
        for d in prof["clinic_days"]:
            if (wk - 1) * 7 < d <= wk * 7:
                r = random.Random(f"{pid}-bp-{d}")
                out.append(("blood_pressure.daily", d, {"SYSBP": r.randint(105, 145), "DIABP": r.randint(65, 92)}))
    bad = prof["bad"]
    if bad == "flat_hr":
        out = [(i, d, {**v, "resting_bpm": 61} if i == "heart_rate.daily" and 22 <= d <= 28 else v) for i, d, v in out]
    elif bad == "implausible_hr":
        out = [(i, d, {**v, "resting_bpm": 236} if i == "heart_rate.daily" and d % 9 == 0 else v) for i, d, v in out]
    elif bad == "double_survey":
        out += [(i, d, {"score_0_10": min(10, v["score_0_10"] + 3)}) for i, d, v in out if i == "fatigue.survey"][:2]
    return out


def catalog_readings(pid: str, prof: dict) -> list[tuple[str, int, dict]]:
    """The wider catalog (T0-T3) for one person: daily device and life-log columns, periodic labs,
    a diagnosis list, and for some people genomic and imaging records."""
    rng = random.Random(f"catalog-{pid}")
    base_w, base_t = rng.uniform(52, 95), rng.uniform(36.2, 36.8)
    on_meds, has_genome, has_imaging = rng.random() < 0.4, rng.random() < 0.3, rng.random() < 0.25
    out = []
    for day in range(1, 57):
        r = random.Random(f"{pid}-cat-{day}")
        if r.random() < prof["adherence"]:
            out.append(("spo2.daily", day, {"pct": r.randint(93, 99)}))
            out.append(("body_temp.daily", day, {"celsius": round(base_t + r.uniform(-0.3, 0.4), 1)}))
        if day % 3 == 0 and r.random() < 0.8:
            out.append(("body_weight.daily", day, {"kg": round(base_w + r.uniform(-0.8, 0.8), 1)}))
        if r.random() < 0.6:
            out.append(("meal.log", day, {"kcal": r.randint(1300, 2900)}))
        if on_meds:
            out.append(("medication.taken", day, {"taken": 1 if r.random() < 0.85 else 0}))
        if r.random() < 0.5:
            out.append(("mood.daily", day, {"score_1_5": r.randint(1, 5)}))
        if day % 7 == 0:
            out.append(("energy.survey", day, {"score_0_10": r.randint(2, 9)}))
    for d in prof["clinic_days"]:
        r = random.Random(f"{pid}-lab-{d}")
        out.append(("lab.glucose", d, {"mg_dl": r.randint(78, 160)}))
        out.append(("lab.hba1c", d, {"pct": round(r.uniform(4.9, 7.8), 1)}))
        out.append(("diagnosis.code", d, {"icd10_index": r.randint(1, 40)}))
        out.append(("prescription.active", d, {"count": r.randint(0, 4)}))
        out.append(("mental.phq9", d, {"score_0_27": r.randint(0, 18)}))
    if has_genome:
        out.append(("genome.variant", 3, {"risk_score": round(rng.uniform(0.1, 0.9), 2)}))
    if has_imaging:
        out.append(("imaging.ct", prof["clinic_days"][0], {"slices": rng.randint(120, 480)}))
        out.append(("imaging.mri", prof["clinic_days"][-1], {"series": rng.randint(4, 12)}))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default=".uniqdata_roster.json")
    ap.add_argument("--catalog", action="store_true", help="add the T0-T3 catalog columns")
    ap.add_argument("--only", nargs="*", default=None, help="only these participants")
    ap.add_argument("--pace", type=float, default=25, help="seconds to wait after each person")
    ap.add_argument("--skip", nargs="*", default=[], help="participants to leave empty (e.g. the manual one)")
    a = ap.parse_args()
    summary = {}
    for pid, client in load_roster(a.roster).items():
        if pid in a.skip or (a.only and pid not in a.only):
            continue
        prof = person_profile(pid)
        if a.catalog:                                # second pass: the wider T0-T3 catalog
            recs = [x for it, day, v in catalog_readings(pid, prof) for x in records_for(it, day, v)]
        else:
            if client.query({"limit": 1}).get("data"):
                print(f"{pid}: already has records, skipped", flush=True)
                continue
            recs = [x for it, day, v in readings(pid, prof) for x in records_for(it, day, v)]
        n = 0
        for i in range(0, len(recs), 500):
            n += len(client.write(recs[i:i + 500]).get("records", []))
        summary[pid] = {"records": n, **{k: prof[k] for k in ("adherence", "declining", "bad", "consent_tiers")}}
        time.sleep(a.pace)                           # UniQdata allows 10 sensitive calls a minute
        print(f"{pid}: {n} records (adherence {prof['adherence']}, declining {prof['declining']}, bad {prof['bad']})",
              flush=True)
    print(json.dumps({"people": len(summary), "records": sum(s["records"] for s in summary.values()),
                      "declining": sum(s["declining"] for s in summary.values()),
                      "bad": {b: sum(s["bad"] == b for s in summary.values()) for b in
                              ("flat_hr", "implausible_hr", "double_survey")}}))


if __name__ == "__main__":
    main()
