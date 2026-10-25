"""Agents. They search, compare fixed quotes, confirm terms and explain. They never decide
permissions or move money directly: policies decide, the engine executes."""
from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass, field

from .connectors import PersonalVaultConnector, RoboticsConnector
from .llm import voice
from .engine import BudgetExceeded, Engine, NeedsHumanApproval, OrderRequest, canonical, sha256_hex
from .reasoning import OwnerLimits, Spec, infer_spec, match_schema, read_licence, terms_hash
from .policy import (ALLOW, AUTOMATION_LEVELS, DENY, HOLD, PARTIAL, SENSITIVITY, ComplianceRules,
                     Decision, PersonalConsentPolicy, SENSITIVE_FIELDS, SellerPolicy)


# ---------------- conversation log ----------------

def talk(store, speaker: str, to: str | None, kind: str, facts: dict, fallback: str, extra: dict | None = None):
    """Log one line of agent dialogue. The decision is in `facts` (set by code);
    the LLM, if configured, only rewrites `fallback` as a sentence."""
    text, by = voice().say(speaker, to, facts, fallback)
    store.log(speaker, kind, text, {"to": to, "by": by, "facts": facts, **(extra or {})})


def licence_text(lic: dict) -> str:
    return ", ".join(f"{k.replace('_', ' ')} {'allowed' if v else 'not allowed'}" for k, v in lic.items())


def xrp(drops: int) -> str:
    return f"{drops / 1e6:g} XRP"


# ---------------- organization seller agent ----------------

class SellerAgent:
    """Publishes fixed prices and terms, and answers quotes within its organization's
    policy: allowed purposes, excluded fields, licence."""

    def __init__(self, party_id: str, connector: RoboticsConnector, policy: SellerPolicy, engine: Engine):
        self.id = party_id
        self.connector = connector
        self.policy = policy
        self.engine = engine
        engine.policies[party_id] = policy

    def confirm_terms(self, buyer_id: str, product_id: str, reading: dict) -> tuple[dict, list[str]]:
        """The buyer's reading of the licence becomes a contract only as far as the seller's own
        structured terms agree: each permission is the AND of both, so a misreading can only narrow."""
        p = self.connector.products[product_id]
        mine = {k: bool(p.licence.get(k, False)) for k in ("commercial_training", "evaluation", "redistribution")}
        agreed = {k: bool(reading.get(k)) and mine[k] for k in mine}
        corrected = [k for k in mine if bool(reading.get(k)) and not mine[k]]
        agreed.update({k: reading.get(k) for k in ("term_months", "attribution") if k in reading})
        fb = (f"{product_id}: your reading of our licence is confirmed." if not corrected else
              f"{product_id}: correction - our licence does not grant {', '.join(corrected)}; "
              f"the contract uses the narrower terms.")
        talk(self.engine.store, self.id, buyer_id, "terms", {"product": product_id, "buyer_reading": reading,
                                                             "seller_terms": mine, "agreed": agreed,
                                                             "corrected": corrected}, fb)
        return agreed, corrected

    def catalog(self) -> list[dict]:
        return [p.public() for p in self.connector.products.values()]

    def sample(self, product_id: str) -> list[dict]:
        return self.connector.sample(product_id)

    def quote(self, buyer_id: str, product_id: str, fields: list[str], purpose: str) -> tuple[Decision, int]:
        p = self.connector.products[product_id]
        d = self.policy.evaluate(buyer_id, purpose, [f for f in fields if f in p.fields], p.price_drops)
        if p.licence.get(purpose) is False:
            d = Decision(DENY, reason=f"licence does not allow {purpose}", policy_version=d.policy_version)
        msg = {ALLOW: f"I can provide {', '.join(d.granted)}",
               PARTIAL: f"I can provide {', '.join(d.granted)} only ({d.reason.split(';')[0]})",
               DENY: f"declined: {d.reason}"}[d.status]
        talk(self.engine.store, self.id, buyer_id, "quote",
             {"product": product_id, "status": d.status, "granted": d.granted, "refused": d.refused,
              "list_price_xrp": p.price_drops / 1e6, "reason": d.reason},
             f"{product_id}: {msg}, fixed price {xrp(p.price_drops)}.")
        return d, p.price_drops


# ---------------- buyer agent (organization procurement) ----------------

