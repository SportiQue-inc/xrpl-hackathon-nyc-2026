# AgentRail: XRPL Commons submission form (copy-paste text)

Prepared 2026-10-25. Source: branch `claude/project-thread-vfr62v` (README, docs/DESIGN.md, docs/legal/README.md, xrpl_checks/README.md). Character counts are measured on the text inside each code block. Plain text only, so it pastes cleanly whether or not the form renders Markdown.

## Step 1: Project details

Narrative: B2B agent data trading (Act 1) → SportiQue and the wall we hit in health → same rail plus a sensitive-data layer (Act 2) → impact → closing line. Synthetic numbers are marked as synthetic in the text.

### Project Name
```
AgentRail
```

### Short Description (190/200)
```
Agents trade data for companies and people. The owner sets the terms, agents check and agree each deal, and XRPL pays and hands over the key: the payment itself releases the key to the data.
```

### Description (4944/5000)
```
THE PROBLEM
To buy or sell data, companies match it against what they need, check it is what was promised, agree who may use it, and settle the payment. People do all four steps by hand. One research data agreement takes a median of 80 days, and most buyers pay first and find out later whether the data was any good. So small, frequent trades never happen.

ACT 1: AN AGENT NETWORK FOR B2B DATA
In AgentRail every company has an agent. The buyer's agent posts a need and matches offers. Before paying, it checks the seller's signed quality certificate and a random sample against a pre-committed Merkle root. It agrees fixed-price terms, then pays on XRPL. The data is sealed with a key K, and the escrow condition is SHA-256(K). The seller's agent gets paid only by publishing K in EscrowFinish, so the payment and the key that opens the data are one transaction. Data that doesn't match what was committed fails the check and is not paid. What an agent buys builds up in its own store and can be sold on; every company that joins adds buyers and sellers.
Prices are set by the market inside the owners' floors and budgets, and a buyer never pays twice for data it already holds. In our simulated market of 50 synthetic accounts, agents completed 109 paid trades in a rule-based run, 80 of them without an owner decision. 6 offers whose delivery did not match the certified rows were refused before payment, and 4 deliveries failed the buyer's check after opening and were recorded as refund claims. A separate LLM-driven run on UniQdata sandbox records produced 120 trades, 85 settled. Robot and battery fleet data trade on the same rail.

OUR RULE: THE LLM PROPOSES, CODE VERIFIES, THE LEDGER ENFORCES
The LLM reads gaps, schemas and license text and proposes. Code recomputes every proposal and can only narrow it, tested against a hostile LLM. An agent cannot raise its own budget: the treasury is multi-signed, and the owner's mandate is checked before every payment.

WHO WE ARE, AND THE WALL WE HIT
We are SportiQue. We run both sides of health data: UniQdata, where people keep their own health records, and UniQLab, a workspace for researchers. In health the headache is far bigger. Consent is needed for every item, people can't tell which studies fit them, and genomes can't be taken back once they leak.

ACT 2: THE SAME RAIL, PLUS A SENSITIVE-DATA LAYER
We kept the exchange and added one policy layer.
- Sensitivity tiers T0-T3 across 46 data columns, each with required GA4GH DUO codes and retention rules.
- The person's agent reads open study postings on the device and shows only the ones that fit. Until she says yes, no lab knows she exists.
- She reviews everything in plain words on one screen and signs once with a passkey. Genomes and imaging (T3) need her passkey every time and are never delegated.
- The agent shares on its own only with labs at or above her trust baseline. Imaging always needs her fresh approval: an A-grade lab's MRI request comes to her for approval, and a C-grade lab's is held.
- Provenance is stamped when data enters her record. A tampered week fails before payment and gets nothing. Genomic, CT and MRI datasets are offered only with a UniQdata intake record behind them.
- One relationship with a lab covers many sub-projects with no new contract, but only within the scope she already approved; anything new comes back to her.
- Release requires k=5: agents form cohorts so no single person is exposed. Per-study pseudonyms, date shifts and blocked quasi-identifier combinations reduce re-identification risk. They don't eliminate it.
- Data is pushed sealed to the lab; the platform holds no keys or funds.
- Withdrawal takes one tap. The study's MPT data-use license is clawed back on the ledger, undelivered rounds are refunded by EscrowCancel, and payments already made stay with her. Delivered data cannot be recalled, and she is told so before she agrees.

IMPACT
In our synthetic consent run of 50 people and 6 studies, owner approvals dropped from 11,600 per-item checks to 233 passkey signatures, and the median time from request to payment fell from 12 hours to under a minute. People decide once, within the scope they approved. Agents do the rest.

EVIDENCE
On XRPL Testnet, with expected refusals, and rerun through QuickNode: key-reveal Escrow in XRP and in a USD test token (TokenEscrow), MPT license and Clawback, Credentials with DepositPreauth, multi-signing, Batch, AMM to RLUSD, x402 through T54.

LEGAL REQUIREMENTS REFLECTED IN THE DESIGN
Separate consents for sensitive data, third-party provision and cross-border transfer; scope checked by code every round; withdrawal never affects compensation; the IRB decides approval; non-custodial. Not legal advice; a live service needs local legal review.

STATUS
All data and amounts are synthetic. XRPL Testnet only. Not a medical device.

The owner sets the terms. Agents do the deal. XRPL pays and hands over the key.
```

