"""Permission checks enforced by code. Agents may propose; only these decide.

Three kinds of settings, one per agent role:
  BuyerMandate          - what the buyer's agent may spend and for which purposes
  SellerPolicy          - what an organization's agent may provide, to whom, how
  PersonalConsentPolicy - what a person allowed, per institution, and how much
                          the person's agent may run without asking again
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

ALLOW, PARTIAL, NEEDS_APPROVAL, DENY, HOLD = "allow", "partial", "needs_approval", "deny", "hold"


@dataclass
class Decision:
    status: str
    granted: list[str] = field(default_factory=list)   # fields/items that may be provided
    pending: list[str] = field(default_factory=list)   # need the holder's approval first
    refused: list[str] = field(default_factory=list)   # excluded by policy
    reason: str = ""
    policy_version: str = ""
    round_confirm: list[str] = field(default_factory=list)  # in consent, but person confirms each round

    @property
    def ok(self) -> bool:
        return self.status in (ALLOW, PARTIAL) and bool(self.granted)


# ---------- buyer side ----------

@dataclass
class BuyerMandate:
    buyer_id: str
    total_drops: int
    per_order_limit_drops: int
    purposes: list[str]


# ---------- organization seller ----------

@dataclass
class SellerPolicy:
    seller_id: str
    allowed_buyers: list[str]            # ["*"] = any authenticated buyer
    allowed_purposes: list[str]
    excluded_fields: list[str] = field(default_factory=list)
    price_floor_drops: int = 0
    licence: dict = field(default_factory=dict)   # e.g. {"commercial_training": True, "resale": False}
    version: int = 1

    def evaluate(self, buyer_id: str, purpose: str, fields: list[str], price_drops: int,
                 **_) -> Decision:
        v = f"{self.seller_id}/policy-v{self.version}"
        if "*" not in self.allowed_buyers and buyer_id not in self.allowed_buyers:
            return Decision(DENY, reason="buyer not allowed by seller policy", policy_version=v)
        if purpose not in self.allowed_purposes:
            return Decision(DENY, reason=f"purpose '{purpose}' not allowed", policy_version=v)
        if price_drops < self.price_floor_drops:
            return Decision(DENY, reason="offer below price floor", policy_version=v)
        refused = [f for f in fields if f in self.excluded_fields]
        granted = [f for f in fields if f not in self.excluded_fields]
        if refused:
            return Decision(PARTIAL, granted=granted, refused=refused, policy_version=v,
                            reason=f"policy excludes {', '.join(refused)}; counter-offer without them")
        return Decision(ALLOW, granted=granted, policy_version=v)


# ---------- personal data holder ----------

# Sensitivity sets the protection level; consent sets what may run.
# A sensitive item is never part of a blanket approval: the person must tick it by name.
SENSITIVITY = {
    "sleep.daily": "standard",
    "activity.daily": "standard",
    "heart_rate.daily": "standard",
    "fatigue.survey": "standard",
    "blood_pressure.daily": "sensitive",
}

# Organization data fields that may identify people (faces, plates, voices).
# A buyer agent requests them only if its owner allowed sensitive fields.
SENSITIVE_FIELDS = {"raw_video"}


# Automation level chosen by the person (their preference, not the agent's):
#   confirm_each   - every round waits for the person
#   auto_standard  - consented standard items run automatically; consented sensitive
#                    items still wait for the person each round
#   auto_all       - every consented item runs automatically
AUTOMATION_LEVELS = ("confirm_each", "auto_standard", "auto_all")


@dataclass
class ComplianceRules:
    """Ethics/compliance layer applied before any personal consent is consulted.
    It can only narrow what consent allows, never widen it."""
    prohibited_purposes: list[str] = field(default_factory=lambda: [
        "insurance_pricing", "employment_screening", "marketing_profiling"])
    # buyers registered with an ethics review for sensitive items (static fallback)
    ethics_approved_buyers: list[str] = field(default_factory=list)
    # preferred: look the approval up on the ledger (XRPL Credential issued by an ethics board)
    credential_check: object = None

    def ethics_approved(self, buyer_id: str) -> bool:
        if buyer_id in self.ethics_approved_buyers:
            return True
        return bool(self.credential_check and self.credential_check(buyer_id))

    def check(self, buyer_id: str, purpose: str, fields: list[str]) -> tuple[list[str], str | None]:
        """Returns (fields allowed to proceed, denial reason or None)."""
        if purpose in self.prohibited_purposes:
            return [], f"purpose '{purpose}' is prohibited by the compliance layer"
        if not any(SENSITIVITY.get(f) == "sensitive" for f in fields):
            return list(fields), None
        if not self.ethics_approved(buyer_id):
            kept = [f for f in fields if SENSITIVITY.get(f) != "sensitive"]
            return kept, None
        return list(fields), None


class ConsentStoreUnavailable(Exception):
    pass


class PersonalConsentPolicy:
    """Reads consents from the store. Any read failure -> HOLD (fail closed)."""

    def __init__(self, store, person_id: str, compliance: ComplianceRules | None = None):
        self.store = store
        self.person_id = person_id
        self.compliance = compliance or ComplianceRules()
        self.fail_reads = False  # test hook

    def _consent(self, buyer_id: str):
        if self.fail_reads:
            raise ConsentStoreUnavailable("consent store unreachable")
        return self.store.one("SELECT * FROM consents WHERE person_id=? AND buyer_id=?",
                              self.person_id, buyer_id)

    def evaluate(self, buyer_id: str, purpose: str, fields: list[str], price_drops: int,
                 week: int | None = None, for_delivery: bool = False) -> Decision:
        try:
            c = self._consent(buyer_id)
        except ConsentStoreUnavailable as e:
            return Decision(HOLD, reason=f"held: {e}")
        if not for_delivery:
            kept, why = self.compliance.check(buyer_id, purpose, fields)
            if why:
                return Decision(DENY, reason=why)
        if c is None:
            return Decision(DENY, reason="no consent for this institution")
        v = f"consent-v{c['version']}:{c['doc_hash'][:16]}"
        if c["status"] == "revoked":
            return Decision(DENY, reason="data access consent revoked", policy_version=v)
        if for_delivery:
            # Already paid: pausing stops new orders, not committed deliveries.
            return Decision(ALLOW, granted=list(fields), policy_version=v)
        if c["status"] == "paused":
            return Decision(DENY, reason="supply paused by the person", policy_version=v)
        filtered = [f for f in fields if f not in kept]
        if week is not None and not (c["period_from"] <= week <= c["period_to"]):
            return Decision(DENY, reason="outside the consented period", policy_version=v)
        if purpose != c["purpose"]:
            return Decision(NEEDS_APPROVAL, pending=list(kept), refused=filtered, policy_version=v,
                            reason=f"new purpose '{purpose}' needs the person's approval")
        per_item = price_drops // max(len(fields), 1)
        if per_item < c["min_price_drops"]:
            return Decision(DENY, reason="below the person's minimum price", policy_version=v)
        allowed = set(json.loads(c["items"]))
        confirmed = self._round_confirmed(buyer_id, week)
        granted, pending, round_confirm = [], [], []
        for f in kept:
            needs_round = (c["automation"] == "confirm_each" or
                           (c["automation"] == "auto_standard" and SENSITIVITY.get(f) == "sensitive"))
            if f not in allowed:
                pending.append(f)                      # outside consent: ask, never assume
            elif needs_round and f not in confirmed:
                pending.append(f)
                round_confirm.append(f)
            else:
                granted.append(f)
        notes = []
        if filtered:
            notes.append(f"{', '.join(filtered)} filtered (sensitive; no ethics credential on ledger)")
        if pending:
            notes.append(f"{', '.join(pending)} wait for the person")
        reason = "; ".join(notes)
        if not granted:
            if pending:
                return Decision(NEEDS_APPROVAL, pending=pending, refused=filtered, reason=reason,
                                policy_version=v, round_confirm=round_confirm)
            return Decision(DENY, refused=filtered, reason=reason or "nothing allowed", policy_version=v)
        status = PARTIAL if (pending or filtered) else ALLOW
        return Decision(status, granted=granted, pending=pending, refused=filtered,
                        reason=reason, policy_version=v, round_confirm=round_confirm)

    def _round_confirmed(self, buyer_id: str, week: int | None) -> set[str]:
        if week is None:
            return set()
        rows = self.store.q("SELECT decided_items FROM approval_requests WHERE person_id=? AND buyer_id=? "
                            "AND kind='round' AND week=? AND status='decided'", self.person_id, buyer_id, week)
        out: set[str] = set()
        for r in rows:
            out |= set(json.loads(r["decided_items"] or "[]"))
        return out
