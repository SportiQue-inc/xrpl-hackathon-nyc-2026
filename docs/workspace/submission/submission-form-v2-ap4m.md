# AgentRail: submission form v2 (AP4M-first), draft for daniel's review

> **HOLD: do not press final submit / confirm on the portal.** Only a new, explicit submit instruction from daniel lifts this. Draft only.

Written 2026-10-25 15:2x UTC. Story follows the pitch deck: bottleneck → agents → payment on AP4M → SportiQue → sensitive-data layer → impact. AP4M proof = PR #77 live run. v1 (`submission-form.md`) is kept for reference.

## Step 1

### Project Name
```
AgentRail
```

### Short Description (186/200)
```
Agents trade data for companies and people, and pay each other through Mastercard AP4M on XRPL EVM. The owner sets the terms, agents check every deal, and a capped channel pays per call.
```

### Description (4656/5000)
```
THE PROBLEM
Data between companies and institutions is traded more and more, but every deal stalls. Someone has to match the data to the need, check it is what was promised, get a person to approve its use, and settle the payment. Each step waits on a human. One research data agreement takes a median of 80 days, and most buyers pay first and find out later whether the data was any good.

OUR ANSWER: AGENTS THAT CHECK, AGREE AND PAY
In AgentRail every company has an agent. The buyer's agent posts a need, matches offers and checks a random sample against the seller's signed, pre-committed rows before it pays anything. The seller's agent applies the owner's rules: sell, ask the owner, or refuse. Then the agents pay each other.

PAYMENT: MASTERCARD AP4M ON XRPL EVM
Agents pay through AP4M. The buyer's treasury opens a funded channel with a hard spending cap. The agent signs an EIP-712 voucher for each paid call, the merchant redeems it on-chain, and RLUSD lands in the merchant's payout wallet. An agent can never spend past its channel cap, so a wrong or hijacked agent is limited by the ledger, not by our code.
We ran it live today on XRPL EVM Testnet: an agent bought 3 data exports at 0.05 RLUSD each, and a 4th at 0.50 RLUSD was refused because it was over the 0.10 cap. All 3 VoucherRedeemed receipts are verified on-chain, and the payout wallet went from 0 to 0.15 RLUSD. The receipts and an on-chain check are in our repo.
Both of our flows pay on this one channel: the agent-to-agent deals in our data vault marketplace, and the research contract payouts to participants. The marketplace then pays its leg on to each seller or participant.

OUR RULE: THE LLM PROPOSES, CODE VERIFIES, THE LEDGER ENFORCES
The LLM reads gaps, schemas and license text and proposes. Code recomputes every proposal and can only narrow it, tested against a hostile LLM. An agent cannot raise its own budget: the treasury is multi-signed, and the owner's mandate is checked before every payment.

WHO WE ARE, AND THE WALL WE HIT
We are SportiQue. We run both sides of health data: UniQdata, where people keep their own health records, and UniQLab, a workspace for researchers. In health the wall is far higher. Consent is needed item by item, people can't tell which studies fit them, so few take part, and genomes can't be taken back once they leak.

THE SAME RAIL, PLUS A SENSITIVE-DATA LAYER
We kept the exchange and added one policy layer that decides what an agent may do on its own.
- Sensitivity tiers T0-T3 across 46 data columns, each with required GA4GH DUO codes and retention rules.
- The person's agent finds studies that fit before any lab sees her. She reviews what goes where in plain words and signs once with a passkey.
- Within the scope she already approved, her agent handles routine contributions on her rules, so she shares more often and earns more research compensation without re-deciding each time. Anything outside that scope comes back to her.
- MRI, CT and genomic data always need her fresh approval, even for an A-grade lab. A C-grade lab's request is held.
- One relationship with a lab covers many sub-projects with no new contract, but only within the scope she approved.
- The lab's agent finds the data it needs and compares candidate data agent to agent, so labs pick better-fitting, provenance-checked data. A tampered week fails before payment.
- Release requires k=5 cohorts; per-study pseudonyms and date shifts reduce re-identification risk. They don't eliminate it.
- Withdrawal takes one tap: the data-use license (MPT) is clawed back on XRPL, undelivered rounds are refunded, and payments already made stay with her.

IMPACT
In our synthetic consent run of 50 people and 6 studies, owner approvals dropped from 11,600 per-item checks to 233 passkey signatures. In a simulated market of 50 synthetic accounts, agents closed 80 of 109 paid trades without an owner decision, and 6 mismatched deliveries were refused before payment.

EVIDENCE
Live on XRPL EVM Testnet: AP4M channel, vouchers, 3 VoucherRedeemed receipts and 1 refusal over cap. On XRPL Testnet, with core checks rerun through QuickNode: key-reveal Escrow (the payment publishes the key to the sealed data), MPT license and Clawback, Credentials with DepositPreauth, multi-signing, Batch.

LEGAL REQUIREMENTS REFLECTED IN THE DESIGN
Separate consents for sensitive data, third-party provision and cross-border transfer; scope checked by code every round; withdrawal never affects compensation; non-custodial. Not legal advice.

STATUS
All data is synthetic. Testnets only. Not a medical device.

The owner sets the terms. Agents do the deal. AP4M pays.
```

