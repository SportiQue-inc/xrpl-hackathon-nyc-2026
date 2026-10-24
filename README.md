# SportiQue Research Data Agents on XRPL

XRPL AI & Fintech Hackathon NYC 2026 (Oct 24-25) - SportiQue team.
Target track: **Agentic Finance** (to be confirmed with mentors).

## Why

Good health research needs the **same person's data over time** - hospital records,
wearables and genomics, connected and kept up to date. Today that data is scattered
across hospitals and apps, researchers buy one-off snapshots, re-recruit for every
study, and the people who generate the data get nothing back and never see how it is used.

Only the individual can connect their own records across sources and over time, and
consent already belongs to them. So the individual should hold the data - and every
time it is used for research, value should flow back to them.

## What we built

A research data rail where AI agents handle the money, and people stay in control.

1. **Data request** - an institution posts a study request: eligibility criteria,
   delivery format (e.g. `sleep.daily.v1`), duration, compensation per delivery, budget.
2. **Personal agents answer privately** - each person's agent checks the request
   against that person's own data and rules *on the person's side*. The institution
   only receives: eligible yes/no, a data manifest (period, completeness, source type,
   last update) and a source attestation. **No raw values before purchase.**
3. **Join** - the person approves the relationship with that institution once.
4. **Institution agent buys fresh data within a budget** - every delivery round the
   agent decides whose updates to buy (skip data it already holds, prefer missing or
   higher-quality data), pays on XRPL, and receives only that round's data.
5. **Value flows back** - each payment goes directly to the person (RLUSD preferred,
   XRP fallback). The person sees which study used their data and what they received.
6. **Pause** - a person pauses; from the next round their data is no longer released,
   and the institution agent reallocates budget to other participants.

## Why AI agents

- Institution agent: autonomous procurement under a mandate - selects participants and
  delivery rounds, tracks budget, avoids paying twice, asks a human to approve budget
  increases above its limit.
- Personal agent: answers eligibility questions without revealing data, applies the
  person's rules (allowed formats, minimum compensation, allowed institution types).
- Code, not the LLM, enforces permissions, amounts, payees and idempotency.

## Why XRPL

- Many small payments to many individuals, settled in seconds at very low cost.
- Planned native features: Payments (RLUSD/XRP), Destination Tags for per-person
  accounting, x402-style pay-per-delivery if a Testnet facilitator is available,
  Credentials for source attestations (availability to be confirmed).
- Settlement confirmed against validated ledgers via QuickNode.

## For institutions

No re-recruiting for follow-up studies, fresh longitudinal data from the same people,
pay only for the delivery rounds actually received, and an auditable record of which
data, under which agreement version, was used in which study.

## Scope and honesty

- All people, institutions, records and amounts are **synthetic**. Testnet only.
- Raw health data is never sent to an LLM and never written on-chain.
- Pausing stops future releases; data already delivered cannot be recalled.
- Not a medical device; no diagnosis or prediction.

See [docs/DEMO_SCOPE.md](docs/DEMO_SCOPE.md), [docs/REUSE_LOG.md](docs/REUSE_LOG.md)
and [docs/MENTOR_QUESTIONS.md](docs/MENTOR_QUESTIONS.md).

## Status

Day 1: concept and scope fixed. Implementation in progress.
