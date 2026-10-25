# One pipeline, two acts

법률 자문 아님 · 합성 데이터 · Testnet. Legal requirements are reflected in the design; this is not a compliance claim.

```
need -> discover offers -> pre-trade quality certificate -> rank (grade x fixed price) -> contract
     -> seller agent's policy (plug-in) -> XRPL escrow, key reveal -> fitness check -> 20% holdback
```

`agentrail/market/exchange.py` is the pipeline. `agentrail/market/acts.py` runs it twice on the same 50 synthetic accounts from `fixtures/market_profiles.json`. Act 2 is Act 1 plus a policy: the exchange class is the same object, and only the policy in each seller's agent changes (`AutonomyPolicy` → `SensitivityPolicy`, a subclass). Tests check this.

The agent is a tool that executes what its owner set and signed. It never consents on the owner's behalf.

## Pre-trade quality certificate (`market/quality.py`)

| part | what the buyer can check before paying |
|---|---|
| profile | per column: completeness, sampling rate, drift, source issuer; signed by the seller's agent (Ed25519) |
| commitment | each row hashed with its own salt into a Merkle root inside the certificate. After the root is fixed, the buyer picks 12 random rows; the seller opens them with proofs; the buyer checks the proofs, value ranges, and completeness within two binomial SDs of the claim |
| delivery | must hash to the same root, or the fitness check fails (`not_as_committed`) and the 20% holdback is withheld |
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

## Act 1: open market (mock ledger, seed 11, 3 rounds)

| | |
|---|---|
| needs posted by the 36 accounts with a budget | 71 |
| trades | 175: 130 settled, 11 settled but unfit (holdback withheld), 23 blocked, 8 declined by the owner, 3 waiting for the owner |
| sold by the agent on its own | 112 of 141 settled |
| volume | 2.68 XRP paid, 0.043 XRP withheld |
| hours from need to fill | median 0 (agent), p90 11.3 (owner answered) |
| unfit deliveries caught | 11 not as committed (bait), 4 incomplete, 4 impossible values |

Health columns, robot logs (lidar, joint torque, gripper events), fleet battery logs and smart-home meters trade side by side. **Reverse direction:** a person buys a wellness trait report (caffeine metabolism, lactose tolerance) from a provider credentialed for wellness reports. The person's agent sends only the variants at the loci the report needs (3 of about 30). The person's payment is escrowed and released by the provider's key reveal. The report says "wellness information, not a diagnosis". The provider signs a deletion confirmation. A request outside the credential ("disease_risk") is refused.

## Act 2: healthcare research, same accounts

Four institutions with 14 researchers. A budget opens only with two researchers' signatures; one is refused.

| institution | country | grade | reasons |
|---|---|---|---|
| org_sleeplab | KR | B | 1 lost fitness dispute; takes copies |
| org_cardio | KR | A | clean record |
| org_neuroimg | US | A | delivery abroad |
| org_genomics | SG | C | a past deletion was never confirmed; delivery abroad |

**The same pseudonymized MRI request** from org_neuroimg (A) and org_genomics (C) produces a mix of outcomes:
- sold on its own to A where the owner's bar allows it
- queued with "needs grade A+, buyer is C" for genomics
- blocked where the owner set imaging to never

**Results:** 365 trades, 245 settled (138 by the agent on its own, the rest after the simulated owner answered), 87 blocked, 22 declined, 11 waiting for the manual approver (P-001). The fill rate is 90%.

## API

- `POST /api/market/run?act=1|2` runs an act.
- `GET /api/market/activity?act=1|2` returns trades, volume, status counts, needs, buyer grades, budgets, reports, and the manual approver's queue.
