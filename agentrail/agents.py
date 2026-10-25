"""Agents. They search, evaluate, negotiate and explain. They never decide
permissions or move money directly: policies decide, the engine executes."""
from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass, field

from .connectors import PersonalVaultConnector, RoboticsConnector
from .engine import BudgetExceeded, Engine, NeedsHumanApproval, OrderRequest, canonical, sha256_hex
from .policy import (ALLOW, AUTOMATION_LEVELS, DENY, HOLD, PARTIAL, SENSITIVITY, ComplianceRules,
                     Decision, PersonalConsentPolicy, SellerPolicy)


# ---------------- organization seller agent ----------------

class SellerAgent:
    def __init__(self, party_id: str, connector: RoboticsConnector, policy: SellerPolicy, engine: Engine):
        self.id = party_id
        self.connector = connector
        self.policy = policy
        self.engine = engine
        engine.policies[party_id] = policy

    def catalog(self) -> list[dict]:
        return [p.public() for p in self.connector.products.values()]

    def sample(self, product_id: str) -> list[dict]:
        return self.connector.sample(product_id)

    def quote(self, buyer_id: str, product_id: str, fields: list[str], purpose: str) -> tuple[Decision, int]:
        p = self.connector.products[product_id]
        d = self.policy.evaluate(buyer_id, purpose, [f for f in fields if f in p.fields], p.price_drops)
        if p.licence.get(purpose) is False:
            d = Decision(DENY, reason=f"licence does not allow {purpose}", policy_version=d.policy_version)
        msg = {ALLOW: "offer: all requested fields", PARTIAL: d.reason, DENY: f"declined: {d.reason}"}[d.status]
        self.engine.store.log(self.id, "quote", f"{product_id}: {msg} at {p.price_drops / 1e6:g} XRP")
        return d, p.price_drops


# ---------------- buyer agent (organization procurement) ----------------

@dataclass
class Goal:
    text: str
    purpose: str
    required_fields: list[str]
    optional_fields: list[str]
    required_scenarios: list[str]
    max_missing_rate: float = 0.05
    max_duplicate_rate: float = 0.05


@dataclass
class Candidate:
    seller: SellerAgent
    product: dict
    decision: Decision | None = None
    price_drops: int = 0
    quality: dict = field(default_factory=dict)
    excluded: str | None = None


def check_quality(sample: list[dict], fields: list[str]) -> dict:
    n = len(sample) or 1
    cells = [r.get(f) for r in sample for f in fields]
    missing = sum(v is None for v in cells) / max(len(cells), 1)
    keys = [r["episode"] for r in sample]
    dup = (len(keys) - len(set(keys))) / n
    return {"missing_rate": round(missing, 3), "duplicate_rate": round(dup, 3),
            "sample_size": len(sample), "basis": "sample-verified"}


