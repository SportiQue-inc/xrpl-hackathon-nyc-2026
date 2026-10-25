# Research contracts: posted, joined, traded

`agentrail/research_contracts.py`. A contract is a record, not code. The researcher posts the terms; each
person joins with their own key and signs the consent document; at each round every member's agent
answers from that member's own consent and data; payment is a key-reveal escrow on the ledger.

The demo study (`org_sleeplab`, the 50 fixture participants, `/api/study/*`) is unchanged and separate.
Contracts keep their own store, so `/api/reset` does not touch them.

## Run it

| env | meaning |
|---|---|
| `AGENTRAIL_CONTRACTS_DB` | SQLite file for contracts, members, orders. Default: `$RAILWAY_VOLUME_MOUNT_PATH/contracts.db` on a Railway volume, otherwise a temp file lost on restart |
| `AGENTRAIL_CONTRACTS_WALLETS` | Testnet wallet labels for institutions and members. Default: `contracts.wallets.json` on the volume |
| `AGENTRAIL_POSTING_CODE` | at least 8 characters; `POST /api/contracts` from anywhere but localhost needs it in `X-Posting-Code` |
| `LEDGER` | `mock` or `testnet` (same as the engine) |
| `UNIQDATA_ROSTER` | optional: UniQdata accounts members may join with (`uniqdata_account`); their vault reads that account and their payments are reported to it |
| `AGENTRAIL_KEYSTORE` | keeps institution box keys and member keyrings across restarts. Default: `keystore/` on the volume |
| `AGENTRAIL_CONTRACTS_PAY` | `ledger` (default: the XRPL escrow pays) or `ap4m`: every delivered member-week is paid through the AP4M rail (`agentrail/ap4m_rail.py`, `AP4M_RAIL_URL`, `AP4M_RAIL_TOKEN`) |
| `AGENTRAIL_CONTRACTS_AUTORUN` | `0` turns the automatic rounds off (default on) |

## Automatic rounds

A contract posted with `round_every_s` runs itself: that many seconds after posting (then after each
round) the institution's agent asks every member's agent for the next week, each member's agent answers
from that member's own consent, and each delivered week is paid at once. After the last week the contract
closes. Nobody runs a script per payment. `60` makes a recordable demo; `604800` is weekly.

## AP4M payments

With `AGENTRAIL_CONTRACTS_PAY=ap4m` a contract is posted with `payment_rail: "ap4m"` in its terms, and:

- one payment per delivered member-week, price per item x items, at most 0.10 RLUSD (refused at posting
  otherwise), from the `research` pool of the rail's budget;
- the ref is `rc-{contract}-{order}`, so a retry never pays twice; a payment that does not go through
  (rail down, budget used up) shows as "pending" with its reason and is tried again at the next round;
- AP4M has one merchant per team, so the payment lands in the team's merchant wallet. A member who
  joined with `payout_address` (XRPL EVM) gets it forwarded there by the rail, with its own tx link;
  otherwise it stays in the team wallet and is credited to the member here. Both are shown as such;
- the data key still moves through the engine's key-reveal escrow on the lane's ledger (on `mock`, that is
  a delivery record, not a payment). The amount shown is the amount paid through AP4M;
- a withdrawal has nothing to refund: nothing is paid before delivery, and later weeks are not delivered.

Pages: `/apps/contracts/post.html` (researcher: post, invite link, run a week, members and orders with
ledger links) and `/apps/contracts/join.html?contract=…&invite=…` (participant: Ed25519 key made in the
browser with WebCrypto, sign the consent, approve a waiting week, withdraw).

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
| POST | `/api/contracts/{cid}/join/start` | invite code: `{invite_code, public_key, items?, automation, uniqdata_account?, payout_address?}` → `{pid, consent, consent_hash, sign}` |
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
