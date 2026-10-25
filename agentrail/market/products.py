"""The person's agent turns what the person holds into products, from the lowest tier up.

Two directions, one pipeline:
  everyday data (T0, T1)        supply first: collect, bundle by domain, list candidates, sell
  sensitive data (T2, T3)       demand first: the agent never lists it on its own; it searches open
                                study postings, and only a posting that matches the person's rules
                                turns that data into a candidate for review

  1 collect     fill gaps from sources the person already connected (wearable, diary app). T0/T1 sync
                on their own, T2 only with the person's opt-in, T3 (genomic, imaging) is never collected
                automatically
  2 bundle      group the columns by domain (sleep, cardio, activity, diet, mental, clinical, ...)
  3 candidates  one product per domain: columns, weeks, quality grade (pre-trade certificate), tier,
                suggested price
  4 review      inside the person's auto-sell rules: listed by the agent; otherwise one tap (T1/T2) or a
                fresh passkey (T3); tiers the person said never to sell are not listed at all
  5 de-identify direct identifiers dropped, a per-buyer research reference instead of the id, dates as
                day offsets, quasi-identifiers generalized until each class holds at least k people;
                imaging through the DICOM steps (deid.py); genomic raw never leaves (aggregate only,
                inside a signed study, vault/genomic.py)
  6 sell        every sale is a push sealed end to end to the buying institution's key (vault/delivery.py),
                paid through an escrow whose key the person's page publishes

The same steps run for every tier; the direction and step 4 change. Lowers the risk that a record is linked back
to a person; it does not remove it.
"""
from __future__ import annotations

import hashlib

from .. import deid, payout_schedule
from ..catalog import columns as catalog
from ..catalog.scope import TouchID, verify_assertion
from ..db import Store
from ..engine import Engine
from ..ledger.conditions import condition_hex
from ..ledger.mock import MockLedger
from ..vault import keys as K
from ..vault.delivery import PushDelivery
from . import imaging, quality
from .exchange import Dataset, quote

DOMAINS = {
    "sleep": ["sleep.daily", "sleep.efficiency", "survey.psqi", "resp_rate.night", "spo2.night"],
    "cardio": ["heart_rate.daily", "hrv.daily", "blood_pressure.daily", "vitals.clinic_hr"],
    "activity": ["steps.daily", "activity.minutes", "active_energy.daily", "screen_time"],
    "body": ["weight", "body_fat", "body_temp.daily", "skin_temp.delta", "vitals.bmi"],
    "diet": ["meal.kcal", "meal.protein", "meal.carbs", "meal.sugar", "caffeine", "alcohol", "water"],
    "mental": ["mood.score", "stress.score", "fatigue.survey", "energy.survey", "mental.phq9", "mental.dx"],
    "clinical": ["lab.hba1c", "lab.ldl", "lab.creatinine", "lab.glucose", "lab.tsh", "dx.codes", "rx.list",
                 "med.adherence", "allergy.list", "procedure.list", "smoking.status"],
    "reproductive": ["repro.cycle", "repro.pregnancy"],
    "imaging": ["imaging.ct", "imaging.mri"],
    "genomic": ["genome.vcf", "genome.pgx"],
}
DOMAIN_OF = {c: d for d, cs in DOMAINS.items() for c in cs}
ORDER = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
K_ANON = 5
WEEKS = 8
REGIONS = {"KR": ["Seoul", "Busan", "Daegu", "Incheon", "Gwangju"], "MN": ["Ulaanbaatar", "Darkhan"]}


def _tier(cols) -> str:
    return max((catalog.CATALOG[c].tier for c in cols), key=ORDER.get)


def quasi(pid: str, home: str) -> dict:
    """Synthetic quasi-identifiers for the release check (the profiles carry none)."""
    h = hashlib.sha256(f"qi|{pid}".encode()).digest()
    return {"age_group": ["<40", "40-64", "65+"][h[0] % 3], "sex": "FM"[h[1] % 2],
            "region": REGIONS[home][h[2] % len(REGIONS[home])], "country": home}


