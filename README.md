# AgentRail - agents that procure data within a mandate, settled on XRPL

XRPL AI & Fintech Hackathon NYC 2026 (Oct 24-25) - SportiQue team.
Track: **Agentic Finance**.

## One line

Give your agent a goal, quality bar and budget. It finds data held in other
organizations' (or people's) own databases, checks quality, negotiates with their
agents, pays on XRPL and receives exactly what was agreed - and it **stops** when a
request falls outside what the data holder allowed, even at a higher price.

## Why

Data that AI and research teams need (robot trajectories, sensor logs, evaluation
sets, personal health time series) sits in many separate databases. Buying it today
means emails, NDAs, manual quality checks, invoices and one-off file drops. Agents
can do the searching and paying, but an agent that can pay is only safe if:

- it cannot spend beyond its mandate (budget, per-order limit, allowed purposes),
- the seller's terms - and, for personal data, the person's consent - are enforced
  by code, not by a prompt,
- every payment is tied to exactly one order, one data version and one usage scope.

## What we built

One engine, two kinds of trade.

**Scene A - organization to organization (robotics data).**
A robot developer's buyer agent gets: *"indoor warehouse navigation data at night,
with LiDAR + IMU, covering dynamic obstacles and narrow aisles, commercial training
allowed, budget 100 XRP"*. It queries three seller agents, inspects samples,
excludes seller A (no LiDAR), accepts seller B's counter-offer (raw video excluded by
B's policy, not needed), combines B + C to cover every required scenario, reserves
budget, pays each seller on XRPL Testnet, and receives sealed bundles. Final report:
data acquired, why, quality checked (sample-verified), usage scope, total spent,
remaining budget, payment and delivery receipts.

**Scene B - same engine, personal health data.**
The data source is swapped for personal data vaults (synthetic participants). Each
person's agent carries the person's settings: which institution, which items, which
purpose, which period, how much automation, and the sensitivity tier of each item.

1. Items the person already allowed (sleep, activity, heart rate) are provided
   automatically every round; payment goes **directly to the person**.
2. The institution asks for two more items (fatigue survey, blood pressure) at a
   higher price - the agent does not provide them; it asks the person.
3. The person approves only the fatigue survey. Blood pressure (sensitive tier)
   stays blocked.
4. Next round runs without the person opening the app, within the new scope.
5. A person pauses: new orders and undelivered bundles stop; completed payments and
   history remain. Another institution without consent is refused.

## Agent settings (the mandate)

| Agent | Settings the owner gives it | Enforced by |
|-------|-----------------------------|-------------|
| Buyer agent | goal spec, required fields/scenarios, quality thresholds, allowed purposes, total budget, per-order limit, approval threshold | `policy.BuyerMandate`, budget reservation in SQLite |
| Seller agent (organization) | catalog, price floor, allowed buyers, allowed purposes, excluded fields, licence (commercial training, resale) | `policy.SellerPolicy` |
| Personal agent | per-institution consent: items, purpose, period; automation level (confirm each / auto within scope); minimum price; sensitivity tier per item; pause / revoke | `policy.PersonalConsentPolicy` |

Sensitivity and delegation are separate: a low-sensitivity item is still never sent
unless the person allowed it; a sensitive item can be provided repeatedly only
inside an explicit consent, and the agent can never widen scope on its own.

Execution requires the intersection of: seller/person permission AND buyer mandate
AND available budget AND data actually available. If the consent store cannot be
read, the trade is held (fail closed).

## Why XRPL

- Many small payments to many payees (organizations or individuals), settled in
  seconds at very low cost.
- Each order pays with a `Payment` carrying `InvoiceID = sha256(order key)`; the
  signed transaction hash is stored **before** submission, so a lost response is
  recovered by looking the hash up on a validated ledger - never by paying again.
- Data is released only after the payment is in a **validated ledger** and the
  permission is re-checked just before release (x402-style: 402 terms -> pay ->
  verify -> deliver).
- Only hashes go on-chain. No health values, names or consent text.

## Safety properties (tested)

See [docs/DESIGN.md](docs/DESIGN.md) for the state machine and the full test list.

- Same order retried -> one order, one payment.
- Same order key with different content -> rejected as a conflict.
- Concurrent orders -> budget reserved serially, never overspent.
- Restart after payment -> pending delivery recovered from the outbox.
- Delivery response lost -> same bundle re-delivered, no extra payment.
- Payment response lost -> recovered by tx hash lookup.
- Request outside consent (even at higher price) -> needs approval, nothing sent.
- Pause -> new orders blocked; revoke -> undelivered bundles withheld, payment kept,
  exception recorded with the institution as cost bearer.
- Budget too small -> agent buys nothing it cannot complete and reports why.

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                   # MockLedger, all safety tests
python -m agentrail.scenario                # both scenes on MockLedger, prints report
LEDGER=testnet python -m agentrail.scenario # same scenes on XRPL Testnet (faucet wallets)
uvicorn agentrail.web:app --reload          # dashboard at http://127.0.0.1:8000
```

Testnet wallets are created from the faucet at run time and kept only in
`wallets.local.json` (git-ignored).

## Scope and honesty

- All organizations, people, records and amounts are **synthetic**. XRPL Testnet only.
- Raw data is never sent to an LLM and never written on-chain. Agents in this demo
  are rule-based; explanations are templated.
- Quality checks run on samples and are labelled "sample-verified", not a guarantee
  about the whole dataset.
- Pausing stops future releases; data already delivered cannot be recalled.
- Not a medical device; no diagnosis.

See [docs/DEMO_SCOPE.md](docs/DEMO_SCOPE.md), [docs/DESIGN.md](docs/DESIGN.md),
[docs/REUSE_LOG.md](docs/REUSE_LOG.md) and [docs/MENTOR_QUESTIONS.md](docs/MENTOR_QUESTIONS.md).
