"""Port from the engine to the shapes UniQdata (participant app) and UniQLab (researcher
workspace) already use. Written during the hackathon. No UniQdata or UniQLab code is imported or
copied; only the field names and rules of their existing contracts are mirrored, as listed in
docs/REUSE_LOG.md. Nothing here calls a UniQdata server: every function turns an engine result
into the record UniQdata would store, so the contract can be tested without one.

Where the two models differ, the mapping is explicit and fails closed:
- consent: the engine's three separate consents map to UniQdata consent lanes; international
  transfer has no UniQdata lane, so a granted one blocks the hand-off instead of being dropped.
- withdrawal: UniQdata keeps paid and pending research rewards after a revoke. The engine refunds
  rounds that were not delivered when the person revoked, so those are reported as not earned,
  never as retained pending rewards. The held 20% of delivered rounds stays the person's and maps
  to pending (paid when review ends); the completion bonus goes back to the study.
- an engine status this port does not know is reported as unmapped, never as earned.
"""
from __future__ import annotations

from . import units

from .engine import sha256_hex
from .study import XRP

# engine separate consent kind -> UniQdata consent_type (None: no lane in UniQdata)
CONSENT_LANES = {
    "third_party_provision": "research_participation",
    "sensitive_data": "sensitive_health_collection",
    "international_transfer": None,
}

# engine contribution status -> UniQdata research earn status after a revoke
EARN_STATUS = {
    "delivered": "paid",              # key published, reward released: stays with the person
    "escrowed": "not_earned",         # held round, withheld at revoke; escrow goes back to the study
    "withheld": "not_earned",
    "refunded": "not_earned",
}

# held part of a round / completion bonus (engine holdbacks) -> UniQdata research earn status
HOLDBACK_EARN_STATUS = {
    ("round", "held"): "pending", ("round", "suspected"): "pending", ("round", "released"): "paid",
    ("round", "withheld"): "not_earned", ("round", "returning"): "not_earned", ("round", "returned"): "not_earned",
    ("bonus", "held"): "pending", ("bonus", "earned"): "pending", ("bonus", "released"): "paid",
    ("bonus", "returning"): "not_earned", ("bonus", "returned"): "not_earned",
}


class UnmappedConsent(ValueError):
    """A granted engine consent that UniQdata has no lane for."""


def consent_grants(doc: dict, project_id: str) -> list[dict]:
    """One UniQdata consent row per engine separate consent that is granted. The engine hash of
    each part travels with it so either side can prove which text the person agreed to."""
    rows = []
    for part in doc["separate_consents"]:
        if not part["granted"]:
            continue
        lane = CONSENT_LANES[part["kind"]]
        if lane is None:
            raise UnmappedConsent(f"{part['kind']} is granted but UniQdata has no consent lane for it")
        rows.append({"consent_type": lane, "project_id": project_id, "status": "APPROVED",
                     "scope": part["scope"], "engine_consent_hash": part["hash"],
                     "engine_consent_version": doc["version"]})
    return rows


def privacy_boundary(kind: str, project_id: str, participant_number: str, privacy_epoch: int) -> dict:
    """What UniQdata does with commands already queued for the study when the person stops.
    Revoke opens a new privacy epoch: every queued command from an older epoch is superseded
    (ParticipantCommandService.supersede_for_privacy_boundary). Pause holds new commands only.
    Declining a round touches nothing."""
    if kind == "revoke":
        return {"action": "supersede", "project_id": project_id, "participant_number": participant_number,
                "superseding_epoch": privacy_epoch + 1}
    if kind == "pause":
        return {"action": "hold_new", "project_id": project_id, "participant_number": participant_number,
                "superseding_epoch": None}
    if kind == "decline_round":
        return {"action": "none", "project_id": project_id, "participant_number": participant_number,
                "superseding_epoch": None}
    raise ValueError(f"unknown withdrawal kind {kind}")


def withdrawal_record(revoke: dict, project_id: str, privacy_epoch: int) -> dict:
    """The engine's revoke result as UniQdata's withdrawal lineage: the deletion audit
    (withdraw_enrollment), the privacy boundary, and what happens to each round's reward."""
    pseudonym = revoke["person"]["study_pseudonym"]
    d = revoke["deletion"]
    rewards = [{"ref": f"agentrail:order:{c['order_id']}", "part": "round", "weeks": c["weeks"],
                "amount_minor": round(c["amount_xrp"] * XRP), "engine_status": c["status"],
                "earn_status": EARN_STATUS.get(c["status"], "unmapped")}
               for c in revoke["contributions"]]
    rewards += [{"ref": f"agentrail:holdback:{h['id']}", "part": f"{h['kind']}_held", "weeks": None,
                 "amount_minor": round(h["amount_xrp"] * XRP), "engine_status": h["status"],
                 "earn_status": HOLDBACK_EARN_STATUS.get((h["kind"], h["status"]), "unmapped")}
                for h in (revoke.get("payout") or {}).get("holdbacks", [])]
    return {
        "participant_number": pseudonym,
        "boundary": privacy_boundary("revoke", project_id, pseudonym, privacy_epoch),
        "deletion_audit": {"deletion_type": "project_withdrawal", "status": "completed",
                           "records_deleted": d["bundles_destroyed"] + d["cells_destroyed"],
                           "tables_affected": {"sealed_bundles": d["bundles_destroyed"],
                                               "person_cells": d["cells_destroyed"]},
                           "confirmation_hash": d["confirmation_hash"]},
        "rewards": rewards,
        "research_rewards_retained": sum(r["earn_status"] in ("paid", "pending") for r in rewards),
        "unmapped": [r["ref"] for r in rewards if r["earn_status"] == "unmapped"],
        "refund_txs": [r["tx"] for r in revoke["refunds"]],
    }


def payout_receipts(contributions: list[dict], ledger: str, holdbacks: list[dict] = ()) -> list[dict]:
    """UniQLab payout_receipt rows: one per delivered round (80% part) and one per released held
    part or bonus. The institution pays on XRPL, so SportiQue only records the proof:
    receipt_ref_hash is the SHA-256 of the EscrowFinish tx hash, and the intent ref is the engine
    order or holdback, which makes reconciliation one receipt per intent."""
    out = []
    for h in holdbacks:
        tx = (h.get("release") or {}).get("tx")
        if h["status"] != "released" or not tx:
            continue
        out.append({"payout_intent_ref": f"agentrail:holdback:{h['id']}", "receipt_ref_hash": sha256_hex(tx),
                    "amount_minor": round(h["amount_xrp"] * XRP), "currency": units.UNIT, "status": "ingested",
                    "executed_by_ref": f"xrpl:{ledger}:EscrowFinish",
                    "metadata": {"part": f"{h['kind']}_held", "explorer_url": h["release"].get("url")}})
    for c in contributions:
        tx = (c.get("finish") or {}).get("tx")
        if c["status"] != "delivered" or not tx:
            continue
        out.append({"payout_intent_ref": f"agentrail:order:{c['order_id']}",
                    "receipt_ref_hash": sha256_hex(tx),
                    "amount_minor": round(c["amount_xrp"] * XRP), "currency": units.UNIT,
                    "status": "ingested", "executed_by_ref": f"xrpl:{ledger}:EscrowFinish",
                    "metadata": {"weeks": c["weeks"], "explorer_url": c["finish"].get("url")}})
    return out
