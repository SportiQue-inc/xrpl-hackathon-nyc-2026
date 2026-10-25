"""Stand-ins for the LLM in tests. `capable` answers like a good model would (including one
plausible mistake: it maps a depth camera to LiDAR); `hostile` tries to widen everything."""
from agentrail.reasoning import LICENCE_SYSTEM, MATCH_SYSTEM, SPEC_SYSTEM, rule_licence

ALIASES = {"lidar": ["lidar", "lidar_xyz", "point_cloud", "depth_cam"], "imu": ["imu", "imu_6axis"],
           "wheel_odometry": ["odom", "wheel_odometry"]}


def capable(system, payload):
    if system == SPEC_SYSTEM:
        inv = payload["inventory"]
        gaps = [{"scenario": s, "evidence": f"coverage.{s} {r['episodes']}/{r['target']}"}
                for s, r in inv["coverage"].items() if r["episodes"] < 0.3 * r["target"]]
        return {"required_fields": inv["robot_sensors"], "optional_fields": ["raw_video"], "gaps": gaps,
                "purpose": "commercial_training", "max_missing_rate": 0.05, "budget_xrp": 40,
                "allow_sensitive_fields": False}
    if system == MATCH_SYSTEM:
        m = {w: next((f for f in payload["seller_fields"] if f in ALIASES.get(w, [w])), None)
             for w in payload["wanted"]}
        return {"mapping": m, "confidence": {w: 0.9 for w in m}}
    if system == LICENCE_SYSTEM:
        return rule_licence(payload["licence_text"])
    return None


def hostile(system, payload):
    if system == SPEC_SYSTEM:
        return {"required_fields": ["lidar", "imu", "raw_video"], "optional_fields": ["raw_video"],
                "gaps": [{"scenario": "night", "evidence": "report line 1"},
                         {"scenario": "narrow_aisle", "evidence": "trust me"},
                         {"scenario": "moon_base", "evidence": "x"}, {"scenario": "dynamic_obstacle"}],
                "purpose": "marketing_profiling", "max_missing_rate": 0.9, "budget_xrp": 999,
                "allow_sensitive_fields": True}
    if system == MATCH_SYSTEM:
        f = payload["seller_fields"]
        return {"mapping": {w: f[0] for w in payload["wanted"]}}
    if system == LICENCE_SYSTEM:
        return {"commercial_training": True, "evaluation": True, "redistribution": True}
    return None


def capable_needs(system, payload):
    from agentrail.cohort import NEEDS_SYSTEM
    if system != NEEDS_SYSTEM:
        return capable(system, payload)
    cov = payload["coverage"]
    gaps = []
    for item, weeks in cov.items():
        low = [int(w[1:]) for w, v in weeks.items() if int(v.split("/")[0]) < 0.9 * int(v.split("/")[1])]
        if low and item != "blood_pressure.daily":
            gaps.append({"item": item, "weeks": low, "evidence": ", ".join(f"{w} {weeks[f'w{w}']}" for w in low)})
    return {"gaps": gaps, "do_not_request": [{"item": "sleep.daily", "reason": "already complete"}],
            "purpose": "sleep_research", "budget_xrp": 30,
            "summary_for_participants": "The study lost fatigue answers for weeks 3-5 and asks to fill them."}
