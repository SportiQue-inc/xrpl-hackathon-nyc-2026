"""What the LLM actually decides - as proposals - and how code checks each one.

Safety rule (monotone): an LLM proposal can only keep or NARROW what the trade may do.
Anything that widens it (more budget, a sensitive field, another purpose, a field that
the sample does not prove, looser licence terms) is cut back by code here or refused by
the seller's own terms or by the ledger.

  L1 infer_spec      goal sentence + what the buyer already holds -> purchase spec
  L2 match_schema    each seller names fields differently -> mapping, verified on samples
  L3 read_licence    free-text licence -> structured terms, confirmed by the seller agent

Every proposal and the code's verdict are stored in the `proposals` table with hashes.
Without an LLM (no key, error) the rule versions below produce the proposal instead.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from .engine import canonical, sha256_hex
from .llm import voice

KNOWN_FIELDS = {"lidar", "imu", "wheel_odometry", "camera_rgb", "depth", "raw_video"}
KNOWN_SCENARIOS = {"night", "narrow_aisle", "dynamic_obstacle", "loading_dock", "outdoor", "daytime"}
LICENCE_KEYS = ("commercial_training", "evaluation", "redistribution")


def _ask(propose, system: str, inp: dict) -> tuple[dict | None, str]:
    """An injected proposer (tests) returns a dict or None; otherwise ask the configured LLM."""
    if propose is None:
        return voice().propose(system, inp)
    out = propose(system, inp)
    return (out, "llm") if isinstance(out, dict) else (None, "rules")


# ---------------- audit ----------------

def record(store, agent: str, task: str, inp: dict, proposal: dict | None, source: str,
           verdict: str, final: dict, notes: list[str]) -> str:
    """Keep the proposal, who made it, and what code did with it."""
    h = sha256_hex(canonical({"task": task, "input": inp, "proposal": proposal}))
    with store.tx() as c:
        c.execute("INSERT INTO proposals (ts, scene, agent, task, source, input, proposal, verdict, final, notes, "
                  "hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  (time.time(), store.scene, agent, task, source, canonical(inp), canonical(proposal),
                   verdict, canonical(final), json.dumps(notes), h))
    return h


# ---------------- L1: goal sentence -> purchase spec ----------------

@dataclass
class OwnerLimits:
    """Set by the buyer organization's owner. The agent can never exceed these."""
    purposes: list[str]
    budget_cap_drops: int
    allow_sensitive_fields: bool = False
    max_missing_rate_ceiling: float = 0.05     # the spec may ask for stricter, never looser
    auto_approve_limit_drops: int | None = None
    min_episodes: int = 30                     # episodes to buy per gap scenario


SPEC_SYSTEM = (
    "You are the data procurement analyst of a robotics company. Read the owner's goal, the company's "
    "data coverage table (episodes held vs target per scenario) and its latest model evaluation report. "
    "Find the data gaps that block the goal. Return JSON with keys: "
    "required_fields (the sensors our robots carry, from inventory.robot_sensors), optional_fields (list), "
    "gaps (list of objects {scenario, evidence}; scenario from: night, narrow_aisle, dynamic_obstacle, "
    "loading_dock, outdoor, daytime; evidence must quote the coverage cell and/or report line you rely on), "
    "purpose (commercial_training or evaluation), max_missing_rate (0-1), budget_xrp (number), "
    "allow_sensitive_fields (bool).")

GAP_RATIO = 0.3   # a scenario is a gap only if we hold less than 30% of its target


def rule_spec(goal_text: str, inventory: dict) -> dict:
    """Baseline without an LLM: sensors from the inventory, scenarios only if the goal names them."""
    t = goal_text.lower()
    scen = [s for s, words in {"night": ["night"], "narrow_aisle": ["narrow aisle"],
                               "dynamic_obstacle": ["dynamic obstacle", "people"],
                               "loading_dock": ["loading dock"], "outdoor": ["outdoor"]}.items()
            if any(w in t for w in words)]
    budget = re.search(r"(\d+(?:\.\d+)?)\s*xrp", t)
    return {"required_fields": list(inventory.get("robot_sensors", [])), "optional_fields": [],
            "gaps": [{"scenario": s, "evidence": "named in the goal text"} for s in scen],
            "purpose": "commercial_training" if "commercial" in t or "train" in t else "evaluation",
            "max_missing_rate": 0.05, "budget_xrp": float(budget.group(1)) if budget else None,
            "allow_sensitive_fields": False}


@dataclass
class Spec:
    text: str
    purpose: str
    required_fields: list[str]
    optional_fields: list[str]
    required_scenarios: list[str]
    max_missing_rate: float
    max_duplicate_rate: float
    allow_sensitive_fields: bool
    budget_cap_drops: int
    auto_approve_limit_drops: int | None
    min_episodes: int = 30
    reasons: dict = field(default_factory=dict)
    proposal_hash: str = ""


