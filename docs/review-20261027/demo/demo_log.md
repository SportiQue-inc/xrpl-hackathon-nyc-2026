# Research-contract lane: one synthetic goal end to end (2026-10-27)

Produced by `run_demo.py` on the mock ledger, LLM off, AP4M rail and UniQdata not connected. Raw responses: `demo_run.json`.

- 1. NEED. The researcher posts the terms over HTTP: ['sleep.daily', 'fatigue.survey'] weeks 1-3, 0.01 per item-week, budget 0.08 (per-order limit 0.02 = one member-week). The engine opens institution org_probe_sleep_lab_fa076b, sets its BuyerMandate from the terms, and issues the ethics credential on the (mock) ledger. Contract RC1-fa076b. The invite code is returned once and never listed.
- 2. CANDIDATE M1 (RC1-23255e29): joins with its own Ed25519 key, auto_all, items ['sleep.daily', 'fatigue.survey']; signs consent c69c10a2f7ba…; stores generated test readings for weeks 1-3 (labelled generated_test).
- 2. CANDIDATE M2 (RC1-fa778914): joins with its own Ed25519 key, auto_all, items ['sleep.daily']; signs consent 5d37a5a52081…; stores generated test readings for weeks 1-3 (labelled generated_test).
- 2. CANDIDATE M3 (RC1-209928c4): joins with its own Ed25519 key, confirm_each, items ['sleep.daily', 'fatigue.survey']; signs consent 31394cd3a76c…; stores generated test readings for weeks 1-3 (labelled generated_test).
- 3. AUTHORITY, both sides, in the same call. Institution side: engine.place_order checks the BuyerMandate (purpose in mandate, price <= per-order limit, budget left) and the ethics credential on the ledger. Person side: PersonalConsentPolicy.evaluate checks consent status, period, purpose, minimum price, consented items and the member's automation choice.
- 4. ROUND 1 (week 1): M1 -> delivered ['fatigue.survey', 'sleep.daily'] 20000; M2 -> delivered granted ['sleep.daily'] for 10000 (fatigue.survey was asked and offered, not consented: not sent, a scope question is opened for M2 instead); M3 -> needs_approval (confirm_each: the agent STOPS and waits for M3).
- 5. STOP FOR THE PERSON. M3's pending request: week 1 ['fatigue.survey', 'sleep.daily']. A wrong signature -> HTTP 403; M1's key on M3's approval -> HTTP 403; M3's own fresh signature -> HTTP 200, order delivered for 20000.
- 6. ALLOWED EXECUTION, then the institution's limit. Round 2: M1 -> delivered (20000); M2 -> delivered (10000); M3 -> needs_approval. M3 then approves week 2 with a valid signature, but the budget is spent: order -> budget (needs 20000 drops, 0 available). A person's approval never widens the institution's budget.
- 7. DELIVERY CONFIRMED. Researcher console: 5 delivered orders, spent 80000 of 80000; every delivered order has an EscrowCreate and EscrowFinish record on the mock ledger. The institution's vault opens each delivered bundle with the key read from the ledger and the hash matches the order: [('RC1-23255e29|week1', 7, ['fatigue.survey', 'sleep.daily']), ('RC1-fa778914|week1', 7, ['sleep.daily']), ('RC1-209928c4|week1', 7, ['fatigue.survey', 'sleep.daily']), ('RC1-23255e29|week2', 7, ['fatigue.survey', 'sleep.daily']), ('RC1-fa778914|week2', 7, ['sleep.daily'])]. Member views: {'M1': {'active_institutions': 1, 'settled_drops': 40000, 'held_drops': 0}, 'M2': {'active_institutions': 1, 'settled_drops': 20000, 'held_drops': 0}, 'M3': {'active_institutions': 1, 'settled_drops': 20000, 'held_drops': 0}}.
- 8. WITHDRAWAL. M2 withdraws with its own signature -> status withdrawn; round 3 asks 2 members, M2 not among them; M2 keeps what it was paid.

## Limits of this run

- Ledger: mock. EscrowCreate/EscrowFinish here are in-memory records, not XRPL Testnet transactions (the lane runs the same code with LEDGER=testnet; not exercised in this run).
- Payment rail: ledger (mock escrow). The AP4M rail was not connected: no RLUSD moved, no VoucherRedeemed, no receipt URL.
- Data: generated test readings labelled generated_test; no UniQdata account was connected, so nothing was written to or read from UniQdata and no settlement record was reported to it.
- LLM: off. Every sentence and every decision came from the rule-based code paths; no proposal was made or checked.
- Candidate comparison: the research-contract lane has none. The institution asks every member at the posted price; the only choices are each member's own consent and the institution's budget. Price negotiation and seller ranking exist only in the market simulation (agentrail/market) and the vault market prototype.
- The researcher has no API or page to download a delivered bundle in this lane; step 7 opened it in-process with the engine's institution vault to show the data is readable by the payer.
- Approvals are Ed25519 signatures from a software key in this script, the same contract the browser join page uses with WebCrypto; no passkey/Touch ID was involved.
