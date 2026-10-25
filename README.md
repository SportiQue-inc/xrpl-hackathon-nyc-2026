# AgentRail - research on one person's whole record, with consent, licence and reward bound on XRPL

XRPL AI & Fintech Hackathon NYC 2026 (Oct 24-25) - SportiQue team.
Track: **Agentic Finance**. Everything in this repository was built during the hackathon
(reused material is listed in [docs/REUSE_LOG.md](docs/REUSE_LOG.md)).

## 1. One line, and the problem

**Not big data, but one person's whole record.** A study's research agent asks people to take
part. Each person's own agent gathers their scattered records (wearable, clinic visits, surveys)
on one time axis and contributes only what they agreed to. **The LLM proposes, code verifies, the
ledger enforces**: consent, a per-study data licence and the reward are bound to every
contribution on XRPL.

Health research increasingly needs the same person followed over weeks, not a large
pooled table. Today a study that loses three weeks of fatigue surveys for half its cohort has no way to
fill those gaps: getting data takes a median of 80 days of agreements, a $20 weekly reward costs
$0.88 in card fees, and nobody can check what each person agreed to round by round. So the study
recruits more people instead, at $2,000+ each.

Person-level health records are the hardest case: consent, re-identification and withdrawal all
apply at once. **We solved that boundary first.** An engine that passes it handles organization
data, AI training and evaluation data or robot sensor data by making the consent layer lighter;
scene A (robot data between companies) runs on the same engine as the Testnet proof.

## 2. How we solved the hard boundaries

Each row: the problem, our answer, where code or the ledger enforces it, the moment in the demo,
and the evidence. `POST /api/run/boundaries` runs every check and returns the evidence with tx links
(`agentrail/boundaries.py`); the dashboard shows the same list.

| Issue | Problem | Our answer | Enforced by | Demo moment | Evidence |
|---|---|---|---|---|---|
| **Consent** | Use is allowed only for the purpose, period and recipient the person agreed to, checked every round | Per-study consent document with GA4GH DUO codes (HMB, NCU, IRB, NPOA), versioned and hashed. The person's agent answers every request: inside consent runs automatically, outside waits for the person, prohibited purposes are refused | Code: `PersonalConsentPolicy.evaluate` on order and again before the key is published. Ledger: consent hash in every escrow memo; ethics-review Credential read from the ledger before sensitive items | The same lab asks for a commercial product: DUO drops NCU, the request stops at "needs your approval", nothing sent, no escrow | `test_new_purpose_waits_for_the_person`, `test_prohibited_purpose_refused_even_with_consent`, `test_payment_memo_carries_consent_version_hash`; Credential tx below |
| **Re-identification** | The more of one life is joined, the easier it is to tell who it is | Only the protocol's items and weeks leave the device; per-study pseudonym (studies cannot link records); per-study date shift known only to the person's agent; bundle sealed to the study's key; two or more quasi-identifiers (birth date, postal code, rare diagnosis) never released together; the ledger sees hashes only | Code: `PersonalVaultConnector.extract`, `ComplianceRules.check`, SealedBox. Ledger: memo = order id, bundle hash, consent hash | Birth date + postal code + rare diagnosis refused; the operator fails to open a bundle with its own key; the same person has different IDs in two studies | `test_quasi_identifier_combination_is_never_released`, `test_pseudonym_differs_per_study`, `test_locked_bundle_cannot_be_opened_before_finish` |
| **Withdrawal** | People must be able to stop, and know what stops, what comes back and what cannot be recalled | Three kinds. **Decline this round**: nothing leaves, nothing on the ledger. **Pause**: no new rounds; rewards and licence stay. **Revoke**: the study's data licence (MPT) is clawed back, rounds not yet released are withheld and their escrow is refunded after the deadline, consent history kept. Delivered rounds cannot be recalled, and the person is told so | Ledger: `Clawback` of the per-(study, participant) MPT; `EscrowCancel` after `CancelAfter`. Code: key published only after re-checking consent and that the study still holds the licence | P-017 taps revoke: Clawback tx, held week-5 escrow withheld, EscrowCancel refund, P-017's row greys out on the researcher heatmap | `test_approve_contributes_and_issues_a_licence_then_revoke_claws_back_and_refunds`, `test_clawed_back_licence_alone_stops_the_key`, `test_three_withdrawals_on_one_study`; Escrow cancel tx below |
| **Fair pay and penalties** | Stopping must never cost anything, yet a study needs protection against fabricated data, and paid money cannot be pulled back from a wallet | Each round pays **80%** when the contribution is confirmed and holds **20%** in its own escrow for a short review (7 days, +14 if fraud is suspected). Default is to pay, also after withdrawal. Code flags fraud signals (impossible values, a series already contributed by someone else); a **named reviewer** decides only after the person was told why and could respond. Then the held part returns to the study, the person is excluded for a period, and a repayment claim is recorded off the ledger. Two missed accepted rounds only pause automatic requests. Completion bonus in a separate escrow, returned on withdrawal | Ledger: `EscrowCreate` with `FinishAfter` and a condition held by the review service; `EscrowFinish` pays, `EscrowCancel` returns. Code: `payout.decision_inputs` is the only input to pay and sanction decisions and has no decline, pause or withdrawal fields; confirmation refused without a reviewer id or before the response period ends; trust level never on the ledger | A synthetic participant's survey says 12 on a 0-10 scale: held part frozen, notice, reviewer confirms, EscrowCancel. P-017 withdrew, yet P-017's held part is paid (EscrowFinish); only the bonus returns | `tests/test_payout.py` (9 tests), incl. `test_withdrawal_history_is_never_an_input` |
| **Other domains are easier** | Does it carry over where data is not about a person? | Robot sensor data between companies: seller licence terms replace personal consent; schema matching, licence reading, budget, multi-signed top-up and settlement unchanged | Code: `SellerPolicy`. Ledger: multi-signed treasury, payment memo with terms hash | The robot company's agent closes its evaluation gaps from two sellers | Scene A payments below |

