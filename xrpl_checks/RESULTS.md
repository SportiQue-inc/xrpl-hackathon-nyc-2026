# XRPL Testnet feature checks

Synthetic faucet accounts on XRPL Testnet only. Re-run: `python xrpl_checks/run_all.py`.

## Amendments on Testnet

| amendment | status |
|---|---|
| Credentials | enabled | feature rpc: enabled=True supported=True |
| DepositAuth | enabled | feature rpc: enabled=True supported=True |
| DepositPreauth | enabled | feature rpc: enabled=True supported=True |
| MPTokensV1 | enabled | feature rpc: enabled=True supported=True |
| Clawback | enabled | feature rpc: enabled=True supported=True |
| Escrow | not enabled | feature rpc: enabled=False supported=True |
| TokenEscrow | enabled | feature rpc: enabled=True supported=True |
| Batch | not enabled |
| BatchV1_1 | enabled | feature rpc: enabled=True supported=True |
| fixBatchV1_2 | enabled | feature rpc: enabled=True supported=True |
| fixBatchInnerSigs | not enabled |
| AMM | enabled | feature rpc: enabled=True supported=True |
| fixAMMv1_1 | enabled | feature rpc: enabled=True supported=True |
| fixAMMv1_2 | enabled | feature rpc: enabled=True supported=True |
| fixAMMv1_3 | enabled | feature rpc: enabled=True supported=True |
| AMMClawback | enabled | feature rpc: enabled=True supported=True |
| PermissionedDomains | enabled | feature rpc: enabled=True supported=True |
| DynamicMPT | not enabled | feature rpc: enabled=False supported=True |
| SingleAssetVault | not enabled | feature rpc: enabled=False supported=True |

`Escrow` reads "not enabled" because it is a retired amendment: its logic is always on and it is no longer listed in the Amendments object. Check 3 shows escrows work.

## Summary