### Technical Description (947/1000)
```
Python engine (SQLite orders, outbox, idempotent payments) + FastAPI; Node AP4M agent in ap4m/.
- Payments: Mastercard AP4M on XRPL EVM Testnet (chain 1449000). Treasury opens a capped channel (requestChannel); agent signs EIP-712 vouchers per paid call; merchant calls redeemVoucher; RLUSD to payout wallet. Receipts checked against the VoucherRedeemed log (status, contract, topic, channel, amount) via GET /api/public/ap4m?verify=1.
- Policy: SensitivityPolicy (T0-T3, DUO, buyer grade A-D, owner baseline); scope checked before each payment, delivery and key release.
- Quality: Ed25519-signed column profile, Merkle root over salted rows, random sample opened before paying.
- XRPL Testnet: key-reveal Escrow (PREIMAGE-SHA-256(K); EscrowFinish publishes K), MPT license with Clawback, Credentials + DepositPreauth, multi-signed treasury, Batch; QuickNode RPC.
- k=5 cohorts; sealed P-256 push.
LLM proposes; code verifies and can only narrow.
```

## Step 2: Links

| Field | Value |
|---|---|
| Website | https://agentrail-try-production.up.railway.app/try (view-only; judges' hands-on code link: https://agentrail-try-production.up.railway.app/try?code=<JUDGE_ACCESS_CODE>) |
| Demo URL | https://youtu.be/QhrUsFrHmIk (v4; swap for the new English cut once it is posted) |
| Repository | https://github.com/SportiQue-inc/xrpl-hackathon-nyc-2026 |
| AP4M VoucherRedeemed 1 | https://explorer.testnet.xrplevm.org/tx/0x318db4c2ace3b95496017f46bdfea617b9e32a2d6ddd1f1ddde0e538b7b2c7a9 |
| AP4M VoucherRedeemed 2 | https://explorer.testnet.xrplevm.org/tx/0x4990ef4459b2fd171782b384950e8843cbf92f0a82c2612465a7df2457b52bb9 |
| AP4M VoucherRedeemed 3 | https://explorer.testnet.xrplevm.org/tx/0x7e27a882ad4eef6e2d1f28163bcde5f9d279f3a83ba15de7d19475ff08e8c1aa |
| AP4M payout wallet (0 → 0.15 RLUSD) | https://explorer.testnet.xrplevm.org/address/0x7BA281DF7cC4A40159Ca957A6a969b9495464160 |
| AP4M channel open (0.2 RLUSD cap) | https://explorer.testnet.xrplevm.org/tx/0xc2015774c462a4d4a88444b015547415eea96336df2208b01b0f68389d3a4d53 |
| AP4M settlement (3 claims) | https://explorer.testnet.xrplevm.org/tx/0xc675193632e48c3fe6ab48e5010b245300cd18f2a6d774c7a73c8c92762dba1e |
| AP4M public receipt, week 3 | https://hackathon.ap4m.build/public/evidence/claims/0xff6db0c50043c85b5cf92fc35480ba955bdf8040d289ad1f3b6d3956ce696201/0xf8bede66a69775ab6e1ac1c8fd6d23f3df099e3429c8b535970be03db5ff0994.json |
| AP4M public receipt, week 4 | https://hackathon.ap4m.build/public/evidence/claims/0x1afe5ad95de052daec971fcf38fdfcdae0d845d3e1c1f8e3648a3b10fdcea6c5/0x3157f326fcff4e6facc832cde6dc29e73f318e6b9990c55bb0398aa3d5d893a8.json |
| AP4M public receipt, week 5 | https://hackathon.ap4m.build/public/evidence/claims/0xe12109adbbe71fbdda33953b44becbf39e0ea323ed3b99e28a0f9ca82944d57c/0xc76be298c1d0eab9717de2b18f5519ceb9df3a09ab14e3a0435eeb8726ded590.json |
| XRPL key-reveal EscrowFinish | https://testnet.xrpl.org/transactions/6A96310816B9EC9F7B445C113FFBB719E794A588AC20BE06D71C086C435706C4 |
| Live vault | https://data-vault-market-production.up.railway.app |

If there is only one explorer slot, use VoucherRedeemed 1.

## Step 3/4: Track and prizes

- Prize: **Mastercard AP4M** (main).
- Track: Agentic Finance (the form needs one track; agents paying under a capped mandate fits it).
- Also tick QuickNode (core XRPL checks rerun through our endpoint). T54 x402: drop or keep as a minor tick; it is no longer in the story.

## Review notes (for daniel)

1. **Written as done (daniel, 15:17):** "Both of our flows pay on this one channel" (vault deals + research payouts). Before final submit, both must actually run on AP4M (vault build in progress). Add their VoucherRedeemed tx to Step 2 when they land.
2. **PR #77 is still open.** The receipts JSON and `/api/public/ap4m` are on its branch. Merge before submit so "in our repo" is true on main.
3. **Numbers:** 80/109 and 6 refused are from the rule-based run (seed 11); 11,600 → 233 is the synthetic consent run. The LLM run (120/85) is no longer cited.
4. **Wording:** within-approved-scope condition, MRI/CT/genomic fresh yes, "research compensation", "reduce re-identification risk", "legal requirements reflected in the design". None of the banned words.
5. Closing line changed to "…AP4M pays." to match the AP4M-first deck. The old line was "XRPL pays and hands over the key".
