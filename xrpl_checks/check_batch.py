"""4. Atomic multi-institution purchase. Batch (XLS-56) if enabled on Testnet; otherwise
(and in any case, as the fallback the engine can rely on) a bundle of escrows that share
one condition: revealing K finishes all of them, the deadline refunds all of them."""
import time

from common import amendment_status, client, run
from agentrail.ledger.conditions import condition_hex, fulfillment_hex, new_key
from agentrail.ledger.xrpl_extras import submit_capture
from xrpl.models.requests import Tx
from xrpl.models.transactions import Batch, BatchFlag, Payment


def inner_applied(L, inner_hash):
    r = L.client.request(Tx(transaction=inner_hash)).result
    return r.get("validated") and r.get("meta", {}).get("TransactionResult")


def batch_part(c, L, buyer, insts):
    amt = "1000000"
    t = time.time()
    tx = Batch(account=buyer, flags=BatchFlag.TF_ALL_OR_NOTHING,
               raw_transactions=[Payment(account=buyer, destination=d, amount=amt) for d in insts])
    h, code, r = submit_capture(L.client, tx, L.wallets[buyer])
    c.step("Batch ALL_OR_NOTHING: 2 Payments buyer -> hospital A, B", h, code, "tesSUCCESS", t)
    for i, raw in enumerate((r.get("tx_json", r).get("RawTransactions") or [])):
        ih = _inner_hash(raw)
        if ih:
            c.step(f"  inner Payment #{i + 1}", ih, inner_applied(L, ih) or "not applied", "tesSUCCESS", t, "check")

    # Failure: second inner payment cannot apply (new unfunded address, amount below reserve).
    from xrpl.wallet import Wallet
    ghost = Wallet.create().classic_address
    before = L.balance_drops(insts[0])
    t = time.time()
    tx = Batch(account=buyer, flags=BatchFlag.TF_ALL_OR_NOTHING,
               raw_transactions=[Payment(account=buyer, destination=insts[0], amount=amt),
                                 Payment(account=buyer, destination=ghost, amount="1000")])
    h, code, r = submit_capture(L.client, tx, L.wallets[buyer])
    c.step("Batch ALL_OR_NOTHING where payment #2 must fail", h, code, None, t, "failure",
           "outer tx is accepted; what matters is that no inner payment applied")
    got = L.balance_drops(insts[0]) - before
    c.step("hospital A received nothing from the failed batch", None, str(got), "0", time.time(), "check")


def _inner_hash(raw):
    from xrpl.models.transactions.transaction import Transaction
    try:  # inner txs carry tfInnerBatchTxn, so get_hash works without a signature
        return Transaction.from_xrpl(raw.get("RawTransaction", raw)).get_hash()
    except Exception:  # noqa: BLE001
        return None


def escrow_bundle_part(c, L, buyer, insts):
    k = new_key()
    cond = condition_hex(k)
    now = L.now()
    created = []
    for i, d in enumerate(insts):
        t = time.time()
        p = L.prepare_escrow_create(buyer, d, 1_000_000, cond, now + 900, f"bundle:{i}")
        L.submit(p)
        c.step(f"bundle EscrowCreate -> hospital {'AB'[i]} (same condition)", p.tx_hash,
               L.wait_validated(p.tx_hash, 60).result, "tesSUCCESS", t)
        created.append(p)
    # One reveal of K lets every leg finish; anyone can submit the finish.
    for i, (d, p) in enumerate(zip(insts, created)):
        t = time.time()
        f = L.prepare_escrow_finish(d, buyer, p.sequence, cond, fulfillment_hex(k), "bundle")
        L.submit(f)
        c.step(f"bundle EscrowFinish hospital {'AB'[i]} with the same K", f.tx_hash,
               L.wait_validated(f.tx_hash, 60).result, "tesSUCCESS", t)
    c.note("Escrow bundle is atomic in the sense the demo needs: until K is revealed no hospital is paid, after "
           "the deadline every leg is refundable with EscrowCancel, and once K is public every leg can be "
           "finished by anyone. It is not single-ledger atomic like Batch.")


def main(c, L):
    buyer = c.account("buyer (study)", L.new_account("batch_buyer"))
    insts = [c.account("hospital_A", L.new_account("batch_hosp_a")),
             c.account("hospital_B", L.new_account("batch_hosp_b"))]
    enabled = c.amendments.get("Batch") == "enabled"
    blocker = None
    if enabled:
        try:
            batch_part(c, L, buyer, insts)
        except Exception as e:  # noqa: BLE001
            blocker = f"Batch submit failed: {type(e).__name__}: {e}"
            c.note(blocker)
    else:
        c.note(f"Batch amendment on Testnet: {c.amendments.get('Batch')}; running the escrow bundle instead")
    escrow_bundle_part(c, L, buyer, insts)
    return c.save(("Batch works on Testnet (all-or-nothing verified)." if enabled and not blocker else
                   "Batch not usable on Testnet; escrow bundle with a shared condition works.")
                  + " Escrow bundle verified as the fallback.",
                  blocker=None if enabled and not blocker else (blocker or "Batch amendment not enabled"),
                  alternative="Escrow bundle: N EscrowCreate with the same condition; one key reveal finishes all")


if __name__ == "__main__":
    run("4_batch", "Batch atomic multi-hospital purchase", ["Batch", "fixBatchInnerSigs"], main)
