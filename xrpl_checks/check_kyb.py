"""1. KYB: VERIFIED_ORG credential + DepositAuth/DepositPreauth on the participant account.
Unverified org payments are refused by the ledger (tecNO_PERMISSION)."""
import time

from common import run
from agentrail.ledger.conditions import condition_hex, fulfillment_hex, new_key
from agentrail.ledger.xrpl_extras import submit_capture
from xrpl.models.transactions import EscrowCreate, EscrowFinish, Payment

CRED = "VERIFIED_ORG"
INV = "00" * 32


def main(c, L):
    reg = c.account("kyb_registry (credential issuer)", L.new_account("kyb_registry"))
    part = c.account("participant_agent (DepositAuth)", L.new_account("kyb_participant"))
    good = c.account("org_verified", L.new_account("kyb_org_verified"))
    bad = c.account("org_unverified", L.new_account("kyb_org_unverified"))

    t = time.time()
    hs = L.issue_credential(reg, good, CRED)
    for h, lab in zip(hs, ["CredentialCreate (registry -> verified org)", "CredentialAccept (verified org)"]):
        c.step(lab, h, "tesSUCCESS", "tesSUCCESS", t, "setup")
    t = time.time()
    hs = L.require_credential_deposits(part, reg, CRED)
    for h in hs:
        c.step("participant DepositAuth / DepositPreauth(AuthorizeCredentials)", h, "tesSUCCESS", "tesSUCCESS", t, "setup")
    cid = L.credential_id(good, reg, CRED)
    c.note(f"VERIFIED_ORG credential ledger index (goes in CredentialIDs): {cid}")

    def pay(src, label, expect, kind):
        t = time.time()
        p = L.prepare_payment(src, part, 1_000_000, INV, f"kyb:{label}")
        L.submit(p)
        st = L.wait_validated(p.tx_hash, timeout=60)
        return c.step(label, p.tx_hash, st.result, expect, t, kind)

    pay(good, "Payment verified org -> participant (engine attaches CredentialIDs)", "tesSUCCESS", "success")
    pay(bad, "Payment unverified org -> participant", "tecNO_PERMISSION", "failure")
    t = time.time()
    h, code, _ = submit_capture(L.client, Payment(account=good, destination=part, amount="1000000"), L.wallets[good])
    c.step("Payment verified org WITHOUT CredentialIDs", h, code, "tecNO_PERMISSION", t, "failure",
           "holding the credential is not enough; the tx must cite it")

    # Escrow: DepositAuth gates EscrowFinish (by a non-destination), not EscrowCreate.
    now = L.now()
    for who, label in ((bad, "unverified"), (good, "verified")):
        k = new_key()
        t = time.time()
        h, code, r = submit_capture(L.client, EscrowCreate(account=who, destination=part, amount="1000000",
                                                           condition=condition_hex(k), cancel_after=now + 3600),
                                    L.wallets[who])
        c.step(f"EscrowCreate {label} org -> participant", h, code, "tesSUCCESS", t, "observe",
               "EscrowCreate is not gated by DepositAuth" if label == "unverified" else "")
        seq = r.get("tx_json", r).get("Sequence")
        t = time.time()
        creds = L.credential_ids_for(who, part)
        h, code, _ = submit_capture(L.client, EscrowFinish(account=who, owner=who, offer_sequence=seq,
                                                           condition=condition_hex(k), fulfillment=fulfillment_hex(k),
                                                           credential_ids=creds), L.wallets[who])
        c.step(f"EscrowFinish submitted by {label} org" + (" with CredentialIDs" if creds else ""), h, code,
               "tesSUCCESS" if creds else "tecNO_PERMISSION", t, "success" if creds else "failure")
    c.note("If the participant (the escrow destination) submits EscrowFinish itself, DepositAuth does not apply. "
           "So on the escrow route the KYB gate is the participant agent checking has_credential() before it "
           "reveals the key; on the Payment/x402 route the ledger enforces it.")
    return c.save("Unverified orgs are refused on the ledger (tecNO_PERMISSION) for Payment and third-party "
                  "EscrowFinish; verified orgs pass only when the tx carries CredentialIDs.")


if __name__ == "__main__":
    run("1_kyb", "KYB credential + DepositPreauth", ["Credentials", "DepositAuth", "DepositPreauth"], main)