@dataclass
class Candidate:
    seller: SellerAgent
    product: dict
    decision: Decision | None = None
    price_drops: int = 0
    quality: dict = field(default_factory=dict)
    mapping: dict = field(default_factory=dict)      # canonical field -> seller's field (sample-verified)
    terms: dict = field(default_factory=dict)        # licence terms both sides agreed to
    terms_hash: str = ""
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
    """Infers what the organization is missing, reads other companies' catalogs and licences,
    and buys. The LLM proposes (spec, field mapping, licence reading); code verifies each
    proposal and can only narrow it; the ledger enforces payment rules."""

    def __init__(self, party_id: str, engine: Engine, propose=None):
        self.id = party_id
        self.engine = engine
        self.propose = propose   # tests inject an adversarial proposer here

    def say(self, kind, facts, fallback, to=None, extra=None):
        talk(self.engine.store, self.id, to, kind, facts, fallback, extra)

    def plan(self, goal_text: str, inventory: dict, limits: OwnerLimits) -> Spec:
        st = self.engine.store
        self.say("goal", {"goal": goal_text, "inventory": [d["name"] for d in inventory.get("datasets", [])]},
                 f"Owner's goal: \"{goal_text}\". Reading our own inventory to see what is missing.")
        spec, notes = infer_spec(st, self.id, goal_text, inventory, limits, self.propose)
        src = st.one("SELECT source FROM proposals WHERE hash=?", spec.proposal_hash)["source"]
        gaps = "; ".join(f"{k} ({v})" for k, v in spec.reasons.items()) or "none found"
        self.say("spec", {"required_fields": spec.required_fields, "required_scenarios": spec.required_scenarios,
                          "purpose": spec.purpose, "budget_xrp": spec.budget_cap_drops / 1e6,
                          "max_missing_rate": spec.max_missing_rate, "evidence": spec.reasons, "proposed_by": src},
                 f"Purchase spec ({'LLM' if src == 'llm' else 'rule baseline'}): gaps {gaps}. Need "
                 f"{', '.join(spec.required_fields) or '-'} for {spec.purpose}, missing rate under "
                 f"{spec.max_missing_rate:.0%}, up to {xrp(spec.budget_cap_drops)}.")
        if notes:
            self.say("verify", {"task": "infer_spec", "narrowed": notes},
                     "Code narrowed the spec to the owner's limits: " + "; ".join(notes) + ".")
        return spec

    def procure(self, goal: Spec, sellers: list[SellerAgent]) -> dict:
        st = self.engine.store
        available = min(self.engine.available_drops(self.id), goal.budget_cap_drops)
        wanted = goal.required_fields + goal.optional_fields
        if not goal.required_fields or not goal.required_scenarios:
            msg = "spec is empty after verification. Nothing bought."
            self.say("report", {"status": "not_purchased"}, msg)
            return {"goal": goal.text, "candidates": [], "status": "not_purchased", "reason": msg, "orders": []}

        cands: list[Candidate] = []
        for s in sellers:
            for prod in s.catalog():
                c = Candidate(s, prod)
                cands.append(c)
                if not set(prod["scenarios"]) & set(goal.required_scenarios):
                    c.excluded = "covers none of the gaps"
                    continue
                sample = s.sample(prod["id"])
                # L2: field mapping proposed, then checked against the sample
                c.mapping, rejected, _ = match_schema(st, self.id, prod, wanted, sample, self.propose)
                lost = [f for f in goal.required_fields if f not in c.mapping]
                if lost:
                    c.excluded = "; ".join(f"{f}: {rejected.get(f, 'no match')}" for f in lost)
                else:
                    native = [c.mapping[f] for f in goal.required_fields]
                    c.quality = check_quality(sample, native)
                    if c.quality["missing_rate"] > goal.max_missing_rate:
                        c.excluded = f"sample missing rate {c.quality['missing_rate']:.0%} above limit"
                    elif c.quality["duplicate_rate"] > goal.max_duplicate_rate:
                        c.excluded = f"sample duplicate rate {c.quality['duplicate_rate']:.0%} above limit"
                if c.excluded:
                    self.say("evaluate", {"product": prod["id"], "mapping": c.mapping, "excluded": c.excluded},
                             f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}.", to=s.id)
                    continue
                renamed = {k: v for k, v in c.mapping.items() if k != v}
                self.say("evaluate", {"product": prod["id"], "mapping": c.mapping, "quality": c.quality},
                         f"{prod['seller']}/{prod['id']}: fields verified on sample"
                         + (f" ({', '.join(f'{v} = {k}' for k, v in renamed.items())})" if renamed else "")
                         + f", missing {c.quality['missing_rate']:.1%}.", to=s.id)
                # L3: licence text read, then confirmed by the seller's own terms
                reading, _ = read_licence(st, self.id, prod, self.propose)
                c.terms, corrected = s.confirm_terms(self.id, prod["id"], reading)
                if not c.terms.get(goal.purpose):
                    c.excluded = f"licence does not allow {goal.purpose}"
                    self.say("evaluate", {"product": prod["id"], "terms": c.terms, "excluded": c.excluded},
                             f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}.", to=s.id)
                    continue
                d, price = s.quote(self.id, prod["id"], [c.mapping[f] for f in wanted if f in c.mapping],
                                   goal.purpose)
                lost_required = [f for f in d.refused if f in (c.mapping[r] for r in goal.required_fields)]
                if d.status == DENY or lost_required:
                    c.excluded = d.reason or "seller refused required fields"
                    self.say("evaluate", {"product": prod["id"], "excluded": c.excluded},
                             f"{prod['seller']}/{prod['id']}: excluded - {c.excluded}.", to=s.id)
                    continue
                c.decision, c.price_drops = d, price
                c.terms_hash = terms_hash(prod["id"], c.terms, c.mapping)

        ok = [c for c in cands if not c.excluded]
        need = set(goal.required_scenarios)
        combos = []

        def episodes(combo, sc):
            return sum(c.product["scenarios"].get(sc, 0) for c in combo)

        for r in range(1, len(ok) + 1):
            for combo in itertools.combinations(ok, r):
                if all(episodes(combo, sc) >= goal.min_episodes for sc in need):
                    combos.append((sum(c.price_drops for c in combo), combo))
        combos.sort(key=lambda t: t[0])
        best = next(((cost, cb) for cost, cb in combos if cost <= available), None)
        report = {"goal": goal.text, "spec": {"required_fields": goal.required_fields,
                                              "required_scenarios": goal.required_scenarios,
                                              "purpose": goal.purpose, "budget_xrp": goal.budget_cap_drops / 1e6},
                  "candidates": [
            {"seller": c.product["seller"], "product": c.product["id"], "price_xrp": c.product["price_xrp"],
             "excluded": c.excluded, "quality": c.quality, "mapping": c.mapping, "terms": c.terms,
             "refused_fields": c.decision.refused if c.decision else []} for c in cands]}
        if best is None:
            if combos:
                gap = combos[0][0] - available
                msg = (f"no combination fits the available {xrp(available)}; cheapest full coverage "
                       f"costs {xrp(combos[0][0])}. Asking a human to approve +{xrp(gap)}. Nothing bought.")
                report["gap_xrp"] = gap / 1e6
            else:
                msg = "no verified data covers all required scenarios. Nothing bought."
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

        self.say("select", {"selected": ids, "cost_xrp": cost / 1e6, "covers": goal.required_scenarios,
                            "available_xrp": available / 1e6,
                            "alternatives": [{"products": [c.product["id"] for c in cb], "cost_xrp": x / 1e6}
                                             for x, cb in combos[1:4]]},
                 f"Compared fixed quotes: {' + '.join(ids)} for {xrp(cost)} is the cheapest combination that "
                 f"gives at least {goal.min_episodes} episodes of {', '.join(goal.required_scenarios)} within the "
                 f"{xrp(available)} available.")
        for c in combo:
            # The agreed terms hash goes into the order's terms and from there into the payment memo.
            c.decision.policy_version = f"{c.decision.policy_version}#{c.terms_hash[:12]}"
            allowed = [k for k in ("commercial_training", "evaluation", "redistribution") if c.terms.get(k)]
            self.say("contract", {"product": c.product["id"], "fields": c.decision.granted, "purpose": goal.purpose,
                                  "terms": c.terms, "terms_hash": c.terms_hash, "price_xrp": c.price_drops / 1e6},
                     f"{c.product['id']}: contract - {', '.join(c.decision.granted)} for {goal.purpose}; agreed terms "
                     f"allow {', '.join(allowed) or 'nothing else'}; terms hash {c.terms_hash[:12]} goes in the "
                     f"payment memo; {xrp(c.price_drops)}.", to=c.seller.id)
        orders = []
        for c in combo:
            rows = c.seller.connector.extract(c.product["id"], c.decision.granted)
            req = OrderRequest(self.id, c.seller.id, c.seller.id, c.product["id"], "once", goal.purpose,
                               c.decision.granted, c.price_drops, rows, c.decision, settle="escrow")
            oid = self.engine.place_order(req)
            status = self.engine.process(oid)
            orders.append({"order_id": oid, "product": c.product["id"], "status": status})
        spent = sum(c.price_drops for c, o in zip(combo, orders) if o["status"] == "delivered")
        remaining = self.engine.available_drops(self.id)
        done = ", ".join(f"{o['product']} {o['status']}" for o in orders)
        self.say("report", {"acquired": ids, "spent_xrp": spent / 1e6, "remaining_xrp": remaining / 1e6,
                            "orders": orders},
                 f"Done: {done}; spent {xrp(spent)}, remaining {xrp(remaining)}.")
        return {**report, "status": "purchased" if spent == cost else "partial", "selected": ids,
                "spent_xrp": spent / 1e6, "remaining_xrp": remaining / 1e6, "orders": orders}


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
                    automation: str = "auto_standard", min_price_drops: int = 0, quiet: bool = False):
        assert automation in AUTOMATION_LEVELS
        st = self.engine.store
        with st.tx() as c:
            cur = c.execute("SELECT version FROM consents WHERE person_id=? AND buyer_id=?",
                            (self.id, buyer_id)).fetchone()
            v = (cur["version"] + 1) if cur else 1
            h = self._write_consent(c, buyer_id, purpose, items, weeks, automation, min_price_drops, "active", v)
            if not quiet:
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