### Technical Description (963/1000)
```
Python engine (SQLite orders, outbox, idempotent payments) + FastAPI, xrpl-py on XRPL Testnet (QuickNode RPC).
- One exchange for both acts; Act 2 adds a SensitivityPolicy (T0-T3, DUO, buyer trust grade A-D, owner baseline).
- Pre-trade quality certificate: Ed25519-signed column profile, Merkle root over salted rows, random sample opened.
- Key-reveal Escrow: K = HKDF of a passkey PRF root; EscrowCreate with PREIMAGE-SHA-256(K) + CancelAfter; EscrowFinish publishes K and pays; EscrowCancel refunds.
- MPT data-use license per (study, participant): supply 1, RequireAuth, CanClawback, no CanTransfer.
- Credentials (ethics review, verified org) + DepositPreauth; multi-signed treasury; Verifiable Intent mandates checked before each payment.
- Provenance signed at intake; k=5 cohorts; sealed P-256 push.
- USD token settlement via TokenEscrow; x402 via T54; AP4M (XRPL EVM) agent in ap4m/.
LLM proposes; code verifies and can only narrow. Tx links in README.
```

## Step 2: Project links

| Field | Value |
|---|---|
| Repository | https://github.com/SportiQue-inc/xrpl-hackathon-nyc-2026 (main has the code) |
| Hands-on demo (judges) | https://agentrail-try-production.up.railway.app/try?code=<JUDGE_ACCESS_CODE> (mock ledger; Testnet proof is in the explorer links below) |
| Live vault | https://data-vault-market-production.up.railway.app |
| Demo video | (to add: link to the recorded video, script in docs/VIDEO_SCRIPT.md) |
| Live demo | (to add if hosted; otherwise leave empty, run steps are in README section 9) |
| Testnet explorer: key-reveal EscrowFinish | https://testnet.xrpl.org/transactions/6A96310816B9EC9F7B445C113FFBB719E794A588AC20BE06D71C086C435706C4 |
| Testnet explorer: EscrowCancel refund on revoke | https://testnet.xrpl.org/transactions/D2575FD948326043D2642CB6C470387FD911939DEC3F3E03FC26EA6C02EF51E6 |
| Testnet explorer: MPT license Clawback | https://testnet.xrpl.org/transactions/9E180A4E6F31A4E76CB3281D478ABA98AE79C4EFA56A73601C335AA6040079AF |
| Testnet explorer: unverified lab refused (tecNO_PERMISSION) | https://testnet.xrpl.org/transactions/C4BDB237A1973CC7C1CBD62BA31C0C17E148F9D720FFBCFF06EA861AD9CD7491 |
| Testnet explorer: co-signed budget (multisig) | https://testnet.xrpl.org/transactions/6EADCC86EFDD078E45EFE4FB88DCD18A2AFDD085CDD2B8357D1FF46B27FCF1A2 |
| Testnet explorer: x402 settlement via T54 | https://testnet.xrpl.org/transactions/68EA814B23881270ECDA345AA9E847B139AE8A9EE1184D05E3DE9134FF764003 |
| All tx with expected refusals | https://github.com/SportiQue-inc/xrpl-hackathon-nyc-2026/blob/claude/project-thread-vfr62v/xrpl_checks/README.md |

