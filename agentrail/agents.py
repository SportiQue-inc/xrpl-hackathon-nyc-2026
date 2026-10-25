"""Agents. They search, evaluate, negotiate and explain. They never decide
permissions or move money directly: policies decide, the engine executes."""
from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass, field

from .connectors import PersonalVaultConnector, RoboticsConnector
from .llm import voice
from .engine import BudgetExceeded, Engine, NeedsHumanApproval, OrderRequest, canonical, sha256_hex
from .policy import (ALLOW, AUTOMATION_LEVELS, DENY, HOLD, PARTIAL, SENSITIVITY, ComplianceRules,
                     Decision, PersonalConsentPolicy, SENSITIVE_FIELDS, SellerPolicy)


# ---------------- conversation log ----------------

def talk(store, speaker: str, to: str | None, kind: str, facts: dict, fallback: str, extra: dict | None = None):
    """Log one line of agent dialogue. The decision is in `facts` (set by code);
    the LLM, if configured, only rewrites `fallback` as a sentence."""
    text, by = voice().say(speaker, to, facts, fallback)
    store.log(speaker, kind, text, {"to": to, "by": by, "facts": facts, **(extra or {})})


def xrp(drops: int) -> str:
    return f"{drops / 1e6:g} XRP"


# ---------------- organization seller agent ----------------

class SellerAgent:
    """Answers quotes and price offers within its organization's policy:
    allowed purposes, excluded fields, licence and the lowest price it may accept."""

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
        msg = {ALLOW: f"I can provide {', '.join(d.granted)}", PARTIAL: f"counter-offer: {d.reason}",
               DENY: f"declined: {d.reason}"}[d.status]
        talk(self.engine.store, self.id, buyer_id, "quote",
             {"product": product_id, "status": d.status, "granted": d.granted, "refused": d.refused,
              "list_price_xrp": p.price_drops / 1e6, "reason": d.reason},
             f"{product_id}: {msg}, list price {xrp(p.price_drops)}.")
        return d, p.price_drops

    def respond_to_offer(self, buyer_id: str, product_id: str, offer_drops: int) -> tuple[str, int]:
        """Deterministic: accept at or above the floor, otherwise counter at the floor."""
        p = self.connector.products[product_id]
        if offer_drops >= p.floor:
            status, price = "accept", offer_drops
            fb = f"{product_id}: {xrp(offer_drops)} accepted."
        else:
            status, price = "counter", p.floor
            fb = f"{product_id}: {xrp(offer_drops)} is below what my policy allows; I can do {xrp(p.floor)}."
        talk(self.engine.store, self.id, buyer_id, "negotiate",
             {"product": product_id, "offer_xrp": offer_drops / 1e6, "answer": status, "price_xrp": price / 1e6}, fb)
        return status, price


# ---------------- buyer agent (organization procurement) ----------------

