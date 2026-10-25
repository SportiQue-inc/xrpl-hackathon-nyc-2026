"""Synthetic providers for the data-contract layer: columns that hold, decline or recover over time,
device sync metadata, and bad records that start partway through a round. Everything is generated
from a seed; nothing here is real data.

Columns (health example; the same machinery runs on robot-sensor columns):
  sleep_minutes   wearable A, min/day   (vendor B exports hours; its normalization step converts)
  resting_hr      chest band A, bpm
  resting_hr_b    wrist device B, bpm   (acceptable substitute for resting_hr)

Faults, each from a given window on:
  wrong_source     exported through an app no registry accepts
  wrong_period     an earlier window's export sent again as this window
  different_person an export the issuer made for another holder
  wrong_unit       hours delivered as min/day (normalization step claims factor 1)
  duplicate        a second account replaying another provider's series
  drift            sensor replaced, values shifted
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .profile import ColumnMeta

SLOTS = 7
HISTORY = [1, 2, 3, 4]          # windows before the round: what the profile is computed from
ROUND = [5, 6, 7, 8]            # windows the buyer asks for

COLUMNS = {
    "sleep_minutes": ColumnMeta("sleep_minutes", "wearable_a", "min/day", None, 120, 900, SLOTS),
    "resting_hr": ColumnMeta("resting_hr", "chest_band_a", "bpm", None, 30, 140, SLOTS),
    "resting_hr_b": ColumnMeta("resting_hr_b", "wrist_device_b", "bpm", None, 30, 140, SLOTS),
}
MEANS = {"sleep_minutes": (420, 45), "resting_hr": (62, 6), "resting_hr_b": (63, 6)}
ITEM_OF = {"sleep_minutes": "sleep.daily", "resting_hr": "heart_rate.daily", "resting_hr_b": "heart_rate.daily"}
ISSUERS = ["wearable_a", "wearable_b", "chest_band_a", "wrist_device_b"]
FRAUD = {"different_person", "duplicate"}
FAULTS = ["wrong_source", "wrong_period", "different_person", "wrong_unit", "duplicate", "drift"]


@dataclass
class ColSim:
    source: str
    base: float                  # completeness at the start
    slope: float = 0.0           # change per window (declining < 0)
    turn: int | None = None      # window where a decline turns into recovery
    native_unit: str = "min/day"


@dataclass
class Provider:
    id: str
    price_drops: int             # base price per window (tier A); tiers take a fixed share of it
    sync: float                  # share of days the device synced on schedule (metadata, not health)
    cols: dict = field(default_factory=dict)
    faults: dict = field(default_factory=dict)        # window -> fault code
    seed: int = 0
    key: str = ""                # random stream name (defaults to the id)

    def completeness(self, col: str, wnum: int) -> float:
        c = self.cols[col]
        k = wnum - 1
        if c.turn and wnum > c.turn:
            k = (c.turn - 1) - (wnum - c.turn)
        return max(0.0, min(1.0, c.base + c.slope * k))

    def native(self, col: str, wnum: int, value_offset: float = 0.0) -> list:
        """Native values for one window, one slot per day (None = no record that day)."""
        c = self.cols[col]
        rng = random.Random(f"{self.seed}|{self.key or self.id}|{col}|{wnum}")
        mu, sd = MEANS[col]
        out = []
        for _ in range(SLOTS):
            if rng.random() < self.completeness(col, wnum) * (0.8 + 0.2 * self.sync):
                v = rng.gauss(mu + value_offset, sd)
                out.append(round(v / 60, 2) if c.native_unit == "h/day" else round(v))
            else:
                out.append(None)
        return out

    def factor(self, col: str) -> float:
        return 60.0 if self.cols[col].native_unit == "h/day" else 1.0

    def history_rows(self) -> list[dict]:
        rows = []
        for wnum in HISTORY:
            per = {c: self.native(c, wnum) for c in self.cols}
            for i in range(SLOTS):
                r = {"slot": (wnum - 1) * SLOTS + i + 1}
                for c, vals in per.items():
                    v = vals[i]
                    r[c] = None if v is None else round(v * self.factor(c), 3)
                rows.append(r)
        return rows


def window_of(row: dict) -> int:
    return (row["slot"] - 1) // SLOTS + 1


def slots_for_window(wnum: int) -> tuple[int, int]:
    return (wnum - 1) * SLOTS + 1, wnum * SLOTS


def make_market(n: int, seed: int = 11, fault_rate: float = 0.25, ids: list[str] | None = None) -> list[Provider]:
    """n providers. Cheaper ones skew towards irregular sync and faults (a plausible market, not a
    measured one). About a third have a declining column; some of those recover."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        pid = ids[i] if ids else f"prov-{i:03d}"
        sync = round(rng.uniform(0.35, 1.0), 2)
        price = int(40_000 + 60_000 * (0.5 * sync + 0.5 * rng.random()))
        vendor_b = rng.random() < 0.3
        cols = {"sleep_minutes": ColSim("wearable_b" if vendor_b else "wearable_a", rng.uniform(0.75, 1.0),
                                        native_unit="h/day" if vendor_b else "min/day"),
                "resting_hr": ColSim("chest_band_a", rng.uniform(0.7, 1.0), native_unit="bpm")}
        if rng.random() < 0.6:
            cols["resting_hr_b"] = ColSim("wrist_device_b", rng.uniform(0.85, 1.0), native_unit="bpm")
        r = rng.random()
        if r < 0.3:
            col = rng.choice(["sleep_minutes", "resting_hr"])
            cols[col].slope = -rng.uniform(0.08, 0.18)
            if rng.random() < 0.3:
                cols[col].turn = rng.choice([4, 5, 6])
        p = Provider(pid, price, sync, cols, seed=seed)
        if rng.random() < fault_rate * (1.4 - sync):
            p.faults[rng.choice(ROUND)] = rng.choice(FAULTS)
        out.append(p)
    return out


def scripted_decliner(pid: str = "prov-decline", seed: int = 3) -> Provider:
    """The negotiation example: the chest band's completeness falls week after week, the same person
    also wears device B, which holds, and sleep slips slowly. As asked (resting HR from the chest band
    for four windows) the first delivery fails; negotiated (device B for resting HR, two windows) it
    passes."""
    return Provider(pid, 50_000, 0.95, {
        "sleep_minutes": ColSim("wearable_a", 1.0, slope=-0.03),
        "resting_hr": ColSim("chest_band_a", 1.0, slope=-0.12),
        "resting_hr_b": ColSim("wrist_device_b", 0.97, native_unit="bpm")}, seed=seed, key="prov-decline")