If the form has only one explorer slot, use the EscrowFinish link (it shows the key being published on the ledger).

## Step 3 and 4: Tracks and prizes (recommendation)

The official track and prize pages could not be opened from here, so this follows press coverage (four tracks: Protocol Innovation, Agentic Finance, Lending & Borrowing, "Why Not"; sponsors reported: Mastercard, Ripple, AWS, Ledger, QuickNode) and earlier team notes. Check the names against the form's list.

| Option | Recommend | Why |
|---|---|---|
| Track: Agentic Finance | Yes (main) | Track text asks for agents that pay and get paid on XRPL escrow, multi-signing and on-chain credentials. All three are in the main flow with Testnet tx |
| Track: Protocol Innovation / Lending & Borrowing / Why Not | No | No XLS-65/66 lending work; picking a second track dilutes the pitch slot |
| Bounty: x402 / T54 (if listed) | Yes | Real Testnet settlement through the T54 facilitator, plus invoice binding, sequential payments and replay checks (xrpl_checks row 5, 5b) |
| Bounty: RLUSD / stablecoin (if listed) | Optional | XRP->RLUSD payout through the Testnet AMM passed, but it is a standalone check, not in the main flow |
| Bounty: QuickNode | Yes | All 8 xrpl_checks rerun on 2026-10-25 through our QuickNode XRPL Testnet endpoint (endpoint 678992, network_id 1). Every expected success and refusal matched. See the QuickNode evidence section below |
| Bounty: Ledger | No | No Ledger device; multisig co-signing is done with software keys |
| Bounty: AWS | No | Nothing runs on AWS |
| Bounty: Mastercard AP4M | Yes (tick before the 9AM selection deadline) | Code and tests are in the repo (ap4m/, 11 tests, dry run: 3 calls paid within cap, 1 refused). Our fit: the participant's agent pays a clinic's export endpoint per call over HTTP 402 to unlock the record it contributes; no payment, no package. Live VoucherRedeemed tx and payout balance change still to be produced before the pitch (blocked on portal registration fix in the morning) |

### Two x402 paths, two bounties

| | T54 x402 (XRPL L1) | Mastercard AP4M |
|---|---|---|
| Ledger | XRPL Testnet (L1), native XRP Payment | XRPL EVM Testnet sidechain, chain 1449000 |
| How the agent pays | presigned XRPL Payment in the X-PAYMENT header; T54 verifies and submits | opens a funded channel (`requestChannel`), signs EIP-712 vouchers; merchant calls `redeemVoucher`; service settles |
| Asset | XRP (InvoiceID bound to the invoice) | RLUSD to the merchant payout address |
| Proof | tx on testnet.xrpl.org | VoucherRedeemed event on the EVM explorer + payout balance change |
| In AgentRail | `agentrail/ledger/x402_rail.py`, unchanged | separate `ap4m/` folder, does not touch the engine |

## QuickNode evidence (run 2026-10-25 04:23 UTC, Mac, folder data/quicknode-verification-20261025T042316Z)

Every transaction below was submitted and confirmed through the QuickNode endpoint. The endpoint URL holds a token, so only its SHA-256 is recorded (`run_receipt.json`).