def k_anonymize(me: dict, cohort: list[dict], k: int = K_ANON) -> tuple[dict | None, list[str]]:
    """Generalize the person's quasi-identifiers until at least k people of the release population
    share them: region -> country first, then drop the age group. None if still below k."""
    steps = []
    keys = ["age_group", "sex", "region"]
    for drop in (None, "region", "age_group"):
        if drop:
            keys = [x for x in keys if x != drop]
            steps.append(f"generalized: {drop} removed")
        size = sum(1 for o in cohort if all(o[x] == me[x] for x in keys) and o["country"] == me["country"])
        if size >= k:
            return {**{x: me[x] for x in keys}, "country": me["country"]}, steps + [f"class size {size} >= k={k}"]
    return None, steps + [f"class size below k={k}: not released"]


def collect(pid: str, holds: list[str], sources: dict, opt_in_t2: bool = False) -> tuple[list[str], list[dict]]:
    have = set(holds)
    log = []
    for c, src in sorted(sources.items()):
        if c in have or c not in catalog.CATALOG:
            continue
        t = catalog.CATALOG[c].tier
        if t == "T3":
            log.append({"column": c, "from": src, "collected": False, "why": "T3 is never collected automatically"})
        elif t == "T2" and not opt_in_t2:
            log.append({"column": c, "from": src, "collected": False, "why": "T2 needs your opt-in to collect"})
        else:
            have.add(c)
            log.append({"column": c, "from": src, "collected": True, "why": f"{t}: syncs on its own"})
    return sorted(have), log


def bundles(cols: list[str]) -> list[tuple[str, str, list[str]]]:
    """One bundle per (domain, tier): never two domains, never two tiers in one product."""
    out = []
    for dom, dcols in DOMAINS.items():
        for t in ("T0", "T1", "T2", "T3"):
            mine = [c for c in dcols if c in cols and catalog.CATALOG[c].tier == t]
            if mine:
                out.append((dom, t, mine))
    return out


def candidates(pid: str, cols: list[str], issuer_of) -> list[dict]:
    out = []
    for dom, tier, mine in bundles(cols):
        kind = {catalog.CATALOG[c].kind for c in mine}
        if kind & {"image", "variants"}:
            out.append({"domain": dom, "columns": mine, "weeks": 1, "tier": tier, "grade": "A", "rows": None,
                        "price_drops": quote(mine, 1, "A"),
                        "note": "pseudonymized imaging" if dom == "imaging" else "aggregate only, inside a signed study"})
            continue
        ds = Dataset(f"{pid}:{dom}:{tier}", pid, mine, WEEKS, 0.93, {c: issuer_of(c) for c in mine})
        ds.build(ds.id)
        cert = quality.Seller(pid).certify(ds.id, ds.shown.rows, {c: _spec(c) for c in mine}, ds.issuer,
                                           quality.reputation(0, 0, True), ds.shown, scope="person")
        g = cert["grade"] or "C"
        out.append({"domain": dom, "columns": mine, "weeks": WEEKS, "tier": tier, "grade": g,
                    "completeness": cert.get("completeness"), "price_drops": quote(mine, WEEKS, g), "rows": ds.rows})
    return out


def _spec(c):
    x = catalog.CATALOG[c]
    return {"unit": x.unit, "lo": x.lo, "hi": x.hi, "tier": x.tier}


def review(p: dict, auto_tiers: list[str], never: list[str], device: TouchID | None, tap: bool) -> dict:
    t = p["tier"]
    if t in never or (t == "T3" and "T3" in never):
        return {"listed": False, "how": "never", "why": f"you set {t} to never be sold"}
    if p["domain"] == "genomic":
        return {"listed": False, "how": "study_only", "why": "raw genomic data is never listed; only aggregates "
                "inside a study you signed"}
    if t in auto_tiers:
        return {"listed": True, "how": "auto", "why": f"{t} is inside your auto-sell rules"}
    if t == "T3":
        if device is None:
            return {"listed": False, "how": "passkey", "why": "waiting for your passkey"}
        h = hashlib.sha256(repr((p["domain"], p["columns"])).encode()).hexdigest()
        err = verify_assertion(device.public, device.assert_(h), h)
        return {"listed": err is None, "how": "passkey", "why": err or "listed after a fresh passkey"}
    return ({"listed": True, "how": "tap", "why": "listed after one tap"} if tap
            else {"listed": False, "how": "tap", "why": "waiting for one tap"})


