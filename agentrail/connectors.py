"""Data connectors: read the holder's own store and export rows for a granted
scope. Everything here is synthetic and deterministic."""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Product:
    id: str
    seller_id: str
    title: str
    domain: str
    fields: list[str]
    scenarios: dict[str, int]          # scenario -> number of episodes
    price_drops: int
    licence: dict
    missing_rate: float = 0.0          # used to generate the sample
    duplicate_rate: float = 0.0
    kinds: dict = field(default_factory=dict)   # private ground truth: seller field -> what it really is
    licence_text: str = ""                      # what the buyer reads

    def kind(self, f: str) -> str:
        return self.kinds.get(f, f)

    def public(self) -> dict:
        """What a buyer agent sees before paying: description only, no raw rows."""
        return {"id": self.id, "seller": self.seller_id, "title": self.title, "domain": self.domain,
                "fields": self.fields, "scenarios": self.scenarios,
                "price_xrp": self.price_drops / 1e6, "licence_text": self.licence_text}


def synth_value(kind: str, rng: random.Random):
    """Typed synthetic values, so a sample can tell a LiDAR scan from a depth image."""
    if kind == "lidar":
        return {"points": rng.randint(20000, 60000), "range_m": round(rng.uniform(15, 40), 1), "frame": "xyz"}
    if kind == "imu":
        return [round(rng.uniform(-2, 2), 3) for _ in range(6)]
    if kind == "wheel_odometry":
        return {"v_mps": round(rng.uniform(0, 2), 2), "w_radps": round(rng.uniform(-1, 1), 2)}
    if kind == "depth":
        return {"width": 640, "height": 480, "range_m": round(rng.uniform(0.3, 6), 2)}
    if kind == "camera_rgb":
        return {"width": 1280, "height": 720, "encoding": "jpeg"}
    return round(rng.uniform(0, 1), 3)


class RoboticsConnector:
    """An organization's own episode store (robot runs)."""

    def __init__(self, products: list[Product]):
        self.products = {p.id: p for p in products}

    def _episodes(self, p: Product, fields: list[str], n_per_scenario: int | None = None):
        rng = random.Random(p.id)
        rows = []
        for scen, n in p.scenarios.items():
            for i in range(n if n_per_scenario is None else min(n, n_per_scenario)):
                row = {"episode": f"{p.id}-{scen}-{i:03d}", "scenario": scen}
                for f in fields:
                    k = p.kind(f)
                    if k == "raw_video":
                        row[f] = f"video://{p.id}/{scen}/{i}"
                    elif rng.random() < p.missing_rate:
                        row[f] = None
                    else:
                        row[f] = synth_value(k, rng)
                rows.append(row)
        dup = int(len(rows) * p.duplicate_rate)
        return rows + [dict(r) for r in rows[:dup]]

    def sample(self, product_id: str) -> list[dict]:
        p = self.products[product_id]
        return self._episodes(p, [f for f in p.fields if p.kind(f) != "raw_video"], n_per_scenario=10)

    def extract(self, product_id: str, fields: list[str]) -> list[dict]:
        return self._episodes(self.products[product_id], fields)


@dataclass
class Person:
    id: str
    label: str
    weeks_available: int = 8
    data: dict = field(default_factory=dict)


class WearableSource:
    """The person's wearable account (synthetic). Exported with the person's own access right."""
    name, items = "wearable", ["sleep.daily", "activity.daily", "heart_rate.daily"]

    def read(self, pid: str, item: str, day: int, rng: random.Random):
        if item == "sleep.daily":
            return {"minutes": rng.randint(300, 480), "efficiency": round(rng.uniform(.7, .95), 2)}
        if item == "activity.daily":
            return {"steps": rng.randint(2000, 12000)}
        return {"resting_bpm": rng.randint(52, 78), "hrv_ms": rng.randint(25, 90)}


class SurveySource:
    """Weekly fatigue survey kept in the person's own survey app."""
    name, items = "survey_app", ["fatigue.survey"]

    def read(self, pid, item, day, rng):
        return {"score_0_10": rng.randint(1, 8)} if day % 7 == 0 else None


class HospitalExportSource:
    """Clinic visit records, exported on the patient's request in the clinic's own format
    (variable names as in public sleep-study data dictionaries). The clinic charges a small
    export fee, paid by the person's agent."""
    name, items = "clinic_export", ["blood_pressure.daily"]
    native = {"blood_pressure.daily": ("SYSBP", "DIABP")}
    export_fee_drops = 100_000

    def read(self, pid, item, day, rng):
        return {"SYSBP": rng.randint(105, 140), "DIABP": rng.randint(65, 90)} if day % 7 == 3 else None


class PersonalVaultConnector:
    """One person's own data, gathered from their sources and joined on a time axis.
    What leaves the vault is only the requested items and weeks, under a study-specific
    pseudonym, with dates shifted per study."""

    ITEMS = ["sleep.daily", "activity.daily", "heart_rate.daily", "fatigue.survey", "blood_pressure.daily"]

    def __init__(self, person: Person, sources=None):
        self.person = person
        self.sources = sources or [WearableSource(), SurveySource(), HospitalExportSource()]
        self.by_item = {i: src for src in self.sources for i in src.items}

    def pseudonym(self, study: str) -> str:
        import hashlib
        return "S-" + hashlib.sha256(f"{study}|{self.person.id}".encode()).hexdigest()[:8]

    def day_shift(self, study: str) -> int:
        import hashlib
        return int(hashlib.sha256(f"shift|{study}|{self.person.id}".encode()).hexdigest(), 16) % 90 + 30

    def timeline(self, weeks: list[int]) -> dict:
        """Which items each source holds per week (no values): what the person's agent can offer."""
        out = {}
        for wk in weeks:
            out[wk] = {}
            for item in self.ITEMS:
                rng = random.Random(f"{self.person.id}-{wk}-{item}")
                days = [d for d in range((wk - 1) * 7 + 1, wk * 7 + 1)
                        if self.by_item[item].read(self.person.id, item, d, rng) is not None]
                out[wk][item] = {"source": self.by_item[item].name, "days": len(days)}
        return out

    def extract(self, items: list[str], week: int, study: str | None = None) -> list[dict]:
        shift = self.day_shift(study) if study else 0
        who = self.pseudonym(study) if study else self.person.id
        rows = []
        for day in range((week - 1) * 7 + 1, week * 7 + 1):
            row = {"person": who, "day": day + shift}
            for it in items:
                src = self.by_item[it]
                rng = random.Random(f"{self.person.id}-{week}-{it}-{day}")
                row[it] = src.read(self.person.id, it, day, rng)
            rows.append(row)
        return rows
