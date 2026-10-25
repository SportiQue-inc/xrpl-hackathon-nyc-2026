"""2. Data licence as MPT: issued by the participant agent, max supply 1, RequireAuth +
CanClawback, no CanTransfer. Onward transfer is refused; revoke claws it back."""
import json
import time

from common import run
from agentrail.ledger.licence import licence_metadata
from xrpl.models.requests import GenericRequest
from xrpl.models.transactions import MPTokenAuthorize

LSF_MPT_CAN_TRANSFER = 0x20
LSF_MPT_REQUIRE_AUTH = 0x04
LSF_MPT_CAN_CLAWBACK = 0x40


def main(c, L):
    from agentrail.ledger.xrpl_extras import submit_capture
    issuer = c.account("participant_agent (MPT issuer)", L.new_account("mpt_participant"))
    study = c.account("study_A (licence holder)", L.new_account("mpt_study_a"))
    other = c.account("study_B (third party)", L.new_account("mpt_study_b"))

    meta = licence_metadata("study_A", ["DUO:0000007", "DUO:0000019"], "ab" * 32)
    t = time.time()
    mpt_id, hs = L.issue_licence(issuer, study, meta)
    for h, lab in zip(hs, ["MPTokenIssuanceCreate (max 1, RequireAuth|CanClawback)",
                           "MPTokenAuthorize (study opts in)", "MPTokenAuthorize (issuer authorizes study)",
                           "MPT Payment issuer -> study (licence granted)"]):
        c.step(lab, h, "tesSUCCESS", "tesSUCCESS", t, "success")
    c.note(f"mpt_issuance_id = {mpt_id}")

    # Cross-check the id and flags on the ledger itself.
    r = L.client.request(GenericRequest(method="ledger_entry", mpt_issuance=mpt_id, ledger_index="validated")).result
    node = r.get("node", {})
    flags = int(node.get("Flags", 0))
    c.note(f"issuance on ledger: found={bool(node)} MaximumAmount={node.get('MaximumAmount')} "
           f"CanTransfer={bool(flags & LSF_MPT_CAN_TRANSFER)} RequireAuth={bool(flags & LSF_MPT_REQUIRE_AUTH)} "
           f"CanClawback={bool(flags & LSF_MPT_CAN_CLAWBACK)}")
    if node.get("MPTokenMetadata"):
        c.note("metadata on ledger: " + bytes.fromhex(node["MPTokenMetadata"]).decode())
    if not node:
        raise RuntimeError(f"mpt_issuance {mpt_id} not found on ledger: {r}")
    held = L.licence_held(study, mpt_id)
    c.step("licence_held(study_A) after grant", None, str(held), "True", time.time(), "check")

    t = time.time()
    h, code, _ = submit_capture(L.client, MPTokenAuthorize(account=other, mptoken_issuance_id=mpt_id), L.wallets[other])
    c.step("MPTokenAuthorize (study_B opts in, to rule out 'no holder object')", h, code, "tesSUCCESS", t, "setup")
    t = time.time()
    code = L.transfer_licence(study, other, mpt_id)
    c.step("study_A -> study_B onward transfer", L.last_tx_hash, code, "tecNO_AUTH", t, "failure",
           "no CanTransfer: holders cannot pass the licence on")

    t = time.time()
    h = L.clawback_licence(issuer, study, mpt_id)
    c.step("Clawback issuer <- study_A (consent revoked)", h, "tesSUCCESS", "tesSUCCESS", t, "success")
    held = L.licence_held(study, mpt_id)
    c.step("licence_held(study_A) after clawback", None, str(held), "False", time.time(), "check")
    t = time.time()
    code = L.transfer_licence(study, other, mpt_id)
    c.step("study_A tries to use/transfer after clawback", L.last_tx_hash, code, None, t, "observe")
    return c.save("Licence MPT works end to end: non-transferable (tecNO_AUTH on onward transfer) and "
                  "revocable by Clawback; licence_held() flips to False.")


if __name__ == "__main__":
    run("2_mpt_licence", "MPT data licence + Clawback", ["MPTokensV1", "Clawback"], main)
