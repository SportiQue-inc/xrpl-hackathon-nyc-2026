"""Tiered consent: the owner's settings decide what the agent may approve on its own.

A standing grant is a level the owner has already consented to: up to a tier, for named purposes,
for classes of institution, at home or also abroad. A request at or below a grant runs at once and
is logged; the owner can revoke any logged approval, which also revokes the grant behind it.

Anything else goes to a safety gate:
  - every T3 request, every time (never covered by a grant)
  - a new scope: a tier, purpose, institution class or country no grant covers

Pending requests are bundled per institution into one consent package that says which institution
and study, why, the risks (re-identification risk class per tier, transfer abroad), what that
institution already receives, and whether this is a first or an additional request. The owner
approves the package once with a fresh device assertion (Touch ID); approving can also widen the
standing grant for the non-T3 parts so the next week runs on its own.

Before any of this, restrictions that travel with the data are checked: a request must carry every
DUO code its columns require, T2 and up need an ethics (IRB) credential, genomic columns need the
genetic-studies-only code. These can only narrow; no setting widens them.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from nacl.signing import SigningKey, VerifyKey

from .columns import CATALOG, RISK, TIERS, duo_for, tier_of

FRESH_SECONDS = 120


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class Grant:
    max_tier: str = "T1"
    purposes: frozenset = frozenset({"sleep_research"})
    classes: frozenset = frozenset({"academic", "hospital"})
    abroad: bool = False
    revoked: bool = False

    def covers(self, r: "Request", home: str) -> bool:
        t = tier_of(r.columns)
        return (not self.revoked and t != "T3" and TIERS.index(t) <= TIERS.index(self.max_tier)
                and r.purpose in self.purposes and r.inst_class in self.classes
                and (r.country == home or self.abroad))


@dataclass
class Request:
    id: str
    institution: str
    inst_class: str              # academic | hospital | commercial
    country: str
    study: str
    purpose: str
    columns: list
    weeks: list
    why: str = ""
    duo: list = field(default_factory=list)
    irb: bool = False            # ethics credential verified on the ledger

    @property
    def tier(self) -> str:
        return tier_of(self.columns)

    @property
    def cells(self) -> int:
        return len(self.columns) * len(self.weeks)


class TouchID:
    """The owner's device. An assertion is a signature over the package hash and a timestamp."""

    def __init__(self, seed: bytes | None = None):
        self.key = SigningKey(seed) if seed else SigningKey.generate()

    @property
    def public(self) -> str:
        return bytes(self.key.verify_key).hex()

    def assert_(self, package_hash: str, now: float | None = None) -> dict:
        ts = int(now if now is not None else time.time())
        return {"package": package_hash, "ts": ts,
                "sig": self.key.sign(f"touchid|{package_hash}|{ts}".encode()).signature.hex()}


def verify_assertion(public: str, a: dict, package_hash: str, now: float | None = None) -> str | None:
    now = now if now is not None else time.time()
    if a.get("package") != package_hash:
        return "assertion is for another package"
    if now - a.get("ts", 0) > FRESH_SECONDS:
        return "assertion is not fresh"
    try:
        VerifyKey(bytes.fromhex(public)).verify(f"touchid|{package_hash}|{a['ts']}".encode(), bytes.fromhex(a["sig"]))
    except Exception:
        return "bad assertion signature"
    return None