def infer_spec(store, agent: str, goal_text: str, inventory: dict, limits: OwnerLimits,
               propose=None) -> tuple[Spec, list[str]]:
    inp = {"goal": goal_text, "inventory": inventory}
    raw, source = _ask(propose, SPEC_SYSTEM, inp)
    if raw is None:
        raw, source = rule_spec(goal_text, inventory), "rules"
    notes: list[str] = []

    def str_list(key, allowed):
        vals = raw.get(key) or []
        vals = [v for v in vals if isinstance(v, str)] if isinstance(vals, list) else []
        bad = [v for v in vals if v not in allowed]
        if bad:
            notes.append(f"{key}: dropped unknown {', '.join(bad)}")
        return [v for v in dict.fromkeys(vals) if v in allowed]

    req = str_list("required_fields", KNOWN_FIELDS)
    sensors = set(inventory.get("robot_sensors", []))
    if sensors and [f for f in req if f not in sensors]:
        notes.append(f"required_fields: kept only sensors our robots carry ({', '.join(sorted(sensors))})")
        req = [f for f in req if f in sensors]
    opt = [f for f in str_list("optional_fields", KNOWN_FIELDS) if f not in req]
    # Gaps: each must cite evidence, and code recomputes it from the coverage table.
    cov = inventory.get("coverage", {})
    scen, reasons = [], {}
    gaps = raw.get("gaps") if isinstance(raw.get("gaps"), list) else []
    for g in gaps:
        if not isinstance(g, dict) or g.get("scenario") not in KNOWN_SCENARIOS:
            notes.append(f"gap {g!r}: unknown scenario, removed")
            continue
        sc, ev = g["scenario"], str(g.get("evidence") or "").strip()
        if not ev:
            notes.append(f"{sc}: no evidence cited, removed")
            continue
        row = cov.get(sc)
        if row is not None and row.get("target"):
            if row["episodes"] >= GAP_RATIO * row["target"]:
                notes.append(f"{sc}: table shows {row['episodes']}/{row['target']} episodes, not a gap; removed")
                continue
            ev = f"{ev} [code: {row['episodes']}/{row['target']} held]"
        elif cov:
            notes.append(f"{sc}: not in our coverage table, removed")
            continue
        if sc not in scen:
            scen.append(sc)
            reasons[sc] = ev[:200]
    purpose = raw.get("purpose")
    if purpose not in limits.purposes:
        notes.append(f"purpose {purpose!r} not allowed by owner; using {limits.purposes[0]}")
        purpose = limits.purposes[0]
    try:
        mmr = float(raw.get("max_missing_rate", limits.max_missing_rate_ceiling))
    except (TypeError, ValueError):
        mmr = limits.max_missing_rate_ceiling
    if not 0 <= mmr <= limits.max_missing_rate_ceiling:
        notes.append(f"max_missing_rate {mmr} looser than owner's {limits.max_missing_rate_ceiling}; capped")
        mmr = limits.max_missing_rate_ceiling
    try:
        budget = int(float(raw.get("budget_xrp")) * 1_000_000)
    except (TypeError, ValueError):
        budget = limits.budget_cap_drops
    if budget > limits.budget_cap_drops or budget <= 0:
        notes.append(f"budget {budget / 1e6:g} XRP above owner's cap {limits.budget_cap_drops / 1e6:g}; capped")
        budget = limits.budget_cap_drops
    sens = bool(raw.get("allow_sensitive_fields")) and limits.allow_sensitive_fields
    if raw.get("allow_sensitive_fields") and not limits.allow_sensitive_fields:
        notes.append("sensitive fields requested but owner does not allow them; removed")
    if not sens:
        dropped = [f for f in req + opt if f == "raw_video"]
        req, opt = [f for f in req if f != "raw_video"], [f for f in opt if f != "raw_video"]
        if dropped:
            notes.append("raw_video removed (may show people)")
    spec = Spec(goal_text, purpose, req, opt, scen, mmr, 0.05, sens, budget, limits.auto_approve_limit_drops,
                limits.min_episodes, reasons)
    final = {"required_fields": req, "optional_fields": opt, "required_scenarios": scen, "evidence": reasons,
             "purpose": purpose,
             "max_missing_rate": mmr, "budget_xrp": budget / 1e6, "allow_sensitive_fields": sens}
    verdict = "narrowed" if notes else "accepted"
    if not req or not scen:
        verdict = "rejected"
        notes.append("spec has no required fields or no missing scenarios; nothing to buy")
    spec.proposal_hash = record(store, agent, "infer_spec", inp, raw, source, verdict, final, notes)
    return spec, notes


# ---------------- L2: schema matching, verified on samples ----------------

