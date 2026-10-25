"""Main scene: a stalled 8-week sleep and fatigue study (all synthetic).

The lab holds a coverage table (participant x week x item). Its research agent reads the
protocol, the table and the latest analysis note, and the LLM proposes which cells are
missing and worth requesting. Code recomputes every gap from the table, drops anything without
support (or already held), and caps budget and purpose. Then each participant's agent
answers for its person: provide automatically, ask the person, or block.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field

from .engine import BudgetExceeded, NeedsHumanApproval, OrderRequest
from .reasoning import _ask, record

ITEMS = ["sleep.daily", "activity.daily", "heart_rate.daily", "fatigue.survey", "blood_pressure.daily"]
WEEKS = list(range(1, 9))
PRIMARY = ("sleep.daily", "fatigue.survey")      # the analysis needs both in the same person-week
EFFECT_R = 0.14                                   # effect size the study was powered for

PROTOCOL = (
    "Sleep and fatigue cohort, 8 weeks, 50 participants (synthetic). Primary analysis: association "
    "between weekly sleep debt and fatigue score; needs sleep.daily and fatigue.survey in the same "
    "participant-week. Secondary: resting heart rate (heart_rate.daily). Exploratory: blood pressure "
    "(blood_pressure.daily), only with ethics approval. Purpose: sleep_research. Data stays with the lab; "
    "no onward transfer.")


def power(complete_pairs: int, r: float = EFFECT_R) -> float:
    """Power of a two-sided correlation test at alpha 0.05 (Fisher z approximation)."""
    if complete_pairs <= 3:
        return 0.0
    z = math.atanh(r) * math.sqrt(complete_pairs - 3) - 1.959964
    return round(0.5 * (1 + math.erf(z / math.sqrt(2))), 2)


@dataclass
class Coverage:
    """cells[person][week] = set of items the lab already holds."""
    people: list[str]
    cells: dict = field(default_factory=dict)

    def has(self, p, w, item) -> bool:
        return item in self.cells[p][w]

    def missing(self, item: str, week: int) -> list[str]:
        return [p for p in self.people if not self.has(p, week, item)]

    def complete_pairs(self) -> int:
        return sum(all(self.has(p, w, i) for i in PRIMARY) for p in self.people for w in WEEKS)

    def table(self) -> dict:
        """What the LLM reads: per item and week, how many participants have data."""
        n = len(self.people)
        return {i: {f"w{w}": f"{n - len(self.missing(i, w))}/{n}" for w in WEEKS} for i in ITEMS}

    def add(self, p, w, items):
        self.cells[p][w] |= set(items)


HERO = "P-017"   # the participant the demo follows


def synthetic_coverage(people: list[str], seed: int = 7) -> Coverage:
    """Sleep and activity nearly complete; fatigue survey lost in weeks 3-5 after an app outage;
    heart rate missing for a subgroup in weeks 4-5; blood pressure never collected."""
    rng = random.Random(seed)
    cov = Coverage(people, {p: {w: set() for w in WEEKS} for p in people})
    hr_gap = set(rng.sample(people, 12))
    for p in people:
        for w in WEEKS:
            have = {"sleep.daily", "activity.daily"} if rng.random() > 0.02 else {"activity.daily"}
            if not (3 <= w <= 5 and rng.random() < 0.7) and rng.random() > 0.04:
                have.add("fatigue.survey")
            if not (p in hr_gap and w in (4, 5)):
                have.add("heart_rate.daily")
            cov.cells[p][w] = have
    if HERO in cov.cells:   # the participant the demo follows: survey lost in weeks 3-5, watch sync gap week 4
        for w in (3, 4, 5):
            cov.cells[HERO][w].discard("fatigue.survey")
        cov.cells[HERO][4].discard("heart_rate.daily")
    return cov


ANALYSIS_NOTE = [
    "Primary model is underpowered: complete sleep+fatigue participant-weeks below plan.",
    "Fatigue survey app outage during weeks 3-5; most participants have no score for those weeks.",
    "Resting heart rate missing for a subgroup in weeks 4-5 (device sync issue).",
    "Sleep and activity streams are complete enough; no action needed.",
]

PERSON_SYSTEM = (
    "You are the study's research agent looking at ONE participant's 8-week record. You get the "
    "protocol and, per week, which items the study already holds for this person. Say what is missing "
    "for this person that the protocol needs, week by week; sources_hold says what the person's own "
    "sources (wearable, survey app, clinic) can supply. Return JSON {\"missing\": [{\"week\": int, "
    "\"item\": string, \"reason\": short}]}.")


def person_gaps(store, agent: str, cov: Coverage, pid: str, propose=None, available: dict | None = None,
                ethics_approved: bool = False) -> list[dict]:
    """Per-person gap reading: the LLM names weeks and items; code keeps only cells that are
    really empty in the table, that the protocol uses, and that the person's sources can supply.
    `available` = {week: [items the person's sources hold]} (counts only, no values)."""
    held = {f"w{w}": sorted(cov.cells[pid][w]) for w in WEEKS}
    inp = {"protocol": PROTOCOL, "participant": pid, "held": held}
    if available is not None:
        inp["sources_hold"] = {f"w{w}": sorted(v) for w, v in available.items()}
    raw, source = _ask(propose, PERSON_SYSTEM, inp, side="participant")
    if raw is None:
        raw = {"missing": [{"week": w, "item": i, "reason": "empty in the coverage table"}
                           for w in WEEKS for i in PRIMARY + ("heart_rate.daily",) if not cov.has(pid, w, i)]
               + [{"week": w, "item": "blood_pressure.daily", "reason": "clinic visit this week; exploratory variable"}
                  for w in WEEKS if available and "blood_pressure.daily" in available.get(w, [])]}
        source = "rules"
    out = []
    for m in raw.get("missing") or []:
        if not isinstance(m, dict):
            continue
        wk, item = m.get("week"), m.get("item")
        if item not in ITEMS or wk not in WEEKS:
            out.append({**m, "verdict": "removed", "code_reason": "not a protocol item or week"})
        elif cov.has(pid, wk, item):
            out.append({**m, "verdict": "removed", "code_reason": "already held for this person"})
        elif available is not None and item not in available.get(wk, []):
            out.append({**m, "verdict": "removed", "code_reason": "none of this person's sources holds it that week"})
        elif item == "blood_pressure.daily" and not ethics_approved:
            out.append({**m, "verdict": "removed", "code_reason": "exploratory item; no ethics credential on the ledger"})
        else:
            out.append({**m, "verdict": "kept", "code_reason": "empty in the coverage table"})
    record(store, agent, "person_gaps", inp, raw, source,
           "accepted" if all(o["verdict"] == "kept" for o in out) else "narrowed",
           [o for o in out if o["verdict"] == "kept"], [o["code_reason"] for o in out if o["verdict"] != "kept"])
    for o in out:
        o["source"] = source
    return out

NEEDS_SYSTEM = (
    "You are the data manager of a research study. Read the protocol, the coverage table "
    "(participants with data / total, per item and week) and the analysis note. Decide which data "
    "to obtain so the study can run, and which data NOT to request because the study already holds it. "
    "Return JSON {\"gaps\": [{\"item\", \"weeks\": [int], \"evidence\": quote the table cells or note "
    "line}], \"do_not_request\": [{\"item\", \"reason\"}], \"purpose\": string, \"budget_xrp\": number, "
    "\"summary_for_participants\": one or two plain sentences explaining why the lab asks}.")

GAP_MIN_MISSING = 0.10   # a cell column is a gap only if at least 10% of participants lack it


@dataclass
class Needs:
    gaps: dict                 # item -> list of weeks (verified)
    cells: dict                # person -> {week: [items]} to request
    purpose: str
    budget_drops: int
    summary: str
    evidence: dict
    notes: list
    proposal_hash: str = ""
    source: str = "rules"
    claims: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    verdict: str = ""


def rule_needs(protocol: str, table: dict) -> dict:
    """Baseline without an LLM: only the primary items named in the protocol, every week."""
    return {"gaps": [{"item": "fatigue.survey", "weeks": WEEKS, "evidence": "protocol primary item"}],
            "do_not_request": [], "purpose": "sleep_research", "budget_xrp": None,
            "summary_for_participants": "The lab asks for data its study is missing."}


def infer_needs(store, agent: str, cov: Coverage, allowed_purposes: list[str], budget_cap_drops: int,
                ethics_approved: bool, propose=None, goal: str | None = None) -> Needs:
    inp = {"protocol": PROTOCOL, "coverage": cov.table(), "analysis_note": ANALYSIS_NOTE}
    if goal:
        inp["researcher_goal"] = goal
    raw, source = _ask(propose, NEEDS_SYSTEM, inp)
    if raw is None:
        raw, source = rule_needs(PROTOCOL, cov.table()), "rules"
    notes, gaps, evidence, claims = [], {}, {}, []
    n = len(cov.people)

    def claim(item, weeks, ev, verdict, kept, why):
        claims.append({"item": item, "weeks": weeks, "llm_evidence": ev, "verdict": verdict,
                       "kept_weeks": kept, "code_reason": why})

    for g in raw.get("gaps") or []:
        if not isinstance(g, dict) or g.get("item") not in ITEMS:
            notes.append(f"gap {g!r}: unknown item, removed")
            claim(str(g.get("item") if isinstance(g, dict) else g), [], "", "removed", [], "not a protocol item")
            continue
        item, ev = g["item"], str(g.get("evidence") or "").strip()
        asked = [w for w in (g.get("weeks") or []) if isinstance(w, int)]
        if not ev:
            notes.append(f"{item}: no evidence cited, removed")
            claim(item, asked, "", "removed", [], "no evidence cited")
            continue
        if item == "blood_pressure.daily" and not ethics_approved:
            notes.append("blood_pressure.daily: exploratory and needs ethics approval; removed")
            claim(item, asked, ev, "removed", [], "exploratory item; no ethics credential on the ledger")
            continue
        weeks = [w for w in asked if w in WEEKS]
        kept = [w for w in weeks if len(cov.missing(item, w)) >= GAP_MIN_MISSING * n]
        dropped = [w for w in weeks if w not in kept]
        if dropped:
            notes.append(f"{item}: weeks {dropped} are {GAP_MIN_MISSING:.0%}+ complete in our table; not requested")
        claim(item, asked, ev, "kept" if kept and not dropped and len(weeks) == len(asked) else
              ("narrowed" if kept else "removed"), kept,
              "table: " + ", ".join(f"w{w} {n - len(cov.missing(item, w))}/{n}" for w in weeks)
              + (f"; weeks {dropped} already held" if dropped else ""))
        if kept:
            gaps.setdefault(item, [])
            gaps[item] = sorted(set(gaps[item]) | set(kept))
            evidence[item] = ev[:200] + " [code: " + ", ".join(
                f"w{w} {n - len(cov.missing(item, w))}/{n}" for w in kept) + "]"
    for d in raw.get("do_not_request") or []:
        if isinstance(d, dict) and d.get("item") in gaps:
            notes.append(f"{d['item']} listed as both gap and do-not-request; kept as gap only where table shows it")
    purpose = raw.get("purpose")
    if purpose not in allowed_purposes:
        notes.append(f"purpose {purpose!r} not in mandate; using {allowed_purposes[0]}")
        purpose = allowed_purposes[0]
    try:
        budget = int(float(raw.get("budget_xrp")) * 1_000_000)
    except (TypeError, ValueError):
        budget = budget_cap_drops
    if not 0 < budget <= budget_cap_drops:
        notes.append(f"budget capped at {budget_cap_drops / 1e6:g} XRP")
        budget = budget_cap_drops
    cells: dict = {}
    for item, weeks in gaps.items():
        for w in weeks:
            for p in cov.missing(item, w):
                cells.setdefault(p, {}).setdefault(w, []).append(item)
    summary = str(raw.get("summary_for_participants") or "")[:300]
    final = {"gaps": gaps, "purpose": purpose, "budget_xrp": budget / 1e6, "people": len(cells),
             "cells": sum(len(v) for wk in cells.values() for v in wk.values())}
    verdict = "rejected" if not gaps else ("narrowed" if notes else "accepted")
    h = record(store, agent, "infer_needs", inp, raw, source, verdict, final, notes)
    return Needs(gaps, cells, purpose, budget, summary, evidence, notes, h, source, claims, raw, verdict)


def fill(w, lab_id: str, needs: Needs, cov: Coverage, people: dict, price_per_cell_drops: int,
         process=True) -> list[dict]:
    """One order per participant for all of their missing cells. Their agent decides what it
    may provide; the rest waits for the person or is blocked."""
    st, e = w.store, w.engine
    out = []
    for pid, weeks in sorted(needs.cells.items()):
        pa = people[pid]
        items = sorted({i for its in weeks.values() for i in its})
        last = max(weeks)
        d = pa.handle_request(lab_id, needs.purpose, items, last, price_per_cell_drops)
        if not d.ok:
            out.append({"person": pid, "status": d.status, "pending": d.pending, "reason": d.reason})
            continue
        granted_cells = {wk: [i for i in its if i in d.granted] for wk, its in weeks.items()}
        granted_cells = {wk: its for wk, its in granted_cells.items() if its}
        n_cells = sum(len(v) for v in granted_cells.values())
        rows = [r for wk, its in sorted(granted_cells.items()) for r in pa.vault.extract(its, wk, study=lab_id)]
        slot = f"{pid}|" + ",".join(f"w{wk}:{'+'.join(its)}" for wk, its in sorted(granted_cells.items()))
        req = OrderRequest(lab_id, pid, pid, "cohort.fill", slot, needs.purpose, sorted(d.granted),
                           n_cells * price_per_cell_drops, rows, d, settle="escrow")
        try:
            oid = e.place_order(req)
        except (BudgetExceeded, NeedsHumanApproval) as ex:
            st.log(lab_id, "stop", f"{pid}: {ex}")
            out.append({"person": pid, "status": "budget", "reason": str(ex)})
            continue
        out.append({"person": pid, "order_id": oid, "cells": granted_cells, "pending": d.pending})
    return out


def apply_deliveries(w, cov: Coverage, results: list[dict]):
    """Cells count as filled only once the order is delivered (payment validated, bundle opened)."""
    for r in results:
        oid = r.get("order_id")
        if oid and w.store.one("SELECT status FROM orders WHERE id=?", oid)["status"] == "delivered":
            for wk, its in r["cells"].items():
                cov.add(r["person"], wk, its)


def heatmap(w, cov: Coverage, lab_id: str) -> dict:
    """Primary pair per person-week: held, contributed (with tx), waiting, missing."""
    orders = w.store.q("SELECT o.id, o.seller_id, o.scope, o.status, p.tx_hash FROM orders o "
                       "LEFT JOIN payments p ON p.order_id=o.id WHERE o.buyer_id=? AND o.product_id='cohort.fill'",
                       lab_id)
    bought = {}
    for o in orders:
        slot = json.loads(o["scope"])["slot"]
        for part in slot.split("|", 1)[1].split(","):
            wk = int(part.split(":")[0][1:])
            bought[(o["seller_id"], wk)] = {"status": o["status"], "tx": o["tx_hash"]}
    waiting = {(r["person_id"], r["week"]) for r in w.store.q(
        "SELECT person_id, week FROM approval_requests WHERE buyer_id=? AND status='open'", lab_id)}
    open_people = {r["person_id"] for r in w.store.q(
        "SELECT person_id FROM approval_requests WHERE buyer_id=? AND status='open'", lab_id)}
    rows = []
    for p in cov.people:
        row = []
        for wk in WEEKS:
            b = bought.get((p, wk))
            if b and b["status"] == "delivered":
                row.append({"s": "contributed", "tx": b["tx"], "url": w.ledger.explorer_url(b["tx"]) if b["tx"] else None})
            elif all(cov.has(p, wk, i) for i in PRIMARY):
                row.append({"s": "held"})
            elif (p, wk) in waiting or (p in open_people and not b):
                row.append({"s": "waiting"})
            else:
                row.append({"s": "missing"})
        rows.append({"person": p, "cells": row})
    pairs = cov.complete_pairs()
    return {"weeks": WEEKS, "rows": rows, "complete_pairs": pairs, "total": len(cov.people) * len(WEEKS),
            "power": power(pairs)}
