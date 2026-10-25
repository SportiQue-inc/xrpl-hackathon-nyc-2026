# xrpl_checks — XRPL Testnet feature checks

Minimal scripts that prove each XRPL feature the demo relies on, on **Testnet only**, with
synthetic faucet accounts. Results (public tx hashes, explorer links, timings) are written to
`results/*.json` and summarised in `RESULTS.md`.

```bash
pip install -r requirements.txt
python xrpl_checks/run_all.py              # everything (~5 min, mostly escrow deadlines)
python xrpl_checks/run_all.py kyb mpt      # a subset
```

Seeds go to `xrpl_checks/wallets.local.json` (git-ignored, 0600). Never commit it. The scripts
refuse to run unless the RPC server reports `network_id = 1` (Testnet).

| script | what it proves |
|---|---|
| `check_amendments.py` | which amendments are enabled on Testnet now |
| `check_kyb.py` | VERIFIED_ORG credential + DepositAuth/DepositPreauth: unverified org Payment → `tecNO_PERMISSION` |
| `check_mpt_licence.py` | MPT licence (max 1, RequireAuth + CanClawback, no CanTransfer): onward transfer `tecNO_AUTH`, Clawback on revoke |
| `check_escrow.py` | key-reveal escrow: wrong key / early cancel refused, finish reveals K, after deadline only cancel (refund) |
| `check_batch.py` | Batch all-or-nothing if enabled; escrow bundle (shared condition) as the fallback |
| `check_x402.py` | one hospital export API fee paid through the T54 Testnet facilitator, replay/tamper refused |
| `check_amm.py` | payer sends XRP, participant receives a stablecoin via AMM (RLUSD pool if present, else synthetic tUSD) |

## What changed in the engine (`agentrail/ledger/`)

- `XrplLedger.require_credential_deposits(account, issuer, cred_type)` — same name as the mock.
  Sets DepositAuth and `DepositPreauth{AuthorizeCredentials:[{Issuer, CredentialType}]}`. Idempotent.
- `XrplLedger.prepare_payment` now attaches `CredentialIDs` automatically when the destination has a
  credential DepositPreauth rule and the source holds a matching accepted credential
  (`credential_ids_for(source, destination)`). Without it the ledger refuses even a verified org.
- `prepare_escrow_finish(..., destination=None)`: pass the escrow destination to attach CredentialIDs
  when a third party finishes. **EscrowCreate is not gated by DepositAuth** (the field does not exist
  on EscrowCreate); EscrowFinish is gated unless the destination itself submits it. So on the escrow
  route the KYB gate is the participant agent checking `has_credential()` before revealing K. The mock
  currently refuses EscrowCreate with `tecNO_PERMISSION`; the real ledger does not.
- `transfer_licence` no longer raises on `tecNO_AUTH` (xrpl-py's `submit_and_wait` raises on any tec);
  it returns the code and keeps the failed hash in `self.last_tx_hash`.
- `xrpl_extras.submit_capture(client, tx, wallet)` — submit and wait without raising, keeps the hash of
  failed txs for evidence.
- x402: the T54 presigned payer builds its own Payment, so it cannot carry CredentialIDs. Do not point
  an x402 payment at a DepositAuth account.