class BuyerAgent:
    def __init__(self, party_id: str, engine: Engine):
        self.id = party_id
        self.engine = engine
        self.log = lambda kind, msg, data=None: engine.store.log(party_id, kind, msg, data)

    def procure(self, goal: Goal, sellers: list[SellerAgent]) -> dict:
        self.log("goal", f"goal: {goal.text} (mandate: {self.engine.available_drops(self.id) / 1e6:g} XRP available)")
        cands: list[Candidate] = []
        for s in sellers:
            for prod in s.catalog():
                c = Candidate(s, prod)
                cands.append(c)
                missing = [f for f in goal.required_fields if f not in prod["fields"]]
                if missing:
                    c.excluded = f"missing required field(s): {', '.join(missing)}"
                elif prod["licence"].get(goal.purpose) is False:
                    c.excluded = f"licence does not allow {goal.purpose}"
                else:
                    c.quality = check_quality(s.sample(prod["id"]), goal.required_fields)
                    if c.quality["missing_rate"] > goal.max_missing_rate:
                        c.excluded = f"sample missing rate {c.quality['missing_rate']:.0%} above limit"
                    elif c.quality["duplicate_rate"] > goal.max_duplicate_rate:
                        c.excluded = f"sample duplicate rate {c.quality['duplicate_rate']:.0%} above limit"
                if c.excluded:
                    self.log("evaluate", f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}")
                    continue
                d, price = s.quote(self.id, prod["id"], goal.required_fields + goal.optional_fields, goal.purpose)
                lost_required = [f for f in d.refused if f in goal.required_fields]
                if d.status == DENY or lost_required:
                    c.excluded = d.reason or "seller refused required fields"
                    self.log("evaluate", f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}")
                    continue
                c.decision, c.price_drops = d, price
                note = f"; accepts counter-offer without {', '.join(d.refused)} (optional)" if d.refused else ""
                self.log("evaluate", f"{prod['seller']}/{prod['id']}: qualifies, covers "
                         f"{', '.join(k for k in prod['scenarios'] if k in goal.required_scenarios)}, "
                         f"missing {c.quality['missing_rate']:.1%} (sample-verified){note}")

        ok = [c for c in cands if not c.excluded]
        need = set(goal.required_scenarios)
        available = self.engine.available_drops(self.id)
        best, best_any = None, None
        for r in range(1, len(ok) + 1):
            for combo in itertools.combinations(ok, r):
                covered = set().union(*(set(c.product["scenarios"]) for c in combo))
                if not need <= covered:
                    continue
                cost = sum(c.price_drops for c in combo)
                if best_any is None or cost < best_any[0]:
                    best_any = (cost, combo)
                if cost <= available and (best is None or cost < best[0]):
                    best = (cost, combo)
        report = {"goal": goal.text, "candidates": [
            {"seller": c.product["seller"], "product": c.product["id"], "price_xrp": c.product["price_xrp"],
             "excluded": c.excluded, "quality": c.quality,
             "refused_fields": c.decision.refused if c.decision else []} for c in cands]}
        if best is None:
            if best_any:
                gap = best_any[0] - available
                msg = (f"no combination fits the available {available / 1e6:g} XRP; cheapest full coverage "
                       f"costs {best_any[0] / 1e6:g} XRP. Asking a human to approve +{gap / 1e6:g} XRP. Nothing bought.")
            else:
                msg = "no qualifying data covers all required scenarios. Nothing bought."
            self.log("report", msg)
            return {**report, "status": "not_purchased", "reason": msg, "orders": []}

        cost, combo = best
        self.log("select", f"selected {' + '.join(c.product['id'] for c in combo)} for {cost / 1e6:g} XRP "
                 f"(covers all of {', '.join(goal.required_scenarios)}; budget {available / 1e6:g} XRP)")
        orders = []
        for c in combo:
            rows = c.seller.connector.extract(c.product["id"], c.decision.granted)
            req = OrderRequest(self.id, c.seller.id, c.seller.id, c.product["id"], "once", goal.purpose,
                               c.decision.granted, c.price_drops, rows, c.decision)
            oid = self.engine.place_order(req)
            status = self.engine.process(oid)
            orders.append({"order_id": oid, "product": c.product["id"], "status": status})
        spent = sum(c.price_drops for c in combo)
        self.log("report", f"acquired {len(combo)} datasets, spent {spent / 1e6:g} XRP, "
                 f"remaining {self.engine.available_drops(self.id) / 1e6:g} XRP")
        return {**report, "status": "purchased", "selected": [c.product["id"] for c in combo],
                "spent_xrp": spent / 1e6, "remaining_xrp": self.engine.available_drops(self.id) / 1e6,
                "orders": orders}


# ---------------- personal agent (person as data holder) ----------------

