# Plan to submission

Submission target: **Sat Oct 25, 12:30 EDT** (form closes 13:00). Times are EDT.
Owner: **T** = build thread (Claude), **D** = daniel's hands needed. Status: done · doing · todo.

## Pitch

Procurement agents that work out what data their organization is missing, read other
companies' catalogs and contracts like a human buyer, and close the deal on XRPL.
**The LLM proposes, code verifies, the ledger enforces.** The same engine runs a research
cohort where each person's agent answers research requests from their phone.

Track fit (Agentic Finance asks for escrow, multi-signing, on-chain credentials): all three
are in the main flow with Testnet evidence, plus x402 (T54) and QuickNode as bonuses.

## Time blocks

| Block | Time | Build | Done when | Owner |
|---|---|---|---|---|
| 1 | 22:40 - 00:30 | LLM layer for B2B: gap inference from coverage table + evaluation report (code recomputes each gap from the table), schema matching verified on samples, licence text -> structured terms confirmed by the seller, `proposals` audit table, adversarial-LLM tests, LLM-off comparison, second input with a different report | `pytest` green; two inputs give different specs and sellers; LLM on/off numbers printed | T |
| 2 | 00:30 - 02:30 | Escrow that ties payment to delivery: bundle locked with key K, `EscrowCreate` with `sha256(K)` condition and `CancelAfter`; seller gets paid only by publishing K in `EscrowFinish`; buyer reads K from the ledger and opens the bundle; deadline passed -> `EscrowCancel` refund | Mock tests for finish and cancel paths; Testnet run on the Mac | T |
| 3 | 02:30 - 03:30 | Organization KYB: `VERIFIED_ORG` Credential + seller `DepositAuth` + `DepositPreauth` by credential; unverified buyer's payment refused by the ledger | Mock test + Testnet tx | T |
| 4 | 03:30 - 05:30 | Research cohort, person side: new "research request" app page in this repo (verified-institution badge, LLM summary of purpose, auto-provide / needs approval / blocked items, real XRP amount) calling the engine API; 8-week cohort with missing person-weeks filled by the lab agent; 50 Testnet participant addresses | Page drives scene B end to end | T |
| 5 | 05:30 - 07:00 | Dashboard: "LLM proposal -> code verdict -> ledger" three columns, coverage heatmap before/after, explorer links | One screen tells scene A | T |
| 6 | 07:00 - 08:00 | **Integrated Testnet run on the Mac**: all scenes, escrow finish + cancel, KYB refusal, multisig, credential, one x402 run; `scripts/verify_ledger.py`; README tx table | Every README claim has a tx link | T + D (Mac awake) |
| 7 | 08:00 - 10:00 | Code freeze, video script, rehearsal | Script final | T |
| 8 | 10:00 - 12:30 | Record video, form text, submit | Submitted | D |

If time runs short, dashboard polish shrinks first; escrow, KYB and the cohort page stay.

## Items

| Item | Status | Owner |
|---|---|---|
| Engine: orders, reservation, outbox, idempotent payment, recovery | done | T |
| Policies: seller policy, consent, sensitivity, automation levels, compliance | done | T |
| Multi-signing treasury (Testnet evidence) | done | T |
| Ethics Credential gating sensitive items (Testnet evidence) | done | T |
| LLM wrapper (GPT via `OPENAI_API_KEY`, rule fallback), `.env` on the Mac | done | T, D |
| Gap inference, schema matching, licence reading, audit, adversarial tests | doing | T |
| LLM on/off comparison, second input | todo | T |
| Escrow with key reveal + cancel path | todo | T |
| KYB Credential + DepositPreauth | todo | T |
| Research request app page + 8-week cohort + 50 participants | todo | T |
| Dashboard three-column view + heatmap | todo | T |
| x402 Testnet run (existing path, evidence only) | todo | T + D |
| Integrated Testnet run, verify_ledger.py, README tx table | todo | T + D |
| Video script / form text | todo | T |
| Video recording, submission | todo | D |

## Dropped

- Price negotiation between agents (fixed published prices).
- Payment-channel style settlement.
- Ledger hardware wallet bounty (one docs line only).
