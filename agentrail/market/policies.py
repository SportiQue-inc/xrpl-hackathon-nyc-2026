"""The seller-side policy plugged into the one trade pipeline.

One rule: the owner sets, per kind of data, the lowest buyer-trust grade their agent may sell to on
its own. The agent then decides:

  hard gate fails         -> blocked, with the reason (no owner setting widens a hard gate)
  buyer grade >= the bar  -> sold automatically
  below the bar           -> queued for the owner, with the reason

Hard gates: a prohibited purpose; T2 and up without a valid ethics (IRB) credential; an expired
institution credential; a destination country the owner excluded.

Buyer trust grade A-D is computed, with its reasons, from: the institution credential, the IRB
credential, past deletion confirmations, past fitness disputes and audit flags, the destination
country, and whether the buyer opens sensitive data only in a controlled workspace (view keys that
expire) or takes a copy.

Owner presets (easy modes; each can be edited per kind of data; changing them re-signs the
delegation with Touch ID):

  | preset | T0 / sensor | T1 | T2 | pseudonymized imaging | other T3 | genomic |
  |---|---|---|---|---|---|---|
  | L0 ask me always | - | - | - | - | - | never |
  | L1 | C | - | - | - | - | never |
  | L2 | C | B | - | - | - | never |
  | L3 | C | B | A | A, controlled workspace | - | never |
  | L4 auto except genomic | C | B | A | A, controlled workspace | A, controlled workspace | never |

Genomic data: the agent is a tool that executes the person's signed consent, never a proxy that
consents for them. Raw variants are never delegated: each study needs a fresh passkey signature from
the person. Within a study the person signed in advance (institution, purpose, loci, period), the
agent may deliver computed or aggregate outputs each round, never raw variants. Anything new (a new
institution, a new purpose, raw data) goes back to the person. There is no "proceed unless refused"
mode. Participants in Mongolia: genomic data is left out of this MVP.

`SensitivityPolicy` (Act 2) adds tiered consent per institution on top (catalog/scope.py).
"""
from __future__ import annotations

from ..catalog import columns as catalog
from ..catalog.scope import Owner, Request

GRADES = ("A", "B", "C", "D")
PRESETS = {
    "L0": {},
    "L1": {"T0": "C", "R": "C"},
    "L2": {"T0": "C", "R": "C", "T1": "B"},
    "L3": {"T0": "C", "R": "C", "T1": "B", "T2": "A", "imaging_pseudo": "A"},
    "L4": {"T0": "C", "R": "C", "T1": "B", "T2": "A", "imaging_pseudo": "A", "T3": "A"},
}
CONTROLLED_ONLY = {"imaging_pseudo", "T3"}
PROHIBITED = {"marketing_profiling", "insurance_pricing", "employment_screening"}
LABEL = {"T0": "everyday data", "T1": "lifestyle data", "T2": "clinical data", "T3": "highly sensitive data",
         "R": "sensor data", "imaging_pseudo": "pseudonymized imaging", "imaging": "imaging",
         "genomic": "genomic data"}


def data_class(col: str, trade: dict) -> str:
    if col.startswith(("robot.", "fleet.", "smarthome.")):
        return "R"
    if col.startswith("genome."):
        return "genomic"
    if col.startswith("imaging."):
        return "imaging_pseudo" if trade.get("pseudonymized") else "imaging"
    return catalog.CATALOG[col].tier


def trust_grade(b: dict) -> tuple[str, int, list[str]]:
    """Buyer trust grade with its reasons. Inputs are the buyer agent's public record."""
    score, why = 100, []
    if not b.get("institution_credential"):
        score -= 25; why.append("no verified institution credential")
    if not b.get("irb"):
        score -= 15; why.append("no ethics (IRB) credential")
    for _ in range(b.get("missed_deletions", 0)):
        score -= 30; why.append("a past deletion was never confirmed")
    if b.get("audit_flags"):
        score -= 15 * b["audit_flags"]; why.append(f"{b['audit_flags']} audit flag(s)")
    if b.get("disputes"):
        score -= 5 * b["disputes"]; why.append(f"{b['disputes']} lost fitness dispute(s)")
    if b.get("country") and b.get("country") != b.get("owner_country", b.get("country")):
        score -= 10; why.append(f"delivery abroad ({b['country']})")
    if b.get("workspace") != "controlled":
        score -= 15; why.append("takes copies instead of a controlled workspace")
    if not b.get("history"):
        score -= 10; why.append("no trading history yet")
    g = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
    return g, score, why or ["clean record"]


def hard_gate(trade: dict, b: dict, excluded_countries: set) -> str | None:
    if trade["purpose"] in PROHIBITED:
        return f"purpose {trade['purpose']} is never allowed"
    classes = {data_class(c, trade) for c in trade["columns"]}
    if classes & {"T2", "T3", "genomic", "imaging", "imaging_pseudo"}:
        if not b.get("irb"):
            return "no valid ethics (IRB) credential"
        if b.get("irb_expired"):
            return "ethics (IRB) credential has expired"
    if b.get("credential_expired"):
        return "institution credential has expired"
    if b.get("country") in excluded_countries:
        return f"destination country {b['country']} is excluded by the owner"
    return None


