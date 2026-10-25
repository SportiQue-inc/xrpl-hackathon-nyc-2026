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
| `check_x402_extra.py` | T54 `/supported` on both hosts, invoice binding `both` vs `invoice_id` (InvoiceID = sha256), two sequential payments, fake x402Secure refused |
| `check_x402.py` | one hospital export API fee paid through the T54 Testnet facilitator, replay/tamper refused |
| `check_amm.py` | payer sends XRP, participant receives a stablecoin via AMM (RLUSD pool if present, else synthetic tUSD) |

## Testnet results (run 2026-10-25)

| # | feature | status | success tx | failure tx (expected refusal) | time | conclusion |
|---|---|---|---|---|---|---|
| 1 | KYB credential + DepositPreauth | pass | [`92CB153F56…`](https://testnet.xrpl.org/transactions/92CB153F56235DB9508AE87E639FFA0B7FB8348B57B6A40E14963F29E31697C2) | [`ABBD54E9EF…`](https://testnet.xrpl.org/transactions/ABBD54E9EFCC707F9183A883219E7E909C73885CE204234A9871D6EE9222CEB6) tecNO_PERMISSION | 190.0s | Unverified orgs are refused on the ledger (tecNO_PERMISSION) for Payment and third-party EscrowFinish; verified orgs pass only when the tx carries CredentialIDs. |
| 2 | MPT data licence + Clawback | pass | [`26ED61533D…`](https://testnet.xrpl.org/transactions/26ED61533DD5FA3F8F29ACD00118BB19C2C813AC606EFB22D484533D24FF4673) | [`6BE571AF3D…`](https://testnet.xrpl.org/transactions/6BE571AF3D33F761410CCDE9AE93FD9FAE44BB01D242757EA96D2B57E2DCFDF1) tecNO_AUTH | 136.3s | Licence MPT works end to end: non-transferable (tecNO_AUTH on onward transfer) and revocable by Clawback; licence_held() flips to False. |
| 3 | Key-reveal conditional Escrow | pass | [`9C698CAD21…`](https://testnet.xrpl.org/transactions/9C698CAD2199A0B29826B5BE2F74FBD0E25CF5827380A822B47594CCA671794A) | [`498CBE2D38…`](https://testnet.xrpl.org/transactions/498CBE2D38C449EF26B560AA55E6CEC9E68261B33AAABA03F99327023C1125A6) tecCRYPTOCONDITION_ERROR | 106.4s | Key-reveal escrow behaves as designed: wrong key and early cancel are refused, the valid EscrowFinish puts K on the ledger, and after the deadline only EscrowCancel (refund) works. |
| 4 | Batch atomic multi-hospital purchase | pass | [`B9FCB1489C…`](https://testnet.xrpl.org/transactions/B9FCB1489CFBF798AE2ED2544ABBD0213FE9BB38B134007996D9BC2A485566DA) | [`43D938D243…`](https://testnet.xrpl.org/transactions/43D938D2434B802D713DEF18A03F5D85E72E00390217AE8F1554A81BD92D21ED) tesSUCCESS | 92.4s | Batch works on Testnet (all-or-nothing verified). Escrow bundle verified as the fallback. |
| 5 | x402 hospital export API fee (T54 facilitator) | pass | [`68EA814B23…`](https://testnet.xrpl.org/transactions/68EA814B23881270ECDA345AA9E847B139AE8A9EE1184D05E3DE9134FF764003) | — | 28.3s | x402 one-off API payment settles on Testnet through T54 and is confirmed on the ledger; see replay/tamper rows for how the facilitator refuses misuse. |
| 5b | x402 facilitator hosts, invoice binding, sequential payments | pass | [`92FF5C3B0C…`](https://testnet.xrpl.org/transactions/92FF5C3B0C7B2F19D235C200F26DC3FDCC8ABAFEF06E2F1AEA3F0E4FF4A18ACA) | — | 58.5s | See rows: facilitator hosts, both invoice bindings, two sequential payments. |
| 6 | AMM stablecoin payout (RLUSD / synthetic tUSD) | pass | [`500498211E…`](https://testnet.xrpl.org/transactions/500498211E45B8A41CDF825AF76BE25450B29294112A9CB227CE40FA49B5955D) | [`A989BE91C4…`](https://testnet.xrpl.org/transactions/A989BE91C48170ADB5CB619007EA707E7E2338E7D2A1EA45157608EC282990AA) tecPATH_DRY | 68.8s | RLUSD via the Testnet XRP/RLUSD AMM works. Synthetic stablecoin via our own AMM works: payer sends XRP, participant receives USD. |

Batch failure row: the outer Batch tx is accepted (tesSUCCESS) but no inner payment applied; hospital A received 0 drops. Per-step tables, amendments and accounts: [RESULTS.md](RESULTS.md).

Other findings: `BatchV1_1` + `fixBatchV1_2` are enabled (original `Batch` is not); T54 testnet host lists `xrpl:1`+`exact`, `xrpl-x402.t54.ai/supported` returns 404; invoice bindings `both` and `invoice_id` both settle; two sequential x402 payments both settle; T54 requires `extra.sourceTag` (now sent by `x402_rail.py`, override `X402_SOURCE_TAG`); x402 replay returns the same tx hash with no second debit; a fake x402Secure extension is refused (`verifiable_intent_requirement_token_missing`). RLUSD: the Testnet XRP/RLUSD AMM delivered 1 RLUSD to a participant paid in XRP.

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
