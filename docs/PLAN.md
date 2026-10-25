# Plan to submission (agent-first)

Submission target: **Sat Oct 25, 12:30 EDT** (form closes 13:00). Times below are EDT.
Owner: **T** = build thread (Claude), **D** = daniel's hands needed.
Status: [done] · [doing] · [todo].

## Priorities

1. Three agents (buyer, seller x3, personal) with settings and a decision log that reads
   as a conversation. LLM (GPT API) writes the sentences; code decides money and permissions.
2. Real Testnet trades from daniel's Mac (tx hashes, explorer links).
3. One command that runs scenes A and B end to end.
4. Dashboard showing the agent conversation, orders and receipts.
5. Submission: README, video script, form text.

Bonuses: keep only what is already in (XRPL Credentials, multi-signing, x402 rail,
QuickNode via `XRPL_RPC_URL`). No new bonus work.

## Time blocks

| Block | Time (EDT) | Finish | Done when | Owner |
|---|---|---|---|---|
| 1 | Fri 22:00 - Sat 01:00 | Agents 3 kinds + settings + negotiation + LLM wrapper with rule fallback + conversation log | `pytest -q` green; scene A shows offer / counter-offer / accept; no key -> same result, rule sentences | T |
| 2 | 01:00 - 03:00 | Testnet run on the Mac | Scene A payments + credential + multisig top-up validated; hashes in README | T (+D: Mac awake, `.env` key) |
| 3 | 03:00 - 05:00 | One-shot demo command `python -m agentrail.scenario` (A guarded + B) on Testnet, re-runnable | Runs twice in a row on Testnet without manual fixes | T |
| 4 | 05:00 - 08:00 | Dashboard: conversation view per agent, receipts, explorer links; screenshot check on phone width | Pressing "Run all" shows the whole story on one screen | T |
| 5 | 08:00 - 11:00 | README final, 3-min video script, submission form text, record video | Video recorded; form text ready to paste | T (script), D (record, submit) |
| 6 | 11:00 - 12:30 | Buffer, final Testnet run, submit | Form submitted by 12:30 | D |

## Items

| Item | Status | Owner |
|---|---|---|
| Engine: orders, reservation, outbox, idempotent payment, recovery | done | T |
| Policies: seller policy, consent, sensitivity, automation levels, compliance layer | done | T |
| Buyer agent settings: budget, required items, min quality, sensitive-field allowance, auto-approval limit | doing | T |
| Seller agents A-D: quote and negotiation by price floor and provision policy | doing | T |
| Personal agent: auto provide / ask / block by consent, sensitive filter | done (sentences: doing) | T |
| LLM wrapper: `LLM_PROVIDER=openai` (GPT API), rule fallback when no key or on error | doing | T |
| Decision log as agent conversation (who -> whom, why) | doing | T |
| `.env` on the Mac with `OPENAI_API_KEY` | todo | D |
| Testnet scene A/B run, hashes reported | doing (Mac session open, no report yet) | T |
| x402 rail run on Testnet | todo (only if block 2 finishes early) | T |
| Dashboard conversation view | todo | T |
| README / video script / form text | todo | T |
| Video recording and form submission | todo | D |

## Dropped (not doing)

- The earlier single-participant (P017-centered) health demo and its handoff plan. P017,
  P023, P031 remain only as synthetic participant labels in scene B.
- Payment-channel style settlement. Each order is one XRPL Payment.
- Ledger hardware wallet bounty. One line in docs only (production approval signing).
- New bonus integrations beyond what is already in the code.
- Escrow, RLUSD, multi-holder aggregate products: listed as open items, not built.
