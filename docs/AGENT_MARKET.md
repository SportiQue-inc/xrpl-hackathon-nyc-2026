# One pipeline, two acts

법률 자문 아님 · 합성 데이터 · Testnet. Legal requirements are reflected in the design; this is not a compliance claim.

```
need -> discover offers -> pre-trade quality certificate -> rank (grade x fixed price) -> contract
     -> seller agent's policy (plug-in) -> XRPL escrow, key reveal -> fitness check (a market dataset exists in full: bought whole after inspection, retrospective schedule)
```

`agentrail/market/exchange.py` is the pipeline. `agentrail/market/acts.py` runs it twice on the same 50 synthetic accounts from `fixtures/market_profiles.json`. Act 2 is Act 1 plus a policy: the exchange class is the same object, and only the policy in each seller's agent changes (`AutonomyPolicy` → `SensitivityPolicy`, a subclass). Tests check this.

The agent is a tool that executes what its owner set and signed. It never consents on the owner's behalf.

## Pre-trade quality certificate (`market/quality.py`)

| part | what the buyer can check before paying |
|---|---|
| profile | per column: completeness, sampling rate, drift, source issuer; signed by the seller's agent (Ed25519) |
| commitment | each row hashed with its own salt into a Merkle root inside the certificate. After the root is fixed, the buyer picks 12 random rows; the seller opens them with proofs; the buyer checks the proofs, value ranges, and completeness within two binomial SDs of the claim |
| delivery | must hash to the same root, or the fitness check fails (`not_as_committed`) the seller's pass rate and grade fall and a refund claim is recorded off the ledger |
| reputation | issuer credential × Beta(1+passed, 1+failed) mean of past fitness checks |
| grade | A/B/C from checked completeness and reputation; the price is a fixed quote per tier × grade |

A person's few weeks and a company's whole dataset carry the same certificate (`scope: person | dataset`).

## The seller agent's policy (`market/policies.py`)

1. **Hard gates.** A failed gate blocks the trade, with the reason, and no setting widens it:
   - a prohibited purpose
   - T2 and up without a valid IRB credential
   - an expired institution credential
   - a country the owner excluded
   - kinds the owner set to "never"
2. **Buyer trust grade A–D**, computed with reasons from:
   - the institution and IRB credentials
   - unconfirmed past deletions
   - audit flags and lost fitness disputes
   - delivery abroad
   - copy vs. controlled workspace
   - trading history
3. **Owner bars per kind of data**: the lowest grade the agent may sell to on its own. Presets L0 ("ask me always") to L4 ("everything except genomic"); advanced owners edit each bar. If the grade meets the bar, the agent sells. If it doesn't, the trade is queued for the owner with the reason, for example "pseudonymized imaging needs grade A+, buyer is C (a past deletion was never confirmed; delivery abroad (SG))".
4. **Genomic.** Raw variants are never delegated; each study needs the person's passkey signature. Inside a study the person signed (institution, purpose, loci), the agent delivers computed outputs only: per-locus allele counts, never positions or alleles. A new institution, purpose or locus goes back to the person. No "proceed unless refused" mode. Participants in Mongolia: genomic data is left out of this MVP.
5. **Act 2 only:** tiered consent per institution (catalog/scope.py). This means DUO codes, standing grants, and one Touch ID package per institution for T3 and new scope, including transfer abroad.

## Imaging pseudonymization (`agentrail/deid.py`, `market/imaging.py`)

This reimplements the interfaces of the people's store (research ref HMAC, per-study participant number, egress de-identification with date truncation, age bands and k=5 for clinical codes), with nothing imported from those repositories. It adds what that store lacks for DICOM:
- UID remapping by HMAC into `2.25.*`
- one date shift per subject
- a burned-in-text gate that blocks the image
- defacing of head scans

Each purpose has its own secret, with no default and no reuse of another key. Every image carries its pseudonymization record. This lowers the risk that an image is linked to a person; it does not remove it.

## How a buyer's agent finds a seller (`agentrail/market/discovery.py`)

1. **Need formed.** The agent compares its own store with what its owner wants, takes one gap
   column, and asks the LLM for columns, weeks, quality floor, price ceiling and a reason. Code keeps
   only columns from the gap, a ceiling inside the owner's budget per item, weeks 1–8 and grades A–C;
   anything else falls back to the rule. Without an LLM key the rule runs and is labelled as such.
2. **Offer book.** Every seller's agent lists its certified datasets. The list's Merkle root goes on
   the ledger in a 1-drop Payment (`InvoiceID` = root, memo `agentrail:offerbook:<n>:<root>`); the
   agent reads the root back from the ledger and ignores any listing whose proof does not reach it.
3. **Fan-out.** Filter by columns, weeks, seller attributes and grade, then open 12 hashed sample rows
   of every survivor against its certificate.
4. **Compare.** Score = 0.45 quality grade + 0.35 price under the ceiling + 0.20 the seller's record
   of fit deliveries. Ranked list kept in the need log.
5. **Negotiate** with the best in order, around the market reference (below). The buyer opens at
   the low end of the reference range; the seller's agent concedes from its ask toward its floor (the
   owner's floor, or 90% of the ask, 95% with a shaky record); a deal is the first bid at or above the
   counter, and a seller already at its floor inside the buyer's ceiling is taken as is. No meeting
   point means the next candidate. The agreed price goes into the contract hash.
6. The LLM may explain the choice in words; an explanation that names a seller who was not a
   candidate is dropped. It never changes the ranking or the price.

`python scripts/export_network.py` replays these logs: the offer book in the middle, the fan-out to
every candidate, the comparison table, the negotiation, then the one trade with escrow and key.

## Who sets the price (`agentrail/market/pricing.py`)