class AutonomyPolicy:
    name = "autonomy"

    def __init__(self, preset: str = "L2", bars: dict | None = None, excluded_countries=(), purposes=None,
                 budget_cap_drops: int | None = None, manual: bool = False, accept: float = 0.8,
                 home: str = "KR", signed_genomic: list | None = None, never=()):
        self.preset = preset
        self.bars = dict(PRESETS[preset]) if bars is None else dict(bars)
        self.excluded = set(excluded_countries)
        self.purposes, self.cap = purposes, budget_cap_drops
        self.manual, self.accept = manual, accept
        self.home = home
        self.never = set(never)                       # kinds of data the person never offers
        self.signed_genomic = signed_genomic or []    # [{institution, purpose, loci}] the person signed
        self.sold_drops = 0

    def genomic(self, trade: dict, b: dict) -> tuple[str, str]:
        if self.home == "MN":
            return "refuse", "blocked: genomic data of participants in Mongolia is left out of this MVP"
        if trade.get("output") != "aggregate":
            return "gate", "raw genomic data: needs your passkey signature for this study"
        inst = b.get("institution", trade["buyer"])
        for s in self.signed_genomic:
            if s["institution"] == inst and s["purpose"] == trade["purpose"] and \
                    set(trade.get("loci", [])) <= set(s["loci"]):
                return "allow", (f"executing your signed consent ({inst}, {trade['purpose']}, "
                                 f"{', '.join(s['loci'])}): computed output only")
        return "gate", "genomic output outside what you signed (new institution, purpose or loci): needs you"

    def decide(self, trade: dict) -> tuple[str, str]:
        b = {**trade.get("buyer_attrs", {}), "owner_country": getattr(self, "home", "KR")}
        bad = hard_gate(trade, b, self.excluded)
        if bad:
            return "refuse", f"blocked: {bad}"
        if self.home == "MN" and b.get("country") != "MN":
            return "refuse", ("blocked in this demo: transfer abroad for participants in Mongolia rests on their PDPL art. 14.1 consent, "
                              "and the A/90 server and access requirements are reviewed separately before a real service")
        g, score, why = trust_grade(b)
        classes = {data_class(c, trade) for c in trade["columns"]}
        nv = {k for k in classes if k in self.never or (k in ("genomic", "imaging", "imaging_pseudo") and "T3" in self.never)}
        if nv:
            return "refuse", f"blocked: you set never for {', '.join(LABEL[k] for k in sorted(nv))}"
        if "genomic" in classes:
            return self.genomic(trade, b)
        short = []
        for k in sorted(classes):
            bar = self.bars.get(k)
            if bar is None:
                short.append(f"{LABEL[k]} is not set to sell on its own")
            elif GRADES.index(g) > GRADES.index(bar):
                short.append(f"{LABEL[k]} needs grade {bar}+, buyer is {g} ({'; '.join(why)})")
            elif k in CONTROLLED_ONLY and b.get("workspace") != "controlled":
                short.append(f"{LABEL[k]} goes only to a controlled workspace")
        if not short and self.purposes is not None and trade["purpose"] not in self.purposes:
            short.append(f"purpose {trade['purpose']} is not in your list")
        if not short and self.cap is not None and self.sold_drops + trade["price_drops"] > self.cap:
            short.append("your budget cap is reached")
        if short:
            return "gate", f"queued for you ({self.preset}): " + "; ".join(short)
        self.sold_drops += trade["price_drops"]
        return "allow", f"sold on its own: buyer grade {g} meets your bar ({self.preset})"

    check = decide

    def owner_answers(self, trade, rng, response_h):
        return rng.random() < self.accept, response_h(rng)


class SensitivityPolicy(AutonomyPolicy):
    """Act 2: the same autonomy check, with tiered consent per institution on top."""
    name = "sensitivity"

    def __init__(self, owner: Owner, **k):
        super().__init__(**k)
        self.owner = owner

    def _request(self, trade: dict) -> Request:
        b = trade.get("buyer_attrs", {})
        cols = trade["columns"]
        duo = catalog.duo_for(cols) + (["DUO:0000016"] if any(c.startswith("genome.") for c in cols) else [])
        return Request(trade["contract"][:16], b.get("institution", trade["buyer"]), b.get("class", "academic"),
                       b.get("country", self.owner.home), b.get("study", trade["need"]), trade["purpose"], cols,
                       list(range(1, trade["weeks"] + 1)), why=trade.get("why", ""),
                       duo=b.get("duo", duo), irb=bool(b.get("irb")))

    def check(self, trade: dict) -> tuple[str, str]:
        v, why = super().decide(trade)
        if v == "refuse":
            return v, why
        r = self._request(trade)
        if v == "allow" and {data_class(c, trade) for c in trade["columns"]} <= {"imaging_pseudo", "T0", "T1", "R"} \
                and any(data_class(c, trade) == "imaging_pseudo" for c in trade["columns"]):
            bad = self.owner.restrictions(r)
            if bad:
                return "refuse", f"blocked: {bad}"
            self.owner._log(r, "auto", "pseudonymized imaging to a controlled workspace, buyer meets your bar")
            return "allow", why
        e = self.owner.request(r)
        if e["decision"] == "refused":
            return "refuse", e["why"]
        if e["decision"] == "auto" and v == "allow":
            return "allow", f"{why}; consent: {e['why']}"
        return "gate", why if v == "gate" else f"consent: {e['why']}"

    def owner_answers(self, trade, rng, response_h):
        inst = trade.get("buyer_attrs", {}).get("institution", trade["buyer"])
        if rng.random() >= self.accept:
            self.owner.decline(inst)
            return False, response_h(rng)
        pkg = self.owner.package(inst)
        if pkg:
            r = self.owner.approve(inst, self.owner.device.assert_(pkg["hash"], self.owner.clock()), remember=True)
            if not r["ok"]:
                return False, 0.0
        return True, response_h(rng)
