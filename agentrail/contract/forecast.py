"""Delivery reliability forecast: the probability that one provider's contribution for one window
passes its contract's fitness check on time.

It forecasts data delivery, never anything about a person's health. Allowed inputs are delivery
behaviour only (ALLOWED). Decline, pause or withdrawal history, health values and demographics are
not inputs: `features` refuses any other key, and tests check that changing them changes nothing.

Uses: ranking providers by expected usable windows per XRP (requests and replacements), and early
warnings to the buyer. It never changes what anyone is paid: price per tier and the 80/20 split are
the same for everyone.

Model: logistic regression (plain Python, L2), so every weight can be read. Trained on synthetic
histories from `market.py`; calibration is reported as a Brier score and a reliability table.
"""
from __future__ import annotations

import math
import random

ALLOWED = ("completeness_margin", "declining", "sync_regularity", "source_pass_rate",
           "round_pass_rate", "drift_so_far")
BANNED = ("declined", "paused", "withdrew", "withdrawal", "age", "sex", "gender", "race", "zip", "postal",
          "diagnosis", "heart_rate", "sleep", "health")


def features(**k) -> list[float]:
    bad = [x for x in k if x not in ALLOWED]
    if bad:
        raise ValueError(f"not an allowed forecast input: {', '.join(bad)}")
    return [float(k.get(n, 0.0)) for n in ALLOWED]


def _sig(z: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


class Model:
    def __init__(self, weights: list[float] | None = None, bias: float = 0.0):
        self.w = weights or [0.0] * len(ALLOWED)
        self.b = bias

    def p(self, x: list[float]) -> float:
        return _sig(self.b + sum(a * b for a, b in zip(self.w, x)))

    def fit(self, X: list[list[float]], y: list[int], epochs: int = 400, lr: float = 0.5, l2: float = 1e-3):
        n = len(X)
        for _ in range(epochs):
            gw, gb = [0.0] * len(self.w), 0.0
            for x, t in zip(X, y):
                e = self.p(x) - t
                gb += e
                for i, v in enumerate(x):
                    gw[i] += e * v
            self.b -= lr * gb / n
            self.w = [w - lr * (g / n + l2 * w) for w, g in zip(self.w, gw)]
        return self

    def explain(self) -> dict:
        return {"bias": round(self.b, 3), **{n: round(w, 3) for n, w in zip(ALLOWED, self.w)}}


def brier(ps: list[float], ys: list[int]) -> float:
    return round(sum((p - y) ** 2 for p, y in zip(ps, ys)) / len(ys), 4)


def ece(ps: list[float], ys: list[int], bins: int = 10) -> float:
    """Expected calibration error: the n-weighted gap between predicted and observed per bin."""
    t = reliability(ps, ys, bins)
    return round(sum(r["n"] * abs(r["predicted"] - r["observed"]) for r in t) / len(ys), 4)


def reliability(ps: list[float], ys: list[int], bins: int = 10) -> list[dict]:
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, p in enumerate(ps) if lo <= p < hi or (b == bins - 1 and p == 1.0)]
        if idx:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(idx),
                        "predicted": round(sum(ps[i] for i in idx) / len(idx), 3),
                        "observed": round(sum(ys[i] for i in idx) / len(idx), 3)})
    return out


