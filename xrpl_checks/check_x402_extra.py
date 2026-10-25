"""5b. x402 details from the agent-payments research:
- /supported on both T54 hosts lists xrpl:1 + exact
- invoice binding "both" (Memos + InvoiceID) vs "invoice_id" (spec: no Memos, InvoiceID = sha256(invoiceId))
- two sequential payments from the same payer both settle
- optional: an x402Secure extension without a real Verifiable Intent chain is refused"""
import hashlib
import os
import time
import uuid

from common import run
from x402_xrpl import FacilitatorClient, FacilitatorClientOptions, PaymentRequirements
from x402_xrpl.client.presigned_payment_payer import XRPLPresignedPaymentPayer, XRPLPresignedPaymentPayerOptions
from xrpl.core.binarycodec import decode

HOSTS = [os.environ.get("X402_FACILITATOR_URL", "https://xrpl-facilitator-testnet.t54.ai"), "https://xrpl-x402.t54.ai"]
FEE = 10_000


def pay_once(c, L, fac, buyer, api, binding, label):
    invoice = f"export:hospital_A:{label}:{uuid.uuid4().hex[:8]}"
    req = PaymentRequirements(scheme="exact", network="xrpl:1", amount=str(FEE), asset="XRP", pay_to=api,
                              max_timeout_seconds=300, extra={"invoiceId": invoice})
    payer = XRPLPresignedPaymentPayer(XRPLPresignedPaymentPayerOptions(
        wallet=L.wallets[buyer], network="xrpl:1", rpc_url=L.client.url, invoice_binding=binding), client=L.client)
    prep = payer.prepare_payment(req)
    tx = decode(prep.signed_tx_blob)
    t = time.time()
    try:
        v = fac.verify(payment_header=prep.payment_header, payment_requirements=req)
        if not v.is_valid:
            return c.step(f"[{binding}] {label}: verify", None, f"invalid: {v.invalid_reason}", "tesSUCCESS", t), tx, req, prep
        s = fac.settle(payment_header=prep.payment_header, payment_requirements=req)
    except Exception as e:  # noqa: BLE001
        return c.step(f"[{binding}] {label}: verify/settle", None, f"error: {e}", "tesSUCCESS", t), tx, req, prep
    st = L.wait_validated(s.transaction, 60) if s.transaction else None
    want = hashlib.sha256(invoice.encode()).hexdigest().upper()
    c.step(f"[{binding}] {label}: settle", s.transaction or None, st.result if st else f"settle failed {s.error_reason}",
           "tesSUCCESS", t, "success",
           f"Memos={'yes' if tx.get('Memos') else 'no'} InvoiceID==sha256(invoiceId): {tx.get('InvoiceID') == want}")
    return st, tx, req, prep


def main(c, L):
    buyer = c.account("buyer agent", L.new_account("x402_buyer"))
    api = c.account("hospital export API", L.new_account("x402_hospital_api"))
    for h in HOSTS:
        t = time.time()
        try:
            kinds = FacilitatorClient(FacilitatorClientOptions(base_url=h, timeout_seconds=30)).supported().__dict__
            has = "xrpl:1" in str(kinds) and "exact" in str(kinds)
            c.step(f"GET {h}/supported lists xrpl:1 + exact", None, str(has), "True", t, "check", str(kinds)[:300])
        except Exception as e:  # noqa: BLE001
            c.step(f"GET {h}/supported", None, f"error: {e}", None, t, "observe")
    fac = FacilitatorClient(FacilitatorClientOptions(base_url=HOSTS[0], timeout_seconds=60))

    pay_once(c, L, fac, buyer, api, "both", "binding both")
    pay_once(c, L, fac, buyer, api, "invoice_id", "binding invoice_id (spec)")
    pay_once(c, L, fac, buyer, api, "both", "sequential #1")
    _, _, req, prep = pay_once(c, L, fac, buyer, api, "both", "sequential #2")

    # Optional: x402Secure extension with a made-up intent chain should be refused.
    t = time.time()
    try:
        v = fac.verify(payment_header=prep.payment_header, payment_requirements=req,
                       extensions={"x402Secure": {"intent": {"chain": ["synthetic-not-signed"]}}})
        res = f"is_valid={v.is_valid} reason={v.invalid_reason}"
    except Exception as e:  # noqa: BLE001
        res = f"refused: {str(e)[:200]}"
    c.step("verify with a fake x402Secure extension (optional)", None, res, None, t, "observe",
           "not used on the demo's main path")
    return c.save("See rows: facilitator hosts, both invoice bindings, two sequential payments.")


if __name__ == "__main__":
    run("5b_x402_extra", "x402 facilitator hosts, invoice binding, sequential payments", [], main)
