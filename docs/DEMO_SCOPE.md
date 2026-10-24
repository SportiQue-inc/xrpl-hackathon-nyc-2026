# Demo scope

Cast: 1 institution (sleep study), 50 synthetic participants, 1 study request,
1 delivery format (`sleep.daily.v1`), 3 simulated weekly rounds.

## Demo flow (3 minutes)

| # | Scene | What must really happen |
|---|-------|-------------------------|
| 1 | Institution posts request: age 40-60, >=80% sleep coverage in last 30 days, `sleep.daily.v1`, 12 weeks, 2 RLUSD per weekly delivery, 50 people, budget 1,200 RLUSD | Request stored with structured criteria |
| 2 | 50 personal agents check privately | Each agent evaluates its own synthetic data and rules; ineligible or unwilling agents stay silent; eligible ones return yes + manifest + attestation only |
| 3 | One person approves joining on screen (others pre-approved in simulation) | Relationship record with agreement version |
| 4 | Week 1: institution agent selects within budget and buys the round | Per-person payment on XRPL Testnet, confirmed on a validated ledger; only that week's data released after confirmation |
| 5 | Week 2: agent skips data it already holds, buys only new days | No duplicate payment for the same round (idempotent by round id) |
| 6 | Week 3: one person pauses | Their release is refused; agent reallocates budget; their payments for past rounds remain |
| 7 | Person view | Study usage history and received payments |

Live variation for judges: lower the budget -> agent buys fewer rounds and asks a human to approve an increase.

## Checks enforced by code (not by the LLM)

- Request format is registered and allowed in the relationship
- Payee matches the participant; amount matches the agreement
- Payment confirmed on a validated ledger before data is released
- Round id not already paid or released
- Relationship active and not paused at release time (re-checked just before release)
- Agent spend stays within its mandate; increases need human approval

## Pre-purchase disclosure (institution side)

Allowed: eligible yes/no, data period, completeness %, source type, last update,
source attestation. Not allowed: any raw value before payment.

## Out of scope (roadmap)

Zero-knowledge eligibility proofs, genome data, real hospital/wearable APIs,
3-party key split UI, multi-institution matching, mainnet funds, bridges.

## Screens

1. Institution: post request, eligible pool, agent budget and purchase log
2. Person: incoming request, approve/pause, usage history, payments
3. Ledger view: payments and confirmations (QuickNode)
