# Research contracts: posted, joined, traded

`agentrail/research_contracts.py`. A contract is a record, not code. The researcher posts the terms; each
person joins with their own key and signs the consent document; at each round every member's agent
answers from that member's own consent and data; payment is a key-reveal escrow on the ledger.

The demo study (`org_sleeplab`, the 50 fixture participants, `/api/study/*`) is unchanged and separate.
Contracts keep their own store, so `/api/reset` does not touch them.

## Run it

| env | meaning |
|---|---|
| `AGENTRAIL_CONTRACTS_DB` | SQLite file for contracts, members, orders (default: a temp file, lost on restart) |
| `AGENTRAIL_POSTING_CODE` | at least 8 characters; `POST /api/contracts` from anywhere but localhost needs it in `X-Posting-Code` |
| `LEDGER` | `mock` or `testnet` (same as the engine) |
| `UNIQDATA_ROSTER` | optional: UniQdata accounts members may join with (`uniqdata_account`); their vault reads that account and their payments are reported to it |
| `AGENTRAIL_KEYSTORE` | keeps institution box keys and member keyrings across restarts |

`scripts/contract_join.py` posts a contract, joins test accounts (`--count 50`), sandbox UniQdata accounts
(`--roster`), or one teammate (`--name`), and runs a round as the researcher. Keys stay in the gitignored
`.contract_keys.json` on the machine that ran it.

## Rules

- Items: the five vault items only. Genomic, CT and MRI are refused at posting (T3 lane, fresh approval each time).
- Sensitive items (blood pressure) pass only to an institution with an ethics credential on the ledger,
  issued at posting from the declared IRB number (`irb_checked: "declared by the researcher"`).
- Automation is the member's own choice: `confirm_each`, `auto_standard` (sensitive items wait), `auto_all`.
- Approving a waiting week and withdrawing each need a fresh signature from the member's key over
  `agentrail-consent|{pid}|sha256("{action}|{cid}|{consent_hash}")`, where action is
  `approve:{request_id}:{items sorted, comma separated}` or `withdraw`.
- Withdrawal: no key is published for rounds not yet paid; those escrows return to the institution at
  their deadline. Payments made stay with the member.
- Test accounts without UniQdata store generated test readings, labelled `generated_test`.

## API

| method | path | who |
|---|---|---|
| GET | `/api/contracts` | anyone: terms and member counts, no identities, never the invite code |
| POST | `/api/contracts` | posting code: `{terms, researcher_key}` → `{contract, invite_code, researcher_sub, ethics_credential}` |
| GET | `/api/contracts/{cid}` | anyone |
| POST | `/api/contracts/{cid}/join/start` | invite code: `{invite_code, public_key, items?, automation, uniqdata_account?}` → `{pid, consent, consent_hash, sign}` |
| POST | `/api/contracts/{cid}/join/complete` | the joiner: `{pid, signature, generate_test_weeks?}` (signature over `sign`) |
| GET | `/api/contracts/{cid}/console` | researcher of that contract |
| POST | `/api/contracts/{cid}/rounds` | researcher: `{week}` |
| POST | `/api/contracts/{cid}/close` | researcher |
| GET | `/api/p/{pid}/contracts` | the member |
| POST | `/api/p/{pid}/contracts/records` | the member: `{records: [{item, day, value}], generate_test_weeks}` |
| POST | `/api/p/{pid}/contracts/{cid}/requests/{rid}/approve` | the member: `{items, signature}` |
| POST | `/api/p/{pid}/contracts/{cid}/withdraw` | the member: `{signature}` |

Sign-in is the engine's usual challenge: `POST /api/auth/challenge {sub}`, sign
`agentrail-login|agentrail-api|{sub}|{nonce}`, `POST /api/auth/token`. The researcher's `sub` is
`researcher@{cid}`; a member's `sub` is their `pid`.

### `GET /api/p/{pid}/contracts` (the 연구 기여 tab's shape)

```json
{"person": "RC1-3b12dcf5", "unit": "USD", "display_unit": "RLUSD", "ledger": "testnet",
 "active_institutions": 1, "settled_drops": 800000, "held_drops": 0,
 "contracts": [{"contract": "RC1-e5fc3b", "title": "...", "institution": "...",
   "items": ["sleep.daily", "fatigue.survey"], "automation": "confirm_each", "status": "active",
   "consent_hash": "…", "pending_approvals": [{"request_id": 3, "week": 2, "kind": "round", "items": ["…"]}],
   "settled_drops": 800000, "held_drops": 0, "latest_tx": {"tx": "…", "url": "https://testnet.xrpl.org/transactions/…"}}],
 "history": [{"contract": "RC1-e5fc3b", "institution": "...", "study": "...", "order_id": 12,
   "status": "delivered", "amount_drops": 800000, "slot": "RC1-3b12dcf5|week1",
   "escrow_create": {"tx": "…", "url": "…"}, "escrow_finish": {"tx": "…", "url": "…"}, "escrow_cancel": {"tx": null, "url": null}}]}
```

Amounts are millionths of the settlement unit; show `display_unit` with the Testnet footnote.

## UniQdata

For members who joined with a UniQdata account, every round, approval and withdrawal reports that
member's orders to their own UniQdata account with their session:
`PUT /api/v1/research/agentrail/settlements` (UniQdata backend, `feat/agentrail-settlement-records`).
The app reads `GET /api/v1/research/agentrail/settlements`: one row per order (held → settled updates the
same row), and server totals (`settled_micro`, `held_micro`, `active_institutions`, per-institution cards
with the latest tx). Test networks only.
