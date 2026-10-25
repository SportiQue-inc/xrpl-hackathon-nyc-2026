"""One procurement round under data contracts, run window by window as contributions arrive.

  recruit   providers share profiles; agents negotiate a contract each; the buyer ranks them
            (forecast strategy: expected usable windows per XRP; price strategy: lowest price)
  window    each contracted provider seals its window; the buyer checks the manifest before any
            escrow (provenance, period), pays 80% by key-reveal escrow, checks the values, and
            releases the held 20% of that contribution only on a pass (a failure goes to review)
  replace   a failed provider is dropped for the rest of the round and the next-best provider is
            contracted for the remaining windows; with the forecast strategy a backup is also
            recruited ahead of time when the expected passes for the next window fall short
  project   after every contribution: usable so far, expected final usable with a 90% band,
            the power that implies, and the providers at risk for the coming windows

The same loop runs on accounting only (for measurement over hundreds of synthetic providers) or on
the ledger through the engine (`LedgerSettle`), where every escrow and release is a transaction.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from .. import payout_schedule
from ..cohort import power
from . import fitness, forecast, market
from .profile import profile
from .terms import Contract, Requirements, _forecast_by_window, negotiate


def requirements(buyer: str = "org_sleeplab", tier: str = "A", lowest: str = "B") -> Requirements:
    """The buyer's per-column requirements for the secondary analysis (sleep duration vs resting HR)."""
    from .terms import ColumnReq
    return Requirements(buyer, "sleep_research", ["DUO:0000006", "DUO:0000046"], [
        ColumnReq("sleep_minutes", "min/day", must=True),
        ColumnReq("resting_hr", "bpm", must=True, substitutes=[{"column": "resting_hr_b", "source": "wrist_device_b"}]),
    ], list(market.ROUND), tier, lowest, min_windows=2)


def as_asked(req: Requirements, provider: str, price: int, prof: dict, holder: str) -> Contract:
    """No negotiation: every column as asked, every window, at the tier-A quote (the fixed-quote-only
    flow). Judged at the lowest completeness the buyer can use, so it is not failed for a stricter bar."""
    from .terms import TIERS
    terms = [{"column": c.column, "source": prof["columns"].get(c.column, {}).get("source", "?"), "unit": c.unit,
              "min_completeness": TIERS[req.lowest_tier]["min_completeness"], "drift_sd": c.drift_sd, "ref": c.column,
              "windows": list(req.windows)} for c in req.columns]
    return Contract(req.buyer, provider, req.purpose, req.duo, req.tier, price, terms, list(req.windows),
                    req.hash(), holder)


class Accounting:
    """No ledger: amounts only."""
    name = "accounting"

    def key_for(self, rnd, p, k, wnum) -> bytes:
        """The participant agent's K for this window (synthetic, deterministic per contribution)."""
        return hashlib.sha256(f"K|{p.id}|{k.hash}|{wnum}".encode()).digest()

    def pay_immediate(self, rnd, p, k, wnum, payload, amount):
        return {"paid": amount, "payload": payload}

    def hold(self, rnd, p, k, wnum, amount, passed, signals, ref):
        return {"released": amount if passed else 0, "held": 0 if passed else amount}


