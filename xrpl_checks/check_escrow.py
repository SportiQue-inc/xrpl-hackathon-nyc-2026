"""3. Key-reveal escrow: EscrowFinish publishes the data key; after the deadline EscrowCancel refunds."""
import time

from common import run
from agentrail.ledger.conditions import condition_hex, fulfillment_hex, key_from_fulfillment, new_key


def main(c, L):
    buyer = c.account("buyer (study)", L.new_account("esc_buyer"))
    payee = c.account("payee (participant agent)", L.new_account("esc_payee"))
    amt = 1_000_000

    # A: finish path
    k = new_key()
    now = L.now()
    t = time.time()
    cr = L.prepare_escrow_create(buyer, payee, amt, condition_hex(k), now + 600, "check:finish")
    L.submit(cr)
    c.step("EscrowCreate (condition = sha256(K), CancelAfter +10 min)", cr.tx_hash,
           L.wait_validated(cr.tx_hash, 60).result, "tesSUCCESS", t)
    t = time.time()
    bad = L.prepare_escrow_finish(payee, buyer, cr.sequence, condition_hex(k), fulfillment_hex(new_key()), "wrong")
    L.submit(bad)
    c.step("EscrowFinish with a wrong key", bad.tx_hash, L.wait_validated(bad.tx_hash, 60).result,
           "tecCRYPTOCONDITION_ERROR", t, "failure")
    t = time.time()
    early = L.prepare_escrow_cancel(buyer, buyer, cr.sequence)
    L.submit(early)
    c.step("EscrowCancel before the deadline", early.tx_hash, L.wait_validated(early.tx_hash, 60).result,
           "tecNO_PERMISSION", t, "failure")
    before = L.balance_drops(payee)
    t = time.time()
    fin = L.prepare_escrow_finish(payee, buyer, cr.sequence, condition_hex(k), fulfillment_hex(k), "reveal")
    L.submit(fin)
    st = L.wait_validated(fin.tx_hash, 60)
    c.step("EscrowFinish revealing K (payee paid)", fin.tx_hash, st.result, "tesSUCCESS", t)
    recovered = st.fulfillment and key_from_fulfillment(st.fulfillment) == k
    c.step("buyer reads K back from the validated EscrowFinish", None, str(bool(recovered)), "True", time.time(), "check")
    c.note(f"payee balance +{L.balance_drops(payee) - before} drops (escrow {amt}, minus finish fee)")

    # B: cancel path
    k2 = new_key()
    now = L.now()
    window = 20
    t = time.time()
    cr2 = L.prepare_escrow_create(buyer, payee, amt, condition_hex(k2), now + window, "check:cancel")
    L.submit(cr2)
    c.step(f"EscrowCreate (CancelAfter +{window}s)", cr2.tx_hash, L.wait_validated(cr2.tx_hash, 60).result,
           "tesSUCCESS", t)
    while L.now() <= now + window:
        time.sleep(3)
    t = time.time()
    late = L.prepare_escrow_finish(payee, buyer, cr2.sequence, condition_hex(k2), fulfillment_hex(k2), "late")
    L.submit(late)
    c.step("EscrowFinish after the deadline", late.tx_hash, L.wait_validated(late.tx_hash, 60).result,
           "tecNO_PERMISSION", t, "failure")
    before = L.balance_drops(buyer)
    t = time.time()
    x = L.prepare_escrow_cancel(buyer, buyer, cr2.sequence)
    L.submit(x)
    c.step("EscrowCancel after the deadline (refund)", x.tx_hash, L.wait_validated(x.tx_hash, 60).result,
           "tesSUCCESS", t)
    c.note(f"buyer balance +{L.balance_drops(buyer) - before} drops on cancel (escrow {amt}, minus fee)")
    return c.save("Key-reveal escrow behaves as designed: wrong key and early cancel are refused, the valid "
                  "EscrowFinish puts K on the ledger, and after the deadline only EscrowCancel (refund) works.")


if __name__ == "__main__":
    run("3_escrow", "Key-reveal conditional Escrow", ["Escrow", "fix1571"], main)
