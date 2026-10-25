"""Who sets the price: the market, inside bounds the owners set.

- Bounds. The seller's owner sets a floor (attrs["floor_mult"] x the rate card, default 0.7); the
  buyer's owner sets the budget, and the buyer's agent never goes above its budget per item.
- Reference price. Per data tier, the median of the last WINDOW settled prices (each as a ratio to the
  rate card, so one week of T1 and four weeks of T2 compare), with the 25th-75th percentile as the
  range. Every settled price is public on the ledger (the EscrowCreate amount); the index reads only
  those. With fewer than MIN_HISTORY trades the rate card is the seed.
- Asks. The seller's agent asks the reference times a scarcity factor from the shared offer book:
  open needs for the columns (demand) over listings that hold them (supply). Never under the floor.
- Bids. The buyer's agent opens at the low end of the range and raises toward its ceiling; its
  ceiling follows the reference (+20%) but stops at the owner's budget per item.

Sensitive tiers still go back to the owner: price never decides consent (policies.py does).
"""
from __future__ import annotations

from statistics import median

WINDOW = 20
MIN_HISTORY = 3
DEFAULT_FLOOR = 0.7
SCARCITY_SLOPE = 0.25
SCARCITY_RANGE = (0.85, 1.4)
DEMAND_WINDOW_H = 24


def _tier_key(columns, spec) -> str:
    return "+".join(sorted({spec(c)["tier"] for c in columns}))


def _pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


class PriceIndex:
    def __init__(self, quote, spec):
        self.quote, self.spec = quote, spec
        self.history: dict[str, list[dict]] = {}       # tier key -> [{ratio, price, tx}]
        self.posted: list[tuple[set, float]] = []       # (columns, hour posted): every need, as posted
        self.supply: dict[str, int] = {}               # column -> listings in the offer book

    # ----- the shared ledger's record of settled prices -----
    def record(self, columns, weeks: int, grade: str, price: int, tx: str | None = None) -> None:
        card = self.quote(columns, weeks, grade)
        self.history.setdefault(_tier_key(columns, self.spec), []).append(
            {"ratio": price / max(1, card), "price": price, "tx": tx})

    def reference(self, columns, weeks: int, grade: str) -> dict:
        card = self.quote(columns, weeks, grade)
        h = [x["ratio"] for x in self.history.get(_tier_key(columns, self.spec), [])[-WINDOW:]]
        if len(h) < MIN_HISTORY:
            return {"price": card, "low": int(card * 0.85), "high": card, "n": len(h), "source": "rate card (seed)",
                    "ratio": 1.0}
        m = median(h)
        return {"price": int(card * m), "low": int(card * _pct(h, 0.25)), "high": int(card * _pct(h, 0.75)),
                "n": len(h), "source": f"median of the last {len(h)} settled trades", "ratio": round(m, 3)}

    # ----- supply and demand, from the offer book and the open needs -----
    def set_supply(self, offers: list[dict]) -> None:
        self.supply = {}
        for o in offers:
            for c in o["dataset"].columns:
                self.supply[c] = self.supply.get(c, 0) + 1

    def post(self, columns, posted_h: float = 0.0) -> None:
        self.posted.append((set(columns), posted_h))

    def scarcity(self, columns, now_h: float | None = None) -> dict:
        """Demand: needs for these columns posted in the last DEMAND_WINDOW_H hours (all of them when no
        time is given); supply: listings that hold them."""
        cs = set(columns)
        d = sum(1 for cols, h in self.posted if cols & cs and (now_h is None or now_h - DEMAND_WINDOW_H < h <= now_h))
        s = max(1, min(self.supply.get(c, 0) for c in columns))
        f = min(max(1 + SCARCITY_SLOPE * (d / s - 1), SCARCITY_RANGE[0]), SCARCITY_RANGE[1])
        return {"demand": d, "supply": s, "factor": round(f, 3)}

    # ----- the two agents -----
    def ask(self, columns, weeks: int, grade: str, floor_mult: float | None, now_h: float | None = None) -> dict:
        ref = self.reference(columns, weeks, grade)
        sc = self.scarcity(columns, now_h)
        floor = int(self.quote(columns, weeks, grade) * (floor_mult or DEFAULT_FLOOR))
        ask = max(floor, int(ref["price"] * sc["factor"]))
        return {"ask": ask, "floor": floor, "reference": ref, "scarcity": sc,
                "why": f"reference {ref['price']} ({ref['source']}) x scarcity {sc['factor']} "
                       f"({sc['demand']} needs in the last day / {sc['supply']} listings); owner's floor {floor}"}

    def ceiling(self, columns, weeks: int, plan: dict) -> dict:
        ref = self.reference(columns, weeks, "A")
        cap = plan.get("budget_per_item_drops")
        want = max(plan.get("max_price_drops") or 0, ref["price"] * 6 // 5)
        c = min(cap, want) if cap else want
        return {"max_price_drops": c, "reference": ref,
                "why": f"20% above the grade A reference {ref['price']} ({ref['source']})"
                       + (f", capped by the owner's budget per item {cap}" if cap and cap < want else "")}


def negotiate(ask: int, ceiling: int, track: tuple[int, int], floor: int, opening: int, rounds: int = 4) -> dict:
    """The buyer opens at `opening` (low end of the reference range, never above its ceiling); the
    seller's agent concedes from its ask toward max(owner's floor, 90% of the ask, 95% on a shaky
    record). A deal is the first bid at or above the seller's standing price."""
    passed, failed = track
    floor = max(floor, int(ask * (0.95 if failed > passed else 0.90)))
    bid, counter, log = min(opening, ceiling, ask), ask, []
    for r in range(1, rounds + 1):
        log.append({"round": r, "bid": bid, "counter": counter})
        if bid >= counter:
            return {"deal": True, "price_drops": counter, "rounds": log, "floor": floor}
        stuck = counter == floor                 # the seller cannot move further
        counter = max(floor, counter - (counter - floor) // 2 - 1)
        # the buyer closes half the gap; a seller at its floor within the ceiling is taken as is
        bid = min(ceiling, counter if stuck else bid + (counter - bid) // 2 + 1)
        if bid >= counter:
            log.append({"round": r + 1, "bid": bid, "counter": counter})
            return {"deal": True, "price_drops": counter, "rounds": log, "floor": floor}
    return {"deal": False, "price_drops": None, "rounds": log, "floor": floor,
            "why": f"ceiling {ceiling} below the seller's floor {floor}" if ceiling < floor else "no meeting point"}
