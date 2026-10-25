"""How a person's agent decides one request, step by step (the "How my agent decides" panel).

The verdict is the one `scope.Owner.request` gives; this module only lays out the same checks in
order so a viewer can see which one decided:

  1. rules that travel with the data   data use codes, an ethics (IRB) credential for T2 and up
  2. sensitivity tier                  T0-T3; T3 (genomic, CT, MRI) is never covered by a standing grant
  3. who is asking                     institution class and country against the person's grant
  4. her standing scope                tier and purpose against what she already approved

Stateless: a fresh synthetic owner with the default grant (up to T1, sleep research, academic or
hospital, at home) answers each call, so nothing about a real person is read or stored.
"""
from __future__ import annotations

from .columns import CATALOG, RISK, TIER_NAME, TIERS, duo_for, tier_of
from .scope import Grant, Owner, Request

DEFAULT_GRANT = Grant()
HOME = "KR"

PRESETS = {
    "steps_hospital": {"label": "Steps and sleep · hospital · sleep research",
                       "institution": "Northside Sleep Lab", "inst_class": "hospital", "country": "KR",
                       "purpose": "sleep_research", "columns": ["steps.daily", "sleep.daily"], "irb": False},
    "same_new_purpose": {"label": "Same data · insurer · product marketing",
                         "institution": "Orbit Insure", "inst_class": "commercial", "country": "KR",
                         "purpose": "product_marketing", "columns": ["steps.daily", "sleep.daily"], "irb": False},
    "mri_irb": {"label": "MRI · hospital with ethics approval",
                "institution": "Northside Sleep Lab", "inst_class": "hospital", "country": "KR",
                "purpose": "sleep_research", "columns": ["imaging.mri"], "irb": True},
    "mri_no_irb": {"label": "MRI · lab without ethics approval",
                   "institution": "Quick Scan Labs", "inst_class": "commercial", "country": "KR",
                   "purpose": "sleep_research", "columns": ["imaging.mri"], "irb": False},
    "genome_abroad": {"label": "Genome · university abroad",
                      "institution": "Boston Genomics Center", "inst_class": "academic", "country": "US",
                      "purpose": "sleep_research", "columns": ["genome.vcf"], "irb": True},
}

SECURITY = [
    ("Passkey signature", "she signs the exact package (institution, items, weeks, payment) on her own device"),
    ("Consent hash on the ledger", "every escrow memo carries the hash of what she approved"),
    ("Sealed delivery", "the bundle is encrypted to the study's key; nobody else can open it"),
    ("Key-reveal escrow", "payment releases only when the key to the data is published on XRPL"),
    ("Licence clawback", "if she withdraws, the study's data licence is taken back on the ledger"),
]


def _step(name: str, state: str, detail: str) -> dict:
    return {"name": name, "state": state, "detail": detail}


def explain(req: dict) -> dict:
    cols = [c for c in req.get("columns", []) if c in CATALOG]
    if not cols:
        raise ValueError("pick at least one known column")
    inst_class = req.get("inst_class", "academic")
    country = req.get("country", HOME)
    purpose = req.get("purpose", "sleep_research")
    irb = bool(req.get("irb"))
    tier = tier_of(cols)
    duo = duo_for(cols) + (["DUO:0000016"] if any(c.startswith("genome.") for c in cols) else [])
    if not irb:
        duo = [d for d in duo if d != "DUO:0000021"]
    r = Request("explain", req.get("institution", "Institution"), inst_class, country, "study", purpose, cols,
                [1], duo=duo, irb=irb)
    owner = Owner("example", home=HOME, grants=[Grant(DEFAULT_GRANT.max_tier, DEFAULT_GRANT.purposes,
                                                      DEFAULT_GRANT.classes, DEFAULT_GRANT.abroad)])
    verdict = owner.request(r)

    g = owner.grants[0]
    steps = []
    bad = Owner.restrictions(r)
    steps.append(_step("Rules that travel with the data", "fail" if bad else "pass",
                       bad or ("carries every data use code its columns need"
                               + ("; ethics (IRB) credential verified" if TIERS.index(tier) >= 2 else ""))))
    t3 = tier == "T3"
    steps.append(_step("Sensitivity tier", "ask" if t3 else "pass",
                       f"{tier} {TIER_NAME[tier]} · re-identification risk: {RISK[tier]}"
                       + (" · never covered by a standing grant: she is asked every time" if t3 else "")))
    who_ok = inst_class in g.classes and (country == HOME or g.abroad)
    steps.append(_step("Who is asking", "pass" if who_ok else "ask",
                       f"{inst_class} institution in {country}"
                       + ("" if inst_class in g.classes else f" · she allowed {', '.join(sorted(g.classes))} only")
                       + ("" if country == HOME or g.abroad else " · outside her country: needs her yes")))
    scope_ok = (not t3 and TIERS.index(tier) <= TIERS.index(g.max_tier) and purpose in g.purposes)
    steps.append(_step("Her standing scope", "pass" if scope_ok else "ask",
                       f"she approved up to {g.max_tier} for {', '.join(sorted(g.purposes))}"
                       + ("" if purpose in g.purposes else f" · '{purpose}' is a new purpose")
                       + (" · T3 is never part of a standing grant" if t3 else "")
                       + ("" if t3 or TIERS.index(tier) <= TIERS.index(g.max_tier) else f" · {tier} is above her grant")))
    if bad:
        for s in steps[1:]:
            s["state"] = "skip"
    outcome = {"auto": "Her agent handles it", "gate": "Comes back to her for a fresh yes",
               "refused": "Refused before anything moves"}[verdict["decision"] if verdict["decision"] in
                                                            ("auto", "gate") else "refused"]
    return {"request": {"institution": r.institution, "inst_class": inst_class, "country": country,
                        "purpose": purpose, "columns": [{"id": c, "label": CATALOG[c].label, "tier": CATALOG[c].tier}
                                                        for c in cols], "irb": irb},
            "tier": tier, "steps": steps, "decision": verdict["decision"], "outcome": outcome,
            "why": verdict["why"],
            "grant": {"max_tier": g.max_tier, "purposes": sorted(g.purposes), "classes": sorted(g.classes),
                      "abroad": g.abroad},
            "tiers": [{"tier": t, "name": TIER_NAME[t], "risk": RISK[t],
                       "examples": [c.label for c in CATALOG.values() if c.tier == t and c.id != "genome.pgx"][:3]} for t in TIERS],
            "security": [{"name": n, "detail": d} for n, d in SECURITY]}


def payout_curve(weeks: int = 6) -> list[dict]:
    from ..payout_schedule import FIRST_SHARE, MAX_SHARE, STEP_SHARE
    out = []
    for w in range(1, weeks + 1):
        pct = min(MAX_SHARE, FIRST_SHARE + STEP_SHARE * (w - 1))
        out.append({"week": w, "at_delivery_pct": pct, "after_review_pct": 100 - pct})
    return out
