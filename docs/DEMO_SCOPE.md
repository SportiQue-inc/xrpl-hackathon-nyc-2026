# Demo scope

All parties, records and amounts are synthetic. XRPL Testnet only.

## Cast

- Buyer: a robot developer (scene A) and a sleep research lab (scene B).
- Organization holders: Alpha Sim, Beta Logistics, Gamma Robotics, Delta Fleet.
- Personal holders: participants P017 (`auto_standard`), P023 (`auto_all`),
  P031 (`confirm_each`).
- An ad network with a prohibited purpose (refused by the compliance layer).

## Flow (about 3 minutes)

| # | Scene | What must really happen |
|---|-------|-------------------------|
| A1 | Buyer gives one goal: night warehouse navigation, LiDAR + IMU, dynamic obstacles + narrow aisles, commercial training, budget 50 XRP | Goal and mandate stored; agent queries 4 sellers |
| A2 | Agent evaluates | A1 excluded (no LiDAR), C2 excluded (licence: evaluation only), D1 excluded (20% missing in sample), B1 counter-offer without raw video accepted |
| A3 | Agent buys B1 + C1 for 35 XRP | Two Payments on Testnet, validated; sealed bundles delivered; report shows spent 35 / remaining 15 |
| A4 | Live variation: budget 30 | Agent buys nothing, reports it needs +5 XRP and asks a human |
| B1 | Three people sign consents (sleep, activity, heart rate) with different automation levels | Consent documents hashed, versions kept |
| B2 | Week 1 | P017, P023 paid and delivered automatically; P031 confirms by hand, then paid |
| B3 | Week 2: lab also asks for fatigue survey + blood pressure at 2 XRP/item | Consented items still run; extra items not sent, people asked |
| B4 | P017 approves fatigue only | Week 3 includes fatigue for P017; blood pressure stays blocked |
| B5 | P023 pauses | Week 4 skips P023; its past payments remain |
| B6 | Ad network asks P017 | Refused: prohibited purpose |
| C | Same order sent twice, payment response lost, delivery ack lost, server restart | One order, one payment, same bundle re-delivered, recovered from outbox |

## Checks enforced by code (not by an LLM)

- Holder permission, buyer mandate, budget and data availability all required.
- Payee, amount and InvoiceID verified on a validated ledger before release.
- Permission re-checked just before payment and just before delivery.
- Order key unique; different content under the same key is a conflict.
- Sensitive items: never auto-approved, filtered for buyers without ethics approval.

## Screens

One dashboard (`uvicorn agentrail.web:app`): mandate numbers per buyer
(budget / reserved / spent / available), candidate evaluation, consents with document
hashes, orders with Testnet explorer links, agent decision log, approvals asked of
people, exceptions, buyer account settings.

## Out of scope

Real hospital or device APIs, mainnet funds, RLUSD, arbitrary queries from buyers,
LLM in the decision path, recall of already delivered copies.
