"""Contract tests: engine results turned into the records UniQdata and UniQLab already store."""
import json

import pytest

from agentrail import payout, scenario, study, uniqdata_port as port
from agentrail.cohort import HERO
from agentrail.engine import sha256_hex
from tests.llm_doubles import capable_needs

LAB = study.LAB
PROJECT = "project-sleeplab"


@pytest.fixture
def revoked():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.set_goal(w, "", capable_needs)
    assert study.approve(w, ["owner", "compliance"])["ok"]
    study.send(w)
    rid = study.participant_view(w, HERO)["requests"][0]["id"]
    study.participant_approve(w, HERO, rid, ["fatigue.survey"])
    doc = json.loads(w.store.one("SELECT doc FROM consents WHERE person_id=? AND buyer_id=?", HERO, LAB)["doc"])
    return w, doc, study.participant_revoke(w, HERO)


def test_separate_consents_map_to_uniqdata_lanes(revoked):
    _, doc, _ = revoked
    rows = port.consent_grants(doc, PROJECT)
    assert [r["consent_type"] for r in rows] == ["research_participation"]   # no sensitive item ticked
    assert rows[0]["engine_consent_hash"] == doc["separate_consents"][0]["hash"]


def test_sensitive_consent_maps_to_the_sensitive_health_lane(revoked):
    _, doc, _ = revoked
    parts = [{**p, "granted": True} if p["kind"] == "sensitive_data" else p for p in doc["separate_consents"]]
    lanes = [r["consent_type"] for r in port.consent_grants({**doc, "separate_consents": parts}, PROJECT)]
    assert lanes == ["research_participation", "sensitive_health_collection"]


def test_granted_international_transfer_has_no_lane_and_blocks(revoked):
    _, doc, _ = revoked
    parts = [{**p, "granted": True} if p["kind"] == "international_transfer" else p for p in doc["separate_consents"]]
    with pytest.raises(port.UnmappedConsent):
        port.consent_grants({**doc, "separate_consents": parts}, PROJECT)


def test_revoke_opens_a_new_privacy_epoch_and_records_the_deletion(revoked):
    _, _, r = revoked
    rec = port.withdrawal_record(r, PROJECT, privacy_epoch=4)
    assert rec["boundary"] == {"action": "supersede", "project_id": PROJECT,
                               "participant_number": r["person"]["study_pseudonym"], "superseding_epoch": 5}
    audit = rec["deletion_audit"]
    assert audit["records_deleted"] == r["deletion"]["bundles_destroyed"] + r["deletion"]["cells_destroyed"]
    assert audit["confirmation_hash"] == r["deletion"]["confirmation_hash"]


def test_paid_rounds_are_retained_and_undelivered_rounds_are_not_earned(revoked):
    _, _, r = revoked
    rec = port.withdrawal_record(r, PROJECT, privacy_epoch=0)
    fatigue = {x["weeks"][0]: x["earn_status"] for x, c in zip(rec["rewards"], r["contributions"])
               if "fatigue.survey" in c["items"]}
    assert fatigue == {3: "paid", 4: "paid", 5: "not_earned"}   # week 5 held at revoke, refunded to the study
    assert rec["research_rewards_retained"] == sum(x["earn_status"] in ("paid", "pending") for x in rec["rewards"])
    assert rec["unmapped"] == []
    assert rec["refund_txs"] and all(rec["refund_txs"])


def test_held_share_stays_pending_and_bonus_goes_back_after_revoke(revoked):
    _, _, r = revoked
    held = {x["part"]: [] for x in port.withdrawal_record(r, PROJECT, 0)["rewards"]}
    for x in port.withdrawal_record(r, PROJECT, 0)["rewards"]:
        held[x["part"]].append(x["earn_status"])
    assert held["round_held"] and set(held["round_held"]) == {"pending"}    # 20% part, paid when review ends
    assert held["bonus_held"] == ["not_earned"]                              # completion bonus returns


def test_released_held_parts_get_their_own_receipt(revoked):
    w, _, _ = revoked
    payout.release_due(w)
    v = study.participant_view(w, HERO)
    receipts = port.payout_receipts(v["contributions"], "mock", v["payout"]["holdbacks"])
    released = [h for h in v["payout"]["holdbacks"] if h["status"] == "released"]
    held_refs = {x["payout_intent_ref"] for x in receipts if x["payout_intent_ref"].startswith("agentrail:holdback:")}
    assert released and held_refs == {f"agentrail:holdback:{h['id']}" for h in released}
    assert len({x["payout_intent_ref"] for x in receipts}) == len(receipts)


def test_unknown_engine_status_is_never_counted_as_earned(revoked):
    _, _, r = revoked
    odd = {**r, "contributions": [{**r["contributions"][0], "status": "something_new"}], "payout": {"holdbacks": []}}
    rec = port.withdrawal_record(odd, PROJECT, 0)
    assert rec["research_rewards_retained"] == 0 and rec["unmapped"]


def test_pause_and_decline_do_not_supersede_queued_commands():
    assert port.privacy_boundary("pause", PROJECT, "S-x", 2)["action"] == "hold_new"
    assert port.privacy_boundary("decline_round", PROJECT, "S-x", 2)["superseding_epoch"] is None


def test_one_payout_receipt_per_delivered_round(revoked):
    _, _, r = revoked
    receipts = port.payout_receipts(r["contributions"], "mock")
    delivered = [c for c in r["contributions"] if c["status"] == "delivered"]
    assert len(receipts) == len(delivered) > 0
    assert len({x["payout_intent_ref"] for x in receipts}) == len(receipts)
    for rec, c in zip([x for x in receipts if x["payout_intent_ref"].startswith("agentrail:order:")], delivered):
        assert rec["receipt_ref_hash"] == sha256_hex(c["finish"]["tx"])
        assert isinstance(rec["amount_minor"], int) and rec["currency"] == "XRP"


def test_no_participant_id_leaves_through_the_port(revoked):
    w, doc, r = revoked
    out = json.dumps([port.withdrawal_record(r, PROJECT, 0),
                      port.payout_receipts(r["contributions"], "mock", r["payout"]["holdbacks"]),
                      port.consent_grants(doc, PROJECT)])
    assert HERO not in out and w.engine.party(HERO)["address"] not in out
