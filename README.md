# SportiQue Consent-Bound Data Agents on XRPL

XRPL AI & Fintech Hackathon NYC 2026 (Oct 24-25) - SportiQue team.

Target track: **Agentic Finance** (to be confirmed with mentors).

## One-line pitch

A person sets a standing data-sharing agreement with a research institution once.
A personal agent and an institution agent then keep the institution supplied with
exactly the allowed data, block anything outside the agreement, stop on withdrawal,
and settle each verified delivery on XRPL Testnet.

## Demo flow (3 minutes)

1. **My data** - a person sees synthetic genomic, lab and lifestyle records in one place.
2. **Connect institution A** - the person allows a fixed list of delivery formats
   (for example `sleep.daily.v1`, `activity.daily.v1`, `clinical.selected-labs.v1`,
   `genomic.panel-a.v1`) under agreement v3.
3. **Deliver package P1** - only the allowed fields are extracted and loaded into a
   separate institution demo DB. A delivery receipt is recorded.
4. **Study 2 reuses P1** - a follow-up study inside institution A reuses the same
   package without a new per-study consent or re-transfer; a usage record is added.
5. **Out-of-scope request** - the institution agent asks for `sleep.minute.v1`.
   It is not in the agreement, so 0 records are sent and the person is asked whether
   to extend the agreement (v3 -> v4).
6. **Testnet settlement** - each valid job receipt pays 2 Test XRP on XRPL Testnet.
   Retrying the same job never pays twice.
7. **Withdrawal** - the person stops future delivery; pending jobs are cancelled and
   the delivery gate refuses new transfers even if an agent is offline.

## Architecture

```
Personal agent  <->  Coordination + permission service  <->  Institution agent
                           |                 |
              Encrypted personal store   Institution demo DB
                           |
                     XRPL Testnet (commitments + payments)
```

- Agents plan and explain; code enforces permissions, amounts, signatures and idempotency.
- Raw genomic data is never sent to an LLM and is never written on-chain.
- On-chain: salted commitments of agreement versions and delivery receipts, plus
  Testnet payment transactions. Detailed terms and data stay off-chain.

## What is built during the hackathon

See [docs/DEMO_SCOPE.md](docs/DEMO_SCOPE.md) and [docs/REUSE_LOG.md](docs/REUSE_LOG.md).
Anything reused from earlier SportiQue work is listed with its source and version.

## Data and safety

- All people, institutions, records, IRB states and amounts in this repo are **synthetic**.
- No real health data, no mainnet funds, no production credentials.
- Not a medical device; no diagnosis or prediction.

## Status

Day 1: repository and scope set up. Implementation in progress.