@dataclass
class Round:
    req: Requirements
    pool: list
    registry: object
    issuers: dict
    model: forecast.Model | None = None
    strategy: str = "forecast"           # forecast | price
    negotiation: bool = True
    checks: bool = True                  # False: manual flow, everything paid, reviewed at the end
    target: int = 40                     # usable provider-windows wanted
    effect_r: float = 0.3
    settle: object = field(default_factory=Accounting)
    consent_hash_of: object = None
    owner_allows_of: object = None
    log: object = None
    drop_on_fail: bool = True            # False only when collecting training histories

    def __post_init__(self):
        self.by_id = {p.id: p for p in self.pool}
        self.profiles = {p.id: self._profile(p) for p in self.pool}
        self.contracts: dict[str, Contract] = {}
        self.transcripts: dict[str, list] = {}
        self.active: set[str] = set()
        self.tried: set[str] = set()
        self.stats = {}                     # pid -> {"pass", "n", "drift"}
        self.sources = {}                   # issuer -> [pass, n]
        self.outcomes: list[dict] = []
        self.projections: list[dict] = []
        self.warnings: list[dict] = []
        self.seen: dict = {}
        self.history: dict[str, list[bool]] = {}         # provider -> verified weeks, for the continuity curve
        self.twins = {}

    # ---------- provider side ----------
    def _profile(self, p):
        prof = profile([market.COLUMNS[c] for c in p.cols], p.history_rows(), market.window_of)
        for c in prof["columns"]:
            if p.cols[c].source != market.COLUMNS[c].source:
                prof["columns"][c]["source"] = p.cols[c].source
        prof["device"] = {"sync_regularity": p.sync}
        return prof

    # ---------- forecast ----------
    def features(self, pid: str, k: Contract, wnum: int) -> list[float]:
        prof = self.profiles[pid]
        comps, srcs, declining = [], [], 0.0
        for t in k.terms:
            if wnum not in t["windows"]:
                continue
            cp = prof["columns"].get(t["column"])
            if cp is None:
                comps.append(-1.0)
                continue
            comps.append((_forecast_by_window(cp, [wnum])[wnum]["mean"] or 0.0) - t["min_completeness"])
            declining = max(declining, 1.0 if cp["behaviour"]["completeness"] == "declining" else 0.0)
            srcs.append(t["source"])
        st = self.stats.get(pid, {"pass": 0, "n": 0, "drift": 0.0})
        sp = [(self.sources.get(s, [0, 0])[0] + 4) / (self.sources.get(s, [0, 0])[1] + 5) for s in srcs] or [0.8]
        return forecast.features(completeness_margin=min(comps) if comps else -1.0, declining=declining,
                                 sync_regularity=prof["device"]["sync_regularity"],
                                 source_pass_rate=sum(sp) / len(sp),
                                 round_pass_rate=(st["pass"] + 1) / (st["n"] + 1),
                                 drift_so_far=min(1.0, st["drift"] / 10))

    def p_pass(self, pid, k, wnum) -> float:
        if self.model is None:
            return 0.8
        return self.model.p(self.features(pid, k, wnum))

    # ---------- recruit ----------
    def _contract(self, p, windows):
        prof = self.profiles[p.id]
        holder = fitness.holder_for(p.id, self.req.buyer).pub
        req = Requirements(**{**self.req.__dict__, "windows": windows,
                              "min_windows": min(self.req.min_windows, len(windows))})
        if not self.negotiation:
            return as_asked(req, p.id, p.price_drops, prof, holder), []
        allows = self.owner_allows_of(p.id) if self.owner_allows_of else None
        return negotiate(req, p.id, prof, p.price_drops, allows, holder=holder)

    def _value(self, p, k):
        if self.strategy == "price" or not k.windows:
            return -k.price_drops_per_window
        exp = sum(self.p_pass(p.id, k, w) for w in k.windows)
        return exp / (k.price_drops_per_window * len(k.windows) / 1e6)

    def recruit(self, windows: list[int], n: int, why: str) -> list[str]:
        cands = []
        for p in self.pool:
            if p.id in self.tried:
                continue
            k, log = self._contract(p, windows)
            if k.status != "agreed":
                self.tried.add(p.id)
                self.transcripts[p.id] = log
                continue
            cands.append((self._value(p, k), p, k, log))
        cands.sort(key=lambda x: -x[0])
        got = []
        for _, p, k, log in cands[:n]:
            self.tried.add(p.id)
            self.contracts[p.id], self.transcripts[p.id] = k, log
            self.active.add(p.id)
            got.append(p.id)
        if self.log and got:
            def desc(pid):
                k = self.contracts[pid]
                subs = [f"{t['ref']} from {t['column']} ({t['source']})" for t in k.terms if t["ref"] != t["column"]]
                return (f"{pid} (tier {k.tier}, windows {k.windows[0]}-{k.windows[-1]}"
                        + (f", {'; '.join(subs)}" if subs else "") + f", contract {k.hash[:12]})")
            self.log("recruit", f"{why}: contracted {', '.join(desc(p) for p in got)}")
        return got

    # ---------- one contribution ----------
    def _record(self, pid, k, wnum, stage, signals, paid, held, released, txs=None, x=None):
        ok = not signals
        st = self.stats.setdefault(pid, {"pass": 0, "n": 0, "drift": 0.0})
        st["n"] += 1
        st["pass"] += ok
        st["drift"] = max(st["drift"], max([s.get("z", 0) for s in signals] or [0]))
        for t in k.terms:
            if wnum in t["windows"]:
                s = self.sources.setdefault(t["source"], [0, 0])
                s[0] += ok
                s[1] += 1
        o = {"provider": pid, "window": wnum, "stage": stage, "verdict": "pass" if ok else "fail",
             "signals": signals, "paid_drops": paid, "held_drops": held, "released_drops": released,
             "contract": k.hash, "tier": k.tier, "txs": txs or {}, "x": x}
        self.outcomes.append(o)
        return o

    def contribute(self, pid: str, wnum: int) -> dict:
        p, k = self.by_id[pid], self.contracts[pid]
        x = self.features(pid, k, wnum)
        consent = self.consent_hash_of(pid) if self.consent_hash_of else "synthetic-consent-v1"
        key = self.settle.key_for(self, p, k, wnum) if hasattr(self.settle, "key_for") else None
        payload = fitness.deliver(p, k, wnum, self.issuers, consent, self.twins.get(pid), key=key)
        hist = self.history.setdefault(pid, [])
        terms = payout_schedule.prospective(k.price_drops_per_window, hist)
        price = terms["week_drops"]
        if not self.checks:                             # manual flow: paid in full now, reviewed later
            r = self.settle.pay_immediate(self, p, k, wnum, payload, price)
            sig = fitness.precheck(payload["manifest"], k, self.registry)
            sig = sig + fitness.check_values(r["payload"], k, self.profiles[pid], self.seen, pid)
            return self._record(pid, k, wnum, "end_review", sig, r["paid"], 0, 0, r.get("txs"), x)
        # every check that needs no opening runs first: source signatures and credentials, the records
        # exactly as the source stamped them at intake, period, holder
        pre = fitness.precheck(payload["manifest"], k, self.registry, payload)
        if pre:
            hist.append(False)
            return self._record(pid, k, wnum, "before_payment", pre, 0, 0, 0, None, x)
        r = self.settle.pay_immediate(self, p, k, wnum, payload, terms["upfront_drops"])
        post = fitness.check_values(r["payload"], k, self.profiles[pid], self.seen, pid, key)
        hist.append(not post)
        h = self.settle.hold(self, p, k, wnum, terms["held_drops"], not post, post, r)
        return self._record(pid, k, wnum, "after_reveal", post, r["paid"], h["held"], h["released"],
                            {**(r.get("txs") or {}), **(h.get("txs") or {})}, x)

    # ---------- projection ----------
    def projection(self, after_window: int) -> dict:
        usable = sum(o["verdict"] == "pass" for o in self.outcomes)
        rest, risks = [], {}
        for pid in self.active:
            k = self.contracts[pid]
            for wn in k.windows:
                if wn > after_window:
                    pr = self.p_pass(pid, k, wn)
                    rest.append(pr)
                    if pr < 0.5:
                        risks.setdefault(wn, []).append(pid)
        mean = usable + sum(rest)
        sd = math.sqrt(sum(q * (1 - q) for q in rest))
        lo, hi = max(usable, mean - 1.64 * sd), mean + 1.64 * sd
        asked = sum(len(k.windows) for k in self.contracts.values())
        return {"after_window": after_window, "usable": usable, "target": self.target,
                "expected_usable": round(mean, 1), "band_90": [round(lo, 1), round(hi, 1)],
                "completeness": round(mean / asked, 3) if asked else 0.0,
                "power": {"mean": power(int(mean), self.effect_r), "lo": power(int(lo), self.effect_r),
                          "hi": power(int(hi), self.effect_r), "effect_r": self.effect_r},
                "risks": [f"{len(v)} provider{'s' if len(v) > 1 else ''} at risk of missing window {w}"
                          for w, v in sorted(risks.items())],
                "at_risk": {w: sorted(v) for w, v in sorted(risks.items())}}

    # ---------- the round ----------
    def run(self) -> dict:
        windows = list(self.req.windows)
        per_window = math.ceil(self.target / len(windows))
        self.recruit(windows, per_window, "initial request")
        self.projections.append(self.projection(windows[0] - 1))
        for i, wnum in enumerate(windows):
            rest = windows[i:]
            if self.strategy == "forecast" and self.model is not None and self.checks:
                due = [pid for pid in self.active if wnum in self.contracts[pid].windows]
                exp = sum(self.p_pass(pid, self.contracts[pid], wnum) for pid in due)
                if exp < per_window:
                    short = math.ceil(per_window - exp)
                    self.warnings.append({"window": wnum, "expected": round(exp, 1), "needed": per_window})
                    self.recruit(rest, short, f"early warning: {exp:.1f} expected passes for window {wnum}, "
                                              f"{per_window} needed")
            for pid in sorted(self.active):
                k = self.contracts[pid]
                if wnum not in k.windows:
                    continue
                o = self.contribute(pid, wnum)
                if o["verdict"] == "fail" and self.checks and self.drop_on_fail:
                    self.active.discard(pid)
                    nxt = windows[i + 1:]
                    if nxt:
                        self.recruit(nxt, 1, f"{pid} failed window {wnum} "
                                             f"({', '.join(sorted({s['code'] for s in o['signals']}))}); replacement")
                self.projections.append(self.projection(wnum - 0.5))
            self.projections.append(self.projection(wnum))
        return self.summary()

    def summary(self) -> dict:
        out = self.outcomes
        fails = [o for o in out if o["verdict"] == "fail"]
        paid = sum(o["paid_drops"] + o["released_drops"] for o in out)
        unfit_paid = [o for o in fails if o["paid_drops"] + o["released_drops"] > 0]
        usable = len(out) - len(fails)
        by_code = {}
        for o in fails:
            for c in {s["code"] for s in o["signals"]}:
                d = by_code.setdefault(c, {"before_payment": 0, "after_reveal": 0, "end_review": 0})
                d[o["stage"]] = d.get(o["stage"], 0) + 1
        return {"strategy": self.strategy, "negotiation": self.negotiation, "checks": self.checks,
                "providers_contracted": len(self.contracts), "contributions": len(out), "usable": usable,
                "target": self.target, "target_met": usable >= self.target,
                "unfit": len(fails), "unfit_paid": len(unfit_paid),
                "xrp_paid": round(paid / 1e6, 4),
                "xrp_paid_for_unfit": round(sum(o["paid_drops"] + o["released_drops"] for o in unfit_paid) / 1e6, 4),
                "xrp_per_usable": round(paid / 1e6 / usable, 4) if usable else None,
                "caught": by_code, "warnings": self.warnings,
                "final_projection": self.projections[-1] if self.projections else None}
