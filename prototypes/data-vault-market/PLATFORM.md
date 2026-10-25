# Data Vault Market: from the health engine to a general data platform

One page. Prototype thinking, not a plan of record.

## The idea in one paragraph

Everyone keeps their own data in their own vault. At upload they mark what they would sell, and the
marked copy is pseudonymized right there, so the clear original never enters the market index. An
agent sorts each vault into packages (running tracks, sleep logs, receipts). Buyers post requests
("urban running tracks from at least 5 people, 12 XRP each, no resale"). The agent in the middle
matches the request across many vaults, applies each owner's standing rules, builds a lot only if it
reaches k people, and asks each owner to tap OK. The sale is one sealed push to the buyer, paid by an
escrow that releases the decryption key at the moment it pays: pay = key.

## Who pays

| Payer | For what | Shape |
|---|---|---|
| Buyers (AI labs, map and mobility firms, insurers' R&D, CPG research, academic groups) | a lot that meets their spec, with provenance and consent attached | per-lot price plus a platform fee on top; the fee never comes out of the owner's payout |
| Buyers with recurring needs | a standing request that refills each period | subscription per request; each refill is still a new consent and a new push |
| Data sources (device and app makers) | being a signed, trusted source that buyers prefer | free to join; their signature raises the price of their users' data, which is their incentive |
| Owners | nothing | owners never pay; a paid tier (bigger vault, auto-OK rules) is optional later |

The first wedge is AI training and evaluation data, where buyers already pay for licensed,
consented, provenance-checked data and run out of scraped supply.

## What the moat is

1. **The supply graph.** Many small vaults, each with standing rules, only become sellable when an
   agent can assemble k of them on demand. A buyer cannot get that lot from any single app.
2. **Provenance stamped at intake.** Each record carries its source's signature from the moment it
   arrives, and the signature is checked before payment. Buyers pay more for data they can trace,
   and a late entrant cannot backfill signatures for data already uploaded elsewhere.
3. **Consent receipts on a ledger.** Every sale leaves an escrow with the bundle hash and the terms.
   That is an audit trail a buyer can show its own regulator, and it accumulates with every trade.
4. **Owner trust.** No one ever reads a vault. Data leaves only as a pushed, sealed copy the owner
   approved. That rule is the product; a broker that copies data into its own lake cannot claim it.

## How it relates to the healthcare version

The hackathon engine (AgentRail) is this platform's hardest vertical, built first on purpose.

| Concept | Health engine (main) | General vault market |
|---|---|---|
| Consent | three separate consents, re-checked each round, ethics credential | one OK per sale on a signing sheet, plus standing rules |
| Pseudonymization | `agentrail/deid.py`: HMAC refs, day-level dates, age buckets, k = 5 | same moves at upload; per-deal pseudonym so buyers cannot link sales |
| Packaging | domain bundles, cohort lots of k people | the agent's packages and lots of k owners |
| Provenance | `agentrail/contract/provenance.py`, checked before payment | source signature at intake, checked before EscrowFinish |
| Delivery | `agentrail/vault/delivery.py`: sealed push, no read access | same sealed push to the buyer's key |
| Payment | XRPL escrow with PREIMAGE-SHA-256, K revealed in EscrowFinish | same, simulated in this prototype |
| Withdrawal | MPT clawback and deletion receipt | not in the prototype; same mechanism applies |

So the general market is the health engine with a lighter consent layer, which the README already
argues (layers 1 and 2 run unchanged in any industry; layer 3 gets lighter). Health stays the premium
vertical: higher prices, harder rules, and the proof that the rail holds where it matters most.

## What the prototype does not do yet

- Real XRPL Testnet calls (the main engine has them; the prototype simulates the ledger).
- An LLM sorter (the agent is rule-based so the demo is deterministic).
- Re-identification risk scoring beyond k on the lot, withdrawal, multi-buyer price discovery.
- Legal review per data type. Location, voice and purchase data each carry their own rules
  (for example biometric laws for voice, data-broker registration in some US states); identity
  documents are blocked outright in the demo.
