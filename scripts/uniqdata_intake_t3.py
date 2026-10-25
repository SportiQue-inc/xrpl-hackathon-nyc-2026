"""Bring each participant's sensitive (T3) records in through UniQdata's intake, as the market profiles say
they hold them: genomic variants, CT and MRI.

    python scripts/uniqdata_intake_t3.py [--roster .uniqdata_roster.json]

Each record goes through UniQdata's write API, the DataQ path: concept and source checks, the quality
engine's range checks, a source registry entry and a record hash. Only a synthetic summary is stored
(variant count and risk score; DICOM series and slice counts with the study day), never an image or
a genome. The market's T3 datasets then carry the UniQdata record hash as their provenance
(uniqdata_live.feed_market), and a T3 dataset whose owner has no such record is not listed.
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.uniqdata_live import load_roster, records_for  # noqa: E402

PROFILES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures", "market_profiles.json")


def t3_readings(pid: str, holds: list[str]) -> list[tuple[str, int, dict]]:
    r = random.Random(f"t3-{pid}")
    out = []
    if "genome.variant" in holds:
        out.append(("genome.variant", 3, {"risk_score": round(r.uniform(0.1, 0.9), 2)}))
    if "imaging.ct" in holds:
        out.append(("imaging.ct", r.randint(5, 50), {"slices": r.randint(120, 480)}))
    if "imaging.mri" in holds:
        out.append(("imaging.mri", r.randint(5, 50), {"series": r.randint(4, 12)}))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default=".uniqdata_roster.json")
    ap.add_argument("--pace", type=float, default=7)
    a = ap.parse_args()
    prof = json.load(open(PROFILES))["participants"]
    clients = load_roster(a.roster)
    done = 0
    for pid, p in sorted(prof.items()):
        holds = [c for c in p["holds"]["health"] if c in ("genome.variant", "imaging.ct", "imaging.mri")]
        if not holds or pid not in clients:
            continue
        have = {(r.get("source_value") or "").split(":")[1] for r in clients[pid].query({"limit": 1000})["data"]
                if (r.get("source_value") or "").startswith("agentrail:")}
        recs = [x for it, d, v in t3_readings(pid, holds) if it not in have for x in records_for(it, d, v)]
        if not recs:
            continue
        out = clients[pid].write(recs).get("records", [])
        done += len(out)
        print(f"{pid}: {[r['record_hash'][:12] for r in out]} {holds}", flush=True)
        time.sleep(a.pace)
    print(f"{done} T3 records taken in through UniQdata")


if __name__ == "__main__":
    main()