class Owner:
    """One person's consent state: standing grants, the approval log, packages and what was shared."""

    def __init__(self, pid: str, home: str = "KR", grants: list[Grant] | None = None, device: TouchID | None = None,
                 clock=time.time):
        self.pid, self.home = pid, home
        self.grants = grants if grants is not None else [Grant()]
        self.device = device or TouchID()
        self.clock = clock
        self.log: list[dict] = []           # every decision, auto or by the owner
        self.pending: dict[str, list[Request]] = {}
        self.shared: dict[str, set] = {}    # institution -> columns already approved
        self.declined: set = set()          # (institution, study): not asked again

    # ---------- the rules that travel with the data ----------
    @staticmethod
    def restrictions(r: Request) -> str | None:
        unknown = [c for c in r.columns if c not in CATALOG]
        if unknown:
            return f"unknown columns {unknown}"
        missing = sorted(set(duo_for(r.columns)) - set(r.duo))
        if missing:
            return f"request lacks data use codes {missing} its columns require"
        if TIERS.index(r.tier) >= 2 and not r.irb:
            return f"{r.tier} columns need a verified ethics (IRB) credential"
        return None

    # ---------- the agent's decision ----------
    def request(self, r: Request) -> dict:
        bad = self.restrictions(r)
        if bad:
            return self._log(r, "refused", bad)
        if (r.institution, r.study) in self.declined:
            return self._log(r, "refused", "owner declined this study earlier; not asked again")
        g = next((g for g in self.grants if g.covers(r, self.home)), None)
        if g is not None:
            self.shared.setdefault(r.institution, set()).update(r.columns)
            return self._log(r, "auto", f"within standing grant (≤{g.max_tier}, {r.purpose}, {r.inst_class}"
                             + (", abroad" if g.abroad else "") + ")", grant=self.grants.index(g))
        self.pending.setdefault(r.institution, []).append(r)
        why = "T3: always asks" if r.tier == "T3" else "new scope: no standing grant covers it"
        return self._log(r, "gate", why)

    def _log(self, r: Request, kind: str, why: str, **k) -> dict:
        e = {"id": len(self.log) + 1, "ts": self.clock(), "request": r.id, "institution": r.institution,
             "country": r.country, "study": r.study, "columns": list(r.columns), "weeks": list(r.weeks),
             "tier": r.tier, "decision": kind, "why": why, "revoked": False, **k}
        self.log.append(e)
        return e

    # ---------- the safety gate ----------
    def package(self, institution: str) -> dict:
        reqs = self.pending.get(institution, [])
        if not reqs:
            return {}
        before = sorted(self.shared.get(institution, set()))
        cols = sorted({c for r in reqs for c in r.columns})
        body = {
            "owner": self.pid, "institution": institution, "country": reqs[0].country,
            "first_time": not before,
            "studies": [{"request": r.id, "study": r.study, "purpose": r.purpose, "why": r.why,
                         "columns": r.columns, "weeks": r.weeks, "tier": r.tier, "duo": r.duo} for r in reqs],
            "risks": {
                "reidentification": {t: RISK[t] for t in sorted({CATALOG[c].tier for c in cols})},
                "transfer_abroad": reqs[0].country != self.home,
                "genomic": [c for c in cols if c.startswith("genome.")],
            },
            "already_shared": before,
            "new_columns": [c for c in cols if c not in before],
            "retention_days": {c: CATALOG[c].retention_days for c in cols},
        }
        if body["risks"]["genomic"]:
            body["warnings"] = ["genomic data also says something about blood relatives who did not consent",
                                "genomic data is permanent: a copy already delivered cannot be taken back"]
        body["hash"] = _h(body)
        return body

    def approve(self, institution: str, assertion: dict, remember: bool = False) -> dict:
        pkg = self.package(institution)
        if not pkg:
            return {"ok": False, "reason": "nothing pending"}
        err = verify_assertion(self.device.public, assertion, pkg["hash"], self.clock())
        if err:
            return {"ok": False, "reason": err}
        reqs = self.pending.pop(institution)
        for r in reqs:
            self.shared.setdefault(institution, set()).update(r.columns)
            self._log(r, "owner", "approved in consent package " + pkg["hash"][:12], package=pkg["hash"])
        if remember:
            non3 = [r for r in reqs if r.tier != "T3"]
            if non3:
                top = max((r.tier for r in non3), key=TIERS.index)
                self.grants.append(Grant(top, frozenset(r.purpose for r in non3),
                                         frozenset(r.inst_class for r in non3),
                                         abroad=any(r.country != self.home for r in non3)))
        return {"ok": True, "package": pkg["hash"], "approved": [r.id for r in reqs]}

    def decline(self, institution: str) -> list[str]:
        reqs = self.pending.pop(institution, [])
        for r in reqs:
            self.declined.add((r.institution, r.study))
            self._log(r, "declined", "owner declined the package")
        return [r.id for r in reqs]

    def revoke(self, log_id: int) -> dict:
        e = next((e for e in self.log if e["id"] == log_id), None)
        if e is None or e["decision"] not in ("auto", "owner"):
            return {"ok": False}
        e["revoked"] = True
        if "grant" in e:
            self.grants[e["grant"]].revoked = True
        return {"ok": True, "revoked": log_id, "grant_revoked": e.get("grant")}
