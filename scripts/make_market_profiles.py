"""Write fixtures/market_profiles.json: who each roster account is in the two demo acts (all synthetic).

Act 1, open market: every account's agent buys and sells by its own needs. Act 2, health B2B2C:
four institutions with three or four researchers each request study data from the participants.
Each profile has what the account holds (health columns from its UniQdata account, and for some
non-health data such as robot sensor logs), what it needs, a budget, a pre-consent tier, and how far
its agent may act alone.
"""
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEALTH = {"T0": ["sleep.daily", "activity.daily", "heart_rate.daily", "spo2.daily", "body_weight.daily",
                 "body_temp.daily"],
          "T1": ["fatigue.survey", "meal.log", "medication.taken", "mood.daily", "energy.survey"],
          "T2": ["blood_pressure.daily", "lab.glucose", "lab.hba1c", "diagnosis.code", "prescription.active"],
          "T3": ["genome.variant", "imaging.ct", "imaging.mri", "mental.phq9"]}
OTHER = ["robot.joint_torque", "robot.lidar_scan", "robot.gripper_events", "fleet.battery_log",
         "smarthome.energy_kwh"]
TIERS = {"T0-T3": ["T0", "T1", "T2", "T3"], "T0-T2": ["T0", "T1", "T2"], "T0-T1": ["T0", "T1"], "T0": ["T0"]}
INSTITUTIONS = [
    {"id": "org_sleeplab", "name": "Sleep & Fatigue Lab (synthetic)", "country": "KR", "max_tier": "T1",
     "study": "sleep debt vs fatigue, 8 weeks"},
    {"id": "org_cardio", "name": "Cardiometabolic Cohort (synthetic)", "country": "KR", "max_tier": "T2",
     "study": "resting HR, BP and HbA1c trajectories"},
    {"id": "org_neuroimg", "name": "Neuroimaging Center (synthetic)", "country": "US", "max_tier": "T3",
     "study": "MRI and PHQ-9 in shift workers"},
    {"id": "org_genomics", "name": "Population Genomics Unit (synthetic)", "country": "SG", "max_tier": "T3",
     "study": "variant risk vs sleep phenotype"},
]


def main():
    fixture = json.load(open(os.path.join(ROOT, "fixtures", "testnet-addresses.public.json")))
    pids = [a["account_id"] for a in fixture["accounts"] if a["role"] == "participant"][:50]
    people = {}
    for pid in pids:
        r = random.Random(f"market-{pid}")
        tier = r.choice(["T0-T3", "T0-T2", "T0-T2", "T0-T1", "T0"])
        holds = [c for t in ["T0", "T1", "T2"] for c in HEALTH[t] if r.random() < 0.8]
        holds += [c for c in HEALTH["T3"] if r.random() < 0.3]
        other = r.sample(OTHER, r.choice([0, 0, 0, 1, 2]))
        wants = r.sample([c for t in HEALTH for c in HEALTH[t]] + OTHER, r.choice([1, 2, 3]))
        people[pid] = {
            "act1_role": r.choice(["seller", "seller", "both", "buyer"]),
            "holds": {"health": holds, "other": other}, "wants": [w for w in wants if w not in holds + other],
            "budget_xrp": r.choice([0, 2, 5, 10]), "pre_consent": tier,
            "auto_tiers": TIERS[tier][:2] if tier != "T0" else ["T0"],      # beyond these: ask the person
            "never": ["T3"] if "T3" not in TIERS[tier] else [],
            "agent_trust": round(r.uniform(0.4, 0.98), 2)}
    researchers = {}
    for i, inst in enumerate(INSTITUTIONS):
        for k in range(4 if i < 2 else 3):
            rid = f"R-{inst['id'][4:]}-{k + 1}"
            r = random.Random(f"res-{rid}")
            researchers[rid] = {"institution": inst["id"], "act1_role": "buyer",
                                "wants": r.sample([c for t in TIERS["T0-T3"] if t <= inst["max_tier"] for c in HEALTH[t]], 3),
                                "budget_xrp": r.choice([20, 40, 60]), "agent_trust": round(r.uniform(0.6, 0.95), 2)}
    out = {"note": "synthetic demo profiles; no person behind any of them",
           "institutions": INSTITUTIONS, "researchers": researchers, "participants": people}
    json.dump(out, open(os.path.join(ROOT, "fixtures", "market_profiles.json"), "w"), indent=1, ensure_ascii=False)
    print(f"{len(people)} participants, {len(researchers)} researchers, {len(INSTITUTIONS)} institutions")


if __name__ == "__main__":
    main()