def looks_like(kind: str, v) -> bool:
    """What a value of each canonical field must look like in a sample."""
    if v is None:
        return True   # missing values are counted by the quality check, not here
    if kind == "lidar":
        return isinstance(v, dict) and isinstance(v.get("points"), int) and v["points"] > 1000 and "range_m" in v
    if kind == "imu":
        return isinstance(v, list) and len(v) == 6 and all(isinstance(x, (int, float)) for x in v)
    if kind == "wheel_odometry":
        return isinstance(v, dict) and "v_mps" in v
    if kind == "camera_rgb":
        return isinstance(v, dict) and v.get("encoding") in ("jpeg", "png")
    if kind == "depth":
        return isinstance(v, dict) and "width" in v and "points" not in v
    return False


MATCH_SYSTEM = (
    "Map each wanted canonical field to the seller's own field name that holds the same data, using "
    "the field names and the sample values. Return JSON {\"mapping\": {canonical: seller_field or null}, "
    "\"confidence\": {canonical: 0-1}, \"why\": {canonical: short reason}}.")


def rule_match(wanted: list[str], seller_fields: list[str]) -> dict:
    """Baseline without an LLM: exact field names only."""
    m = {w: (w if w in seller_fields else None) for w in wanted}
    return {"mapping": m, "confidence": {w: 1.0 if m[w] else 0.0 for w in wanted}}


def match_schema(store, agent: str, product: dict, wanted: list[str], sample: list[dict],
                 propose=None) -> tuple[dict, dict, list[str]]:
    """Returns (verified mapping canonical->seller field, rejected {canonical: reason}, notes)."""
    preview = {f: next((r.get(f) for r in sample if r.get(f) is not None), None) for f in product["fields"]}
    inp = {"product": product["id"], "wanted": wanted, "seller_fields": product["fields"], "sample_values": preview}
    raw, source = _ask(propose, MATCH_SYSTEM, inp)
    if raw is None or not isinstance(raw.get("mapping"), dict):
        raw, source = rule_match(wanted, product["fields"]), "rules"
    verified, rejected, notes = {}, {}, []
    for w in wanted:
        f = raw["mapping"].get(w)
        if not f:
            rejected[w] = "no matching field"
            continue
        if f not in product["fields"]:
            rejected[w] = f"proposed field {f!r} does not exist"
            continue
        vals = [r.get(f) for r in sample]
        if vals and all(looks_like(w, v) for v in vals) and any(v is not None for v in vals):
            verified[w] = f
        else:
            rejected[w] = f"{f!r} does not look like {w} in the sample"
    if rejected:
        notes = [f"{k}: {v}" for k, v in rejected.items()]
    verdict = "accepted" if not rejected else ("narrowed" if verified else "rejected")
    record(store, agent, "match_schema", inp, raw, source, verdict, {"verified": verified, "rejected": rejected}, notes)
    return verified, rejected, notes


# ---------------- L3: licence text -> structured terms ----------------

LICENCE_SYSTEM = (
    "Read the data licence text. Return JSON {\"commercial_training\": bool, \"evaluation\": bool, "
    "\"redistribution\": bool, \"term_months\": int or null, \"attribution\": bool}. If the text does not "
    "clearly allow something, set it to false.")


def rule_licence(text: str) -> dict:
    t = text.lower()
    eval_only = "only" in t and ("evaluation" in t or "benchmark" in t)
    commercial = (("commercial" in t and not re.search(r"not (for|permitted|allowed)[^.]*commercial", t)
                   and "non-commercial" not in t) or "any internal use" in t) and not eval_only
    term = re.search(r"(\d+)\s*months?", t)
    return {"commercial_training": commercial,
            "evaluation": commercial or "evaluation" in t or "benchmark" in t,
            "redistribution": "redistribut" in t and not any(
                w in t for w in ("no redistribution", "no resale", "not redistribute", "redistribution prohibited",
                                 "or redistribution")),
            "term_months": int(term.group(1)) if term else None, "attribution": "attribution" in t}


def read_licence(store, agent: str, product: dict, propose=None) -> tuple[dict, str]:
    inp = {"product": product["id"], "licence_text": product["licence_text"]}
    raw, source = _ask(propose, LICENCE_SYSTEM, inp)
    if raw is None:
        raw, source = rule_licence(product["licence_text"]), "rules"
    terms = {k: bool(raw.get(k)) for k in LICENCE_KEYS}
    terms["term_months"] = raw.get("term_months") if isinstance(raw.get("term_months"), int) else None
    terms["attribution"] = bool(raw.get("attribution"))
    h = record(store, agent, "read_licence", inp, raw, source, "pending_seller_confirmation", terms, [])
    return terms, h


def terms_hash(product_id: str, terms: dict, mapping: dict) -> str:
    return sha256_hex(canonical({"product": product_id, "terms": terms, "mapping": mapping}))