class PersonalAgent:
    """Acts for one person. Its settings are the person's: consents per institution,
    automation level, minimum price. It can explain and ask; it cannot widen scope."""

    def __init__(self, person, engine: Engine, compliance: ComplianceRules | None = None):
        self.person = person
        self.id = person.id
        self.engine = engine
        self.vault = PersonalVaultConnector(person)
        self.policy = PersonalConsentPolicy(engine.store, person.id, compliance)
        engine.policies[person.id] = self.policy

    def _write_consent(self, c, buyer_id, purpose, items, weeks, automation, min_price, status, version):
        doc = consent_document(self.id, buyer_id, purpose, items, weeks, automation, min_price, status, version)
        doc_json = canonical(doc)
        h = sha256_hex(doc_json)
        c.execute("INSERT OR REPLACE INTO consents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (self.id, buyer_id, purpose, json.dumps(sorted(items)), weeks[0], weeks[1],
                   automation, min_price, status, version, doc_json, h))
        c.execute("INSERT INTO consent_history (person_id,buyer_id,version,status,doc,doc_hash,ts) "
                  "VALUES (?,?,?,?,?,?,?)", (self.id, buyer_id, version, status, doc_json, h, time.time()))
        return h

    def set_consent(self, buyer_id: str, purpose: str, items: list[str], weeks=(1, 8),
                    automation: str = "auto_standard", min_price_drops: int = 0):
        assert automation in AUTOMATION_LEVELS
        st = self.engine.store
        with st.tx() as c:
            cur = c.execute("SELECT version FROM consents WHERE person_id=? AND buyer_id=?",
                            (self.id, buyer_id)).fetchone()
            v = (cur["version"] + 1) if cur else 1
            h = self._write_consent(c, buyer_id, purpose, items, weeks, automation, min_price_drops, "active", v)
            st.log(self.id, "consent", f"{self.person.label} signs consent v{v} with {buyer_id}: "
                   f"{', '.join(sorted(items))} for '{purpose}', weeks {weeks[0]}-{weeks[1]}, "
                   f"automation={automation} (doc {h[:12]}…)", {"doc_hash": h})

    def _update(self, buyer_id: str, **changes):
        st = self.engine.store
        with st.tx() as c:
            cur = dict(c.execute("SELECT * FROM consents WHERE person_id=? AND buyer_id=?",
                                 (self.id, buyer_id)).fetchone())
            items = changes.pop("items", None) or json.loads(cur["items"])
            cur.update(changes)
            return self._write_consent(c, buyer_id, cur["purpose"], items, (cur["period_from"], cur["period_to"]),
                                       cur["automation"], cur["min_price_drops"], cur["status"], cur["version"] + 1)

    def pause(self, buyer_id: str):
        h = self._update(buyer_id, status="paused")
        self.engine.store.log(self.id, "paused", f"{self.person.label} paused supply to {buyer_id} "
                              f"(new orders stop; delivered data and payments stay) doc {h[:12]}…")

    def resume(self, buyer_id: str):
        self._update(buyer_id, status="active")
        self.engine.store.log(self.id, "resumed", f"{self.person.label} resumed supply to {buyer_id}")

    def revoke(self, buyer_id: str):
        h = self._update(buyer_id, status="revoked")
        self.engine.store.log(self.id, "revoked", f"{self.person.label} revoked data access consent for "
                              f"{buyer_id} (undelivered bundles withheld) doc {h[:12]}…")

    def set_automation(self, buyer_id: str, automation: str):
        assert automation in AUTOMATION_LEVELS
        self._update(buyer_id, automation=automation)
        self.engine.store.log(self.id, "settings", f"{self.person.label} set automation for {buyer_id} to {automation}")

    def approve(self, request_id: int, items: list[str]):
        """The person ticks items by name. Sensitive items are never implied."""
        st = self.engine.store
        r = st.one("SELECT * FROM approval_requests WHERE id=?", request_id)
        asked = json.loads(r["items"])
        items = [i for i in items if i in asked]
        declined = [i for i in asked if i not in items]
        if r["kind"] == "scope" and items:
            c0 = st.one("SELECT items FROM consents WHERE person_id=? AND buyer_id=?", self.id, r["buyer_id"])
            self._update(r["buyer_id"], items=sorted(set(json.loads(c0["items"])) | set(items)))
        with st.tx() as c:
            c.execute("UPDATE approval_requests SET status='decided', decided_items=? WHERE id=?",
                      (json.dumps(items), request_id))
        what = "consent scope" if r["kind"] == "scope" else f"week {r['week']} only"
        st.log(self.id, "approve", f"{self.person.label} approved {', '.join(items) or 'nothing'} ({what})"
               + (f"; declined {', '.join(declined)}" if declined else ""))

    def _ask(self, buyer_id, kind, items, week, price):
        st = self.engine.store
        key = json.dumps(sorted(items))
        if st.one("SELECT id FROM approval_requests WHERE person_id=? AND buyer_id=? AND status='open' "
                  "AND kind=? AND items=? AND (week IS ? OR kind='scope')", self.id, buyer_id, kind, key, week):
            return
        with st.tx() as c:
            c.execute("INSERT INTO approval_requests (person_id,buyer_id,kind,week,items,offered_price_drops,"
                      "status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                      (self.id, buyer_id, kind, week, key, price, "open", time.time()))
        sens = [i for i in items if SENSITIVITY.get(i) == "sensitive"]
        if kind == "scope":
            msg = (f"{self.person.label}: {buyer_id} asks for {', '.join(items)} at {price / 1e6:g} XRP/item - "
                   f"outside consent, nothing sent; asking the person")
        else:
            msg = f"{self.person.label}: week {week} {', '.join(items)} needs the person's confirmation"
        st.log(self.id, "ask_person", msg + (f" ({', '.join(sens)} is sensitive: ticked by name only)" if sens else ""))

    def handle_request(self, buyer_id: str, purpose: str, items: list[str], week: int,
                       price_per_item_drops: int, extra_price_drops: int | None = None) -> Decision:
        d = self.policy.evaluate(buyer_id, purpose, items, price_per_item_drops * len(items), week=week)
        scope_items = [i for i in d.pending if i not in d.round_confirm]
        if scope_items:
            self._ask(buyer_id, "scope", scope_items, None, extra_price_drops or price_per_item_drops)
        if d.round_confirm:
            self._ask(buyer_id, "round", d.round_confirm, week, price_per_item_drops)
        if d.refused:
            self.engine.store.log(self.id, "filter", f"{self.person.label}: {d.reason}")
        if d.status in (DENY, HOLD):
            self.engine.store.log(self.id, d.status, f"{self.person.label}: refused {buyer_id} week {week} - {d.reason}")
        return d

    def open_requests(self) -> list:
        return self.engine.store.q("SELECT * FROM approval_requests WHERE person_id=? AND status='open'", self.id)


def consent_document(person_id, buyer_id, purpose, items, weeks, automation, min_price, status, version) -> dict:
    """The consent contract. Its hash is put in each payment memo, so a payment on
    XRPL can be matched to the exact consent version it relied on."""
    return {
        "type": "agentrail.consent/v1", "version": version, "status": status,
        "data_holder": person_id, "recipient": buyer_id, "purpose": purpose,
        "items": sorted(items),
        "sensitivity": {i: SENSITIVITY.get(i, "standard") for i in sorted(items)},
        "period_weeks": list(weeks), "delivery": "sealed weekly bundle, recipient key only",
        "retention": "recipient deletes on study end or on request; delivered copies cannot be recalled",
        "automation": automation, "min_price_drops": min_price,
        "payment": "direct to data holder on XRPL, per delivered round",
        "withdrawal": "pause stops new orders; revoke also withholds undelivered bundles; "
                      "completed payments are kept",
        "onward_transfer": "not allowed", "synthetic_demo": True,
    }


class InstitutionAgent:
    """Buyer agent for personal data: one order per person per round, paid to the person."""

    def __init__(self, party_id: str, engine: Engine, purpose: str):
        self.id = party_id
        self.engine = engine
        self.purpose = purpose

    def run_round(self, people: list[PersonalAgent], week: int, items: list[str],
                  price_per_item_drops: int, extra_items: list[str] | None = None,
                  extra_price_drops: int | None = None) -> list[dict]:
        st = self.engine.store
        ask = items + (extra_items or [])
        st.log(self.id, "round", f"week {week}: requesting {', '.join(ask)} from {len(people)} people")
        out = []
        for pa in people:
            d = pa.handle_request(self.id, self.purpose, ask, week, price_per_item_drops, extra_price_drops)
            if not d.ok:
                out.append({"person": pa.id, "status": d.status, "reason": d.reason})
                continue
            price = sum(extra_price_drops if (extra_items and i in extra_items and extra_price_drops)
                        else price_per_item_drops for i in d.granted)
            rows = pa.vault.extract(d.granted, week)
            req = OrderRequest(self.id, pa.id, pa.id, "personal.weekly", f"{pa.id}|week{week}",
                               self.purpose, d.granted, price, rows, d)
            try:
                oid = self.engine.place_order(req)
            except (BudgetExceeded, NeedsHumanApproval) as e:
                st.log(self.id, "stop", f"{pa.person.label}: {e}")
                out.append({"person": pa.id, "status": "budget", "reason": str(e)})
                continue
            status = self.engine.process(oid)
            out.append({"person": pa.id, "status": status, "order_id": oid, "granted": d.granted,
                        "pending": d.pending})
        return out
