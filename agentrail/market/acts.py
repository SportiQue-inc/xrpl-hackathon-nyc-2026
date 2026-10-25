"""Two acts on the same 50 accounts and the same trade pipeline (exchange.py).

Act 1, an open market. Every account's agent lists what its owner holds and posts what its owner
wants. The agents find each other, check quality before the trade, agree a contract, settle by
escrow with key reveal, check fitness and release or withhold the holdback, with no human in the
loop except where the owner's own setting says "ask me". Health columns, robot and fleet logs and
smart-home meters trade side by side. One trade runs the other way: a person buys a wellness trait
report from a credentialed provider and sends only the loci the report needs.

Act 2, healthcare research. The same accounts are now participants, and four institutions with
three or four researchers each compete for them. The pipeline is the same object; what changes is
the policy plugged into each participant's agent: tiered consent per institution, safety-gate
packages, transfer-abroad consent, genomic rules. A researcher's budget opens only with two
researchers' signatures. One participant is a real person who approves by hand.

Profiles come from fixtures/market_profiles.json (synthetic; no person behind any of them).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import random

from nacl.signing import SigningKey, VerifyKey

from ..catalog import columns as catalog
from ..catalog.scope import Grant, Owner, TouchID
from ..policy import BuyerMandate
from . import imaging, policies
from .exchange import ROBOT, Account, Dataset, Exchange, Need

PROFILES = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "market_profiles.json")
MANUAL = "P-001"            # the person who approves by hand in the demo
ISSUERS = {"T0": "wearable_a", "T1": "diary_app", "T2": "clinic_emr", "T3": "hospital_pacs", "R": "fleet_gateway"}
FAULTS = ("wrong_unit", "drift", "copy", "bait")


def load(path: str = PROFILES) -> dict:
    with open(path) as f:
        return json.load(f)


def _kind(col: str) -> str:
    if col in ROBOT:
        return "R"
    return catalog.CATALOG[col].tier


def preset_for(p: dict) -> tuple[str, dict, set]:
    """The fixture's agent_trust (how far the owner lets the agent go) and pre-consent, as bars per kind."""
    t = p.get("agent_trust", 0.5)
    level = "L4" if t >= 0.9 else "L3" if t >= 0.75 else "L2" if t >= 0.6 else "L1" if t >= 0.45 else "L0"
    top = p.get("pre_consent", "T0").split("-")[-1]
    allowed = set(catalog.TIERS[: catalog.TIERS.index(top) + 1]) | {"R"}
    if "T3" in allowed:
        allowed |= {"imaging_pseudo"}
    bars = {k: v for k, v in policies.PRESETS[level].items() if k in allowed}
    return level, bars, set(p.get("never", []))


def datasets_for(pid: str, p: dict, rng: random.Random, key: bytes) -> list[Dataset]:
    cols = [catalog.canon(c) for c in p["holds"].get("health", [])]
    series = [c for c in cols if catalog.CATALOG[c].kind not in ("variants", "image")]
    out = []
    if series:
        out.append(Dataset(f"{pid}:health", pid, series, 8, rng.uniform(0.7, 0.98),
                           {c: ISSUERS[_kind(c)] for c in series}))
    for c in cols:
        k = catalog.CATALOG[c].kind
        if k == "image":
            out.append(Dataset(f"{pid}:{c}", pid, [c], 1, 1.0, {c: ISSUERS["T3"]},
                               meta={"rows": 1, "pseudonymized": True,
                                     "transform": {c: lambda o, d, c=c: imaging.deidentify(catalog.synth(c, o, d), o, "UQ-" + o[-4:])}}))
        elif k == "variants":
            out.append(Dataset(f"{pid}:{c}", pid, [c], 1, 1.0, {c: ISSUERS["T3"]}, meta={"rows": 1}))
    for c in p["holds"].get("other", []):
        out.append(Dataset(f"{pid}:{c}", pid, [c], 8, rng.uniform(0.75, 0.99), {c: ISSUERS["R"]}))
    for ds in out:
        if len(ds.columns) and rng.random() < 0.15 and ds.meta.get("rows") is None:
            ds.fault = rng.choice(FAULTS)
    return out


