# QuickNode XRPL Testnet verification

The complete existing standalone `xrpl_checks` suite was rerun through a dedicated QuickNode XRP Testnet endpoint. All seven feature checks passed: 59 recorded steps and 48 transaction hashes, including expected ledger refusals. All people, data, accounts and payments in this run are synthetic or faucet-funded Testnet fixtures.

- Run: 2026-10-25 00:23:17 EDT to 00:40:00 EDT (2026-10-25T04:23:17.015840+00:00 to 2026-10-25T04:40:00.838938+00:00).
- QuickNode endpoint: `678992`, chain `xrp`, network `xrp-testnet`, active. `server_info` returned `network_id=1` before execution and the suite checks that network before using wallets.
- Configuration: the local `.env` contains `QUICKNODE_API_KEY` for management and `XRPL_RPC_URL` for ledger calls. The run explicitly exported the RPC setting before starting child Python processes. The API key and token-bearing RPC URL are excluded from this report.
- RPC URL SHA-256: `0e69ce9108d559f40b5fdb5ba91a5971e701f9be9c9d4b5f69996d72c7d319b6`.
- Source base: `126b0a3fb5e698274f2999658b2d775d809f9958`. The tested snapshot differs from that commit in `agentrail/ledger/xrpl_extras.py`. The report applies to the isolated snapshot, rather than a clean run of the commit alone. SHA-256 of the sorted source-hash manifest: `aa908215e8ef707079007323cb8339a040f8656dfb99c32f04eb33fd782f14c1`.
- Dashboard readback after the run: endpoint active, XRP Testnet, 558 method calls in the last 24 hours. The local screenshot and its SHA-256 are recorded in the run receipt.
- Four sampled transactions (successful and refused direct payments, escrow finish and escrow refund) were independently fetched again through QuickNode with `validated=true` and the expected result codes.
- Direct XRPL calls use QuickNode. The x402 facilitator is T54: it verifies and settles x402 payments, and the ledger adapter confirms their validated outcome through QuickNode. A transaction hash alone does not identify the RPC provider; the local run receipt binds the configured URL hash and source snapshot, and the QuickNode dashboard shows endpoint usage.

Local audit files are under `data/quicknode-verification-20261025T042316Z/`: `run_receipt.json` contains timestamps, source/result hashes and per-check status; `quicknode_tx_readback.json` contains the four independent readbacks; `run.log` contains the redacted output. The `data/` directory is git-ignored, and wallet seeds stay in the private local run directory.

## Reproduce

From the repository root, with dependencies installed and a configured `.env`:

```bash
set -a
source .env
set +a
.venv/bin/python xrpl_checks/run_all.py
```

The RPC setting is read from the process environment when the ledger module imports. Saving `.env` alone does not load it into `xrpl_checks/run_all.py`.

## Observed limits

- QuickNode rejects the administrative `feature` method with HTTP 400, code `-32604` (method not supported). The amendment baseline below was read from the validated Amendments ledger entry. The optional `feature` cross-check records `'result'` errors; this does not mean those amendments are disabled.
- The existing licence metadata emits an optional XLS-89d formatting warning. The transactions succeeded, but explorers/indexers may not discover that metadata as a standardized asset. No metadata code was changed in this configuration task.
- This is a standalone Testnet suite. The integrated health-study demo, production data, Mainnet and AWS AgentCore were not run in this verification.
- Another task advanced the working checkout while this suite ran. These results apply to the isolated source snapshot above; they do not certify the subsequently changed application code. The configuration and four independent transaction readbacks were verified separately.

## Partner requirement readback