| Check | Success tx | Expected refusal |
|---|---|---|
| KYB credential + DepositPreauth | [verified org pays](https://testnet.xrpl.org/transactions/5539F10629980F1DFF44203AAF3B381D36925EA567D815413263F8EEDCEF7B2B) | [unverified org: tecNO_PERMISSION](https://testnet.xrpl.org/transactions/FB9CCD2E607A2B6C348BA4EB20764EA9AC31FEC36A1735B22A297B8765A51370) |
| MPT license + Clawback | [MPTokenIssuanceCreate](https://testnet.xrpl.org/transactions/3E658ADBB300E75FA7634E0428EDDA18F9C6AF2B93AB6EA245218CBC37CD423E), [Clawback](https://testnet.xrpl.org/transactions/BB9E9814A13E6D0266C870E6197CAD36511BBBFE06332B6FF4F1B17B8376AF3F) | [onward transfer: tecNO_AUTH](https://testnet.xrpl.org/transactions/49D67DFFBA2054351486D650DB8C0393C2A252F72143D75E87A045C95476D093) |
| Key-reveal Escrow | [EscrowFinish reveals K](https://testnet.xrpl.org/transactions/02F294F005188A0D96ACB9CA17F836C8AF544A884D4A9983C0328F2F31A27B6F), [EscrowCancel refund](https://testnet.xrpl.org/transactions/2F7FE2F00C56042522F488ECC6994C487E3608293ADC66193C477A085BFE38E0) | [wrong key: tecCRYPTOCONDITION_ERROR](https://testnet.xrpl.org/transactions/EB42B232463E64299C654E573ABFDE87CFD911FFBB72A60996BAB26B4FB66148) |
| Batch all-or-nothing | [Batch](https://testnet.xrpl.org/transactions/4DD5DE9FC891BBB2AF50963B9FBB9518A7A6C3BDDE603A9021848971C0EC0979) | [failing batch, nothing applied](https://testnet.xrpl.org/transactions/625B77F00C0E808D18510DC11C6A3791B5B01FEAEB00B63567A123662BD23762) |
| x402 via T54 | [export fee settled](https://testnet.xrpl.org/transactions/9EF6E50FA1969F62B1CEC528CAD4EF839626AED5ABAEF943D526FF534FAEF147) | tampered price refused (payment_requirements_mismatch) |
| XRP -> RLUSD via AMM | [participant receives 1 RLUSD](https://testnet.xrpl.org/transactions/D0AC61991BE3286234CEF957688CE7ACB1EDEA87C8AF03D33476BA6FCD3692C6) | |

Two honest caveats for the pitch:
- QuickNode did not answer the `feature` RPC, so the amendment table in this run is not QuickNode evidence. Use the transactions above instead.
- x402 payments are submitted by the T54 facilitator. Our engine confirmed them on the validated ledger through QuickNode.

Line for Step 4 if the QuickNode prize asks for a description: "All XRPL Testnet transactions in our feature checks (Credentials, DepositPreauth, MPT license and Clawback, key-reveal Escrow, Batch, AMM) were submitted and confirmed through a QuickNode XRPL Testnet endpoint; tx links in the repo."

## Korean summary (한국어 요약)

- 서사는 최종 피치와 같아요: B2B 에이전트 데이터 거래(Act 1) → SportiQue와 헬스케어에서 만난 벽 → 같은 레일에 민감정보 층(Act 2) → 효과(승인 11,600 → 233, 합성 실행) → 마지막 문장 "The owner sets the terms. Agents do the deal. XRPL pays and hands over the key." (대본 v9)
- 한 줄 소개: 주인이 조건을 정하고, 에이전트가 거래를 확인·합의하고, XRPL이 지급하면서 키를 넘긴다.
- 사람 데이터 쪽(Act 2)은 "판매" 대신 "share/goes through"로 썼어요. B2B는 buy/sell을 그대로 썼어요. 금지 표현(reward, 재식별 불가, 진단, 준수 단정, only we)은 없어요. Act 1(유료 거래 109건, 그중 80건은 주인 결정 없이, 6건은 지급 전 거절, 4건은 환불 청구), Act 2(366건 중 239건 정산), 11,600→233은 모두 합성 실행이라고 본문에 적었어요.
- 테스트 개수는 README와 맞지 않을 수 있어서 본문에서 뺐어요. AP4M은 라이브 전이라 성과로 쓰지 않았어요(Technical에 코드 위치만).
- 숫자는 두 실행을 섞지 않아요. 규칙 기반 실행: 유료 109건 중 80건 주인 결정 없이(6건 지급 전 거절, 4건 환불 청구). LLM 실행(network-replay-uniqdata.html): 거래 120건, 정산 85건.
- 하위 프로젝트와 동의·계약 재사용은 본인이 이미 승인한 범위 안에서만 새 계약 없이 돌아가고, 범위를 벗어나면 다시 본인에게 묻는다고 적었어요.
- 8차 실행(11:05 UTC 예정)은 결과 대기, AP4M은 실제 redemption 전까지 미완료예요.
- 트랙은 Agentic Finance, 바운티는 T54 x402, QuickNode, Mastercard AP4M(9시 전 체크, 피치 전 라이브). Ledger와 AWS는 제외.