def reliability_svg(table: list[dict], title: str = "Delivery reliability forecast: calibration",
                    before: list[dict] | None = None) -> str:
    W, H, P = 380, 380, 44
    sx = lambda v: P + v * (W - 2 * P)
    sy = lambda v: H - P - v * (H - 2 * P)

    def series(t, color, dash=""):
        pts = " ".join(f"{sx(r['predicted']):.1f},{sy(r['observed']):.1f}" for r in t)
        dots = "".join(f'<circle cx="{sx(r["predicted"]):.1f}" cy="{sy(r["observed"]):.1f}" '
                       f'r="{2 + min(6, r["n"] ** 0.5 / 3):.1f}" fill="{color}"><title>{r["bin"]}: n={r["n"]}, '
                       f'predicted {r["predicted"]}, observed {r["observed"]}</title></circle>' for r in t)
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.5" {dash}/>{dots}'

    ticks = "".join(f'<text x="{sx(v):.0f}" y="{H - P + 16}" font-size="10" text-anchor="middle">{v:.1f}</text>'
                    f'<text x="{P - 8}" y="{sy(v) + 3:.0f}" font-size="10" text-anchor="end">{v:.1f}</text>'
                    for v in (0, .25, .5, .75, 1))
    legend = (f'<rect x="{P + 8}" y="{P + 8}" width="10" height="3" fill="#2a6fdb"/>'
              f'<text x="{P + 24}" y="{P + 13}" font-size="10">calibrated</text>')
    if before:
        legend += (f'<rect x="{P + 8}" y="{P + 22}" width="10" height="3" fill="#d9822b"/>'
                   f'<text x="{P + 24}" y="{P + 27}" font-size="10">before calibration</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif">'
            f'<rect width="{W}" height="{H}" fill="#fff"/>'
            f'<text x="{W / 2}" y="18" font-size="12" text-anchor="middle">{title}</text>'
            f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(1)}" y2="{sy(1)}" stroke="#bbb" stroke-dasharray="4 3"/>'
            f'<rect x="{P}" y="{P}" width="{W - 2 * P}" height="{H - 2 * P}" fill="none" stroke="#888"/>'
            + (series(before, "#d9822b", 'stroke-dasharray="5 3"') if before else "") + series(table, "#2a6fdb")
            + ticks + legend
            + f'<text x="{W / 2}" y="{H - 8}" font-size="11" text-anchor="middle">forecast probability of passing</text>'
            f'<text x="12" y="{H / 2}" font-size="11" text-anchor="middle" transform="rotate(-90 12 {H / 2})">'
            f'observed pass rate</text></svg>')


def split(X, y, seed=5, test=0.3):
    idx = list(range(len(X)))
    random.Random(seed).shuffle(idx)
    k = int(len(idx) * (1 - test))
    tr, te = idx[:k], idx[k:]
    return [X[i] for i in tr], [y[i] for i in tr], [X[i] for i in te], [y[i] for i in te]


class Isotonic:
    """Monotone map from raw score to probability (pool-adjacent-violators), fit on held-out data."""

    def __init__(self):
        self.x, self.y = [0.0, 1.0], [0.0, 1.0]

    def fit(self, ps: list[float], ys: list[int]):
        blocks = []                                   # [sum_y, n, min_x, max_x]
        for p, y in sorted(zip(ps, ys)):
            blocks.append([float(y), 1, p, p])
            while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] >= blocks[-1][0] / blocks[-1][1]:
                b = blocks.pop()
                a = blocks[-1]
                a[0], a[1], a[3] = a[0] + b[0], a[1] + b[1], b[3]
        self.x = [(b[2] + b[3]) / 2 for b in blocks]
        self.y = [b[0] / b[1] for b in blocks]
        return self

    def __call__(self, p: float) -> float:
        xs, ys = self.x, self.y
        if p <= xs[0]:
            return ys[0]
        if p >= xs[-1]:
            return ys[-1]
        for i in range(1, len(xs)):
            if p <= xs[i]:
                t = (p - xs[i - 1]) / ((xs[i] - xs[i - 1]) or 1)
                return ys[i - 1] + t * (ys[i] - ys[i - 1])
        return ys[-1]


class Platt:
    """Logistic recalibration of the raw score's log-odds."""

    def fit(self, ps: list[float], ys: list[int]):
        self.m = Model([1.0], 0.0).fit([[_logit(p)] for p in ps], ys, epochs=600, lr=0.3, l2=0.0)
        return self

    def __call__(self, p: float) -> float:
        return self.m.p([_logit(p)])


def _logit(p: float) -> float:
    p = min(1 - 1e-6, max(1e-6, p))
    return math.log(p / (1 - p))


class Calibrated(Model):
    """The logistic model with a monotone calibration map on top; the weights stay readable."""

    def __init__(self, base: Model, cal):
        super().__init__(base.w, base.b)
        self.cal = cal

    def p(self, x: list[float]) -> float:
        return self.cal(super().p(x))