def _build_rows(accounts: list[Account]):
    by_cols = {}
    for a in accounts:
        for ds in a.datasets:
            src = by_cols.get(tuple(ds.columns)) if ds.fault == "copy" else None
            ds.build(ds.id, copy_of=src)
            by_cols.setdefault(tuple(ds.columns), ds)


def person_record(pid: str, rng: random.Random) -> dict:
    """A person's agent as a buyer: verified account, no ethics credential, takes copies."""
    r = {"institution_credential": True, "irb": False, "workspace": "copy", "history": True, "country": "KR"}
    x = rng.random()
    if x < 0.08:
        r["missed_deletions"] = 1
    elif x < 0.2:
        r["audit_flags"] = 1
    return r


def participants(prof: dict, act: int, seed: int = 11) -> list[Account]:
    rng = random.Random(seed)
    out = []
    for i, (pid, p) in enumerate(sorted(prof["participants"].items())):
        key = hmac.new(b"agentrail-pseudonym", pid.encode(), hashlib.sha256).digest()
        level, bars, never = preset_for(p)
        home = "MN" if i >= len(prof["participants"]) - 2 else "KR"
        a = Account(pid, pid, "person", attrs={**person_record(pid, rng), "country": home},
                    datasets=datasets_for(pid, p, rng, key), credentials=set(ISSUERS.values()))
        signed = ([{"institution": "org_genomics", "purpose": "genomics_research", "loci": ["CYP1A2", "MCM6"]}]
                  if rng.random() < 0.5 else [])
        common = dict(preset=level, bars=bars, never=never, home=home, manual=pid == MANUAL,
                      signed_genomic=signed)
        if act == 1:
            a.policy = policies.AutonomyPolicy(**common)
        else:
            top = p.get("pre_consent", "T0").split("-")[-1]
            grant = Grant(min(top, "T2"), frozenset({"sleep_research", "cardiometabolic_research"}),
                          frozenset({"academic", "hospital"}), abroad=False)
            a.policy = policies.SensitivityPolicy(Owner(pid, home=home, grants=[grant],
                                                        device=TouchID(hashlib.sha256(pid.encode()).digest())),
                                                  **common)
        a.needs_spec = p.get("wants", []) if p.get("budget_xrp", 0) > 0 else []
        a.budget_xrp = p.get("budget_xrp", 2)
        out.append(a)
    return out


# ---------------- Act 1 ----------------

PURPOSE_OF = {"R": "model_training", "T0": "personal_research", "T1": "personal_research",
              "T2": "personal_research", "T3": "personal_research"}


def act1(seed: int = 11, ledger=None, store=None, prof: dict | None = None, rounds: int = 3) -> dict:
    prof = prof or load()
    accounts = participants(prof, act=1, seed=seed)
    provider = Account("svc_dtc", "Wellness trait report provider (synthetic)", "org",
                       attrs={"institution_credential": True, "irb": True, "workspace": "controlled",
                              "history": True, "country": "KR"},
                       credentials={"DTC_WELLNESS"})
    provider.report_types = {"caffeine_metabolism": ["CYP1A2"], "lactose_tolerance": ["MCM6"]}
    _build_rows(accounts)
    from ..uniqdata_live import feed_market, market_clients
    uq = feed_market(accounts, market_clients())     # each person's own UniQdata account, when connected
    ex = Exchange(accounts + [provider], ledger=ledger, store=store, seed=seed)
    rng = random.Random(seed + 1)
    for a in accounts:
        ex.engine.set_mandate(BuyerMandate(a.id, int(a.budget_xrp * 1e6), int(a.budget_xrp * 1e6), list(set(PURPOSE_OF.values()))))
    needs = []
    for rnd in range(rounds):
        for a in accounts:
            for j, w in enumerate(a.needs_spec):
                c = catalog.canon(w) if w not in ROBOT else w
                one = c not in ROBOT and catalog.CATALOG[c].kind in ("image", "variants")
                if one and rnd:
                    continue
                needs.append(Need(f"{a.id}-r{rnd + 1}-n{j + 1}", a.id, [c], 1 if one else rng.choice([1, 2]), 3,
                                  PURPOSE_OF[_kind(c)], posted_h=round(rnd * 24 + rng.uniform(0, 24), 2),
                                  why=f"{a.id} wants {w}"))
    results = [ex.fill(n) for n in sorted(needs, key=lambda n: n.posted_h)]
    reports = []
    buyers = [a for a in accounts if any(d.columns == ["genome.vcf"] for d in a.datasets)][:3]
    for a, rt in zip(buyers, ["caffeine_metabolism", "lactose_tolerance", "disease_risk"]):
        reports.append(buy_report(ex, a.id, provider, rt))
    return {"act": 1, "activity": ex.activity(), "needs": results, "reports": reports, "exchange": ex,
            "uniqdata_records_used": uq}


