"""Person -> institution -> sub-project.

A person consents once to an institution's scope (purposes, data types). The institution then opens
sub-projects under that scope; each is a record under the institution's single account and wallet
(no sub-accounts), with its own purpose, data types, budget and period. Routing per person and item:

  auto     inside the scope and the person's own rules: settled per sub-project, no new contract
  ask      outside the scope, or T3 (genomic, imaging, mental health, reproductive): the person decides
  blocked  the person paused or withdrew, or has not consented to this institution

Every order of a sub-project carries its id in the product id and in the escrow memo (sub:<id>), so
payouts are listed per sub-project. Synthetic data, mock ledger or Testnet.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import units
from .catalog import columns as catalog
from .engine import BudgetExceeded, NeedsHumanApproval, OrderRequest
from .policy import ALLOW, Decision
from .study import CELL_PRICE, LAB, ensure

T3_TIERS = {"T3"}


def _tier(item: str) -> str:
    c = catalog.canon(item)
    return catalog.CATALOG[c].tier if c in catalog.CATALOG else "T3"      # unknown counts as sensitive


@dataclass
class SubProject:
    id: str
    name: str
    purpose: str
    data_types: list
    budget_drops: int
    weeks: int
    created: float = field(default_factory=time.time)
    status: str = "open"                           # open | closed
    rounds: int = 0
    allowed: dict = field(default_factory=dict)    # pid -> items the person allowed by hand
    refused: dict = field(default_factory=dict)    # pid -> items the person refused


# The study protocol's items: the scope before the study has read its gaps (scenario.STANDARD_ITEMS + EXTRA_ITEMS).
PROTOCOL_ITEMS = ["sleep.daily", "activity.daily", "heart_rate.daily", "fatigue.survey", "blood_pressure.daily"]


class Relationships:
    def __init__(self, w):
        self.w = w
        self.own: dict[str, dict] = {}             # consents given through this API: pid -> {at, tx}
        self.subprojects: dict[str, SubProject] = {}
        ensure(w)
        self.wrap()

    def wrap(self):
        """The scope covers sub-project orders; the person's own rules still run first."""
        for pid in list(self.w.engine.policies):
            p = self.w.engine.policies[pid]
            if pid in getattr(self.w, "cohort_people", {}) and not isinstance(p, _ScopePolicy):
                self.w.engine.policies[pid] = _ScopePolicy(self, pid, p)

    @property
    def scope(self) -> dict:
        """The protocol the person agreed to, plus anything the study's needs added. The week's gaps never
        narrow it: a sub-project inside the agreed items reuses the consent with no new ask."""
        s = ensure(self.w)
        cells = s.needs.cells if s.needs else {}
        types = sorted({i for wk in cells.values() for its in wk.values() for i in its} | set(PROTOCOL_ITEMS))
        types = [catalog.canon(t) if catalog.canon(t) in catalog.CATALOG else t for t in types]
        return {"purposes": [s.needs.purpose] if s.needs else ["sleep_research"],
                "data_types": sorted({t for t in types if _tier(t) not in T3_TIERS}),
                "tiers_allowed": sorted({_tier(t) for t in types} - T3_TIERS)}

    @property
    def consents(self) -> dict:
        """People who contribute to the study hold the relationship (read on every access), plus those
        who consented here."""
        out = {}
        for r in ensure(self.w).requests.values():
            if r["status"] in ("contributed", "partly_open") and r["person"] not in out:
                first = next(iter(r["orders"]), None)
                pm = self.w.store.one("SELECT tx_hash FROM payments WHERE order_id=?", first["order_id"]) if first else None
                out[r["person"]] = {"at": r["created"], "tx": pm["tx_hash"] if pm else None}
        return {**out, **self.own}

    # ----- consent and routing -----
    def consent(self, pid: str) -> dict:
        self.own.setdefault(pid, {"at": time.time(), "tx": None})
        self.w.store.log(pid, "consent", f"{pid} consented to {LAB}'s scope: {', '.join(self.scope['purposes'])}; "
                         f"{', '.join(self.scope['data_types'])}")
        return self.own[pid]

    def _withdrawn(self, pid: str) -> bool:
        c = self.w.store.one("SELECT status FROM consents WHERE person_id=? AND buyer_id=?", pid, LAB)
        return c is not None and c["status"] in ("paused", "revoked")

    def route(self, sp: SubProject, pid: str, item: str) -> tuple[str, str]:
        if pid not in self.consents:
            return "blocked", "rule"
        if self._withdrawn(pid) or item in sp.refused.get(pid, []):
            return "blocked", "rule"
        if item in sp.allowed.get(pid, []):
            return "auto", "rule"
        if _tier(item) in T3_TIERS:
            return "ask", "T3"
        if item not in self.scope["data_types"] or sp.purpose not in self.scope["purposes"]:
            return "ask", "outside_scope"
        return "auto", "in_scope"

    def routing(self, sp: SubProject) -> list[dict]:
        out = []
        for pid in sorted(self.w.cohort_people):
            pseud = self.w.cohort_people[pid].vault.pseudonym(LAB)
            for item in sp.data_types:
                d, why = self.route(sp, pid, item)
                out.append({"person": pid, "pid_pseudonym": pseud, "item": item, "decision": d, "reason": why})
        return out

    # ----- sub-projects -----
    def create(self, name: str, purpose: str, data_types: list, budget_drops: int, weeks: int) -> dict:
        sid = f"sp-{len(self.subprojects) + 1}"
        sp = SubProject(sid, name, purpose, list(data_types), int(budget_drops), int(weeks))
        self.subprojects[sid] = sp
        self.w.store.log(LAB, "subproject", f"{LAB} opened sub-project {sid} '{name}' under its scope: {purpose}; "
                         f"{', '.join(data_types)}; budget {units.fmt(budget_drops)}, {weeks} weeks")
        return {**self.view(sp), "routing": [{k: v for k, v in r.items() if k != "person"} for r in self.routing(sp)]}

    def decide(self, pid: str, sid: str, item: str, allow: bool) -> dict:
        sp = self.subprojects[sid]
        (sp.allowed if allow else sp.refused).setdefault(pid, []).append(item)
        self.w.store.log(pid, "subproject_decision", f"{pid} {'allowed' if allow else 'refused'} {item} for {sid}")
        return {"ok": True, "decision": self.route(sp, pid, item)}

    def _paid(self, sid: str) -> int:
        return sum(r["price_drops"] for r in self.w.store.q(
            "SELECT price_drops FROM orders WHERE product_id=? AND status NOT IN ('blocked','failed','refunded')",
            f"subproject:{sid}"))

    def run(self, sid: str) -> dict:
        """One delivery round: every person's in-scope (or allowed) items, one escrow per person, tagged."""
        sp = self.subprojects[sid]
        sp.rounds += 1
        e = self.w.engine
        by_person: dict[str, list] = {}
        for r in self.routing(sp):
            if r["decision"] == "auto":
                by_person.setdefault(r["person"], []).append(r["item"])
        oids, stopped = [], None
        for pid, items in sorted(by_person.items()):
            price = CELL_PRICE * len(items)
            if self._paid(sid) + price > sp.budget_drops:
                stopped = f"sub-project budget {units.fmt(sp.budget_drops)} reached"
                break
            pa = self.w.cohort_people[pid]
            req = OrderRequest(LAB, pid, pid, f"subproject:{sid}", f"{pid}|{sid}|r{sp.rounds}", sp.purpose,
                               sorted(items), price, pa.vault.extract(sorted(items), sp.rounds, study=LAB),
                               Decision(ALLOW, granted=sorted(items), policy_version=f"scope:{sid}"), settle="escrow")
            try:
                oids.append(e.place_order(req))
            except (BudgetExceeded, NeedsHumanApproval) as x:
                stopped = str(x)
                break
        settled = []
        for oid in oids:
            st = e.process(oid)
            pm = self.w.store.one("SELECT tx_hash, finish_tx FROM payments WHERE order_id=?", oid)
            o = self.w.store.one("SELECT seller_id, price_drops FROM orders WHERE id=?", oid)
            settled.append({"order_id": oid, "person": o["seller_id"], "status": st, "amount": o["price_drops"] / 1e6,
                            "asset": units.UNIT, "escrow_create": pm["tx_hash"], "escrow_finish": pm["finish_tx"],
                            "url": self.w.ledger.explorer_url(pm["finish_tx"]) if pm["finish_tx"] else None})
        return {"subproject": sid, "round": sp.rounds, "settled": settled, "stopped": stopped}

    def payouts(self, sid: str, pid: str | None = None) -> list[dict]:
        rows = self.w.store.q(
            "SELECT o.id, o.seller_id, o.price_drops, o.scope, o.status, p.finish_tx FROM orders o "
            "JOIN payments p ON p.order_id=o.id WHERE o.product_id=?", f"subproject:{sid}")
        out = []
        for r in rows:
            if pid and r["seller_id"] != pid:
                continue
            rnd = r["scope"].split("|r")[-1].split('"')[0] if "|r" in r["scope"] else "?"
            out.append({"person": r["seller_id"], "round": rnd, "amount": r["price_drops"] / 1e6, "asset": units.UNIT,
                        "status": r["status"], "tx": r["finish_tx"]})
        return out

    def view(self, sp: SubProject) -> dict:
        pays = [p for p in self.payouts(sp.id) if p["status"] == "delivered"]
        return {"id": sp.id, "name": sp.name, "purpose": sp.purpose, "data_types": sp.data_types,
                "budget": sp.budget_drops / 1e6, "weeks": sp.weeks, "status": sp.status, "rounds": sp.rounds,
                "delivered": len(pays), "paid": round(sum(p["amount"] for p in pays), 6), "asset": units.UNIT}

    def institution(self) -> dict:
        return {"institution": {"id": LAB, "name": self.w.engine.party(LAB)["name"]}, "scope": self.scope,
                "relationships": len(self.consents), "asset": units.UNIT, "asset_label": units.LABEL,
                "subprojects": [self.view(sp) for sp in self.subprojects.values()]}

    def relationship(self, pid: str) -> dict:
        subs, pending = [], []
        for sp in self.subprojects.values():
            items = [{"item": i, "decision": self.route(sp, pid, i)[0], "reason": self.route(sp, pid, i)[1]}
                     for i in sp.data_types]
            pending += [{"sid": sp.id, "item": x["item"], "reason": x["reason"]} for x in items if x["decision"] == "ask"]
            pays = [p for p in self.payouts(sp.id, pid) if p["status"] == "delivered"]
            subs.append({"id": sp.id, "name": sp.name, "status": sp.status, "items": items, "payouts": pays,
                         "total": round(sum(p["amount"] for p in pays), 6)})
        return {"institution": {"id": LAB, "name": self.w.engine.party(LAB)["name"]}, "scope": self.scope,
                "consented": self.consents.get(pid), "subprojects": subs, "pending": pending,
                "asset": units.UNIT, "asset_label": units.LABEL}


