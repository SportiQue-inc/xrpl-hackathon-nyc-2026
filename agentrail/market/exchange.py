"""One trade pipeline for every kind of data and every direction.

  need -> discover offers -> pre-trade quality check -> rank (grade x price) -> contract
       -> policy (plug-in) -> settle (XRPL escrow, key reveal) -> fitness check

Every account has its own agent, its own data and its own needs. Agents trade among themselves with
no human in the loop. The only thing that changes between an open market (Act 1) and healthcare
research (Act 2) is the policy plugged into the seller's agent: `OpenPolicy` lets through what the
owner listed; `SensitivityPolicy` adds tiered consent, safety-gate packages and the T3 rules. Same
code path, same ledger flow.

Prices are fixed quotes per tier and grade, never haggled. A market dataset already exists in full,
so it is a retrospective purchase (payout_schedule.retrospective): the buyer's agent inspects it
before buying (quality certificate, a sample opened against the committed root, the policy and
gates) and pays it whole by key-reveal escrow, nothing held. A delivery that fails the fitness check
after opening is recorded against the seller (its pass rate, and so its grade on every later
offer, falls) and noted as a refund claim off the ledger; paid money is never pulled back on chain.
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field

from ..db import Store
from ..engine import BudgetExceeded, Engine, NeedsHumanApproval, OrderRequest
from ..ledger.mock import MockLedger
from ..policy import ALLOW, BuyerMandate, Decision
from ..catalog import columns as catalog
from .. import payout_schedule
from . import quality

# ---------------- columns any account may hold ----------------

ROBOT = {
    "robot.lidar_scan": {"unit": "points", "lo": 1000, "hi": 200000, "tier": "R"},
    "robot.joint_torque": {"unit": "N·m", "lo": 0, "hi": 300, "tier": "R"},
    "robot.gripper_events": {"unit": "events/h", "lo": 0, "hi": 600, "tier": "R"},
    "fleet.battery_log": {"unit": "%", "lo": 0, "hi": 100, "tier": "R"},
    "smarthome.energy_kwh": {"unit": "kWh/day", "lo": 0, "hi": 80, "tier": "R"},
    "robot.lidar_points": {"unit": "points", "lo": 1000, "hi": 200000, "tier": "R"},
    "robot.accel_x": {"unit": "m/s2", "lo": -50, "hi": 50, "tier": "R"},
    "robot.wheel_speed": {"unit": "m/s", "lo": 0, "hi": 5, "tier": "R"},
    "robot.arm_torque": {"unit": "N·m", "lo": 0, "hi": 300, "tier": "R"},
    "robot.grasp_ok": {"unit": "0/1", "lo": 0, "hi": 1, "tier": "R"},
}


def spec(col: str) -> dict:
    if col in ROBOT:
        return ROBOT[col]
    c = catalog.CATALOG[col]
    return {"unit": c.unit, "lo": c.lo, "hi": c.hi, "tier": c.tier}


RATE = {"T0": 10_000, "T1": 15_000, "T2": 40_000, "T3": 120_000, "R": 20_000}      # drops per column-week, grade A
GRADE_MULT = {"A": 1.0, "B": 0.8, "C": 0.6}
GRADE_RANK = {"A": 3, "B": 2, "C": 1}
MIN_MATCHED_ROWS = 3
DUPLICATE_SHARE = 0.9       # an offer the buyer already holds this much of is refused; below it, only the new part is paid
DAYS = 7
SAMPLE_K = 12


def quote(columns, weeks: int, grade: str) -> int:
    return int(sum(RATE[spec(c)["tier"]] for c in columns) * weeks * GRADE_MULT[grade])


# ---------------- accounts, data, needs ----------------

@dataclass
class Dataset:
    id: str
    owner: str
    columns: list
    weeks: int
    completeness: float
    issuer: dict
    fault: str | None = None          # wrong_unit | drift | copy | bait
    rows: list = field(default_factory=list)
    salts: list = field(default_factory=list)
    shown: object = None              # what the sample is opened from (differs only for bait)
    meta: dict = field(default_factory=dict)   # e.g. pseudonymized imaging, genomic loci

    def build(self, seed: str, copy_of: "Dataset | None" = None):
        rng = random.Random(seed)
        rows = []
        n = self.meta.get("rows", self.weeks * DAYS)
        for d in range(n):
            r = {"day": d}
            for c in self.columns:
                s = spec(c)
                if rng.random() > self.completeness:
                    r[c] = None
                    continue
                if self.meta.get("transform") and c in self.meta["transform"]:
                    v = self.meta["transform"][c](self.owner, d)
                elif c in ROBOT:
                    v = rng.uniform(s["lo"] + (s["hi"] - s["lo"]) * 0.2, s["lo"] + (s["hi"] - s["lo"]) * 0.6)
                    v = round(v) if c in ("robot.lidar_points", "robot.lidar_scan", "robot.grasp_ok") else round(v, 3)
                else:
                    v = catalog.synth(c, self.owner, d)
                if isinstance(v, (int, float)) and self.fault == "drift" and d >= n // 2:
                    v = round(v + (s["hi"] - s["lo"]) * 0.25, 3)
                r[c] = v
            rows.append(r)
        if copy_of is not None:
            rows = [{**r} for r in copy_of.rows]
        self.rows = rows
        self.salts = [hashlib.sha256(f"{seed}|salt|{i}".encode()).hexdigest()[:16] for i in range(len(rows))]
        self.shown = quality.Committed(rows, self.salts)

    def delivered(self) -> tuple[list, list]:
        """What the seller actually sends. Honest sellers send what they committed."""
        if self.fault == "wrong_unit":
            c = next((c for c in self.columns if c in ROBOT or catalog.CATALOG[c].kind == "numeric"), None)
            if c is None:                   # nothing numeric to put in the wrong unit
                return self.rows, self.salts
            return [{**r, c: (r[c] * 60 if isinstance(r.get(c), (int, float)) else r.get(c))} for r in self.rows], self.salts
        if self.fault == "bait":
            return [{**r, **{c: None for c in self.columns}} if i % 2 else r for i, r in enumerate(self.rows)], self.salts
        return self.rows, self.salts


@dataclass
class Need:
    id: str
    buyer: str
    columns: list
    weeks: int
    quantity: int
    purpose: str
    min_grade: str = "C"
    match: dict = field(default_factory=dict)      # attribute filter, e.g. {"job": "nurse"}
    posted_h: float = 0.0
    why: str = ""
    output: str = "raw"             # raw | aggregate (computed on the provider side)
    loci: list = field(default_factory=list)
    plan: dict = field(default_factory=dict)        # how the buyer's agent formed the need (gap, budget)


@dataclass
class Account:
    id: str
    name: str
    kind: str                       # person | org
    attrs: dict = field(default_factory=dict)
    datasets: list = field(default_factory=list)
    needs: list = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    policy: object = None
    seller: quality.Seller = None
    credentials: set = field(default_factory=set)


# ---------------- policies (the only part that differs between acts) ----------------

class OpenPolicy:
    """Act 1: the owner listed the dataset for these purposes; anything listed may be traded."""
    name = "open"

    def __init__(self, refuse_purposes=("marketing_profiling", "insurance_pricing", "employment_screening")):
        self.refuse = set(refuse_purposes)

    def check(self, trade: dict) -> tuple[str, str]:
        if trade["purpose"] in self.refuse:
            return "refuse", f"purpose {trade['purpose']} is never allowed"
        return "allow", "listed by the owner"


# ---------------- the exchange ----------------

class Exchange:
    def __init__(self, accounts: list[Account], ledger=None, store: Store | None = None, seed: int = 5,
                 owner_response_h=lambda rng: rng.expovariate(1 / 18.0)):
        self.accounts = {a.id: a for a in accounts}
        self.ledger = ledger or MockLedger()
        self.engine = Engine(store or Store(":memory:"), self.ledger)
        self.rng = random.Random(seed)
        self.owner_response_h = owner_response_h
        self.trades: list[dict] = []
        self.events: list[dict] = []
        self.pending: list[dict] = []           # waiting for an owner (safety gate)
        self.seen_series: dict[str, str] = {}   # series hash -> seller (duplicate check)
        self._grants: dict[tuple, Decision] = {}
        self.book = None                        # shared offer book, anchored on the ledger (publish_book)
        self.anchors: list[dict] = []
        self.contracts: list[dict] = []          # one conversation per contract attempt (contract_trace)
        self.holdings: dict[str, dict] = {}      # buyer -> {"roots", "rows"}: what each buyer's store already holds
        self._explained = 0
        for a in accounts:
            a.seller = a.seller or quality.Seller(a.id)
            self.engine.add_party(a.id, a.name, a.kind, self.ledger.new_account(a.id))
            self.engine.policies[a.id] = _EnginePolicy(self, a.id)

    # ----- offers -----
    def offers(self) -> list[dict]:
        out = []
        for a in self.accounts.values():
            for ds in a.datasets:
                rep = quality.reputation(a.passed, a.failed, all(i in a.credentials or i == "self"
                                                                for i in ds.issuer.values()))
                cert = a.seller.certify(ds.id, ds.shown.rows, {c: spec(c) for c in ds.columns}, ds.issuer, rep,
                                        ds.shown, scope="dataset" if a.kind == "org" else "person")
                if cert["grade"] is None:
                    continue
                out.append({"seller": a.id, "dataset": ds, "cert": cert, "grade": cert["grade"]})
        return out

    # ----- the person's agent also collects, within the person's rules -----
    def collect(self, need: Need, missing: int) -> list[dict]:
        """When a need went short, each person's agent checks whether it could fill the gap from a
        source the person already connected (attrs["sources"]: {column: source}). T0 and T1 sync
        automatically; T2 only if the person opted in (attrs["collect_t2"]); T3 (genomic, imaging) is
        never collected automatically. Collecting only creates the person's own dataset: selling it
        still goes through the person's policy and the pre-trade quality check like anything else."""
        if need.output != "raw" or any(c in ROBOT for c in need.columns):
            return []
        out = []
        for a in self.accounts.values():
            src = a.attrs.get("sources") or {}
            if a.id == need.buyer or a.kind != "person" or not src:
                continue
            if any(set(need.columns) <= set(d.columns) for d in a.datasets):
                continue
            tiers = {spec(c)["tier"] for c in need.columns}
            if not set(need.columns) <= set(src) or "T3" in tiers or ("T2" in tiers and not a.attrs.get("collect_t2")):
                continue
            weeks = max([d.weeks for d in a.datasets if d.meta.get("rows") is None] + [need.weeks])
            ds = Dataset(f"{a.id}:collected:{'+'.join(need.columns)}", a.id, list(need.columns), weeks, 0.95,
                         {c: src[c] for c in need.columns}, meta={"collected_for": need.id,
                                                                  "source": {c: src[c] for c in need.columns}})
            ds.build(ds.id)
            a.datasets.append(ds)
            ev = {"kind": "collected", "person": a.id, "columns": need.columns, "weeks": weeks,
                  "from": sorted(set(src[c] for c in need.columns)), "for_need": need.id, "dataset": ds.id}
            self.events.append(ev)
            out.append(ev)
            if len(out) >= missing + 1:      # one spare: a person's own policy may still say no
                break
        return out

    # ----- the shared offer book -----
    def publish_book(self) -> dict:
        """List every certified dataset in the shared offer book and anchor its root on the ledger."""
        from .discovery import OfferBook
        if self.book is None:
            self.book = OfferBook(self.ledger, self.ledger.new_account("market_registry"),
                                  self.ledger.new_account("market_registry_sink"))
        r = self.book.publish(self.offers())
        self.events.append({"kind": "offer_book", **r})
        self.anchors.append(r)
        return r

    # ----- one need, end to end -----
    def fill(self, need: Need, now_h: float | None = None) -> dict:
        t0 = time.time()
        now_h = need.posted_h if now_h is None else now_h
        cands, rejected, fills, collected = [], [], [], []
        disc = {"listed": 0, "anchored_root": self.book.root if self.book else None,
                "anchor_tx": self.book.anchor_tx if self.book else None, "dropped": {}, "sampled": [],
                "ranked": []}
        gated = self._fill_pass(need, now_h, None, cands, rejected, fills, disc)
        if not gated and len(fills) < need.quantity:
            # short: the sellers' agents may collect the missing data from sources their people connected
            collected = self.collect(need, need.quantity - len(fills))
            if collected:
                if self.book is not None:       # newly collected datasets are listed before anyone may buy them
                    r = self.publish_book()
                    disc["relisted"] = {"root": r["root"], "tx": r["tx"]}
                self._fill_pass(need, now_h, {e["dataset"] for e in collected}, cands, rejected, fills, disc)
        from .discovery import explain, explain_budget
        chosen = [f["seller"] for f in fills]
        use_llm = self._explained < explain_budget() and bool(disc["ranked"])
        self._explained += use_llm
        disc["explanation"] = explain(need.id, self._ceiling(need), disc["ranked"], chosen, use_llm=use_llm)
        out = {"need": need.id, "buyer": need.buyer, "columns": need.columns, "purpose": need.purpose,
               "wanted": need.quantity, "filled": sum(1 for f in fills if f["status"] == "settled"),
               "unfit": sum(1 for f in fills if f["status"] == "settled_unfit"),
               "offers_seen": len(cands) + len([r for r in rejected if r.get("stage") == "pre_trade"]),
               "rejected": rejected, "fills": fills, "collected": collected, "wall_s": round(time.time() - t0, 3),
               "plan": need.plan, "discovery": disc}
        self.events.append({"kind": "need", **{k: v for k, v in out.items() if k not in ("fills", "rejected")}})
        return out

    @staticmethod
    def _row_key(row: dict, cols: list) -> str:
        """Content of one row for the overlap check: day and values, without the seller, so a copy listed
        by someone else still matches."""
        return hashlib.sha256(json.dumps([row.get("day")] + [row.get(c) for c in sorted(cols)],
                                         default=str).encode()).hexdigest()

    @staticmethod
    def _telling(row: dict, cols: list) -> bool:
        """Only rows with a measured, non-round value say who they came from; yes/no answers and
        whole-number scores repeat across people by chance, so they never count as overlap."""
        return any(isinstance(row.get(c), float) and not float(row[c]).is_integer() for c in cols)

    def overlap(self, buyer: str, cert_root: str, sample_rows: list[dict], cols: list) -> tuple[float, str]:
        """How much of an offer the buyer already holds: 1.0 for a dataset with a certified root it
        bought before, else the share of the opened sample rows whose content it already holds."""
        h = self.holdings.get(buyer)
        if not h:
            return 0.0, ""
        if cert_root in h["roots"]:
            return 1.0, "same certified root as data I already bought"
        keys = [self._row_key(r, cols) for r in sample_rows if self._telling(r, cols)]
        same = sum(1 for k in keys if k in h["rows"])
        if same < MIN_MATCHED_ROWS:          # a few equal readings on the same day happen by chance
            return 0.0, ""
        return same / max(1, len(keys)), f"{same} of {len(keys)} sampled rows match rows I already hold"

    def _hold(self, buyer: str, o: dict, cols: list, weeks: int) -> None:
        h = self.holdings.setdefault(buyer, {"roots": set(), "rows": set()})
        h["roots"].add(o["cert"]["root"])
        h["rows"].update(self._row_key(r, cols) for r in o["dataset"].rows[: weeks * DAYS] if self._telling(r, cols))

    def _ceiling(self, need: Need) -> dict:
        """The need as the buyer's agent formed it; without a plan, the grade A asking price is the ceiling."""
        return {"columns": need.columns, "weeks": need.weeks,
                "max_price_drops": need.plan.get("max_price_drops") or quote(need.columns, need.weeks, "A")}

    def _fill_pass(self, need, now_h, only, cands, rejected, fills, disc=None) -> bool:
        """Query the shared offer book, filter, check a hashed sample of each survivor, score them,
        negotiate with the best in order and trade. Returns True when a gate on the buyer itself refused
        (every other seller would say the same)."""
        from .discovery import negotiate, score
        disc = disc if disc is not None else {"listed": 0, "dropped": {}, "sampled": [], "ranked": []}
        drop = lambda why: disc["dropped"].__setitem__(why, disc["dropped"].get(why, 0) + 1)
        ceiling = self._ceiling(need)
        book = self.offers()
        disc["listed"] = max(disc["listed"], len(book))
        mine = []
        for o in book:
            ds, seller = o["dataset"], self.accounts[o["seller"]]
            if only is not None and ds.id not in only:
                continue
            if seller.id == need.buyer:
                continue
            if not set(need.columns) <= set(ds.columns):
                drop("other columns")
                continue
            if ds.weeks < need.weeks:
                drop("too few weeks")
                continue
            if any(seller.attrs.get(k) != v for k, v in need.match.items()):
                drop("seller attributes")
                continue
            if GRADE_RANK[o["grade"]] < GRADE_RANK[need.min_grade]:
                drop("grade below minimum")
                continue
            if self.book is not None and not self.book.anchored(o):
                drop("not in the anchored offer book")
                continue
            bad = quality.check_certificate(o["cert"])
            nonce = f"{need.id}|{seller.id}|{self.rng.random()}"
            opened = ds.shown.open(quality.sample_indices(len(ds.rows), SAMPLE_K, nonce))
            ok, why = (False, bad) if bad else quality.check_sample(o["cert"], opened, {c: spec(c) for c in need.columns})
            disc["sampled"].append({"seller": seller.id, "grade": o["grade"], "ok": ok, **({} if ok else {"why": why})})
            if not ok:
                rejected.append({"seller": seller.id, "stage": "pre_trade", "why": why})
                continue
            ask = quote(need.columns, need.weeks, o["grade"])
            ov, ov_why = self.overlap(need.buyer, o["cert"]["root"], [x["row"] for x in opened], need.columns)
            if ov >= DUPLICATE_SHARE:
                # already in the buyer's store: never pay again for the same data
                drop("already held")
                disc["sampled"][-1].update(ok=False, why=f"duplicate: {ov_why}")
                rejected.append({"seller": seller.id, "stage": "overlap", "why": f"duplicate: {ov_why}"})
                continue
            sc = score(o, int(ask * (1 - ov)), ceiling, (seller.passed, seller.failed))
            if ov:
                sc.update(overlap=round(ov, 3), overlap_why=ov_why, full_ask_drops=ask)
            mine.append((sc, o, int(ask * (1 - ov))))
        mine.sort(key=lambda x: (-x[0]["score"], x[0]["seller"]))
        cands += mine
        first = len(disc["ranked"])
        disc["ranked"] += [m[0] for m in mine]
        from . import contract_trace
        for i, (sc, o, ask) in enumerate(mine):
            if len(fills) >= need.quantity:
                break
            seller = self.accounts[o["seller"]]
            track = (seller.passed, seller.failed)          # before this trade, as the agents saw it
            neg = negotiate(ask, ceiling["max_price_drops"], track)
            disc["ranked"][first + i]["negotiation"] = neg
            cand = {**sc, "rank": first + i + 1}
            if not neg["deal"]:
                rejected.append({"seller": seller.id, "stage": "negotiation", "why": neg["why"]})
                self.contracts.append(contract_trace.build(need, need.plan, disc, cand, {**neg, "ceiling": ceiling["max_price_drops"]},
                                                           None, seller, self.accounts[need.buyer], track))
                continue
            r = self._trade(need, o, neg["price_drops"], now_h)
            disc["ranked"][first + i]["outcome"] = r["status"]
            r["trace"] = len(self.contracts)
            if r["status"] in ("settled", "settled_unfit"):
                self._hold(need.buyer, o, need.columns, need.weeks)
            self.contracts.append(contract_trace.build(need, need.plan, disc, cand, {**neg, "ceiling": ceiling["max_price_drops"]},
                                                       r, seller, self.accounts[need.buyer], track))
            if r["status"] == "refused" and r["why"].startswith("blocked: no valid") or \
                    r["status"] == "refused" and "credential has expired" in r["why"]:
                rejected.append(r)
                return True
            (fills if r["status"] in ("settled", "settled_unfit") else rejected).append(r)
        return False

    def _trade(self, need: Need, o: dict, price: int, now_h: float) -> dict:
        seller = self.accounts[o["seller"]]
        ds = o["dataset"]
        terms = {"buyer": need.buyer, "seller": seller.id, "dataset": ds.id, "columns": need.columns,
                 "weeks": need.weeks, "purpose": need.purpose, "grade": o["grade"], "price_drops": price,
                 "root": o["cert"]["root"]}
        contract = hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()
        trade = {**terms, "contract": contract, "need": need.id, "posted_h": need.posted_h,
                 "buyer_attrs": self.accounts[need.buyer].attrs, "why": need.why,
                 "pseudonymized": ds.meta.get("pseudonymized", False), "output": need.output,
                 "loci": need.loci}
        verdict, why = (seller.policy or OpenPolicy()).check(trade)
        base = {"need": need.id, "seller": seller.id, "buyer": need.buyer, "contract": contract[:16],
                "grade": o["grade"], "price_drops": price, "policy": getattr(seller.policy, "name", "open"),
                "columns": need.columns, "weeks": need.weeks, "purpose": need.purpose, "posted_h": need.posted_h,
                "need_why": need.why, "min_grade": need.min_grade, "sample_k": SAMPLE_K, "root": o["cert"]["root"][:16]}
        try:
            from .policies import trust_grade
            base["buyer_grade"] = trust_grade({**self.accounts[need.buyer].attrs,
                                               "owner_country": getattr(seller.policy, "home", "KR")})[0]
        except Exception:
            pass
        if verdict == "refuse":
            return self._log({**base, "status": "refused", "stage": "policy", "why": why})
        base["why"] = why
        wait_h = 0.0
        if verdict == "gate":
            if getattr(seller.policy, "manual", False):
                self.pending.append({**base, "trade": trade, "offer": o, "why": why})
                return self._log({**base, "status": "awaiting_owner", "stage": "policy", "why": why})
            ok, wait_h = seller.policy.owner_answers(trade, self.rng, self.owner_response_h)
            if not ok:
                return self._log({**base, "status": "declined", "stage": "policy", "why": f"owner declined ({why})"})
            base["why"] = f"owner approved after {wait_h:.1f} h ({why})"
        return self.settle(trade, o, price, now_h + wait_h, base)

    def approve_pending(self, i: int, assertion: dict | None = None, now_h: float | None = None) -> dict:
        """The person who approves by hand answers one queued trade. Under tiered consent the answer is
        the Touch ID assertion over the institution's consent package."""
        p = self.pending[i]
        seller = self.accounts[p["seller"]]
        owner = getattr(seller.policy, "owner", None)
        if owner is not None:
            inst = p["trade"]["buyer_attrs"].get("institution", p["buyer"])
            pkg = owner.package(inst)
            if pkg:
                r = owner.approve(inst, assertion or {}, remember=False)
                if not r["ok"]:
                    return {"ok": False, "reason": r["reason"]}
        self.pending.pop(i)
        base = {k: v for k, v in p.items() if k not in ("trade", "offer")}
        base["why"] = "approved by the owner"
        return self.settle(p["trade"], p["offer"], p["price_drops"], p["trade"]["posted_h"] if now_h is None else now_h, base)

    def settle(self, trade: dict, o: dict, price: int, at_h: float, base: dict) -> dict:
        need_cols, ds, seller = trade["columns"], o["dataset"], self.accounts[o["seller"]]
        rows, salts = ds.delivered()
        part = [{"day": r["day"], **{c: r.get(c) for c in need_cols}} for r in rows[: trade["weeks"] * DAYS]]
        if trade.get("output") == "aggregate":
            from .genomic import aggregate
            part = aggregate(part, need_cols, trade.get("loci", []))
        if trade.get("output") != "aggregate" and not quality.delivery_matches(o["cert"], rows, salts):
            # The gate holds the plain rows here: a seller who opened good samples but sends other rows is
            # stopped before any escrow exists, instead of being paid and leaving the buyer a refund claim.
            seller.failed += 1
            return self._log({**base, "status": "refused", "stage": "binding", "paid_drops": 0,
                              "why": "delivery does not hash to the certified root; no escrow created",
                              "signals": [{"code": "not_as_committed",
                                           "detail": "delivery does not hash to the certified root"}]})
        main = payout_schedule.retrospective(price)["upfront_drops"]
        self._grants[(trade["buyer"], seller.id, trade["contract"])] = Decision(ALLOW, granted=list(need_cols))
        req = OrderRequest(trade["buyer"], seller.id, seller.id, f"contract:{trade['contract']}",
                           f"{ds.id}|{trade['need']}", trade["purpose"], list(need_cols), main, part,
                           Decision(ALLOW, granted=list(need_cols), policy_version=base["policy"]), settle="escrow",
                           extra={"contract": trade, **({"aggregate": True} if trade.get("output") == "aggregate"
                                                         else {"full_rows": rows, "salts": salts})})
        try:
            oid = self.engine.place_order(req)
            status = self.engine.process(oid)
        except (BudgetExceeded, NeedsHumanApproval) as e:
            return self._log({**base, "status": "no_budget", "stage": "settle", "why": str(e)})
        if status != "delivered":
            return self._log({**base, "status": "not_settled", "stage": "settle", "why": status})
        pm = self.engine.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        payload = self.engine.open_payload(trade["buyer"], oid)
        ok, signals = self.fitness(o["cert"], payload, need_cols, seller.id)
        txs = {"escrow_create": pm["tx_hash"], "escrow_finish": pm["finish_tx"]}
        if ok:
            seller.passed += 1
        else:
            seller.failed += 1
        return self._log({**base, "status": "settled" if ok else "settled_unfit", "stage": "fitness",
                          "order_id": oid, "paid_drops": main, "withheld_drops": 0, "schedule": "retrospective",
                          **({} if ok else {"refund_claim_drops": main}),
                          "signals": signals, "txs": txs, "filled_h": round(at_h, 3),
                          "hours_to_fill": round(at_h - trade["posted_h"], 3),
                          "urls": {k: self.ledger.explorer_url(v) for k, v in txs.items() if v}})

    def fitness(self, cert: dict, payload: dict, cols: list, seller: str) -> tuple[bool, list]:
        sig = []
        if payload.get("aggregate"):
            # Computed on the provider's side; raw rows never leave, so the root cannot be re-checked here.
            return (bool(payload["rows"]), [] if payload["rows"] else [{"code": "incomplete"}])
        if not quality.delivery_matches(cert, payload["full_rows"], payload["salts"]):
            sig.append({"code": "not_as_committed", "detail": "delivery does not hash to the certified root"})
        rows = payload["rows"]
        # The rows the buyer uses must be the certified rows, not a second list sent alongside them.
        from_full = [{"day": r["day"], **{c: r.get(c) for c in cols}} for r in payload["full_rows"][: len(rows)]]
        if from_full != rows:
            sig.append({"code": "not_as_committed", "detail": "delivered rows differ from the certified rows"})
            rows = from_full
        for c in cols:
            s = spec(c)
            xs = [r[c] for r in rows if isinstance(r.get(c), (int, float))]
            if s["lo"] is not None and xs and sum(not s["lo"] <= x <= s["hi"] for x in xs) > len(xs) * 0.1:
                sig.append({"code": "impossible_value", "column": c})
            comp = len([r for r in rows if r.get(c) is not None]) / max(1, len(rows))
            claim = cert["columns"][c]["completeness"]
            if comp + 2 * (claim * (1 - claim) / max(1, len(rows))) ** 0.5 + 0.05 < claim:
                sig.append({"code": "incomplete", "column": c, "detail": f"{comp:.2f}"})
            if len(xs) >= 6:
                a, b = xs[: len(xs) // 2], xs[len(xs) // 2:]
                mu = sum(a) / len(a)
                sd = (sum((x - mu) ** 2 for x in a) / len(a)) ** 0.5 or 1.0
                if abs(sum(b) / len(b) - mu) / sd > 3:
                    sig.append({"code": "drift", "column": c})
        series = hashlib.sha256(json.dumps([{c: r.get(c) for c in cols} for r in rows], sort_keys=True).encode()).hexdigest()
        first = self.seen_series.setdefault(series, seller)
        if first != seller:
            sig.append({"code": "duplicate", "detail": f"same series as {first}"})
        return not sig, sig

    def _log(self, r: dict) -> dict:
        self.trades.append(r)
        return r

    # ----- activity for the UI -----
    def activity(self) -> dict:
        t = self.trades
        settled = [x for x in t if x["status"] in ("settled", "settled_unfit")]
        by = {}
        for x in t:
            by[x["status"]] = by.get(x["status"], 0) + 1
        hrs = sorted(x["hours_to_fill"] for x in settled)
        return {"trades": len(t), "by_status": by, "needs": len([e for e in self.events if e["kind"] == "need"]),
                "volume_xrp": round(sum(x.get("paid_drops", 0) for x in settled) / 1e6, 6),
                "withheld_xrp": round(sum(x.get("withheld_drops", 0) for x in settled) / 1e6, 6),
                "refund_claims_xrp": round(sum(x.get("refund_claim_drops", 0) for x in settled) / 1e6, 6),
                "median_hours_to_fill": hrs[len(hrs) // 2] if hrs else None,
                "awaiting_owner": len(self.pending),
                "auto_collected": len([e for e in self.events if e["kind"] == "collected"]),
                "collected_recent": [e for e in self.events if e["kind"] == "collected"][-10:], "recent": t[-30:]}


class _EnginePolicy:
    """What the engine re-checks right before money moves and before delivery: the decision this
    exchange recorded for the contract (and nothing broader)."""

    def __init__(self, ex: Exchange, seller: str):
        self.ex, self.seller = ex, seller

    def evaluate(self, buyer_id, purpose, fields, price_drops, week=None, for_delivery=False):
        for (b, s, _), d in self.ex._grants.items():
            if b == buyer_id and s == self.seller and set(fields) <= set(d.granted):
                return d
        return Decision("deny", reason="no recorded decision for this trade")