The official [QuickNode prize](https://hackathons.xrpl-commons.org/hackathons/ai-fintech-xrp-ledger-hackathon-f78ed817?tab=prizes#quicknode), read on 2026-10-25, offers $3,000 for the best use of QuickNode and requires joining its track. RPC configuration and actual use are evidenced here; portal track selection and project submission were not changed by this task.

The official [AWS prize](https://hackathons.xrpl-commons.org/hackathons/ai-fintech-xrp-ledger-hackathon-f78ed817?tab=prizes#aws) lists $2,000 in Agentic Finance for the AgentCore + x402/RLUSD agentic payments stack. This repository has x402 code, synthetic connectors and SQLite storage, with no AgentCore integration found. Therefore, adding S3 or DynamoDB alone would not demonstrate the requested stack; AWS prize eligibility is not established by this run.

## Amendments on Testnet

| amendment | status |
|---|---|
| Credentials | enabled | feature rpc error: 'result' |
| DepositAuth | enabled | feature rpc error: 'result' |
| DepositPreauth | enabled | feature rpc error: 'result' |
| MPTokensV1 | enabled | feature rpc error: 'result' |
| Clawback | enabled | feature rpc error: 'result' |
| Escrow | not enabled | feature rpc error: 'result' |
| TokenEscrow | enabled | feature rpc error: 'result' |
| Batch | not enabled | feature rpc error: 'result' |
| BatchV1_1 | enabled | feature rpc error: 'result' |
| fixBatchV1_2 | enabled | feature rpc error: 'result' |
| fixBatchInnerSigs | not enabled | feature rpc error: 'result' |
| AMM | enabled | feature rpc error: 'result' |
| fixAMMv1_1 | enabled | feature rpc error: 'result' |
| fixAMMv1_2 | enabled | feature rpc error: 'result' |
| fixAMMv1_3 | enabled | feature rpc error: 'result' |
| AMMClawback | enabled | feature rpc error: 'result' |
| PermissionedDomains | enabled | feature rpc error: 'result' |
| DynamicMPT | not enabled | feature rpc error: 'result' |
| SingleAssetVault | not enabled | feature rpc error: 'result' |

`Escrow` reads "not enabled" because it is a retired amendment: its logic is always on and it is no longer listed in the Amendments object. Check 3 shows escrows work.

## Summary

| # | feature | status | success tx | failure tx (expected refusal) | time | conclusion |
|---|---|---|---|---|---|---|
| 1 | KYB credential + DepositPreauth | pass | [`5539F10629…`](https://testnet.xrpl.org/transactions/5539F10629980F1DFF44203AAF3B381D36925EA567D815413263F8EEDCEF7B2B) | [`FB9CCD2E60…`](https://testnet.xrpl.org/transactions/FB9CCD2E607A2B6C348BA4EB20764EA9AC31FEC36A1735B22A297B8765A51370) tecNO_PERMISSION | 206.7s | Unverified orgs are refused on the ledger (tecNO_PERMISSION) for Payment and third-party EscrowFinish; verified orgs pass only when the tx carries CredentialIDs. |
| 2 | MPT data licence + Clawback | pass | [`3E658ADBB3…`](https://testnet.xrpl.org/transactions/3E658ADBB300E75FA7634E0428EDDA18F9C6AF2B93AB6EA245218CBC37CD423E) | [`49D67DFFBA…`](https://testnet.xrpl.org/transactions/49D67DFFBA2054351486D650DB8C0393C2A252F72143D75E87A045C95476D093) tecNO_AUTH | 160.5s | Licence MPT works end to end: non-transferable (tecNO_AUTH on onward transfer) and revocable by Clawback; licence_held() flips to False. |
| 3 | Key-reveal conditional Escrow | pass | [`D103F16F04…`](https://testnet.xrpl.org/transactions/D103F16F04CB057AC535B8E247D78AACCC442CDBEDE56515F48B1902A4127984) | [`EB42B23246…`](https://testnet.xrpl.org/transactions/EB42B232463E64299C654E573ABFDE87CFD911FFBB72A60996BAB26B4FB66148) tecCRYPTOCONDITION_ERROR | 133.8s | Key-reveal escrow behaves as designed: wrong key and early cancel are refused, the valid EscrowFinish puts K on the ledger, and after the deadline only EscrowCancel (refund) works. |
| 4 | Batch atomic multi-hospital purchase | pass | [`4DD5DE9FC8…`](https://testnet.xrpl.org/transactions/4DD5DE9FC891BBB2AF50963B9FBB9518A7A6C3BDDE603A9021848971C0EC0979) | [`625B77F00C…`](https://testnet.xrpl.org/transactions/625B77F00C0E808D18510DC11C6A3791B5B01FEAEB00B63567A123662BD23762) tesSUCCESS | 139.1s | Batch works on Testnet (all-or-nothing verified). Escrow bundle verified as the fallback. |
| 5 | x402 hospital export API fee (T54 facilitator) | pass | [`9EF6E50FA1…`](https://testnet.xrpl.org/transactions/9EF6E50FA1969F62B1CEC528CAD4EF839626AED5ABAEF943D526FF534FAEF147) | — | 54.5s | x402 one-off API payment settles on Testnet through T54 and is confirmed on the ledger; see replay/tamper rows for how the facilitator refuses misuse. |
| 5b | x402 facilitator hosts, invoice binding, sequential payments | pass | [`67E890B4F1…`](https://testnet.xrpl.org/transactions/67E890B4F1991C825098301EE4263668A5273F65EEEB109A056AB4FE0EF8E69B) | — | 68.8s | See rows: facilitator hosts, both invoice bindings, two sequential payments. |
| 6 | AMM stablecoin payout (RLUSD / synthetic tUSD) | pass | [`D0AC61991B…`](https://testnet.xrpl.org/transactions/D0AC61991BE3286234CEF957688CE7ACB1EDEA87C8AF03D33476BA6FCD3692C6) | [`C0F61EDCEA…`](https://testnet.xrpl.org/transactions/C0F61EDCEA901E9F89711097BC8ABC85A70ADA8E25C9103A4E1FA257A7653B28) tecPATH_DRY | 201.2s | RLUSD via the Testnet XRP/RLUSD AMM works. Synthetic stablecoin via our own AMM works: payer sends XRP, participant receives USD. |

## 1. KYB credential + DepositPreauth — pass

amendments: Credentials enabled, DepositAuth enabled, DepositPreauth enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| CredentialCreate (registry -> verified org) | tesSUCCESS | tesSUCCESS | ✅ | 27.1 | [`92B6DDB9BC…`](https://testnet.xrpl.org/transactions/92B6DDB9BCB7BB210C18E2C5A704DFAA65A8CABEB483E54908D0B300D278ACE7) |
| CredentialAccept (verified org) | tesSUCCESS | tesSUCCESS | ✅ | 27.1 | [`C3F03BA7BC…`](https://testnet.xrpl.org/transactions/C3F03BA7BC119AC2757A6FC348D821E58724016D81C3AB0CEF3F112D889B42FE) |
| participant DepositAuth / DepositPreauth(AuthorizeCredentials) | tesSUCCESS | tesSUCCESS | ✅ | 29.8 | [`6B702BC5CE…`](https://testnet.xrpl.org/transactions/6B702BC5CE1ECAFB774D164D5EFB38E6DCC4683FD3A31B5ED16561023FE681D6) |
| participant DepositAuth / DepositPreauth(AuthorizeCredentials) | tesSUCCESS | tesSUCCESS | ✅ | 29.8 | [`FB96BE0B29…`](https://testnet.xrpl.org/transactions/FB96BE0B299115FE50D69834CBD3F3CFF121B069F2C2CB01C1289AE3D653C79C) |
| Payment verified org -> participant (engine attaches CredentialIDs) | tesSUCCESS | tesSUCCESS | ✅ | 14.6 | [`5539F10629…`](https://testnet.xrpl.org/transactions/5539F10629980F1DFF44203AAF3B381D36925EA567D815413263F8EEDCEF7B2B) |
| Payment unverified org -> participant | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 14.6 | [`FB9CCD2E60…`](https://testnet.xrpl.org/transactions/FB9CCD2E607A2B6C348BA4EB20764EA9AC31FEC36A1735B22A297B8765A51370) |
| Payment verified org WITHOUT CredentialIDs | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 13.1 | [`D0A43B31CC…`](https://testnet.xrpl.org/transactions/D0A43B31CCE53A595F755190C0D8D7843D60C9F3BCEB9FC419BF36E0572EB69B) |
| EscrowCreate unverified org -> participant | tesSUCCESS | tesSUCCESS | ✅ | 10.2 | [`B9D94CCF26…`](https://testnet.xrpl.org/transactions/B9D94CCF26C96AE099AADA8806B780A9A09209AA6E1DBCE5FD7EC64E40BB5BD9) |
| EscrowFinish submitted by unverified org | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 14.2 | [`8859594877…`](https://testnet.xrpl.org/transactions/885959487744406FF16734F4F3903513B05BB312A91DF41A79F210EBB8F03B31) |
| EscrowCreate verified org -> participant | tesSUCCESS | tesSUCCESS | ✅ | 13.1 | [`4928AE3BB7…`](https://testnet.xrpl.org/transactions/4928AE3BB7909F7488C56F6F1940ABA785420EB423B43462A875DDC2E27F9D14) |
| EscrowFinish submitted by verified org with CredentialIDs | tesSUCCESS | tesSUCCESS | ✅ | 14.2 | [`2E761A4B03…`](https://testnet.xrpl.org/transactions/2E761A4B03C97305661635FB8519DE8ADB610D6609C428D5D7AF2590B2CC0701) |

- VERIFIED_ORG credential ledger index (goes in CredentialIDs): 7137A883C8C632F3AC137E5644900069A38FEE4C8E53F36EE1AA9BAA2BAE56A2
- If the participant (the escrow destination) submits EscrowFinish itself, DepositAuth does not apply. So on the escrow route the KYB gate is the participant agent checking has_credential() before it reveals the key; on the Payment/x402 route the ledger enforces it.

accounts: kyb_registry (credential issuer) `rnv3fCNh5aR3zg7UPNNt2Wqx5UDstB4SEH`, participant_agent (DepositAuth) `rhR8Kdkpb4UQsCDKmEHyGaW6Lurn6r28qW`, org_verified `rLYB7T4jkDwEVPkahFQCVNAy8uoZbVsHvs`, org_unverified `rfRgQ7exVmEND7fheePZ5dwUZ6n9cpQeyx`

## 2. MPT data licence + Clawback — pass

amendments: MPTokensV1 enabled, Clawback enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| MPTokenIssuanceCreate (max 1, RequireAuth|CanClawback) | tesSUCCESS | tesSUCCESS | ✅ | 59.4 | [`3E658ADBB3…`](https://testnet.xrpl.org/transactions/3E658ADBB300E75FA7634E0428EDDA18F9C6AF2B93AB6EA245218CBC37CD423E) |
| MPTokenAuthorize (study opts in) | tesSUCCESS | tesSUCCESS | ✅ | 59.4 | [`0B8010594C…`](https://testnet.xrpl.org/transactions/0B8010594C3A5DF260B79121BCD4BD3C8AA3DD915FFD121E0CDCE222D959742B) |
| MPTokenAuthorize (issuer authorizes study) | tesSUCCESS | tesSUCCESS | ✅ | 59.4 | [`CD771625EE…`](https://testnet.xrpl.org/transactions/CD771625EE067DD321A516BC14686C14647087D4D6A24352EDBBC2E84FAC0DB2) |
| MPT Payment issuer -> study (licence granted) | tesSUCCESS | tesSUCCESS | ✅ | 59.4 | [`0F6FACE602…`](https://testnet.xrpl.org/transactions/0F6FACE602A4EA5373BFFB05B0194C44A7A5C171023AD9CC728C3778D3EC8C7D) |
| licence_held(study_A) after grant | True | True | ✅ | 0.0 | — |
| MPTokenAuthorize (study_B opts in, to rule out 'no holder object') | tesSUCCESS | tesSUCCESS | ✅ | 16.2 | [`CC6235062E…`](https://testnet.xrpl.org/transactions/CC6235062E3A671C773A5639803798E2A317429653109CA129A5F7AC72D80F60) |
| study_A -> study_B onward transfer | tecNO_AUTH | tecNO_AUTH | ✅ | 13.1 | [`49D67DFFBA…`](https://testnet.xrpl.org/transactions/49D67DFFBA2054351486D650DB8C0393C2A252F72143D75E87A045C95476D093) |
| Clawback issuer <- study_A (consent revoked) | tesSUCCESS | tesSUCCESS | ✅ | 14.7 | [`BB9E9814A1…`](https://testnet.xrpl.org/transactions/BB9E9814A13E6D0266C870E6197CAD36511BBBFE06332B6FF4F1B17B8376AF3F) |
| licence_held(study_A) after clawback | False | False | ✅ | 0.0 | — |
| study_A tries to use/transfer after clawback | tecNO_AUTH | observe | ✅ | 13.1 | [`EED37ADB34…`](https://testnet.xrpl.org/transactions/EED37ADB3423192E35E28878ACBAEE089D2733A995A307319E0B9DB121AE92DB) |

- mpt_issuance_id = 014CB57A24D143CC1197A02BFAD1B518869FC215DE9DB627
- issuance on ledger: found=True MaximumAmount=1 CanTransfer=False RequireAuth=True CanClawback=True
- metadata on ledger: {"consent":"abababababababababababababababab","duo":["DUO:0000007","DUO:0000019"],"study":"aae50e2724243756","t":"agentrail.licence/v1"}

accounts: participant_agent (MPT issuer) `rhMgrtfvBpYL53FfoEwaac2XTxoJNqFDMU`, study_A (licence holder) `rDUx6DBcqXG8CTJ3WRQ8wipH8hignn4VpY`, study_B (third party) `rPiRxaSpMavrEfVKbxVLVdEtrj3NFLZvq2`

## 3. Key-reveal conditional Escrow — pass

amendments: Escrow not enabled, fix1571 enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| EscrowCreate (condition = sha256(K), CancelAfter +10 min) | tesSUCCESS | tesSUCCESS | ✅ | 11.4 | [`D103F16F04…`](https://testnet.xrpl.org/transactions/D103F16F04CB057AC535B8E247D78AACCC442CDBEDE56515F48B1902A4127984) |
| EscrowFinish with a wrong key | tecCRYPTOCONDITION_ERROR | tecCRYPTOCONDITION_ERROR | ✅ | 15.7 | [`EB42B23246…`](https://testnet.xrpl.org/transactions/EB42B232463E64299C654E573ABFDE87CFD911FFBB72A60996BAB26B4FB66148) |
| EscrowCancel before the deadline | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 12.2 | [`B0C3C02282…`](https://testnet.xrpl.org/transactions/B0C3C0228255B366E9E06FEE2E4468CFDF6A3E574E20E9A9A00D5B32600DF237) |
| EscrowFinish revealing K (payee paid) | tesSUCCESS | tesSUCCESS | ✅ | 12.2 | [`02F294F005…`](https://testnet.xrpl.org/transactions/02F294F005188A0D96ACB9CA17F836C8AF544A884D4A9983C0328F2F31A27B6F) |
| buyer reads K back from the validated EscrowFinish | True | True | ✅ | 0.0 | — |
| EscrowCreate (CancelAfter +20s) | tesSUCCESS | tesSUCCESS | ✅ | 12.3 | [`7835AA29B4…`](https://testnet.xrpl.org/transactions/7835AA29B4F41BAC3E08C21284F9E326B4E442AB0EC58F0B7385E0CEA06D2390) |
| EscrowFinish after the deadline | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 10.1 | [`75F633D954…`](https://testnet.xrpl.org/transactions/75F633D95442C17CC03FBAB24985E3634CCDB263AFFA3AC8E427E7BA020C4693) |
| EscrowCancel after the deadline (refund) | tesSUCCESS | tesSUCCESS | ✅ | 12.4 | [`2F7FE2F00C…`](https://testnet.xrpl.org/transactions/2F7FE2F00C56042522F488ECC6994C487E3608293ADC66193C477A085BFE38E0) |

- payee balance +999625 drops (escrow 1000000, minus finish fee)
- buyer balance +999990 drops on cancel (escrow 1000000, minus fee)

accounts: buyer (study) `rEzcisRQchKinU49tD395dNyyNptKb6T6b`, payee (participant agent) `raN4m2inxJQQStsbHbnFp7TZFwsBYioejY`

## 4. Batch atomic multi-hospital purchase — pass

amendments: Batch not enabled, BatchV1_1 enabled, fixBatchV1_2 enabled, fixBatchInnerSigs not enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| Batch ALL_OR_NOTHING: 2 Payments buyer -> hospital A, B | tesSUCCESS | tesSUCCESS | ✅ | 20.0 | [`4DD5DE9FC8…`](https://testnet.xrpl.org/transactions/4DD5DE9FC891BBB2AF50963B9FBB9518A7A6C3BDDE603A9021848971C0EC0979) |
|   inner Payment #1 | tesSUCCESS | tesSUCCESS | ✅ | 21.3 | [`032A6DE503…`](https://testnet.xrpl.org/transactions/032A6DE503B393B441A145CAB1DBD0D6D9F303489D8D214A2D80904D5133A470) |
|   inner Payment #2 | tesSUCCESS | tesSUCCESS | ✅ | 22.8 | [`555A6BAEE5…`](https://testnet.xrpl.org/transactions/555A6BAEE5E899A42A2D15F213F227BB1A8E2F0F34B6FB6A5845166132356934) |
| Batch ALL_OR_NOTHING where payment #2 must fail | tesSUCCESS | observe | ✅ | 21.2 | [`625B77F00C…`](https://testnet.xrpl.org/transactions/625B77F00C0E808D18510DC11C6A3791B5B01FEAEB00B63567A123662BD23762) |
| hospital A received nothing from the failed batch | 0 | 0 | ✅ | 0.0 | — |
| bundle EscrowCreate -> hospital A (same condition) | tesSUCCESS | tesSUCCESS | ✅ | 11.1 | [`2B34D2016A…`](https://testnet.xrpl.org/transactions/2B34D2016A78E5B63769BEC4CE66802BA281BCCA1C233DDD610EFEDE1BF42431) |
| bundle EscrowCreate -> hospital B (same condition) | tesSUCCESS | tesSUCCESS | ✅ | 9.8 | [`EDE002ECBB…`](https://testnet.xrpl.org/transactions/EDE002ECBB7183C20A68BC48D50A38CC099E79DDF0F46A7269556740D0290DAE) |
| bundle EscrowFinish hospital A with the same K | tesSUCCESS | tesSUCCESS | ✅ | 14.0 | [`30282A939A…`](https://testnet.xrpl.org/transactions/30282A939A30B88A1534C225BFC1F653F775CF1EBEC624518C4AAA60B3965B91) |
| bundle EscrowFinish hospital B with the same K | tesSUCCESS | tesSUCCESS | ✅ | 17.3 | [`C46AB6C229…`](https://testnet.xrpl.org/transactions/C46AB6C2293BA7BD64A291637EDC3BA11EC904BB7B3E5C2E5C660C09DFEF3486) |

- Escrow bundle is atomic in the sense the demo needs: until K is revealed no hospital is paid, after the deadline every leg is refundable with EscrowCancel, and once K is public every leg can be finished by anyone. It is not single-ledger atomic like Batch.

**Alternative:** Escrow bundle: N EscrowCreate with the same condition; one key reveal finishes all

accounts: buyer (study) `rwn5q3Ynr43PESs1azFuNjtQ1CdwsCRKcd`, hospital_A `rJLrRbfvTbNieun5jVxzEK3ARRvBsJBqAt`, hospital_B `rsyriNRcaqnNtNTzm9hrrbZhD5JkW4ubWs`

## 5. x402 hospital export API fee (T54 facilitator) — pass

amendments: n/a

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| x402 verify+settle via T54, confirmed on a validated ledger | tesSUCCESS | tesSUCCESS | ✅ | 17.5 | [`9EF6E50FA1…`](https://testnet.xrpl.org/transactions/9EF6E50FA1969F62B1CEC528CAD4EF839626AED5ABAEF943D526FF534FAEF147) |
| hospital API received exactly the fee | 100000 | 100000 | ✅ | 0.0 | — |
| replay the same payment header | success=True reason=None tx=same | observe | ✅ | 2.1 | — |
| hospital API balance unchanged after the replay | 0 | 0 | ✅ | 0.0 | — |
| verify against a different price (tampered requirement) | is_valid=False reason=payment_requirements_mismatch | observe | ✅ | 0.9 | — |

- facilitator: https://xrpl-facilitator-testnet.t54.ai
- /supported: {'kinds': [FacilitatorKind(x402_version=2, scheme='exact', network='xrpl:1'), FacilitatorKind(x402_version=2, scheme='upto', network='xrpl:1'), FacilitatorKind(x402_version=2, scheme='batch-settlement', network='xrpl:1')], 'extensions': ['x402Secure'], 'signers': {'xrpl:*': []}}
- HTTP 402 body the gate returns: {'status': 402, 'x402Version': 2, 'accepts': [{'scheme': 'exact', 'network': 'xrpl:1', 'amount': '100000', 'asset': 'XRP', 'payTo': 'rnsJWLUudqb86oXpRC7JD7TGepv6BARZyP', 'maxTimeoutSeconds': 300, 'extra': {'invoiceId': 'export:hospital_A:study_A:cohort_v1|n:9c1003f6', 'sourceTag': 804681468}}]}

accounts: buyer agent `rPudVURw4yD13JqFWGjjVeweVnHiBq4N7k`, hospital export API (payTo) `rnsJWLUudqb86oXpRC7JD7TGepv6BARZyP`

## 5b. x402 facilitator hosts, invoice binding, sequential payments — pass

amendments: n/a

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| GET https://xrpl-facilitator-testnet.t54.ai/supported lists xrpl:1 + exact | True | True | ✅ | 0.8 | — |
| GET https://xrpl-x402.t54.ai/supported | error: facilitator_http_error:404 | observe | ✅ | 1.2 | — |
| [both] binding both: settle | tesSUCCESS | tesSUCCESS | ✅ | 9.2 | [`67E890B4F1…`](https://testnet.xrpl.org/transactions/67E890B4F1991C825098301EE4263668A5273F65EEEB109A056AB4FE0EF8E69B) |
| [invoice_id] binding invoice_id (spec): settle | tesSUCCESS | tesSUCCESS | ✅ | 8.2 | [`D21BA5E944…`](https://testnet.xrpl.org/transactions/D21BA5E944496F458C774ACB2845CE622AE113260A041B1676606CDF0D748CA9) |
| [both] sequential #1: settle | tesSUCCESS | tesSUCCESS | ✅ | 10.9 | [`3A78877DEB…`](https://testnet.xrpl.org/transactions/3A78877DEB4EDF56E6513040BA3927BCD4A0886173690706160127A557E18E67) |
| [both] sequential #2: settle | tesSUCCESS | tesSUCCESS | ✅ | 9.3 | [`38DB90BA0D…`](https://testnet.xrpl.org/transactions/38DB90BA0D1860AA311F6FEA5EEAD21A4C1FBAD4C78166AF808CC138E2C05E4C) |
| verify with a fake x402Secure extension (optional) | is_valid=False reason=verifiable_intent_requirement_token_missing | observe | ✅ | 0.8 | — |

accounts: buyer agent `rPudVURw4yD13JqFWGjjVeweVnHiBq4N7k`, hospital export API `rnsJWLUudqb86oXpRC7JD7TGepv6BARZyP`

## 6. AMM stablecoin payout (RLUSD / synthetic tUSD) — pass

amendments: AMM enabled, fixAMMv1_1 enabled, fixAMMv1_2 enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| [RLUSD] participant TrustSet to the stablecoin | tesSUCCESS | tesSUCCESS | ✅ | 13.1 | [`831D1B2046…`](https://testnet.xrpl.org/transactions/831D1B20469954B89EB4F79A0887C58984907307895A1EE4766F53726179A63B) |
| [RLUSD] Payment XRP -> 1 stablecoin to participant via AMM | tesSUCCESS | tesSUCCESS | ✅ | 14.4 | [`D0AC61991B…`](https://testnet.xrpl.org/transactions/D0AC61991BE3286234CEF957688CE7ACB1EDEA87C8AF03D33476BA6FCD3692C6) |
| [tUSD] issuer DefaultRipple | tesSUCCESS | tesSUCCESS | ✅ | 13.0 | [`D108C25489…`](https://testnet.xrpl.org/transactions/D108C25489AF287E1A3547503D22417065A7CB551BB99C063E09F66B8274DD26) |
| [tUSD] LP TrustSet | tesSUCCESS | tesSUCCESS | ✅ | 14.8 | [`6338392BCF…`](https://testnet.xrpl.org/transactions/6338392BCF0221F93B49A423723C7F9487DDB5D7966FA0528967DDF0F239C54B) |
| [tUSD] issue 10,000 tUSD to LP | tesSUCCESS | tesSUCCESS | ✅ | 15.1 | [`2CA10A4E86…`](https://testnet.xrpl.org/transactions/2CA10A4E86595652C154564DCCFB3CA93BFFECBD00DD3456784763B785E6F30A) |
| [tUSD] AMMCreate 40 XRP / 2,000 tUSD | tesSUCCESS | tesSUCCESS | ✅ | 16.6 | [`FD656C34C7…`](https://testnet.xrpl.org/transactions/FD656C34C72374E9F3F462957273FBB30389676BE1480C0FE08415859651A91D) |
| [tUSD] participant TrustSet to the stablecoin | tesSUCCESS | tesSUCCESS | ✅ | 13.8 | [`9564B0BFC0…`](https://testnet.xrpl.org/transactions/9564B0BFC088C951F432C53BE33D3396D8D2ADC4D0232DE08959D5E4649F0DC3) |
| [tUSD] Payment XRP -> 5 stablecoin to participant via AMM | tesSUCCESS | tesSUCCESS | ✅ | 17.2 | [`8CD7B43FCE…`](https://testnet.xrpl.org/transactions/8CD7B43FCE2DB0BB643FDBE1780B0B5656053055A529097C1E88272652CA60C5) |
| [tUSD] same payment to a participant with no trust line | tecPATH_DRY | tecPATH_DRY | ✅ | 16.3 | [`C0F61EDCEA…`](https://testnet.xrpl.org/transactions/C0F61EDCEA901E9F89711097BC8ABC85A70ADA8E25C9103A4E1FA257A7653B28) |

- XRP/RLUSD AMM on Testnet: account=rPn7kHwycXzS5XNj167CnKwC2t82yAAdNW amount=1454683113948 amount2={'currency': '524C555344000000000000000000000000000000', 'issuer': 'rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV', 'value': '119745.0161726213'} fee=501
- tUSD AMM: {'lp_token': {'currency': '03930D02208264E2E40EC1B0C09E4DB96EE197B1', 'issuer': 'rsqJmnqJzoJvf2ZnFBMZDwxnN8LcXFPuaa', 'value': '282842.712474619'}, 'amount': '40000000', 'amount2': {'currency': 'USD', 'issuer': 'rGJFeSJuFMKFvV1NMy15HwHjUqW933gbCE', 'value': '2000'}, 'account': 'rsqJmnqJzoJvf2ZnFBMZDwxnN8LcXFPuaa', 'trading_fee': 300, 'auction_slot': {'time_interval': 0, 'price': {'currency': '03930D02208264E2E40EC1B0C09E4DB96EE197B1', 'issuer': 'rsqJmnqJzoJvf2ZnFBMZDwxnN8LcXFPuaa', 'value': '0'}, 'discounted_fee': 30, 'account': 'rNt2SjqbmQkqL9L61VbSbdADcagdN15m51', 'expiration': '2026-10-26T04:39:02+0000'}, 'vote_slots': [{'account': 'rNt2SjqbmQkqL9L61VbSbdADcagdN15m51', 'trading_fee': 300, 'vote_weight': 100000}], 'asset2_frozen': False}
- Fallback that always works: pay XRP, or the participant's agent swaps XRP->stablecoin itself.

accounts: study payer (holds XRP only) `r3aYMcQ4FmL8sTj4mLeXoDVBeBjdxPk6xi`, participant `rUxvK7mmtNBBckYVhuckvGWVLnHSBmD4wz`, participant without trust line `rfqV5RJDnYL2H883FL6jPQcYLe3b5T7Lb5`, tUSD issuer (synthetic) `rGJFeSJuFMKFvV1NMy15HwHjUqW933gbCE`, liquidity provider `rNt2SjqbmQkqL9L61VbSbdADcagdN15m51`
