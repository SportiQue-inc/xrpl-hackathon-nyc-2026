# Demo scope

Fixed cast: 1 person, 1 institution (A), 2 allowed studies, 1 out-of-scope request.

## In scope (built during the hackathon)

| # | Feature | Done when |
|---|---------|-----------|
| 1 | Synthetic data intake | Genomic panel, 6 lab tests and 7-day sleep/activity summaries appear under one person |
| 2 | Delivery format registry | Each format has id, version, fields, calculation rule and missing-data rule |
| 3 | Institution agreement | Person approves an allow-list of formats for institution A (v3); versions are immutable |
| 4 | Exact extraction + push | Only allowed fields land in a separate institution demo DB; receipt recorded |
| 5 | Follow-up study reuse | Study 2 reuses package P1 with a usage record, no new consent, no re-transfer |
| 6 | Out-of-scope handling | Request for a non-allowed format sends 0 records and creates an agreement-change request |
| 7 | Testnet settlement | 2 Test XRP per valid job receipt; idempotent by job id |
| 8 | Withdrawal | Future delivery stops; gate re-checks latest state right before every transfer |
| 9 | Agent planning | Institution agent maps a natural-language request to registered formats and picks: reuse / allowed update / request change / wait for review |

## Request outcomes the code must distinguish

- Allowed format, data exists -> deliver
- Allowed format, data not yet available -> data pending (prospective collection)
- Registered format, not allowed for this institution -> agreement change needed
- Unregistered format -> unsupported, define the format first

## Checks enforced by code (not by the LLM)

- Requested format id and version are in the institution allow-list
- Genomic loci requested are within the allowed panel parameters
- Recipient institution and receiving key match the registered ones
- Agreement / delegation is currently valid and not withdrawn
- Actual output matches the signed plan (fields, period, transform version)
- Job not already executed or paid

## Out of scope

Large genome files on-chain, production KMS/cloud, real hospital APIs, WGS analysis,
clinical report engine, TEE/MPC/FHE, bridges, real IRB integration, mainnet funds.

## UI screens

1. My data (record list -> record detail with sharing history)
2. Institution connection (allowed formats, agreement version)
3. Institution view (participants, packages, follow-up studies)
4. Pending request review (approve / decline agreement change)
