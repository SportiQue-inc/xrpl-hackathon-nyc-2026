# Existing UniQdata account: approved file → Testnet payment → original withdrawal

This resident operator path uses the main UniQdata file-contribution flow and the
person's existing passkey. Core owns the exact consent, selected files, archived
UV evidence and withdrawal. It exports only the reviewed, pseudonymized package.
The engine retains the original consent reference and checks Core again before
delivery and key publication. It never calls the sandbox roster, local passkey
registration, generic personal-data query, or consent-approval API.

Core must include `research_file_testnet_service`, `research_file_testnet_ledger`,
`scripts.agentrail_file_bridge` and `scripts.prepare_agentrail_file_offer` before
this path can run. The engine change alone does not deploy or enable that boundary.

## Resident setup

Run the engine operator on the **same resident host** as the authorized Core.
Use a private local process pipe, such as `docker exec -i`. Never copy an exported
package into SSH/SSM command logs, public telemetry or a different country.
Only the final metadata/receipt JSON is suitable for an evidence log.

Use a dedicated directory outside the source checkout, with mode 0700. It contains
the SQLite outbox and separate role key stores; do not delete or reset it to retry.
This is an isolated native-XRP Testnet case, independent of any RLUSD demo service.

```sh
SETTLE_ASSET=XRP python -m scripts.uniqdata_file_testnet prepare \
  --country KR --case-dir /private/operator/file-testnet-case
```

`prepare` creates separate Testnet payer, payee and treasury wallets using the
Testnet faucet, sets a two-key treasury signer list and emits a fixed 1 XRP quote.
The two treasury approvers are simulated devices using distinct private stores;
this does **not** prove two humans approved. These Testnet keys do not register or
replace a main UniQdata passkey, UMK or personal-wallet key.

## Main-app approval

1. Prepare a resident Core `FileContributionTerms` document with the emitted quote
   under `testnet_settlement`, actual recipient, purpose, period, permitted MIME
   types and localized notices. Set real `compensation_minor` to 0. Display that
   the approved address receives test XRP, with no real monetary compensation.
2. Invoke Core `python -m scripts.prepare_agentrail_file_offer` with explicit
   `--country KR --lane prod --owner EXISTING_PERSON_UUID --title ... --lang ko
   --terms-file PRIVATE_TERMS_FILE`. The returned project is visible only to that
   account. This creates no enrollment or consent.
3. The person opens that offer in the main app, selects the actual permissible
   file, reviews the exact purpose/recipient/period/Testnet payout terms and signs
   with their existing passkey. No synthetic account or software assertion counts.
4. Use the existing resident `scripts.research_file_delivery stage` and `review`
   workflow for the resulting submission. A human must actually review the
   pseudonymized copy/checklist. Do not manufacture a reviewer or auto-check it.
   The file bridge refuses absent review, changed bytes, or revoked authority.

Save a mode 0600 JSON argv file for the existing approved submission. This is
trusted operator configuration, never a browser-provided command:

```json
["docker", "exec", "-i", "CORE_CONTAINER", "python", "-m",
 "scripts.agentrail_file_bridge", "--country", "KR", "--lane", "prod",
 "--owner", "EXISTING_PERSON_UUID", "--submission", "APPROVED_SUBMISSION_UUID",
 "--private-pipe"]
```

## Delivery, payment and withdrawal

```sh
SETTLE_ASSET=XRP python -m scripts.uniqdata_file_testnet settle \
  --country KR --case-dir /private/operator/file-testnet-case \
  --core-command /private/operator/core-command.json
```

The exact case can fund a 1 XRP spending mandate once. Its signed mandate names
only this participant and purpose. The engine seals the reviewed package, issues
an MPT licence, creates the escrow, acknowledges encrypted delivery, rechecks Core
and publishes the decryption key through EscrowFinish. Core independently reads
both validated transactions from the fixed public Testnet and matches their
escrow, amount, addresses, commitments, fulfillment and payee balance delta.
The recipient opener verifies the approved package hash without printing bytes.

The Core readback puts this evidence under `testnet_settlement`, never a real
`payout_receipt` or `paid=true`. An existing main-app outcome card displays the
Testnet result when no prior study outcome exists; an existing outcome is preserved.
Source tests are not proof that the currently deployed app displayed the card.

The person then withdraws the **same original consent** in the main app. Run:

```sh
SETTLE_ASSET=XRP python -m scripts.uniqdata_file_testnet withdraw \
  --country KR --case-dir /private/operator/file-testnet-case \
  --core-command /private/operator/core-command.json
```

This restores the same saved order after a restart, observes Core's revocation,
claws back its MPT licence and proves the next mediated read is refused. Already
earned payments remain. It cannot erase previously disclosed recipient copies;
Core's existing recipient follow-up and deletion evidence remain separate.

`status` reads Core state and receipts without opening the package or sending a
payment. Retrying a completed case reuses its original order/receipt. An ambiguous
treasury or licence submission stops for ledger reconciliation; never delete the
case directory or generate a new request merely to retry. An expired signed
mandate is not silently renewed.

Acceptance requires the same main account, existing physical passkey, exact
submission/consent, reviewed package hash, actual Testnet create/finish hashes and
balance delta, original Core withdrawal, validated clawback, and refused next
read. Mock tests, a runtime health response, or a historical transaction are not
substitutes for these observations.