@dataclass
class Goal:
    """What the buyer organization tells its agent. Budget and per-order limit live in
    the mandate (enforced by the engine); the rest is enforced here, in code."""
    text: str
    purpose: str
    required_fields: list[str]
    optional_fields: list[str]
    required_scenarios: list[str]
    max_missing_rate: float = 0.05          # minimum quality, measured on samples
    max_duplicate_rate: float = 0.05
    allow_sensitive_fields: bool = False    # e.g. raw video that may show people
    auto_approve_limit_drops: int | None = None  # above this total, a human approves first
    opening_offer: float = 0.85             # first offer as a share of list price


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
    """Discovery -> quality check -> quote -> negotiation -> selection -> purchase -> report.
    Every step is logged with its reason. Money moves only through the engine."""

    def __init__(self, party_id: str, engine: Engine):
        self.id = party_id
        self.engine = engine

    def say(self, kind, facts, fallback, to=None, extra=None):
        talk(self.engine.store, self.id, to, kind, facts, fallback, extra)

    def procure(self, goal: Goal, sellers: list[SellerAgent]) -> dict:
        available = self.engine.available_drops(self.id)
        self.say("goal", {"goal": goal.text, "available_xrp": available / 1e6,
                          "max_missing_rate": goal.max_missing_rate,
                          "sensitive_fields_allowed": goal.allow_sensitive_fields},
                 f"Goal: {goal.text}. Mandate has {xrp(available)} available; sample missing rate must stay "
                 f"under {goal.max_missing_rate:.0%}; sensitive fields "
                 f"{'allowed' if goal.allow_sensitive_fields else 'not requested'}.")
        wanted = goal.required_fields + goal.optional_fields
        skipped = [f for f in wanted if f in SENSITIVE_FIELDS and not goal.allow_sensitive_fields]
        if skipped:
            wanted = [f for f in wanted if f not in skipped]
            self.say("settings", {"not_requested": skipped},
                     f"Not requesting {', '.join(skipped)}: it may show people and my settings do not "
                     f"allow sensitive fields.")

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
                    self.say("evaluate", {"product": prod["id"], "excluded": c.excluded, "quality": c.quality},
                             f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}.", to=s.id)
                    continue
                d, price = s.quote(self.id, prod["id"], wanted, goal.purpose)
                lost_required = [f for f in d.refused if f in goal.required_fields]
                if d.status == DENY or lost_required:
                    c.excluded = d.reason or "seller refused required fields"
                    self.say("evaluate", {"product": prod["id"], "excluded": c.excluded},
                             f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}.", to=s.id)
                    continue
                c.decision, c.price_drops = d, price
                covers = [k for k in prod["scenarios"] if k in goal.required_scenarios]
                note = f"; accepting counter-offer without {', '.join(d.refused)} (optional)" if d.refused else ""
                self.say("evaluate", {"product": prod["id"], "covers": covers, "quality": c.quality,
                                      "refused_optional": d.refused},
                         f"{prod['seller']}/{prod['id']}: qualifies, covers {', '.join(covers)}, missing "
                         f"{c.quality['missing_rate']:.1%} (sample-verified){note}.", to=s.id)

        ok = [c for c in cands if not c.excluded]
        # Negotiation: one opening offer, seller accepts or counters at its floor.
        for c in ok:
            offer = int(c.price_drops * goal.opening_offer)
            self.say("negotiate", {"product": c.product["id"], "list_price_xrp": c.price_drops / 1e6,
                                   "offer_xrp": offer / 1e6},
                     f"{c.product['id']}: would you take {xrp(offer)} instead of {xrp(c.price_drops)}?",
                     to=c.seller.id)
            _, agreed = c.seller.respond_to_offer(self.id, c.product["id"], offer)
            c.price_drops = min(agreed, c.price_drops)   # never pay above list

        need = set(goal.required_scenarios)
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
             "agreed_xrp": c.price_drops / 1e6 if c.decision else None,
             "excluded": c.excluded, "quality": c.quality,
             "refused_fields": c.decision.refused if c.decision else []} for c in cands]}
        if best is None:
            if best_any:
                gap = best_any[0] - available
                msg = (f"no combination fits the available {xrp(available)}; cheapest full coverage "
                       f"costs {xrp(best_any[0])}. Asking a human to approve +{xrp(gap)}. Nothing bought.")
                report["gap_xrp"] = gap / 1e6
            else:
                msg = "no qualifying data covers all required scenarios. Nothing bought."
            self.say("report", {"status": "not_purchased", "reason": msg}, msg)
            return {**report, "status": "not_purchased", "reason": msg, "orders": []}

        cost, combo = best
        ids = [c.product["id"] for c in combo]
        if goal.auto_approve_limit_drops is not None and cost > goal.auto_approve_limit_drops:
            msg = (f"{' + '.join(ids)} costs {xrp(cost)}, above my auto-approval limit of "
                   f"{xrp(goal.auto_approve_limit_drops)}. Waiting for a human. Nothing bought.")
            self.say("ask_human", {"selected": ids, "cost_xrp": cost / 1e6,
                                   "auto_approve_limit_xrp": goal.auto_approve_limit_drops / 1e6}, msg)
            return {**report, "status": "needs_approval", "reason": msg, "orders": []}

        listed = sum(c.product["price_xrp"] for c in combo)
        self.say("select", {"selected": ids, "cost_xrp": cost / 1e6, "list_total_xrp": listed,
                            "covers": goal.required_scenarios, "available_xrp": available / 1e6},
                 f"Selected {' + '.join(ids)} for {xrp(cost)} (list {listed:g} XRP): together they cover "
                 f"{', '.join(goal.required_scenarios)} within the {xrp(available)} available.")
        orders = []
        for c in combo:
            rows = c.seller.connector.extract(c.product["id"], c.decision.granted)
            req = OrderRequest(self.id, c.seller.id, c.seller.id, c.product["id"], "once", goal.purpose,
                               c.decision.granted, c.price_drops, rows, c.decision)
            oid = self.engine.place_order(req)
            status = self.engine.process(oid)
            orders.append({"order_id": oid, "product": c.product["id"], "status": status})
        remaining = self.engine.available_drops(self.id)
        self.say("report", {"acquired": ids, "spent_xrp": cost / 1e6, "remaining_xrp": remaining / 1e6,
                            "orders": orders},
                 f"Acquired {len(combo)} datasets, spent {xrp(cost)}, remaining {xrp(remaining)}. "
                 f"Receipts: payment on a validated ledger, sealed bundle delivered.")
        return {**report, "status": "purchased", "selected": ids,
                "spent_xrp": cost / 1e6, "remaining_xrp": remaining / 1e6, "orders": orders}


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
        talk(st, f"person {self.person.label}", self.id, "approve",
             {"approved": items, "declined": declined, "applies_to": what},
             f"Approve {', '.join(items) or 'nothing'} ({what})"
             + (f"; decline {', '.join(declined)}." if declined else "."))

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
            msg = (f"{buyer_id} asks for {', '.join(items)} at {price / 1e6:g} XRP/item. That is outside "
                   f"your consent, so nothing was sent. Allow it?")
        else:
            msg = f"Week {week}: {', '.join(items)} needs your confirmation before it is sent."
        msg += f" ({', '.join(sens)} is sensitive: only if you tick it by name.)" if sens else ""
        talk(st, self.id, f"person {self.person.label}", "ask_person",
             {"buyer": buyer_id, "kind": kind, "items": items, "week": week, "price_per_item_xrp": price / 1e6,
              "sensitive": sens, "sent": False}, msg)

    def handle_request(self, buyer_id: str, purpose: str, items: list[str], week: int,
                       price_per_item_drops: int, extra_price_drops: int | None = None) -> Decision:
        d = self.policy.evaluate(buyer_id, purpose, items, price_per_item_drops * len(items), week=week)
        scope_items = [i for i in d.pending if i not in d.round_confirm]
        if scope_items:
            self._ask(buyer_id, "scope", scope_items, None, extra_price_drops or price_per_item_drops)
        if d.round_confirm:
            self._ask(buyer_id, "round", d.round_confirm, week, price_per_item_drops)
        st = self.engine.store
        if d.refused:
            talk(st, self.id, buyer_id, "filter", {"refused": d.refused, "reason": d.reason},
                 f"{self.person.label}: not providing {', '.join(d.refused)} - {d.reason}.")
        if d.status in (DENY, HOLD):
            talk(st, self.id, buyer_id, d.status, {"status": d.status, "week": week, "reason": d.reason},
                 f"{self.person.label}: request for week {week} refused - {d.reason}.")
        elif d.ok and not d.pending:
            talk(st, self.id, buyer_id, "provide", {"granted": d.granted, "week": week},
                 f"{self.person.label}: week {week} {', '.join(d.granted)} is within consent; providing it "
                 f"after payment is validated.")
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
        talk(st, self.id, "personal agents", "round",
             {"week": week, "items": ask, "people": len(people), "price_per_item_xrp": price_per_item_drops / 1e6,
              "extra_price_xrp": (extra_price_drops or 0) / 1e6},
             f"Week {week}: requesting {', '.join(ask)} from {len(people)} people for {self.purpose}.")
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