## 3. Architecture

```mermaid
flowchart LR
  subgraph Lab["Research institution"]
    R[Researcher] -->|goal, budget| RA[Research agent]
    RT[(Study treasury<br/>multi-signed)] -->|budget needs PI + compliance| RW[(Agent account)]
  end
  subgraph Person["Each participant (phone)"]
    P[Person] -->|consent, approve,<br/>decline / pause / revoke| PA[Personal agent]
    PA --- W[(Wearable)] & S[(Survey app)] & C[(Clinic export<br/>fee paid by the agent)]
  end
  subgraph Engine["Engine (deterministic code)"]
    POL[Consent + compliance gate]
    ORD[Orders, budget reservation]
    OB[Outbox: escrow -> sealed delivery -> key -> payment]
  end
  RA -->|participation request| PA
  PA -->|answer: auto / ask person / blocked| POL --> ORD --> OB
  OB -->|EscrowCreate with sha256 of key| XRPL[(XRPL)]
  PA -->|EscrowFinish publishes key = reward paid| XRPL
  RA -->|reads key from ledger, opens sealed bundle| XRPL
  PA -->|licence MPT, Clawback on revoke| XRPL
  ETH[Ethics board] -->|Credential| XRPL
  LLM[[LLM: GPT by default]] -.->|proposals only:<br/>gap reading, request summary,<br/>schema and licence reading| RA & PA
```

| Agent | Given by its owner | Does |
|---|---|---|
| Research agent (`study.py`, `cohort.py`) | goal, protocol, budget cap, allowed purposes | reads the coverage table and the analysis note, proposes which person-weeks are missing (code recomputes each one from the table), sends participation requests, escrows rewards, opens bundles with the key from the ledger, tracks study power |
| Personal agent (`PersonalAgent`, `PersonalVaultConnector`) | the person's consent per study, automation level, pause / revoke | joins the person's sources on a time axis, answers each request (auto / ask / block), previews exactly what would leave, seals and contributes, publishes the key to get the reward, issues and claws back the study's licence |
| Seller agents (scene A only) | catalog, fixed prices, licence text | fixed quotes, confirm the buyer's reading of the licence |

