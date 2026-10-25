"""Testnet smoke test for the key-reveal escrow: one finish, one cancel after deadline.
Run: LEDGER=testnet python scripts/escrow_smoke.py"""
import time

from agentrail.ledger import make_ledger
from agentrail.ledger.conditions import condition_hex, fulfillment_hex, new_key

L = make_ledger("testnet")
buyer, payee = L.new_account("smoke_buyer"), L.new_account("smoke_payee")
for label, window, finish in (("finish", 300, True), ("cancel", 15, False)):
    now = L.now()  # per case: the finish case alone takes longer than the 15 s cancel window
    k = new_key()
    c = L.prepare_escrow_create(buyer, payee, 1_000_000, condition_hex(k), now + window, f"smoke:{label}")
    L.submit(c)
    st = L.wait_validated(c.tx_hash)
    print(label, "EscrowCreate", st.result, L.explorer_url(c.tx_hash))
    if finish:
        f = L.prepare_escrow_finish(payee, buyer, c.sequence, condition_hex(k), fulfillment_hex(k), "smoke")
        L.submit(f)
        st = L.wait_validated(f.tx_hash)
        print("  EscrowFinish", st.result, "fulfillment on ledger:", bool(st.fulfillment), L.explorer_url(f.tx_hash))
    else:
        while L.now() <= now + window:
            time.sleep(3)
        x = L.prepare_escrow_cancel(buyer, buyer, c.sequence)
        L.submit(x)
        st = L.wait_validated(x.tx_hash)
        print("  EscrowCancel", st.result, L.explorer_url(x.tx_hash))
