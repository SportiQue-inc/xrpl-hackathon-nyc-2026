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
5. **Negotiate** with the best in order: the buyer opens at 80% of the ask, the seller's agent concedes
   toward its floor (90% of the ask, 95% with a shaky record), a deal is the first bid at or above the
   counter; no meeting point means the next candidate. The agreed price goes into the contract hash.
6. The LLM may explain the choice in words; an explanation that names a seller who was not a
   candidate is dropped. It never changes the ranking or the price.

`python scripts/export_network.py` replays these logs: the offer book in the middle, the fan-out to
every candidate, the comparison table, the negotiation, then the one trade with escrow and key.

## Act 1: open market (mock ledger, seed 11, 3 rounds)

| | |
|---|---|
| needs formed by the accounts with a budget | 74 |
| offer book | 477 listings, root anchored on the ledger before trading (re-anchored when agents collect new data) |
| candidates per need | median 34 sampled and scored |
| already held | 127 offers refused before trading (same certified root as data the buyer bought); 3 copies bought at the new part only |
| trades | 141: 99 settled, 10 settled but unfit (refund claim recorded), 23 blocked, 6 declined by the owner, 3 waiting for the owner |
| sold by the agent on its own | 87 of 109 settled |
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
- blocked where the owner set imaging to never

**Results:** 366 trades, 239 settled (131 by the agent on its own, the rest after the simulated owner answered), 98 blocked, 28 declined, 1 waiting for the manual approver (P-001).

## API

- `POST /api/market/run?act=1|2` runs an act.
- `GET /api/market/activity?act=1|2` returns trades, volume, status counts, needs, buyer grades, budgets, reports, and the manual approver's queue.
