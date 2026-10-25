# Plan to submission

Submission target: **Sat Oct 25, 12:30 EDT** (form closes 13:00). Times are EDT.
Owner: **E** = engine thread (Claude), **X** = XRPL checks thread, **D** = daniel (UI, Mac, recording).

## Pitch

Not big data, but one person's whole record. A study's research agent asks people to take part;
each person's agent gathers their own records on one time axis and contributes only what they
agreed to. **The LLM proposes, code verifies, the ledger enforces.** We solved the hardest
boundary first (consent, re-identification, withdrawal on person-level health records); the robot
scene shows the same engine with a lighter consent layer.

Order of the story (README section 2, demo, video): **consent -> re-identification -> withdrawal
-> other domains (robot, Testnet)**. Each issue: problem, answer, where code or ledger enforces it,
demo moment, tests and tx.

## Time blocks

| Block | Time | Work | Done when | Owner |
|---|---|---|---|---|
| 1 | 22:40 - 23:10 | Boundary solutions in the engine: DUO consent, quasi-identifier rule, per-study pseudonym and date shift, three withdrawals with MPT clawback and escrow refund, KYB credential | `tests/test_study.py` green; `POST /api/run/boundaries` returns evidence | E (done) |
| 2 | 23:10 - 00:30 | Both service surfaces as API: participant app (request card, preview, approve, decline, pause, revoke) and researcher console (goal, LLM gap reading with code verdict, co-signed approval, send, close round, sweep, bundle open), live events | docs/API.md matches code; one test drives both pages | E (done) |
| 3 | 23:10 - 02:00 | Full health study on Testnet from the Mac: MPT licence + clawback, KYB refusal, escrow finish + cancel, multisig approval; feature checks | every row in README section 4 has a tx link | D's Mac, X |
| 4 | 23:30 - 05:00 | UI for both surfaces on the API (participant phone page, researcher console), dashboard boundary tab | pages served at `/participant`, `/console`; one tap on the phone shows on the console | D |
| 5 | 00:30 - 03:00 | Engine polish from Testnet findings; x402 clinic export fee evidence; LLM answers recorded for replay (quota 50/day) | `fixtures/llm_cache.json` committed; Testnet rerun clean | E |
| 6 | 03:00 - 05:30 | README tx table, DEMO_SCOPE, DESIGN to the person-centric frame; REUSE_LOG for any reused UI | docs consistent, forbidden phrases checked | E |
| 7 | 05:30 - 08:00 | Integrated rehearsal on Testnet with both pages; fix only blockers | two clean runs | E + D |
| 8 | 08:00 - 10:00 | Code freeze, video script (2-3 min: phone request -> contribution -> heatmap -> revoke -> robot), form text | script final | E |
| 9 | 10:00 - 12:30 | Record, submit | submitted | D |

If time runs short: dashboard polish first, then x402 evidence. Consent, re-identification,
withdrawal, escrow, MPT, Credentials, multi-signing and both surfaces stay.

## Items

| Item | Status | Owner |
|---|---|---|
| Engine: orders, reservation, outbox, idempotent payment, recovery | done | E |
| LLM layer: gap reading (cohort and per person), schema matching, licence reading, proposals audit, adversarial tests, record/replay | done | E |
| Key-reveal escrow (finish + cancel), Testnet evidence | done | E, D |
| Consent with DUO codes; new purpose waits; prohibited purpose refused | done | E |
| Re-identification: minimization, pseudonym and date shift per study, quasi-identifier rule, sealed bundles | done | E |
| Withdrawal: decline round, pause, revoke (MPT clawback, withheld key, escrow refund) | done (mock), Testnet running | E, D |
| MPT data licence per (study, participant) | done (mock), Testnet running | E, X |
| KYB: VERIFIED_ORG Credential, DepositAuth + DepositPreauth, CredentialIDs | done (mock), Testnet running | E, X |
| Multi-signed study budget approval | done | E |
| Participant app API + researcher console API + events | done | E |
| Participant app UI, researcher console UI | doing | D |
| Clinic export fee (x402 path) evidence | todo | E, X |
| README / docs to the new frame | README done, rest todo | E |
| Video script, form text | todo | E |
| Recording, submission | todo | D |

## Dropped

- Price negotiation between agents (fixed published prices).
- Bulk dataset wording for health data: studies request participation; they do not acquire records.
