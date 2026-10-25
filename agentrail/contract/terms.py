"""Per-column requirements, the negotiation between the buyer's and the provider's agents, and the
data contract they settle on.

The buyer's agent states, per column: required or nice-to-have, minimum completeness per window,
unit, the windows it wants, drift tolerance, and acceptable substitutes (the same measure from
another source). The provider's agent answers with its column profile (statistics only). Both
agents then match requirement to profile column by column and repair what does not fit, in a fixed
order and without humans:

  1. the column as asked, if its forecast completeness holds over the windows asked;
  2. a substitute column from the buyer's list, for the windows where the original falls short;
  3. a shorter period: only the windows whose forecast meets the minimum (never below `min_windows`);
  4. a lower quality tier with its own fixed price, if the buyer allows it.

Imputation is never offered. Price is a fixed quote per tier, never haggled. A proposal that needs a
column outside the provider's consent, a sensitive column, or a new purpose stops and goes to the
owner (`needs_owner`); nothing else reaches a human. The settled contract (columns, sources, units,
thresholds, windows, tier, purpose code) is hashed; the hash goes into the EscrowCreate memo and
into every bundle delivered under it, so the delivery check and the payment refer to the same terms.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field

# Fixed quote per tier: minimum completeness per window the provider commits to, and the share of the
# provider's base price per window. The buyer cannot haggle; it can only pick a tier it allows.
# A valid week of daily wearable data is commonly taken as 4-5 of 7 days; tier A asks 5, B 4, C 3.
TIERS = {"A": {"min_completeness": 0.70, "price_share": 1.0},
         "B": {"min_completeness": 0.55, "price_share": 0.8},
         "C": {"min_completeness": 0.40, "price_share": 0.6}}


def canonical(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class ColumnReq:
    column: str
    unit: str
    must: bool = True                     # must-have vs nice-to-have
    drift_sd: float = 3.0                 # delivered window mean may move this many profile SDs
    substitutes: list[dict] = field(default_factory=list)   # [{"column", "source"}], same unit
    sensitive: bool = False


@dataclass
class Requirements:
    buyer: str
    purpose: str                          # purpose code (DUO terms are attached by the caller)
    duo: list[str]
    columns: list[ColumnReq]
    windows: list[int]
    tier: str = "A"                       # tier asked for
    lowest_tier: str = "B"                # lowest tier the buyer accepts
    min_windows: int = 3

    def hash(self) -> str:
        return hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()


def _tiers_from(asked: str, lowest: str) -> list[str]:
    order = list(TIERS)
    return order[order.index(asked): order.index(lowest) + 1]


def _forecast_by_window(col_profile: dict, windows: list[int]) -> dict:
    """Expected completeness for each asked window: observed if the window is past, else the forecast."""
    seen = {int(k): v for k, v in col_profile["completeness_by_window"].items()}
    last = max(seen) if seen else 0
    fc = col_profile["forecast"]["completeness"]
    out = {}
    for wnum in windows:
        if wnum in seen:
            out[wnum] = {"mean": seen[wnum], "lo": seen[wnum], "observed": True}
        else:
            step = min(len(fc), max(1, wnum - last))
            f = fc[step - 1]
            out[wnum] = {"mean": f["mean"], "lo": f["lo"], "observed": False}
    return out


CONFIDENCE = 0.75         # a window is offered only if it meets the minimum with this probability


def meet_probability(p: float, minimum: float, slots: int = 7) -> float:
    """P(at least ceil(minimum * slots) of `slots` filled) when each slot is filled with probability p."""
    need = math.ceil(minimum * slots - 1e-9)
    return sum(math.comb(slots, k) * p ** k * (1 - p) ** (slots - k) for k in range(need, slots + 1))


def _fits(exp: dict, minimum: float) -> bool:
    """Judged halfway between the forecast and its lower band: a profile that looks good on four windows
    is partly luck, and taking the plain forecast would overpromise (measured in measure.py)."""
    if exp["mean"] is None:
        return False
    return meet_probability((exp["mean"] + exp["lo"]) / 2, minimum) >= CONFIDENCE


@dataclass
class Contract:
    buyer: str
    provider: str
    purpose: str
    duo: list[str]
    tier: str
    price_drops_per_window: int
    terms: list[dict]                     # [{column, source, unit, windows, min_completeness, drift_sd, ref}]
    windows: list[int]
    requirements_hash: str
    holder: str = ""                      # the provider's holder key for this buyer: exports must be made for it
    status: str = "agreed"                # agreed | needs_owner | no_deal
    reason: str = ""

    def body(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k not in ("status", "reason")}

    @property
    def hash(self) -> str:
        return hashlib.sha256(canonical(self.body()).encode()).hexdigest()


def negotiate(req: Requirements, provider: str, profile: dict, base_price_drops: int,
              owner_allows: set[str] | None = None, sensitive_ok: bool = False, holder: str = "") -> tuple[Contract, list[dict]]:
    """Both agents' moves as a transcript of messages; returns the contract and the transcript.
    owner_allows: the columns the provider's owner consented to share for this purpose (None = all)."""
    cols = profile["columns"]
    log = [{"from": req.buyer, "to": provider, "kind": "requirements", "hash": req.hash(),
            "columns": [c.column for c in req.columns], "windows": req.windows, "tier": req.tier}]
    say = lambda frm, kind, **k: log.append({"from": frm, "to": provider if frm == req.buyer else req.buyer,
                                             "kind": kind, **k})
    say(provider, "profile", columns={c: {"completeness": p["completeness"], "behaviour": p["behaviour"],
                                         "unit": p["unit"], "source": p["source"]} for c, p in cols.items()})

    def needs_owner(why):
        say(provider, "needs_owner", reason=why)
        return Contract(req.buyer, provider, req.purpose, req.duo, req.tier, 0, [], [], req.hash(), holder,
                        "needs_owner", why), log

    for tier in _tiers_from(req.tier, req.lowest_tier):
        minimum = TIERS[tier]["min_completeness"]
        terms, windows_ok, failed = [], set(req.windows), None
        for c in req.columns:
            plan = []
            p = cols.get(c.column)
            if p is not None and p["unit"] != c.unit:
                say(provider, "unit_mismatch", column=c.column, offered=p["unit"], asked=c.unit)
                p = None
            if c.sensitive and not sensitive_ok:
                return needs_owner(f"{c.column} is a sensitive column")
            if p is not None and owner_allows is not None and c.column not in owner_allows:
                return needs_owner(f"{c.column} is outside the owner's consent for {req.purpose}")
            exp = _forecast_by_window(p, req.windows) if p else {}
            short = [w for w in req.windows if not (p and _fits(exp[w], minimum))]
            if p and not short:
                plan.append({"column": c.column, "source": p["source"], "windows": list(req.windows)})
            else:
                if p:
                    plan.append({"column": c.column, "source": p["source"],
                                 "windows": [w for w in req.windows if w not in short]})
                    say(provider, "falls_short", column=c.column, windows=short,
                        behaviour=p["behaviour"]["completeness"],
                        forecast={w: exp[w]["mean"] for w in short})
                for sub in c.substitutes:            # 2. substitute column for the short windows
                    sp = cols.get(sub["column"])
                    if not sp or sp["unit"] != c.unit or sp["source"] != sub.get("source", sp["source"]):
                        continue
                    if owner_allows is not None and sub["column"] not in owner_allows:
                        return needs_owner(f"substitute {sub['column']} is outside the owner's consent")
                    se = _forecast_by_window(sp, short)
                    cover = [w for w in short if _fits(se[w], minimum)]
                    if cover:
                        plan.append({"column": sub["column"], "source": sp["source"], "windows": cover,
                                     "substitutes": c.column})
                        say(req.buyer, "accept_substitute", column=c.column, substitute=sub["column"],
                            source=sp["source"], windows=cover)
                        short = [w for w in short if w not in cover]
                if short:
                    if c.must:
                        windows_ok -= set(short)
                    else:
                        say(req.buyer, "drop_optional", column=c.column, windows=short)
            for t in plan:
                if t["windows"]:
                    terms.append({"column": t["column"], "source": t["source"], "unit": c.unit,
                                  "min_completeness": minimum, "drift_sd": c.drift_sd,
                                  "ref": t.get("substitutes", t["column"]), "windows": t["windows"]})
        windows = sorted(windows_ok)
        if len(windows) < req.min_windows:              # 3. a shorter period, but not too short
            say(req.buyer, "period_too_short", tier=tier, windows=windows, min_windows=req.min_windows)
            failed = True
        if not failed:
            if windows != sorted(req.windows):
                say(req.buyer, "shorter_period", windows=windows, dropped=sorted(set(req.windows) - set(windows)))
            terms = [{**t, "windows": [w for w in t["windows"] if w in windows]} for t in terms]
            terms = [t for t in terms if t["windows"]]
            price = int(base_price_drops * TIERS[tier]["price_share"])
            k = Contract(req.buyer, provider, req.purpose, req.duo, tier, price, terms, windows, req.hash(), holder)
            say(req.buyer, "agree", tier=tier, windows=windows, price_drops_per_window=price, contract=k.hash)
            say(provider, "agree", contract=k.hash)
            return k, log
        if tier != _tiers_from(req.tier, req.lowest_tier)[-1]:   # 4. lower tier, fixed quote
            say(req.buyer, "offer_lower_tier", tier=list(TIERS)[list(TIERS).index(tier) + 1])
    say(req.buyer, "no_deal", reason="no tier the buyer accepts can be met")
    return Contract(req.buyer, provider, req.purpose, req.duo, req.tier, 0, [], [], req.hash(), holder, "no_deal",
                    "no tier the buyer accepts can be met"), log