class _ScopePolicy:
    """The person's own policy first; an order it would hold is still allowed when every item routes
    "auto" in an open sub-project of this institution with that purpose (the consented scope, or the
    person's own decision). A pause or withdrawal blocks it like any other order."""

    def __init__(self, rel: "Relationships", pid: str, inner):
        self.rel, self.pid, self.inner = rel, pid, inner

    def __getattr__(self, k):
        return getattr(self.inner, k)

    def evaluate(self, buyer_id, purpose, fields, price_drops, week=None, for_delivery=False):
        d = self.inner.evaluate(buyer_id, purpose, fields, price_drops, week=week, for_delivery=for_delivery)
        if (d.ok and set(fields) <= set(d.granted)) or buyer_id != LAB:
            return d
        for sp in self.rel.subprojects.values():
            if sp.status == "open" and sp.purpose == purpose and \
                    all(self.rel.route(sp, self.pid, f)[0] == "auto" for f in fields):
                return Decision(ALLOW, granted=list(fields), reason=f"inside the consented scope ({sp.id})",
                                policy_version=f"scope:{sp.id}")
        return d


def of(w) -> Relationships:
    if getattr(w, "relationships", None) is None:
        w.relationships = Relationships(w)
    w.relationships.wrap()                 # policies a later step replaced
    return w.relationships
