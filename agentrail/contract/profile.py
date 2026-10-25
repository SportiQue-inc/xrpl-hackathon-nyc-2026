"""Column profile, computed by the provider's agent on its own device. Only these statistics leave;
no row does.

A column is a time series of values, one slot per sampling period (a day for wearable or survey
columns, an episode slot for robot sensors). Rows are grouped into windows (a study week, a run
batch). Per column the profile reports type, unit, source, sampling rate, completeness, the value
distribution, and how the column behaves over time: whether completeness and quality are holding,
declining or recovering, a short-horizon forecast of both with a band, the longest gap, and
day-of-cycle seasonality of missingness. This describes data behaviour, nothing about the person.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

TREND_EPS = 0.03          # slope per window below which a column counts as holding


@dataclass
class ColumnMeta:
    name: str
    source: str           # issuer of the records (device vendor, survey app, clinic, robot fleet)
    unit: str
    field: str | None = None      # numeric field inside a structured value, e.g. "minutes"
    lo: float | None = None       # physically possible range in this unit (quality = share inside)
    hi: float | None = None
    slots_per_window: int = 7


def _num(v, field):
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get(field) if field else next(iter(v.values()), None)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _slope(ys: list[float]) -> float:
    n = len(ys)
    if n < 2:
        return 0.0
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (y - my) for i, y in enumerate(ys)) / den


def _quantile(xs: list[float], q: float) -> float:
    s = sorted(xs)
    if not s:
        return float("nan")
    k = (len(s) - 1) * q
    f = math.floor(k)
    return s[f] if f == len(s) - 1 else s[f] + (s[f + 1] - s[f]) * (k - f)


def behaviour(series: list[float]) -> str:
    """holding | declining | recovering, from the last windows of a per-window series."""
    if len(series) < 3:
        return "holding"
    half = len(series) // 2
    early, late = _slope(series[:half + 1]), _slope(series[half:])
    whole = _slope(series)
    if whole <= -TREND_EPS and late <= -TREND_EPS / 2:
        return "declining"
    if early <= -TREND_EPS and late >= TREND_EPS:
        return "recovering"
    if whole >= TREND_EPS:
        return "recovering" if min(series) < max(series) - 0.15 else "holding"
    return "holding"


def forecast(series: list[float], horizon: int = 4) -> list[dict]:
    """Linear trend over the last windows, clipped to [0, 1], with a band from the residual spread."""
    n = len(series)
    if n == 0:
        return [{"step": h + 1, "mean": None, "lo": None, "hi": None} for h in range(horizon)]
    tail = series[-min(n, 6):]
    b = _slope(tail)
    a = sum(tail) / len(tail) - b * (len(tail) - 1) / 2
    res = [y - (a + b * i) for i, y in enumerate(tail)]
    sd = math.sqrt(sum(r * r for r in res) / max(1, len(tail) - 2)) if len(tail) > 2 else 0.05
    sxx = sum((i - (len(tail) - 1) / 2) ** 2 for i in range(len(tail))) or 1
    if abs(b) < 2 * sd / math.sqrt(sxx) and behaviour(series) == "holding":
        # no trend the data can support: forecast the level, with the spread of the windows around it
        b, a = 0.0, sum(tail) / len(tail)
        sd = math.sqrt(sum((y - a) ** 2 for y in tail) / max(1, len(tail) - 1)) if len(tail) > 1 else 0.05
    out = []
    for h in range(1, horizon + 1):
        m = a + b * (len(tail) - 1 + h)
        band = 1.64 * max(sd, 0.02) * math.sqrt(1 + h / len(tail))
        clip = lambda x: round(min(1.0, max(0.0, x)), 3)
        out.append({"step": h, "mean": clip(m), "lo": clip(m - band), "hi": clip(m + band)})
    return out


def profile_column(meta: ColumnMeta, rows: list[dict], window_of, horizon: int = 4) -> dict:
    """rows: the provider's own rows (each with a time key); window_of(row) -> window number."""
    windows = sorted({window_of(r) for r in rows})
    per_w, qual_w, vals, present = {}, {}, [], []
    for wnum in windows:
        rs = [r for r in rows if window_of(r) == wnum]
        got = [_num(r.get(meta.name), meta.field) for r in rs]
        have = [v for v in got if v is not None]
        per_w[wnum] = round(len(have) / meta.slots_per_window, 3)
        ok = [v for v in have if (meta.lo is None or v >= meta.lo) and (meta.hi is None or v <= meta.hi)]
        qual_w[wnum] = round(len(ok) / len(have), 3) if have else None
        vals += have
        present += [v is not None for v in got] + [False] * max(0, meta.slots_per_window - len(rs))
    gap = run = 0
    for p in present:
        run = 0 if p else run + 1
        gap = max(gap, run)
    comp = [per_w[x] for x in windows]
    qual = [q for q in (qual_w[x] for x in windows) if q is not None]
    # seasonality of missingness: completeness by position inside the window (e.g. weekday)
    pos = [[] for _ in range(meta.slots_per_window)]
    for i, p in enumerate(present):
        pos[i % meta.slots_per_window].append(p)
    by_pos = [round(sum(x) / len(x), 2) if x else None for x in pos]
    spread = (max(v for v in by_pos if v is not None) - min(v for v in by_pos if v is not None)) if any(
        v is not None for v in by_pos) else 0
    mean = sum(vals) / len(vals) if vals else None
    sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / max(1, len(vals) - 1)) if len(vals) > 1 else 0.0
    return {
        "column": meta.name, "type": "number", "unit": meta.unit, "source": meta.source,
        "sampling": f"{meta.slots_per_window} slots per window",
        "windows": windows,
        "completeness": round(sum(present) / len(present), 3) if present else 0.0,
        "completeness_by_window": per_w, "quality_by_window": qual_w,
        "distribution": None if not vals else {
            "n": len(vals), "mean": round(mean, 3), "sd": round(sd, 3), "min": min(vals),
            "p10": round(_quantile(vals, .1), 3), "median": round(_quantile(vals, .5), 3),
            "p90": round(_quantile(vals, .9), 3), "max": max(vals)},
        "behaviour": {"completeness": behaviour(comp), "quality": behaviour(qual) if qual else "holding"},
        "forecast": {"completeness": forecast(comp, horizon), "quality": forecast(qual, horizon)},
        "longest_gap": gap,
        "seasonality": {"completeness_by_slot": by_pos, "pattern": "weekly" if spread >= 0.4 else "none"},
    }


def profile(columns: list[ColumnMeta], rows: list[dict], window_of, horizon: int = 4) -> dict:
    """The profile a provider's agent shares: statistics per column, no rows."""
    return {"columns": {m.name: profile_column(m, rows, window_of, horizon) for m in columns},
            "rows_shared": 0}