ALLOWED_REPORTS = {"DTC_WELLNESS": {"caffeine_metabolism", "lactose_tolerance", "ancestry", "trait"}}


def buy_report(ex: Exchange, pid: str, provider: Account, report_type: str) -> dict:
    """The reverse direction: the person's agent is the buyer of a service paid for with their own data."""
    log = {"buyer": pid, "provider": provider.id, "report": report_type}
    if not any(report_type in ALLOWED_REPORTS.get(c, set()) for c in provider.credentials):
        return {**log, "status": "refused",
                "why": f"{report_type} is not a report type the provider's credential allows (wellness, trait, ancestry)"}
    loci = provider.report_types[report_type]
    person = ex.accounts[pid]
    ds = next(d for d in person.datasets if d.columns == ["genome.vcf"])
    sent = [v for v in ds.rows[0]["genome.vcf"] if v["gene"] in loci]           # only the loci the report needs
    alt = sum({"0/0": 0, "0/1": 1, "1/1": 2}[v["gt"]] for v in sent)
    report = {"type": report_type, "loci": loci, "result": "fast" if alt == 0 else "slower" if alt == 1 else "slow",
              "note": "wellness information, not a diagnosis"}
    from ..engine import OrderRequest
    from ..policy import ALLOW, Decision
    price = 2_000_000
    ex.engine.set_mandate(BuyerMandate(pid, price * 4, price, ["wellness_report"]))
    ex._grants[(pid, provider.id, report_type)] = Decision(ALLOW, granted=["report"])
    oid = ex.engine.place_order(OrderRequest(pid, provider.id, provider.id, f"report:{report_type}", f"{pid}|report",
                                             "wellness_report", ["report"], price, [report],
                                             Decision(ALLOW, granted=["report"]), settle="escrow"))
    status = ex.engine.process(oid)
    got = ex.engine.open_payload(pid, oid)["rows"][0]
    pm = ex.engine.store.one("SELECT * FROM payments WHERE order_id=?", oid)
    deletion = _deletion_confirmation(provider, pid, oid, len(sent))
    ex.events.append({"kind": "report", "buyer": pid, "report": report_type, "order": oid})
    return {**log, "status": status, "loci_sent": loci, "variants_sent": len(sent),
            "variants_held": len(ds.rows[0]["genome.vcf"]), "report_received": got,
            "txs": {"escrow_create": pm["tx_hash"], "escrow_finish": pm["finish_tx"]}, "deletion": deletion}


_DEL_KEY = SigningKey(hashlib.sha256(b"svc_dtc deletion key").digest())


def _deletion_confirmation(provider, pid, oid, n) -> dict:
    body = json.dumps({"provider": provider.id, "person": pid, "order": oid, "deleted_variants": n,
                       "workspace_keys": "destroyed"}, sort_keys=True)
    return {"body": body, "sig": _DEL_KEY.sign(body.encode()).signature.hex(),
            "key": bytes(_DEL_KEY.verify_key).hex()}


# ---------------- Act 2 ----------------

INSTITUTIONS = {
    "org_sleeplab": {"class": "academic", "purpose": "sleep_research", "workspace": "copy", "disputes": 1},
    "org_cardio": {"class": "hospital", "purpose": "cardiometabolic_research", "workspace": "controlled"},
    "org_neuroimg": {"class": "academic", "purpose": "neuroimaging_research", "workspace": "controlled"},
    "org_genomics": {"class": "academic", "purpose": "genomics_research", "workspace": "controlled",
                     "missed_deletions": 1},
}


def institution_record(inst: dict) -> dict:
    x = INSTITUTIONS[inst["id"]]
    return {"institution": inst["id"], "class": x["class"], "country": inst["country"], "study": inst["study"],
            "institution_credential": True, "irb": True, "workspace": x["workspace"], "history": True,
            "missed_deletions": x.get("missed_deletions", 0), "disputes": x.get("disputes", 0)}


