"""5. x402 via the T54 Testnet facilitator: one hospital export API fee, paid once.
Uses the engine's X402Mixin (PAYMENT_RAIL=x402) end to end, then shows that a tampered
requirement and a replayed payment header are refused."""
import time

from common import run
from x402_xrpl import FacilitatorClient, FacilitatorClientOptions

from agentrail.ledger.x402_rail import FACILITATOR_URL

FEE = 100_000  # 0.1 XRP per export call


def main(c, L):
    buyer = c.account("buyer agent", L.new_account("x402_buyer"))
    api = c.account("hospital export API (payTo)", L.new_account("x402_hospital_api"))
    c.note(f"facilitator: {FACILITATOR_URL}")
    fac = FacilitatorClient(FacilitatorClientOptions(base_url=FACILITATOR_URL, timeout_seconds=60))
    try:
        c.note(f"/supported: {fac.supported().__dict__}")
    except Exception as e:  # noqa: BLE001
        c.note(f"/supported failed: {e}")

    t = time.time()
    p = L.prepare_payment(buyer, api, FEE, "00" * 32, "export:hospital_A:study_A:cohort_v1")
    c.note(f"HTTP 402 body the gate returns: {L.challenges[-1]}")
    before = L.balance_drops(api)
    L.submit(p)  # facilitator verify + settle
    st = L.wait_validated(p.tx_hash, 60)
    c.step("x402 verify+settle via T54, confirmed on a validated ledger", p.tx_hash, st.result, "tesSUCCESS", t)
    c.step("hospital API received exactly the fee", None, str(L.balance_drops(api) - before), str(FEE),
           time.time(), "check")

    header, req = L._x402_state()[p.tx_hash]
    t = time.time()
    try:
        s = fac.settle(payment_header=header, payment_requirements=req)
        res = f"success={s.success} reason={s.error_reason}"
    except Exception as e:  # noqa: BLE001
        res = f"refused: {e}"
    c.step("replay the same payment header", None, res, None, t, "failure",
           "must not pay twice: same signed tx, sequence already used")

    from dataclasses import replace
    t = time.time()
    try:
        v = fac.verify(payment_header=header, payment_requirements=replace(req, amount=str(FEE * 10)))
        res = f"is_valid={v.is_valid} reason={v.invalid_reason}"
    except Exception as e:  # noqa: BLE001
        res = f"refused: {e}"
    c.step("verify against a different price (tampered requirement)", None, res, None, t, "failure")
    return c.save("x402 one-off API payment settles on Testnet through T54 and is confirmed on the ledger; "
                  "see replay/tamper rows for how the facilitator refuses misuse.")


if __name__ == "__main__":
    run("5_x402", "x402 hospital export API fee (T54 facilitator)", [], main, rail="x402")
