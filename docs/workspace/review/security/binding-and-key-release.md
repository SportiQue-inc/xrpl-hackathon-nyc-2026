# Bundle binding and key release: independent check on main (0d895b7)

Tests: `tests/test_binding.py` on branch `claude/project-thread-qyrkp7` (not on main). Gaps are
`xfail(strict=True)`: each one turns into a failure once fixed, so the marker gets removed. Result
today: 3 passed, 4 xfailed.

## Holds

| Property | Evidence |
|---|---|
| K alone does not open a bundle for a third party. Vault path: the outer layer is ECDH to the institution's key, the inner is K (`vault/keys.py:104-120`). Engine path: the inner layer is a SealedBox to the buyer, the outer is K (`engine.py:160-176`). | `test_vault_bundle_needs_the_institution_key_as_well_as_k`, `test_engine_bundle_with_k_alone_is_still_sealed_to_the_buyer` |
| The contract hash covers the certified root (`market/exchange.py:411-415`). The vault checks the bundle hash when it opens (`vault/keys.py:94`). | code read |

## Gaps (most severe first)

1. **A failed or late EscrowFinish publishes K, and the buyer gets the data plus the refund.**
   `engine._escrow_finish` (`engine.py:554-581`) and `PushDelivery.reveal` (`vault/delivery.py:132`)
   never compare ledger time with `cancel_after`. A finish submitted at or after CancelAfter fails
   on XRPL with `tecNO_PERMISSION`. A tec result is still written into the ledger together with its
   `Fulfillment`, so K becomes public. The buyer already holds the locked bundle (delivery happens
   at the escrowed stage), opens it, and then sweeps the refund. A finish that is merely broadcast
   and never applied also exposes K to anyone watching the network, and `_send` re-signs it after
   LastLedgerSequence (`engine.py:448-456`).
   *Test:* `test_late_finish_does_not_publish_k` (xfail), and `test_late_finish_today_gives_the_buyer_the_data_and_the_refund` (shows the effect).
   *Fix:* in `_escrow_finish`, refuse to sign when `ledger.now() + margin >= cancel_after`, with a
   margin that covers LastLedgerSequence plus the validation wait (e.g. 120 s on Testnet). Set
   LastLedgerSequence so the tx cannot apply after that point, and never re-sign a finish whose
   first blob may have been broadcast. Make the window long enough that an honest reveal never hits
   the margin (600 s default today, `engine.py:83`). The same check belongs in `reveal`.

2. **The seller is paid before anyone checks that the delivery matches the certified root.**
   `Exchange.settle` places and processes the order through EscrowFinish
   (`market/exchange.py:479-480`). Only afterwards does `fitness` compare the rows with the
   certificate root (`market/exchange.py:505`). A "bait" seller who opened good sample rows but
   delivers others is paid in full; the trade is logged `settled_unfit` with a refund *claim*
   (Act 1: 2 such trades, paid 9124 and 10949 drops).
   *Test:* `test_seller_who_delivers_other_rows_than_committed_is_not_paid` (xfail).
   *Fix:* the gate holds the plaintext at `place_order`. Before `place_order` in `settle`, run
   `quality.delivery_matches(o["cert"], rows, salts)` and refuse on mismatch, so no escrow is
   created. Also derive `payload["rows"]` from `full_rows` at the buyer instead of trusting a
   second field (`exchange.py:467` and `:477` both come from `rows` today; nothing binds them).

3. **Vault path: the escrow condition is not bound to the sealed record.** `accept_sealed`
   (`vault/delivery.py:102-118`) and `place_order` (`engine.py:165-168`) take the page's
   `condition` as given. A page can seal with K2 and post the condition of K1. The reveal of K1
   satisfies the escrow and the seller is paid, but the institution cannot open what it holds. The
   same holds for a record whose ciphertext is not the prepared bundle: `bundle_hash` in the record
   is checked only as a claimed string.
   *Test:* `test_condition_for_another_key_is_refused_or_refunded` (xfail).
   *Fix (fits the design):* the engine cannot check this before payment without K. Put the full
   ciphertext hash (SHA-256 of the sealed record) and the full contract hash in the EscrowCreate
   memo; today the memo has only 16 hex characters of the plaintext bundle hash and of the contract
   (`engine.py:94-97`). Then the escrow (ciphertext hash), K (EscrowFinish) and the record are all
   public evidence. If K does not open the record, anyone can prove the seller's fault, and the
   payout schedule's holdback pays the refund automatically. For person-to-institution pushes, pay
   the hold-back part only after the institution's signed "opened, hash ok" receipt.

4. **The bundle-hash check at decrypt is an `assert`** (`engine.py:638`, `engine.py:645`).
   `python -O` removes it, and a mismatch raises a bare AssertionError that no caller turns into a
   refund claim.
   *Test:* `test_bundle_hash_check_survives_python_O` (xfail).
   *Fix:* `if ...: raise BundleMismatch(order_id)`, then record an exception row with the evidence
   from gap 3.

5. **K is in the database before it is published.** `_send` stores the signed finish blob, which
   contains the Fulfillment, before submit (`engine.py:439-441`). If the submit then fails or
   is withheld, the operator's database holds K. This is lower risk (the operator does not hold the
   locked bundle's outer key in the vault path), but it contradicts "the engine never holds K".
   *Fix:* store only the finish tx hash before submit, and keep the blob in the keyring holder
   until it is validated.