class Institution:
    """Researchers each hold a key; a budget opens only with two different researchers' signatures."""

    def __init__(self, iid: str, researchers: list[str]):
        self.id = iid
        self.keys = {r: SigningKey(hashlib.sha256(f"researcher|{r}".encode()).digest()) for r in researchers}

    def sign(self, researcher: str, budget: dict) -> str:
        return self.keys[researcher].sign(json.dumps(budget, sort_keys=True).encode()).signature.hex()

    def open_budget(self, engine, budget: dict, sigs: dict) -> tuple[bool, str]:
        ok = set()
        for r, s in sigs.items():
            try:
                VerifyKey(bytes(self.keys[r].verify_key)).verify(json.dumps(budget, sort_keys=True).encode(), bytes.fromhex(s))
                ok.add(r)
            except Exception:
                pass
        if len(ok) < 2:
            return False, f"budget needs two researchers' signatures, has {len(ok)}"
        engine.set_mandate(BuyerMandate(self.id, budget["total_drops"], budget["per_order_drops"], budget["purposes"]))
        return True, f"budget opened by {', '.join(sorted(ok))}"


def act2(seed: int = 11, ledger=None, store=None, prof: dict | None = None) -> dict:
    prof = prof or load()
    people = participants(prof, act=2, seed=seed)
    _build_rows(people)
    from ..uniqdata_live import feed_market, market_clients
    uq = feed_market(people, market_clients())
    insts = []
    for inst in prof["institutions"]:
        insts.append(Account(inst["id"], inst["name"], "org", attrs=institution_record(inst)))
    ex = Exchange(people + insts, ledger=ledger, store=store, seed=seed)
    rng = random.Random(seed + 2)
    budgets = {}
    for inst in prof["institutions"]:
        rs = [r for r, v in prof["researchers"].items() if v["institution"] == inst["id"]]
        I = Institution(inst["id"], rs)
        b = {"institution": inst["id"], "total_drops": int(sum(prof["researchers"][r]["budget_xrp"] for r in rs) * 1e6),
             "per_order_drops": 5_000_000, "purposes": [INSTITUTIONS[inst["id"]]["purpose"]]}
        one = I.open_budget(ex.engine, b, {rs[0]: I.sign(rs[0], b)})
        two = I.open_budget(ex.engine, b, {rs[0]: I.sign(rs[0], b), rs[1]: I.sign(rs[1], b)})
        budgets[inst["id"]] = {"one_signature": one, "two_signatures": two}
    needs = []
    for r, v in sorted(prof["researchers"].items()):
        inst = v["institution"]
        for j, w in enumerate(v["wants"]):
            c = catalog.canon(w)
            k = catalog.CATALOG[c].kind
            n = Need(f"{r}-n{j + 1}", inst, [c], 1 if k in ("image", "variants") else 2, 6,
                     INSTITUTIONS[inst]["purpose"], posted_h=round(rng.uniform(0, 48), 2), why=f"{r}: {inst} study")
            if k == "variants":
                n.output, n.loci = "aggregate", ["CYP1A2", "MCM6"]
            needs.append(n)
    # The scene: the same pseudonymized MRI request from a grade-A and a grade-C institution.
    for inst in ("org_neuroimg", "org_genomics"):
        needs.append(Need(f"{inst}-mri", inst, ["imaging.mri"], 1, 8, INSTITUTIONS[inst]["purpose"],
                          posted_h=1.0, why=f"{inst}: pseudonymized MRI"))
    results = [ex.fill(n) for n in sorted(needs, key=lambda n: n.posted_h)]
    grades = {i.id: policies.trust_grade({**i.attrs, "owner_country": "KR"}) for i in insts}
    return {"act": 2, "uniqdata_records_used": uq, "activity": ex.activity(), "needs": results, "budgets": budgets,
            "buyer_grades": {k: {"grade": g, "score": s, "reasons": w} for k, (g, s, w) in grades.items()},
            "pending_for_manual": [{k: v for k, v in p.items() if k not in ("trade", "offer")} for p in ex.pending],
            "exchange": ex}