def deidentify_rows(pid: str, buyer: str, rows: list[dict], cols: list[str], qi: dict) -> dict:
    ref = deid.research_ref(f"{buyer}|{pid}")
    out = [{"day": r["day"], **{c: r.get(c) for c in cols}} for r in rows]
    return {"subject": ref, "quasi": qi, "rows": out,
            "removed": ["person id", "wallet address", "calendar dates (day offsets only)"]}


def sell(pd: PushDelivery, pid: str, inst: str, purpose: str, product: dict, released: dict, passkey: K.SoftPasskey) -> dict:
    rows = [{**r, "subject": released["subject"], **released["quasi"]} for r in released["rows"]]
    cols = product["columns"] + ["subject"] + list(released["quasi"])
    pd.consent(pid, inst, cols, purpose)
    prep = pd.prepare(pid, inst, rows, cols, hashlib.sha256(repr(product["columns"]).encode()).hexdigest(),
                      product["price_drops"])
    rec, k = K.seal(passkey.root(pid), prep["order_id"], K.unb64u(prep["bundle_b64u"]), prep["institution_jwk"])
    pushed = pd.accept_sealed(pid, rec, condition_hex(k))
    paid = pd.reveal(pid, prep["order_id"], k)
    got = pd.engine.open_payload(inst, pushed["order_id"])
    return {"institution": inst, "pushed": pushed["ok"], "escrow_create": pushed.get("escrow_create"),
            "escrow_finish": paid.get("escrow_finish"), "paid": paid["ok"], "opened_rows": len(got["rows"]),
            "carries_person_id": any(pid in str(v) for r in got["rows"] for v in r.values())}


SENSITIVE = ("T2", "T3")


def postings(prof: dict) -> list[dict]:
    """Open study postings: each researcher's sensitive wants, under the institution's study."""
    insts = {i["id"]: i for i in prof["institutions"]}
    out = []
    for rid, r in sorted(prof["researchers"].items()):
        cols = sorted({catalog.canon(w) for w in r.get("wants", [])} & set(catalog.CATALOG))
        cols = [c for c in cols if catalog.CATALOG[c].tier in SENSITIVE]
        if cols:
            i = insts[r["institution"]]
            out.append({"posting": rid, "institution": i["id"], "country": i["country"], "study": i["study"],
                        "max_tier": i["max_tier"], "columns": cols})
    return out


def match(post: dict, holds: list[str], home: str, never: list[str]) -> tuple[list[str], str | None]:
    cols = [c for c in post["columns"] if c in holds]
    if not cols:
        return [], "you do not hold these columns"
    tier = _tier(cols)
    if tier in never:
        return [], f"you set {tier} to never be sold"
    if ORDER[tier] > ORDER[post["max_tier"]]:
        return [], f"the institution is not cleared for {tier}"
    if any(DOMAIN_OF.get(c) == "genomic" for c in cols):
        return [], "raw genomic data is never sold; only aggregates inside a study you signed"
    if home == "MN" and post["country"] != "MN":
        return [], ("not in this demo: transfer abroad for participants in Mongolia rests on their PDPL art. 14.1 "
                    "consent, and the A/90 server and access requirements are reviewed separately before a real service")
    return cols, None


def _sensitive_candidate(pid, post, cols, issuer_of) -> dict:
    tier = _tier(cols)
    if any(catalog.CATALOG[c].kind == "image" for c in cols):
        return {"domain": DOMAIN_OF[cols[0]], "columns": cols, "weeks": 1, "tier": tier, "grade": "A",
                "price_drops": quote(cols, 1, "A"), "posting": post["posting"], "image": True}
    c = candidates(pid, cols, issuer_of)
    return {**c[0], "columns": cols, "tier": tier, "posting": post["posting"]} if c else None


