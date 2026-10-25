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
    floor_drops: int | None = None     # lowest price the seller agent may agree to (default: list price)

    @property
    def floor(self) -> int:
        return self.price_drops if self.floor_drops is None else self.floor_drops

    def public(self) -> dict:
        """What a buyer agent sees before paying: description only, no raw rows."""
        return {"id": self.id, "seller": self.seller_id, "title": self.title, "domain": self.domain,
                "fields": self.fields, "scenarios": self.scenarios,
                "price_xrp": self.price_drops / 1e6, "licence": self.licence}


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
                    if f == "raw_video":
                        row[f] = f"video://{p.id}/{scen}/{i}"
                    elif rng.random() < p.missing_rate:
                        row[f] = None
                    else:
                        row[f] = round(rng.uniform(0, 1), 3)
                rows.append(row)
        dup = int(len(rows) * p.duplicate_rate)
        return rows + [dict(r) for r in rows[:dup]]

    def sample(self, product_id: str) -> list[dict]:
        p = self.products[product_id]
        return self._episodes(p, [f for f in p.fields if f != "raw_video"], n_per_scenario=10)

    def extract(self, product_id: str, fields: list[str]) -> list[dict]:
        return self._episodes(self.products[product_id], fields)


@dataclass
class Person:
    id: str
    label: str
    weeks_available: int = 8
    data: dict = field(default_factory=dict)


class PersonalVaultConnector:
    """One person's own data vault (synthetic). Exports only requested items for one week."""

    ITEMS = ["sleep.daily", "activity.daily", "heart_rate.daily", "fatigue.survey", "blood_pressure.daily"]

    def __init__(self, person: Person):
        self.person = person

    def extract(self, items: list[str], week: int) -> list[dict]:
        rng = random.Random(f"{self.person.id}-{week}")
        rows = []
        for day in range((week - 1) * 7 + 1, week * 7 + 1):
            row = {"person": self.person.id, "day": day}
            for it in items:
                if it == "sleep.daily":
                    row[it] = {"minutes": rng.randint(300, 480), "efficiency": round(rng.uniform(.7, .95), 2)}
                elif it == "activity.daily":
                    row[it] = {"steps": rng.randint(2000, 12000)}
                elif it == "heart_rate.daily":
                    row[it] = {"resting_bpm": rng.randint(52, 78)}
                elif it == "fatigue.survey":
                    row[it] = {"score_0_10": rng.randint(1, 8)} if day % 7 == 0 else None
                elif it == "blood_pressure.daily":
                    row[it] = {"sys": rng.randint(105, 140), "dia": rng.randint(65, 90)}
            rows.append(row)
        return rows