Neither side alone. Owners set the bounds; the market sets the price inside them.

- **Bounds.** The seller's owner sets a floor (a share of the rate card, 0.6–0.9 in the simulation).
  The buyer's owner sets the budget; the buyer's agent never offers more than its budget per item.
- **Reference price.** Per data tier: the median of the last 20 settled prices (as a ratio to the rate
  card, so one week and four weeks compare) and the 25th–75th percentile as the range. Settled prices
  are public on the ledger (the escrow amount). With fewer than 3 trades the rate card is the seed.
- **Ask.** The seller's agent asks the reference × a scarcity factor: needs posted for those columns
  in the last 24 hours over listings in the offer book that hold them (0.85–1.4). Never under the floor.
- **Bid.** The buyer's agent's ceiling follows the market (20% above the grade A reference) but stops
  at the owner's budget per item; it opens at the low end of the range.
- **Each contract's conversation names the reference**, its source (rate card or "median of the last N
  settled trades"), the scarcity numbers and the owner's floor.
- Price never decides consent: T2 and T3 still follow the owner's rules and go back to the person.

**Measured** (`python scripts/measure_prices.py`, Act 1, mock ledger, synthetic accounts; settled
price as a share of the rate card):

| market | trades settled | median | mean |
|---|---|---|---|
| baseline (477 listings, 74 needs: oversupplied) | 109 | 0.70 | 0.75 |
| 3× the needs | 264 | 0.80 | 0.78 |
| half the listings | 95 | 0.80 | 0.78 |
| 3× the needs and half the listings | 206 | 0.80 | 0.78 |

With more listings than needs, prices settle near the owners' floors. When demand rises or supply
falls, the median moves up by about 14%. With both at once, it rises no further in this simulation,
because the floors and the buyers' ceilings bound the price.

## Sub-projects under one institution (`agentrail/subprojects.py`)

A person consents once to an institution's scope (purposes, data types). The institution then opens
sub-projects under that scope. A sub-project is a record under the institution's one account and
wallet, not a sub-account. It has a purpose, data types, a budget and a period. For each person and
item, the agent routes as follows:

- **auto**: the item is inside the scope and the person's own rules. It is settled per sub-project,
  one escrow per person per round, with no new contract.
- **ask**: the item is outside the scope, or it is T3 (genomic, imaging, mental health,
  reproductive). The person decides for this sub-project only.
- **blocked**: the person paused or withdrew, or never consented to this institution.

Each order carries the sub-project id in its product id and in the escrow memo (`sub:<id>`), so
payouts are listed per sub-project in the person's relationship view and in UniQLab. The routes are
`GET /api/institution`, `POST /api/institution/subprojects`,
`POST /api/institution/subprojects/{sid}/run`, `GET /api/p/{pid}/relationship`,
`POST /api/p/{pid}/relationship/consent` and `POST /api/p/{pid}/subprojects/{sid}/decision`.

## Act 1: open market (mock ledger, seed 11, 3 rounds)

| | |
|---|---|
| needs formed by the accounts with a budget | 74 |
| offer book | 477 listings, root anchored on the ledger before trading (re-anchored when agents collect new data) |
| candidates per need | median 34 sampled and scored |
| already held | 127 offers refused before trading (same certified root as data the buyer bought); 3 copies bought at the new part only |
| trade attempts | 141: 109 paid (escrow finished, key revealed), 23 blocked by the seller's rules, 6 declined by the owner, 3 waiting for the owner |
| paid trades | 109: 99 passed the buyer's delivery check, 10 failed it (refund claim recorded); 87 of the 109 needed no owner decision |
| volume | 1.72 XRP paid at negotiated prices (about 9% under the asks) |
| hours from need to fill | median 0 (agent), p90 11.3 (owner answered) |
| unfit deliveries caught | 10 after delivery (not as committed, incomplete or impossible values), each with a refund claim |

Health columns, robot logs (lidar, joint torque, gripper events), fleet battery logs and smart-home meters trade side by side. **Reverse direction:** a person buys a wellness trait report (caffeine metabolism, lactose tolerance) from a provider credentialed for wellness reports. The person's agent sends only the variants at the loci the report needs (3 of about 30). The person's payment is escrowed and released by the provider's key reveal. The report says "wellness information, not a diagnosis". The provider signs a deletion confirmation. A request outside the credential ("disease_risk") is refused.

## Act 2: healthcare research, same accounts

Four institutions with 14 researchers. A budget opens only with two researchers' signatures; one is refused.

| institution | country | grade | reasons |
|---|---|---|---|
| org_sleeplab | KR | B | 1 lost fitness dispute; takes copies |
| org_cardio | KR | A | clean record |
| org_neuroimg | US | A | delivery abroad |
| org_genomics | SG | C | a past deletion was never confirmed; delivery abroad |

**The same pseudonymized MRI request** from org_neuroimg (A) and org_genomics (C). MRI is T3, so the
agent never sells it on its own:
- A passes the owner's rules and goes to the person for a fresh approval each time
- C is held with "MRI needs grade A+ and a controlled workspace, buyer is C", without asking
- the same screen runs first for every T3 type (CT, MRI, genomic): a buyer below the bar or outside a
  controlled workspace is held, never put to the owner; the reason names the actual data type
- blocked where the owner set imaging to never

**Results:** 366 trades, 239 settled (131 by the agent on its own, the rest after the simulated owner answered), 98 blocked, 28 declined, 1 waiting for the manual approver (P-001).

## API

- `POST /api/market/run?act=1|2` runs an act.
- `GET /api/market/activity?act=1|2` returns trades, volume, status counts, needs, buyer grades, budgets, reports, and the manual approver's queue.