def scene(pid: str = "P-017", prof: dict | None = None, tap: bool = True, ledger=None) -> dict:
    """One person's agent, end to end, both directions."""
    from . import acts
    prof = prof or acts.load()
    people = sorted(prof["participants"])
    p = prof["participants"][pid]
    home = "MN" if people.index(pid) >= len(people) - 2 else "KR"
    never = p.get("never", [])
    holds = [catalog.canon(c) for c in p["holds"].get("health", []) if catalog.canon(c) in catalog.CATALOG]
    sources = acts.connected_sources(pid)
    cols, collected = collect(pid, holds, sources)
    issuer = lambda c: sources.get(c) or acts.ISSUERS[acts._kind(c)]
    everyday = [c for c in cols if catalog.CATALOG[c].tier not in SENSITIVE]
    cands = [{**c, "direction": "supply"} for c in candidates(pid, everyday, issuer)]
    searched = []
    for post in postings(prof):
        mc, why = match(post, cols, home, never)
        searched.append({"posting": post["posting"], "institution": post["institution"], "columns": post["columns"],
                         "matched": mc, "why": why or "matches your rules: prepared for your review"})
        if mc and post["country"] != home:
            searched[-1]["why"] += "; delivery abroad also needs your separate transfer-abroad consent"
        for dom, tier, part in bundles(mc):          # a posting spanning domains becomes one product per domain
            if any(c.get("posting") and set(c["columns"]) == set(part) for c in cands):
                continue
            c = _sensitive_candidate(pid, post, part, issuer)
            if c:
                cands.append({**c, "direction": "demand", "buyer": post["institution"], "study": post["study"],
                              "transfer_abroad": post["country"] != home})
    for c in cands:
        # same rail, different schedule: what exists is bought whole after inspection; a study that
        # also follows the person pays a baseline once and then follow-up weeks on the continuity curve
        c["payout"] = (payout_schedule.hybrid(c["price_drops"], c["price_drops"] // max(1, c["weeks"]), [])
                       if c["direction"] == "demand" and not c.get("image")
                       else payout_schedule.retrospective(c["price_drops"]))
    device = TouchID(hashlib.sha256(pid.encode()).digest())
    for c in cands:
        c["review"] = review(c, p.get("auto_tiers", ["T0"]), never, device, tap)
        if c.get("transfer_abroad") and c["review"]["listed"]:
            c["review"]["why"] += " and the separate transfer-abroad consent"
    cohort = [quasi(x, "MN" if i >= len(people) - 2 else "KR") for i, x in enumerate(people)]
    qi, kanon = k_anonymize(quasi(pid, home), cohort)
    insts = {i["id"]: i for i in prof["institutions"]}
    pd = PushDelivery(Engine(Store(":memory:"), ledger or MockLedger()))
    keys, pk, sales = {}, K.SoftPasskey(), []
    for c in cands:
        if not c["review"]["listed"]:
            continue
        if qi is None:
            c["sale"] = {"sold": False, "why": "re-identification check failed: not released"}
            continue
        buyer = insts.get(c.get("buyer")) or next((i for i in insts.values() if i["country"] == home
                                                    and ORDER[c["tier"]] <= ORDER[i["max_tier"]]), None)
        if buyer is None:
            c["sale"] = {"sold": False, "why": "no institution in your country is cleared for this tier"}
            continue
        if buyer["id"] not in keys:
            keys[buyer["id"]] = K.InstitutionKey()
            pd.register_institution(buyer["id"], buyer["country"], keys[buyer["id"]])
        if c.get("image"):
            num = deid.participant_number("UQ", people.index(pid) + 1)
            img = imaging.deidentify(catalog.synth(c["columns"][0], pid, 0), pid, num)
            if img is None:
                c["sale"] = {"sold": False, "why": "image blocked by the burned-in text gate"}
                continue
            rows = [{"day": 0, c["columns"][0]: {k: v for k, v in img.items() if k != "pixels"}}]
            c["deid"] = ["DICOM identifiers removed", "UIDs remapped (2.25.<int>)", "dates shifted per subject",
                         "burned-in text gate passed"] + kanon
        else:
            rows = c["rows"]
            c["deid"] = ["person id, wallet address removed", "per-buyer research reference",
                         "day offsets, no calendar dates"] + kanon
        released = deidentify_rows(pid, buyer["id"], rows, c["columns"], qi)
        r = sell(pd, pid, buyer["id"], buyer["study"], c, released, pk)
        c["sale"] = {"sold": r["paid"], **r}
        sales.append(r)
    for c in cands:
        c.pop("rows", None)
    return {"person": pid, "home": home, "sources": sorted(set(sources.values())), "collected": collected,
            "postings_searched": searched, "candidates": cands, "k_anonymity": kanon,
            "listed": sum(1 for c in cands if c["review"]["listed"]), "sold": sum(1 for s in sales if s["paid"]),
            "waiting": [c["domain"] for c in cands if not c["review"]["listed"] and c["review"]["how"] in ("tap", "passkey")],
            "e2e": "every sale is a sealed push to the buying institution's key; the escrow key is published by "
                   "the person's page"}