**LLM proposes, code verifies, ledger enforces.** The LLM reads the coverage table and analysis
note (which weeks and items are missing, and why), one person's 8-week record ("P-017: week 4
heart rate, weeks 3-5 fatigue"), seller schemas and licence text. Every proposal is stored with its
hash in `proposals` and checked by code: a gap the table does not show is removed, a purpose
outside the mandate is replaced, a budget above the cap is capped. The LLM can only narrow what
the code allows; money and permission are widened only by code and the ledger
(`test_hostile_llm_can_only_narrow`, `test_hostile_llm_cannot_widen_the_study`). Without a key the
agents fall back to rules, and recorded LLM answers are replayed when a live call fails.

## 4. XRPL implementation

| XRPL feature | Why | How | Code | Testnet evidence |
|---|---|---|---|---|
| **Escrow (key reveal)** | reward is paid only when the data can be opened, and refunded if the person withdraws | bundle encrypted with key K and sealed to the study; `EscrowCreate` with a PREIMAGE-SHA-256 condition on K and `CancelAfter`; the personal agent publishes K in `EscrowFinish` to get paid; the study reads K from the ledger; withheld key -> `EscrowCancel` refund | `engine._escrow_*`, `ledger/conditions.py` | [EscrowCreate](https://testnet.xrpl.org/transactions/04C820C4EC1CC1A586F26CEE455BBD1CEAF8DE72C6D0CB308574F6FF4A068AAC), [EscrowFinish with key](https://testnet.xrpl.org/transactions/6A96310816B9EC9F7B445C113FFBB719E794A588AC20BE06D71C086C435706C4), [EscrowCreate 15 s](https://testnet.xrpl.org/transactions/E8ED3C1F14BD44C9F895E88B862041E1BBA2E568254FC658DE8156352795D7FB), [EscrowCancel refund](https://testnet.xrpl.org/transactions/6BD9AF3ACF2EADEEF650BC06E2358894AFC6ED0F8606C953ADDB641A10C76587) |
| **MPT data licence** | the study holds a licence per (study, participant) that cannot be passed on and is taken back on revoke | issuer = participant's agent; `MPTokenIssuanceCreate` (supply 1, RequireAuth, CanClawback, no CanTransfer, metadata = study hash, DUO codes, consent hash); holder and issuer `MPTokenAuthorize`; MPT `Payment`; `Clawback` on revoke; the key is published only while the study holds it | `ledger/licence.py`, `study._after_contribution`, `study.participant_revoke` | health run: [MPTokenIssuanceCreate](https://testnet.xrpl.org/transactions/76C15EB2769A5F732BF0B33C0B419C54D580EAAA990CDC17F21F31D4EEB63BC9), [MPTokenAuthorize (study)](https://testnet.xrpl.org/transactions/AF466D9FB5A949D705484FF9FEF179F58E79D4CB5790FEC50BFD37D49ECF9F22), [MPTokenAuthorize (participant)](https://testnet.xrpl.org/transactions/2AB7D64D62E761247AA7118DC88B3127432D511CAD0036121A9D5DC9DD641C5B), [MPT Payment](https://testnet.xrpl.org/transactions/AF090722504F115A807D99FE788E4E9A5809F062007CD559B47884FCDD7EA483), [Clawback on revoke](https://testnet.xrpl.org/transactions/9E180A4E6F31A4E76CB3281D478ABA98AE79C4EFA56A73601C335AA6040079AF); onward transfer refused: [tecNO_AUTH](https://testnet.xrpl.org/transactions/6BE571AF3D33F761410CCDE9AE93FD9FAE44BB01D242757EA96D2B57E2DCFDF1) |
| **Credentials** | sensitive items only for an ethics-approved study; verified organization badge | ethics board issues `ETHICS_REVIEW` (an attestation by the issuer; the ethics board, not the ledger, decides approval); the consent gate reads the accepted credential from the ledger | `ledger/xrpl_extras.py`, `ComplianceRules` | [CredentialCreate](https://testnet.xrpl.org/transactions/58656AB4E6ABEC47BAA92F90C3F304B8959D1FDAE03AE6ED193FA2D98CBD1A37), [CredentialAccept](https://testnet.xrpl.org/transactions/FC7710C97C3783157778952291A28B2322E2FD65DBBDB5B52F4662DF9D514218) |
| **Multi-signing** | an agent cannot raise its own budget | study and buyer treasuries have a SignerList (owner + compliance, quorum 2), master key disabled; agent-only top-up refused by the ledger | `ledger/xrpl_extras.py`, `scenario.top_up`, `study.approve` | [SignerListSet](https://testnet.xrpl.org/transactions/6812EB098980EFEA7478517484AFDD082BD119CF32E9128D630B6D7AECFA029A), [master key off](https://testnet.xrpl.org/transactions/5FAAF7FE40D30E9558B120E27A49BAA55443F53BBF400C7596437864D620C8F8), [co-signed top-up](https://testnet.xrpl.org/transactions/E6F9FD3BB14245F7ED3ADF79FAA185C83155C1D40F70241FACDDA7178AB16D1C); agent alone: `tefBAD_SIGNATURE` |
| `Payment` + `InvoiceID` + memo | one payment per order, tied to order, bundle and terms; clinic export fee paid by the person's agent | signed blob and hash stored before submit; lost response -> look up by hash, resubmit the same blob | `engine._pay`, `study._export_fee` | scene A: [B1 20 XRP](https://testnet.xrpl.org/transactions/FD14E5D69E6F244D5ECF6AFE8B8EBF038D6E75BD5C03D16A4F32DDB76B362B03), [C1 15 XRP](https://testnet.xrpl.org/transactions/AD54A5E8064C13DA41E6D24D97A95E5E77B6A7BFB6386758C771C8D81036C98A); 50 people paid in parallel in 58.7 s |
| **DepositAuth + DepositPreauth by credential (KYB)** | only verified organizations reach participants | a registry issues `VERIFIED_ORG`; the participant's account sets DepositAuth and DepositPreauth by that credential, and verified payers attach `CredentialIDs`; an unverified lab's direct payment fails with `tecNO_PERMISSION`. Escrows are not gated by DepositAuth on XRPL, so on the escrow route the personal agent checks the credential before it answers or publishes a key | `XrplExtrasMixin.require_credential_deposits`, `credential_ids_for`, `study._kyb`, `ComplianceRules.verified_check` | health run: [CredentialCreate VERIFIED_ORG](https://testnet.xrpl.org/transactions/B1136D3751EC5CA442BE8F6589B6B69F18ED1C5F792CFC1459966ADCD3F515AE), [CredentialAccept](https://testnet.xrpl.org/transactions/1719662B76AFAA263870F966525CED89D2BDDC3822F0C12029AB3E4A9D103FAA), [DepositAuth](https://testnet.xrpl.org/transactions/7FC34103156D4D143C8E2FD8EECAB8147171CD125EC348684A3E63E41D921BA7), [DepositPreauth](https://testnet.xrpl.org/transactions/DB8615A294585F2BA87F794BB2F45949780A76632B8628286652BD28016C532B), [unverified lab pays directly: tecNO_PERMISSION](https://testnet.xrpl.org/transactions/C4BDB237A1973CC7C1CBD62BA31C0C17E148F9D720FFBCFF06EA861AD9CD7491) |
| x402 (T54 facilitator) | HTTP pay-per-request for agents | 402 PaymentRequirements, presigned payment, facilitator settles; the engine still checks the validated ledger | `ledger/x402_rail.py` (`PAYMENT_RAIL=x402`) | [export fee settled through T54](https://testnet.xrpl.org/transactions/68EA814B23881270ECDA345AA9E847B139AE8A9EE1184D05E3DE9134FF764003) (standalone check) |
| QuickNode RPC | production endpoint | any rippled JSON-RPC via `XRPL_RPC_URL` | `ledger/xrpl_ledger.py` | config |

Amendments checked on Testnet with the `feature` RPC: MPTokensV1, Credentials, DepositAuth,
DepositPreauth, TokenEscrow, BatchV1_1, PermissionedDomains, AMM, PriceOracle enabled.
Only hashes go on-chain: no health values, names or consent text.

**One integrated Testnet run** (`LEDGER=testnet python scripts/run_health_demo.py`, 50 synthetic
participants, about 13 minutes): power 0.65 -> 0.75; 36 people paid 19.4 XRP by key-reveal escrow;
one signer refused (`tefBAD_QUORUM`), then a
[co-signed 40 XRP budget](https://testnet.xrpl.org/transactions/6EADCC86EFDD078E45EFE4FB88DCD18A2AFDD085CDD2B8357D1FF46B27FCF1A2); [escrow with the consent hash in its memo](https://testnet.xrpl.org/transactions/3BD87B70CBC94F786C8B464B3F011299C82D759D817AE315AF581FAEED6FCEBC); on revoke the licence [clawback](https://testnet.xrpl.org/transactions/9E180A4E6F31A4E76CB3281D478ABA98AE79C4EFA56A73601C335AA6040079AF), the held week's key never published and its [EscrowCancel refund](https://testnet.xrpl.org/transactions/D2575FD948326043D2642CB6C470387FD911939DEC3F3E03FC26EA6C02EF51E6). Each XRPL feature was
also checked on its own, with the expected refusals: [xrpl_checks/RESULTS.md](xrpl_checks/RESULTS.md).

## 5. Two app surfaces on one engine

| Surface | For | Flow | API |
|---|---|---|---|
| Participant app: research participation request | one participant on their phone | request with verified-institution badges from the ledger, LLM summary of why, DUO codes -> each item marked auto / needs you / blocked -> preview of exactly what leaves (pseudonym, shifted dates, requested items only) -> approve -> sealed contribution, reward by escrow -> licence -> decline / pause / revoke with the ledger result | `GET /api/p/{pid}`, `/preview`, `POST .../approve`, `/decline`, `/pause`, `/revoke` |
| Researcher console | the study team | goal and protocol -> 50 x 8 coverage heatmap and LLM gap reading next to the code verdict -> co-signed budget approval (one signer refused) -> participation requests -> responses (auto / approval / blocked) -> sealed bundles opened with the key from the ledger -> power before and after -> settlement record | `GET /api/study`, `POST /api/study/goal`, `/approve`, `/send`, `/close-round`, `/sweep`, `GET /api/study/bundle/{id}` |

Both pages poll `GET /api/events` and share the same engine and ledger: a tap on the phone shows
on the console at the next poll. Contract: [docs/API.md](docs/API.md).

## 6. Standards we align with

| Standard | Where in AgentRail | Status |
|---|---|---|
| AP2 (Agent Payments Protocol) intent / cart / payment mandates | owner's mandate (L2) and one signed order (L3) per payment, verified before money moves (`agentrail/mandate.py`, `Engine._mandate_check`) | implemented (signed with Verifiable Intent; AP2 has no amount cap field, so the cap follows ACP `allowance.max_amount`) |
| Verifiable Intent L1 -> L2 -> L3 (ES256 SD-JWT) | issuer credential -> owner delegation -> agent's final action; hash of L3 in each payment memo | implemented with `x402_xrpl.vi`; verification is ours |
| [ACP delegate payment](https://raw.githubusercontent.com/agentic-commerce-protocol/agentic-commerce-protocol/main/rfcs/rfc.delegate_payment.md) `allowance.max_amount` | `per_transaction_max`, `total_max` in the owner's L2 | implemented |
| [x402 v2](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md), [XRPL exact scheme](https://github.com/x402-foundation/x402/blob/main/specs/schemes/exact/scheme_exact_xrpl.md) | `ledger/x402_rail.py` through the [T54 facilitator](https://docs.t54.ai/docs/xrpl/x402-facilitator); clinic export fee paid this way | implemented; [Testnet settlement](https://testnet.xrpl.org/transactions/68EA814B23881270ECDA345AA9E847B139AE8A9EE1184D05E3DE9134FF764003) |
| [A2A v1.0](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md) Agent Card, task states | `/.well-known/agent-card.json`, `/agents/{id}/.well-known/agent-card.json`; each dialogue line carries `SendMessage` and `TASK_STATE_INPUT_REQUIRED` / `REJECTED` / `WORKING` | message shape only; no A2A server |
| GA4GH Data Use Ontology (DUO) | consent documents, request cards, licence MPT metadata | implemented |
| ISO/IEC TS 27560 consent record | `consent_document` (versioned, hashed, history kept) | aligned in structure, not certified |
| Web Bot Auth (RFC 9421 signatures), Skyfire KYA | agent identity at the HTTP layer | future |

## 7. Track and judging fit

| Criterion | How | Evidence |
|---|---|---|
| Agentic Finance: escrow, multi-signing, on-chain credentials | all three are in the main flow, not side demos | section 4 tx links |
| Idea | research on one person's whole record, contributed by that person's agent; the counterpart is a person, not a dataset | sections 1-2 |
| Implementation | key-reveal escrow, MPT licence with clawback, Credentials and DepositPreauth, multi-signed treasury, owner-signed delegation checked before every payment, 80% now and 20% held for review, idempotent payments and recovery, 80 tests | `tests/`, sections 4 and 6 |
| Demo | phone request -> contribution -> researcher heatmap fills -> revoke -> clawback and refund, all with explorer links | section 9 |
| Potential | small, frequent contributions that cards and 80-day agreements cannot carry | section 8 |
| Bonus: QuickNode, x402 | `XRPL_RPC_URL`; `PAYMENT_RAIL=x402` | section 4 |

## 8. Potential and market

**Data is licensed for a lot, but rarely.** The AI training dataset market grows from $3.2B (2025) to
$16.3B (2033, 22.6% CAGR, as reported) ([Grand View Research](https://www.giikorea.co.kr/report/grvi2018158-ai-training-dataset-market-size-share-trends.html)),
and real-world evidence solutions are a $2-2.6B market ([IMARC](https://www.imarcgroup.com/real-world-evidence-solutions-market)).
Yet supply moves through a few large contracts: Reddit -> Google (~$60M/yr), News Corp -> OpenAI
($250M+ over 5 years), Tempus -> AstraZeneca ($200M over 3 years). Only 28 AI content-licensing
deals were publicly reported in 2024 ([Media and the Machine](https://mediaandthemachine.substack.com/p/ai-content-licensing-deals-june-2026)).
Getting research data takes a median of 80 days, 35 of them to sign the data use agreement
([Yale YODA](https://yoda.yale.edu/wp-content/uploads/2026/07/YODA-Project-Dashboard-Metrics-July-2026.pdf)).

**Research needs small gaps filled.** Recruiting one trial participant costs $2,273-6,533, and
15-40% drop out. In remote wearable studies, median retention is 5.5 days
([Pratap et al. 2020](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7026051/)). Filling a few missing
weeks is too small for an 80-day agreement, and paying for it by card costs more than the reward
($0.30 fixed fee, [Stripe](https://stripe.com/nl/help/pricing)). So that contribution does not
happen today, and studies over-recruit instead.

**We drive the transaction cost toward zero.** The study's agent infers what is missing, each
participant's agent consents per round, and XRPL settles with Escrow, MPT licences and Credentials
in 3-5 seconds for under $0.0001. A $20 weekly contribution costs $0.88 to settle by card and about
$0.00002 on XRPL (estimate at XRP $2). Agentic payments on XRPL already passed 13.5M transactions
across 168 x402 merchants (as reported).

**Revenue (estimate):** $20 per participant-week, 10% take rate, $12k per study per year.
Year 3: 300 studies x 500 participants x 26 weeks = 3.9M settlements a year, $78M contributed value,
$11.4M revenue, under 1% of the ~35k clinical trials started each year.

| Layer | Size | Source |
|---|---|---|
| TAM: AI training data + RWE + data marketplaces (2025) | ~$7B | Grand View, IMARC, GMI (sum, overlapping; estimate) |
| SAM: institutions using person-level longitudinal health data | ~$2.5B | RWE market (estimate) |
| SOM: year 3, bottom-up | $11.4M revenue / $78M contributed | our model (estimate) |

Sources and the full model: [docs/MARKET.md](docs/MARKET.md).

## 9. Demo and how to run

1. **Researcher console**: the sleep study is stalled at power 0.65. The LLM reads the coverage
   table and note; code keeps fatigue weeks 3-5 and heart rate weeks 4-5 and shows why. One
   signer cannot release the budget (`tefBAD_QUORUM` / `tefBAD_SIGNATURE`); PI + compliance can.
   Requests go out; auto contributions fill the heatmap; power rises.
2. **P-017's phone**: a request from a lab with an ethics-review badge read from the ledger, a
   two-sentence reason, DUO chips, fatigue weeks 3-5 "needs you", heart rate week 4 "auto". Preview
   shows what leaves. Approve: three escrows, keys published, rewards paid, licence issued.
3. **Boundaries**: new purpose stops for approval; quasi-identifier combination refused; operator
   cannot open a bundle; decline / pause / revoke with Clawback and EscrowCancel links.
4. **Other domains**: robot company's agent buys two datasets on Testnet with a multi-signed top-up.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                     # optional: OPENAI_API_KEY=... (never committed)
python -m pytest -q                      # 111 tests on the mock ledger (25 attack tests)
python scripts/run_health_demo.py        # whole health study, mock ledger, JSON summary
LEDGER=testnet python scripts/run_health_demo.py   # same on XRPL Testnet (faucet wallets)
LEDGER=testnet python -m agentrail.scenario        # robot scene A, cohort round, failure scene
uvicorn agentrail.web:app --reload       # API + dashboard at http://127.0.0.1:8000
```

The dashboard signs in with the demo login (`POST /api/dev/login/{sub}`, localhost and dev mode
only). Production settings: [docs/SECURITY.md](docs/SECURITY.md#7-production-mode).

`.env`: `LLM_PROVIDER` (`openai` | `anthropic` | `replay` | `none`), `OPENAI_API_KEY`,
`OPENAI_MODEL`, `XRPL_RPC_URL`, `PAYMENT_RAIL`, `LLM_SAY`. Testnet wallets come from the faucet
and are kept only in `wallets.local.json` (git-ignored).

## 10. Security design and limits

Full design, production settings and the attack table: [docs/SECURITY.md](docs/SECURITY.md).

- **Sign-in and access**: every API call needs a 15-minute token from a device-signed login
  (Ed25519 challenge, no passwords). Roles: participant, researcher, approver, reviewer, operator.
  One policy table decides every route; a route without a rule is denied. A participant reaches
  only their own record, and no other role can act for them.
- **Keys stay with their owners**: each round's escrow key and the pseudonym / date-shift secret
  sit in the participant's keyring; the study's decryption key sits with the institution; the
  service relays sealed bundles and cannot open them. Treasury keys sit on each approver's device.
- **Co-sign**: the server prepares the exact XRPL transaction with a nonce and expiry; each approver
  signs it on their own device; the server checks every signature and the signer list, then
  submits. One person cannot release a budget, a signature cannot be reused, and one approval per
  study plan stops repeated top-ups.
- **State changes**: a withdrawn participant comes back only with a new consent signed on their
  device; reviewers decide only under their own name; withdrawal deletes the sealed copies and
  unreleased keys.
- **Audit**: hash-chained event log with every state-changing call and its actor; chain check
  endpoint; chain head anchored on the ledger every 5 minutes.
- **HTTP**: strict request bodies, exact CORS origins, rate limits, security headers, secrets only
  from env or secret files, secrets masked in logs. `AGENTRAIL_ENV=prod` requires the token secret
  and turns the demo harness off.
- **Tested by attack**: 25 tests reproduce the attacks (reading health data without sign-in,
  one-person budget release, reactivating a withdrawn person, forged tokens, log tampering, ...).
  On the code before this layer 23 of them failed; now all pass.

Data and scope: all people, institutions, records and amounts are **synthetic**; XRPL Testnet
only. Raw records never go to an LLM or on-chain. Re-identification risk is reduced
(minimization, per-study HMAC pseudonyms and private date offsets, quasi-identifier rule), not
eliminated; delivered rounds cannot be recalled, and the person is told so before approving. An
unreadable consent store holds the round. Not a medical device; no diagnosis.

**Not done yet** (needed before real participants): keys in KMS / HSM (local key files today, the
interface is in place); an external penetration test; personal agents running on the person's
device (simulated in the service process today); enrolment from the identity provider; shared
rate-limit and token deny-list store for more than one instance; payout review keys moved to the
keystore; a live Testnet rerun of the co-sign path.

## 11. Legal basis (summary)

> Not legal advice. The demo uses synthetic data and XRPL Testnet only. A live service needs review by regulators and counsel.

- **Consent**: separate consent for health (sensitive) data, third-party provision and international transfer, scoped per round and purpose (Korea PIPA Arts. 15, 17, 22, 23, 28-8; Bioethics Act Art. 16; US 45 CFR 46.116). Each consent is hashed and tied to the participant's signature.
- **Scope check**: deterministic code, not the LLM, compares each request with the consented recipient, purpose, fields and period, and checks current consent on every access. Any change needs new consent.
- **Pseudonymization**: researchers receive only a participant number and the consented fields. The link between a person and their number is stored separately, where researchers cannot reach it. This is pseudonymized data, and the data agreement prohibits re-identification.
- **Three withdrawal options**: decline this round / stop future contributions / withdraw data-use consent (PIPA Art. 37). Withdrawal immediately blocks sessions and key release, and asks the institution to destroy individual-level data and confirm; the demo records the request and the confirmation as events. Aggregate statistics already produced remain.
- **International transfer**: access from abroad counts as transfer, so we disclose countries, recipients, purpose, fields and retention, and ask for separate consent. Each person's records stay in their own country.
- **IRB**: approval and exemption are decided by the IRB (Bioethics Act Art. 15; 45 CFR 46.112). An XRPL Credential only shows the issuer's attestation.
- **Participation compensation**: paid per round by the institution through Escrow and never taken back after withdrawal; Clawback applies only to the licence token. 20% of each round is held for a short review and paid by default; it is withheld only when a named reviewer confirms fraud after notice and a chance to respond. Declining or withdrawing never affects future requests, priority or compensation. The platform holds no keys or funds.
- **Records**: access logs are kept 2 years and permission-change logs 3 years; no personal data, study names or conditions go on the ledger.

## 12. Where this goes (production targets)

The two surfaces in this repository were built during the hackathon to show where the engine
plugs in. The team runs two existing products that are the intended production targets:
**UniQdata** (participant app: research participation requests) and **UniQLab** (researcher
workspace). No code from them is in this repository except what is listed in
[docs/REUSE_LOG.md](docs/REUSE_LOG.md).

`agentrail/uniqdata_port.py` (written here, contract-tested in `tests/test_uniqdata_port.py`)
turns engine results into the records those products already store, without calling them:

| Engine | UniQdata / UniQLab | Difference, handled explicitly |
|---|---|---|
| Separate consents: third-party provision, sensitive data | Consent lanes `research_participation`, `sensitive_health_collection` | International transfer has no UniQdata lane: a granted one blocks the hand-off |
| Revoke | New `privacy_epoch`; queued commands from older epochs superseded; withdrawal deletion audit | Pause holds new commands only; declining a round touches nothing |
| Rewards after revoke | Paid and pending research rewards are kept | Rounds not delivered at revoke are refunded to the study by the escrow, so they map to `not_earned`, never to kept pending rewards |
| EscrowFinish of a delivered round | One `payout_receipt` per payout intent | `receipt_ref_hash` = SHA-256 of the XRPL tx hash; amounts in drops (`amount_minor`, currency `XRP`) |

More: [docs/API.md](docs/API.md), [docs/PLAN.md](docs/PLAN.md), [docs/DESIGN.md](docs/DESIGN.md),
[docs/DEMO_SCOPE.md](docs/DEMO_SCOPE.md).