| # | feature | status | success tx | failure tx (expected refusal) | time | conclusion |
|---|---|---|---|---|---|---|
| 1 | KYB credential + DepositPreauth | pass | [`92CB153F56…`](https://testnet.xrpl.org/transactions/92CB153F56235DB9508AE87E639FFA0B7FB8348B57B6A40E14963F29E31697C2) | [`ABBD54E9EF…`](https://testnet.xrpl.org/transactions/ABBD54E9EFCC707F9183A883219E7E909C73885CE204234A9871D6EE9222CEB6) tecNO_PERMISSION | 190.0s | Unverified orgs are refused on the ledger (tecNO_PERMISSION) for Payment and third-party EscrowFinish; verified orgs pass only when the tx carries CredentialIDs. |
| 2 | MPT data licence + Clawback | pass | [`26ED61533D…`](https://testnet.xrpl.org/transactions/26ED61533DD5FA3F8F29ACD00118BB19C2C813AC606EFB22D484533D24FF4673) | [`6BE571AF3D…`](https://testnet.xrpl.org/transactions/6BE571AF3D33F761410CCDE9AE93FD9FAE44BB01D242757EA96D2B57E2DCFDF1) tecNO_AUTH | 136.3s | Licence MPT works end to end: non-transferable (tecNO_AUTH on onward transfer) and revocable by Clawback; licence_held() flips to False. |
| 3 | Key-reveal conditional Escrow | pass | [`9C698CAD21…`](https://testnet.xrpl.org/transactions/9C698CAD2199A0B29826B5BE2F74FBD0E25CF5827380A822B47594CCA671794A) | [`498CBE2D38…`](https://testnet.xrpl.org/transactions/498CBE2D38C449EF26B560AA55E6CEC9E68261B33AAABA03F99327023C1125A6) tecCRYPTOCONDITION_ERROR | 106.4s | Key-reveal escrow behaves as designed: wrong key and early cancel are refused, the valid EscrowFinish puts K on the ledger, and after the deadline only EscrowCancel (refund) works. |
| 4 | Batch atomic multi-hospital purchase | pass | [`B9FCB1489C…`](https://testnet.xrpl.org/transactions/B9FCB1489CFBF798AE2ED2544ABBD0213FE9BB38B134007996D9BC2A485566DA) | [`43D938D243…`](https://testnet.xrpl.org/transactions/43D938D2434B802D713DEF18A03F5D85E72E00390217AE8F1554A81BD92D21ED) tesSUCCESS (outer Batch only; with ALLORNOTHING none of the inner payments applied) | 92.4s | Batch works on Testnet (all-or-nothing verified). Escrow bundle verified as the fallback. |
| 5 | x402 hospital export API fee (T54 facilitator) | pass | [`68EA814B23…`](https://testnet.xrpl.org/transactions/68EA814B23881270ECDA345AA9E847B139AE8A9EE1184D05E3DE9134FF764003) | — | 28.3s | x402 one-off API payment settles on Testnet through T54 and is confirmed on the ledger; see replay/tamper rows for how the facilitator refuses misuse. |
| 5b | x402 facilitator hosts, invoice binding, sequential payments | pass | [`92FF5C3B0C…`](https://testnet.xrpl.org/transactions/92FF5C3B0C7B2F19D235C200F26DC3FDCC8ABAFEF06E2F1AEA3F0E4FF4A18ACA) | — | 58.5s | See rows: facilitator hosts, both invoice bindings, two sequential payments. |
| 6 | AMM stablecoin payout (RLUSD / synthetic tUSD) | pass | [`500498211E…`](https://testnet.xrpl.org/transactions/500498211E45B8A41CDF825AF76BE25450B29294112A9CB227CE40FA49B5955D) | [`A989BE91C4…`](https://testnet.xrpl.org/transactions/A989BE91C48170ADB5CB619007EA707E7E2338E7D2A1EA45157608EC282990AA) tecPATH_DRY | 68.8s | RLUSD via the Testnet XRP/RLUSD AMM works. Synthetic stablecoin via our own AMM works: payer sends XRP, participant receives USD. |

## 1. KYB credential + DepositPreauth — pass

amendments: Credentials enabled, DepositAuth enabled, DepositPreauth enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| CredentialCreate (registry -> verified org) | tesSUCCESS | tesSUCCESS | ✅ | 28.8 | [`F61FDB9673…`](https://testnet.xrpl.org/transactions/F61FDB96736164B29E6D024631404247540B124813D1DA2F2C3CD5D44328CB71) |
| CredentialAccept (verified org) | tesSUCCESS | tesSUCCESS | ✅ | 28.8 | [`B69DCB6640…`](https://testnet.xrpl.org/transactions/B69DCB6640E15AD074DF2CC87983AA2F2891B241017CA6669F04FF855ECEEB75) |
| participant DepositAuth / DepositPreauth(AuthorizeCredentials) | tesSUCCESS | tesSUCCESS | ✅ | 29.9 | [`44C872C549…`](https://testnet.xrpl.org/transactions/44C872C549B48EE0BEF13A0B015EC55E6D94CEA348136A0DB99E673E0C890009) |
| participant DepositAuth / DepositPreauth(AuthorizeCredentials) | tesSUCCESS | tesSUCCESS | ✅ | 29.9 | [`07CD426FAF…`](https://testnet.xrpl.org/transactions/07CD426FAF9F3E7A3400C9DCF94FC208D3B391039E7701DBCE5F178E12C65D64) |
| Payment verified org -> participant (engine attaches CredentialIDs) | tesSUCCESS | tesSUCCESS | ✅ | 13.1 | [`92CB153F56…`](https://testnet.xrpl.org/transactions/92CB153F56235DB9508AE87E639FFA0B7FB8348B57B6A40E14963F29E31697C2) |
| Payment unverified org -> participant | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 12.9 | [`ABBD54E9EF…`](https://testnet.xrpl.org/transactions/ABBD54E9EFCC707F9183A883219E7E909C73885CE204234A9871D6EE9222CEB6) |
| Payment verified org WITHOUT CredentialIDs | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 11.5 | [`6697D09BD4…`](https://testnet.xrpl.org/transactions/6697D09BD41EEFBC9A1084FA67B1BC643CB498F85B2981EBF66E1259DA3523CD) |
| EscrowCreate unverified org -> participant | tesSUCCESS | tesSUCCESS | ✅ | 11.6 | [`5568A06E83…`](https://testnet.xrpl.org/transactions/5568A06E838BBFDE864BD0202AF7AFE256C3D8639E44B3FD139D022860EADB09) |
| EscrowFinish submitted by unverified org | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 13.3 | [`E2EF9E9D6E…`](https://testnet.xrpl.org/transactions/E2EF9E9D6EEF7B64E2824A1D984604A359230C5701BC117F48FBC84FF3093B03) |
| EscrowCreate verified org -> participant | tesSUCCESS | tesSUCCESS | ✅ | 11.6 | [`6DB0899211…`](https://testnet.xrpl.org/transactions/6DB0899211555FBBFA3A80E4DB16F5DF115B9F3DA4E762E1DB6F2291F6D4BD46) |
| EscrowFinish submitted by verified org with CredentialIDs | tesSUCCESS | tesSUCCESS | ✅ | 12.8 | [`DCDAEC2B4F…`](https://testnet.xrpl.org/transactions/DCDAEC2B4FF47237977A60ACC49B0AE0E85E23E40F07D07DB38D0F29CA6C725F) |

- VERIFIED_ORG credential ledger index (goes in CredentialIDs): 30E3B5CF7960DD4D8356F423A1673F1317D95F3E9A9EF9EC2BBCAD156C3B04E3
- If the participant (the escrow destination) submits EscrowFinish itself, DepositAuth does not apply. So on the escrow route the KYB gate is the participant agent checking has_credential() before it reveals the key; on the Payment/x402 route the ledger enforces it.

accounts: kyb_registry (credential issuer) `rNguCcHJefj3DXx8ZH8u6tAySNxUEjMJFa`, participant_agent (DepositAuth) `rhyAwXeUhW91Xzn4jo4Eeqx9jksYTrSsi8`, org_verified `rhQcGLD4NvUpkphNX2hjRNAArzBk4nbw95`, org_unverified `rnWSkAGvx6UDHQiE5prKZGLJamGMRgp47D`

## 2. MPT data licence + Clawback — pass

amendments: MPTokensV1 enabled, Clawback enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| MPTokenIssuanceCreate (max 1, RequireAuth|CanClawback) | tesSUCCESS | tesSUCCESS | ✅ | 48.9 | [`26ED61533D…`](https://testnet.xrpl.org/transactions/26ED61533DD5FA3F8F29ACD00118BB19C2C813AC606EFB22D484533D24FF4673) |
| MPTokenAuthorize (study opts in) | tesSUCCESS | tesSUCCESS | ✅ | 48.9 | [`AEB6B460D7…`](https://testnet.xrpl.org/transactions/AEB6B460D751B7321F53FE63514168E285841C079A2D314BA2D2A11445924C7D) |
| MPTokenAuthorize (issuer authorizes study) | tesSUCCESS | tesSUCCESS | ✅ | 48.9 | [`DE1344EB9F…`](https://testnet.xrpl.org/transactions/DE1344EB9F35214BB8237D6C208A3555A05CE0E88DCC8E339E02EED4D80FE2A8) |
| MPT Payment issuer -> study (licence granted) | tesSUCCESS | tesSUCCESS | ✅ | 48.9 | [`11742C9108…`](https://testnet.xrpl.org/transactions/11742C910834817A1560FE57601A6FD1A9CA8B519B85B67FA00D879D8D701378) |
| licence_held(study_A) after grant | True | True | ✅ | 0.0 | — |
| MPTokenAuthorize (study_B opts in, to rule out 'no holder object') | tesSUCCESS | tesSUCCESS | ✅ | 11.8 | [`0150C67714…`](https://testnet.xrpl.org/transactions/0150C6771497C581DA7E52D5AEF858CFDE4DB77016C614EBD732BD5171BD6657) |
| study_A -> study_B onward transfer | tecNO_AUTH | tecNO_AUTH | ✅ | 15.5 | [`6BE571AF3D…`](https://testnet.xrpl.org/transactions/6BE571AF3D33F761410CCDE9AE93FD9FAE44BB01D242757EA96D2B57E2DCFDF1) |
| Clawback issuer <- study_A (consent revoked) | tesSUCCESS | tesSUCCESS | ✅ | 10.4 | [`57E38EDDC4…`](https://testnet.xrpl.org/transactions/57E38EDDC483DB31B9D1F66BC7771C9CF6548F97F566FD834A5B7E693F818E8B) |
| licence_held(study_A) after clawback | False | False | ✅ | 0.0 | — |
| study_A tries to use/transfer after clawback | tecNO_AUTH | observe | ✅ | 11.8 | [`186CA5B8EB…`](https://testnet.xrpl.org/transactions/186CA5B8EB3476D474CC205D4CDCAA5DB3F1EA99A8DB5F9FF564DDE48C17C92B) |

- mpt_issuance_id = 014CAF91EF0EF374614632B5C6F7D2042514381999E8E865
- issuance on ledger: found=True MaximumAmount=1 CanTransfer=False RequireAuth=True CanClawback=True
- metadata on ledger: {"consent":"abababababababababababababababab","duo":["DUO:0000007","DUO:0000019"],"study":"study_A","t":"agentrail.licence/v1"}

accounts: participant_agent (MPT issuer) `r4opQCK1ymsmtB1xdVUYBmjn7scMEj5aar`, study_A (licence holder) `rsdgcxcK3bUWxkSUe1osVjkYcAG13HGuqd`, study_B (third party) `rs4zAcio6fByVmC6RLikmYaJAr6ACQezwv`

## 3. Key-reveal conditional Escrow — pass

amendments: Escrow not enabled, fix1571 enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| EscrowCreate (condition = sha256(K), CancelAfter +10 min) | tesSUCCESS | tesSUCCESS | ✅ | 9.6 | [`9C698CAD21…`](https://testnet.xrpl.org/transactions/9C698CAD2199A0B29826B5BE2F74FBD0E25CF5827380A822B47594CCA671794A) |
| EscrowFinish with a wrong key | tecCRYPTOCONDITION_ERROR | tecCRYPTOCONDITION_ERROR | ✅ | 10.1 | [`498CBE2D38…`](https://testnet.xrpl.org/transactions/498CBE2D38C449EF26B560AA55E6CEC9E68261B33AAABA03F99327023C1125A6) |
| EscrowCancel before the deadline | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 8.7 | [`393908CE4A…`](https://testnet.xrpl.org/transactions/393908CE4A7D114443A48DBF619B955BB95A4C38FDED89FCE24E995F5DE56E76) |
| EscrowFinish revealing K (payee paid) | tesSUCCESS | tesSUCCESS | ✅ | 8.4 | [`6BD3349621…`](https://testnet.xrpl.org/transactions/6BD3349621853722DA29E400AB42D4B8CCA0E6CBF2A318F8D1F24C761D759C67) |
| buyer reads K back from the validated EscrowFinish | True | True | ✅ | 0.0 | — |
| EscrowCreate (CancelAfter +20s) | tesSUCCESS | tesSUCCESS | ✅ | 11.0 | [`94CB46B573…`](https://testnet.xrpl.org/transactions/94CB46B5736C44C010D1872F48E86D01ED22D552A94B0D4EB3C3EABDE7280D09) |
| EscrowFinish after the deadline | tecNO_PERMISSION | tecNO_PERMISSION | ✅ | 8.4 | [`FC6318EA2D…`](https://testnet.xrpl.org/transactions/FC6318EA2DE60A4D3A3AC260CDF1D507A65B0ED8BC6F8421FBEED3321B58BD3C) |
| EscrowCancel after the deadline (refund) | tesSUCCESS | tesSUCCESS | ✅ | 8.4 | [`1AD9F9305E…`](https://testnet.xrpl.org/transactions/1AD9F9305EBC033BC5892586C605869A3500319BC8A976DE347DA5A403226B47) |

- payee balance +999625 drops (escrow 1000000, minus finish fee)
- buyer balance +999990 drops on cancel (escrow 1000000, minus fee)

accounts: buyer (study) `rsiEbA5qp75WMLgicWGiJFUqTh7GjtksMz`, payee (participant agent) `rhdCSsphpbJi42FxkFUzqt55TVUcwirA71`

## 4. Batch atomic multi-hospital purchase — pass

amendments: Batch not enabled, BatchV1_1 enabled, fixBatchV1_2 enabled, fixBatchInnerSigs not enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| Batch ALL_OR_NOTHING: 2 Payments buyer -> hospital A, B | tesSUCCESS | tesSUCCESS | ✅ | 18.7 | [`B9FCB1489C…`](https://testnet.xrpl.org/transactions/B9FCB1489CFBF798AE2ED2544ABBD0213FE9BB38B134007996D9BC2A485566DA) |
|   inner Payment #1 | tesSUCCESS | tesSUCCESS | ✅ | 19.9 | [`BB21262B0D…`](https://testnet.xrpl.org/transactions/BB21262B0D35334A34D61276383B31B07D66152DE931A2118DB625EACC661EB0) |
|   inner Payment #2 | tesSUCCESS | tesSUCCESS | ✅ | 21.2 | [`26281F9FA5…`](https://testnet.xrpl.org/transactions/26281F9FA5090C4AA43C1A13A4D12BE57A7C0D850524474039E5B311DAEC2EA4) |
| Batch ALL_OR_NOTHING where payment #2 must fail | tesSUCCESS | observe | ✅ | 16.7 | [`43D938D243…`](https://testnet.xrpl.org/transactions/43D938D2434B802D713DEF18A03F5D85E72E00390217AE8F1554A81BD92D21ED) |
| hospital A received nothing from the failed batch | 0 | 0 | ✅ | 0.0 | — |
| bundle EscrowCreate -> hospital A (same condition) | tesSUCCESS | tesSUCCESS | ✅ | 14.2 | [`747F192965…`](https://testnet.xrpl.org/transactions/747F192965CA4E95ABC7459D1F39E0A07F772DB1EFC7D17619E1114513AEE9D8) |
| bundle EscrowCreate -> hospital B (same condition) | tesSUCCESS | tesSUCCESS | ✅ | 11.5 | [`A97E62DDC3…`](https://testnet.xrpl.org/transactions/A97E62DDC3B1F872F8C84D9F63EBA9DC648F65709BBE4881AA515051CC1A2ABA) |
| bundle EscrowFinish hospital A with the same K | tesSUCCESS | tesSUCCESS | ✅ | 10.0 | [`F788F9BB3D…`](https://testnet.xrpl.org/transactions/F788F9BB3D70225E0E4E28BB80CEB23A4001CBFC6430305640CE582583222E5C) |
| bundle EscrowFinish hospital B with the same K | tesSUCCESS | tesSUCCESS | ✅ | 12.5 | [`823F9D0EAB…`](https://testnet.xrpl.org/transactions/823F9D0EAB3A13AEC3E898C4D8B1211B098D4BC99D7900921CB9FF1F8F839115) |

- Escrow bundle is atomic in the sense the demo needs: until K is revealed no hospital is paid, after the deadline every leg is refundable with EscrowCancel, and once K is public every leg can be finished by anyone. It is not single-ledger atomic like Batch.

**Alternative:** Escrow bundle: N EscrowCreate with the same condition; one key reveal finishes all

accounts: buyer (study) `r4tDdJmTxfxd5zoxofCdkTXMeka5J975W1`, hospital_A `rpHKR5kZVvxkbGkifMB6wxrMCzGQmPeNKX`, hospital_B `rD1tJ437vmf1w6geKCdxtMyF83TniBy4rU`

## 5. x402 hospital export API fee (T54 facilitator) — pass

amendments: n/a

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| x402 verify+settle via T54, confirmed on a validated ledger | tesSUCCESS | tesSUCCESS | ✅ | 14.2 | [`68EA814B23…`](https://testnet.xrpl.org/transactions/68EA814B23881270ECDA345AA9E847B139AE8A9EE1184D05E3DE9134FF764003) |
| hospital API received exactly the fee | 100000 | 100000 | ✅ | 0.0 | — |
| replay the same payment header | success=True reason=None tx=same | observe | ✅ | 2.1 | — |
| hospital API balance unchanged after the replay | 0 | 0 | ✅ | 0.0 | — |
| verify against a different price (tampered requirement) | is_valid=False reason=payment_requirements_mismatch | observe | ✅ | 0.8 | — |

- facilitator: https://xrpl-facilitator-testnet.t54.ai
- /supported: {'kinds': [FacilitatorKind(x402_version=2, scheme='exact', network='xrpl:1'), FacilitatorKind(x402_version=2, scheme='upto', network='xrpl:1'), FacilitatorKind(x402_version=2, scheme='batch-settlement', network='xrpl:1')], 'extensions': ['x402Secure'], 'signers': {'xrpl:*': []}}
- HTTP 402 body the gate returns: {'status': 402, 'x402Version': 2, 'accepts': [{'scheme': 'exact', 'network': 'xrpl:1', 'amount': '100000', 'asset': 'XRP', 'payTo': 'rUmP3J8AGvNQm5few7RiWMoTaLZyRD5ovf', 'maxTimeoutSeconds': 300, 'extra': {'invoiceId': 'export:hospital_A:study_A:cohort_v1|n:ea2bd921', 'sourceTag': 804681468}}]}

accounts: buyer agent `rwoXSYaf5jnsZyzjFVUYkW1NdNkzpiWFLt`, hospital export API (payTo) `rUmP3J8AGvNQm5few7RiWMoTaLZyRD5ovf`

## 5b. x402 facilitator hosts, invoice binding, sequential payments — pass

amendments: n/a

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| GET https://xrpl-facilitator-testnet.t54.ai/supported lists xrpl:1 + exact | True | True | ✅ | 0.8 | — |
| GET https://xrpl-x402.t54.ai/supported | error: facilitator_http_error:404 | observe | ✅ | 1.4 | — |
| [both] binding both: settle | tesSUCCESS | tesSUCCESS | ✅ | 10.5 | [`92FF5C3B0C…`](https://testnet.xrpl.org/transactions/92FF5C3B0C7B2F19D235C200F26DC3FDCC8ABAFEF06E2F1AEA3F0E4FF4A18ACA) |
| [invoice_id] binding invoice_id (spec): settle | tesSUCCESS | tesSUCCESS | ✅ | 6.9 | [`BB43552DB6…`](https://testnet.xrpl.org/transactions/BB43552DB66FB26715D67C024E0B7A43FA9F74AE13B9836346150D8CE21081B8) |
| [both] sequential #1: settle | tesSUCCESS | tesSUCCESS | ✅ | 8.1 | [`092F6BFAC9…`](https://testnet.xrpl.org/transactions/092F6BFAC912C11BCBD19C895910173CFBBFC41BC53DB2157416BF38E904CF90) |
| [both] sequential #2: settle | tesSUCCESS | tesSUCCESS | ✅ | 9.3 | [`F1243D8BFF…`](https://testnet.xrpl.org/transactions/F1243D8BFFBE94C6FD2BB872599E9D11C8F72FC13F43CEEE866354F274382280) |
| verify with a fake x402Secure extension (optional) | is_valid=False reason=verifiable_intent_requirement_token_missing | observe | ✅ | 0.9 | — |

accounts: buyer agent `rwoXSYaf5jnsZyzjFVUYkW1NdNkzpiWFLt`, hospital export API `rUmP3J8AGvNQm5few7RiWMoTaLZyRD5ovf`

## 6. AMM stablecoin payout (RLUSD / synthetic tUSD) — pass

amendments: AMM enabled, fixAMMv1_1 enabled, fixAMMv1_2 enabled

| step | result | expected | ok | s | tx |
|---|---|---|---|---|---|
| [RLUSD] participant TrustSet to the stablecoin | tesSUCCESS | tesSUCCESS | ✅ | 12.9 | [`B8061BD488…`](https://testnet.xrpl.org/transactions/B8061BD488EEAE837C28CE6A7FFF2965A06FAE86978145DB3112D4593EE68EB9) |
| [RLUSD] Payment XRP -> 1 stablecoin to participant via AMM | tesSUCCESS | tesSUCCESS | ✅ | 12.9 | [`500498211E…`](https://testnet.xrpl.org/transactions/500498211E45B8A41CDF825AF76BE25450B29294112A9CB227CE40FA49B5955D) |
| [tUSD] participant TrustSet to the stablecoin | tesSUCCESS | tesSUCCESS | ✅ | 11.9 | [`B18BCE301B…`](https://testnet.xrpl.org/transactions/B18BCE301B044140B863A70722781CA2951B78EEC2CF6123980BB1AB235AB696) |
| [tUSD] Payment XRP -> 5 stablecoin to participant via AMM | tesSUCCESS | tesSUCCESS | ✅ | 13.0 | [`25C3510780…`](https://testnet.xrpl.org/transactions/25C3510780C81A1F28F1890880B3F650D1E5D8FCC44BE50F6F9027C0670AE852) |
| [tUSD] same payment to a participant with no trust line | tecPATH_DRY | tecPATH_DRY | ✅ | 11.7 | [`A989BE91C4…`](https://testnet.xrpl.org/transactions/A989BE91C48170ADB5CB619007EA707E7E2338E7D2A1EA45157608EC282990AA) |

- XRP/RLUSD AMM on Testnet: account=rPn7kHwycXzS5XNj167CnKwC2t82yAAdNW amount=1454670904709 amount2={'currency': '524C555344000000000000000000000000000000', 'issuer': 'rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV', 'value': '119746.0161726213'} fee=501
- tUSD AMM: {'account': 'r3vv6QZb5sh3hebUgCoDWj7XiB3HuCJTnp', 'amount': '40100553', 'amount2': {'currency': 'USD', 'issuer': 'rawFRYQK6L2tXYVZCUFBPvDRtgPVpqXDPF', 'value': '1995'}, 'asset2_frozen': False, 'auction_slot': {'account': 'rLGjKkok1G45yhVCbWSpZMQUuzHyvczfYh', 'discounted_fee': 30, 'expiration': '2026-10-26T03:13:10+0000', 'price': {'currency': '03930D02208264E2E40EC1B0C09E4DB96EE197B1', 'issuer': 'r3vv6QZb5sh3hebUgCoDWj7XiB3HuCJTnp', 'value': '0'}, 'time_interval': 0}, 'lp_token': {'currency': '03930D02208264E2E40EC1B0C09E4DB96EE197B1', 'issuer': 'r3vv6QZb5sh3hebUgCoDWj7XiB3HuCJTnp', 'value': '282842.712474619'}, 'trading_fee': 300, 'vote_slots': [{'account': 'rLGjKkok1G45yhVCbWSpZMQUuzHyvczfYh', 'trading_fee': 300, 'vote_weight': 100000}]}
- Fallback that always works: pay XRP, or the participant's agent swaps XRP->stablecoin itself.

accounts: study payer (holds XRP only) `rEM1YZdVPwsgzSfVtEdoibsQpYVbxXfHFn`, participant `rJJJyB1pW4tMw6dcPWBpeX25Gmc6iZtSfa`, participant without trust line `rJPez2KQvJixVEpTUom6DUMsC5WmfJojq`, tUSD issuer (synthetic) `rawFRYQK6L2tXYVZCUFBPvDRtgPVpqXDPF`, liquidity provider `rLGjKkok1G45yhVCbWSpZMQUuzHyvczfYh`
