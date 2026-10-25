# Security design and limits

What the service enforces today, how to run it in production mode, which attacks the tests
reproduce, and what is still missing before real participants and real money. Code is in
`agentrail/security/`; attack tests are in `tests/test_security.py`.

## 1. Who can call what

Every API call needs a short-lived token, except the two login calls. Access is decided in one
place (`security/rbac.py`, `POLICY`) for every route; a route without a rule answers **403
(default deny)**, and a test fails if any route has no rule.

| Role | Scope in the token | May |
|---|---|---|
| participant | their participant id | their own requests, preview, approve / decline, pause / resume, withdraw, new consent, their own integrity cases |
| researcher | study id | goal, requests, rounds, payouts, sealed bundles of that study, open a treasury approval, events |
| approver | study id + signer name | sign a treasury approval on their own device |
| reviewer | study id | decide integrity cases, only under their own name |
| operator | `*` | dashboard state, audit verification and anchoring, demo harness (dev only). Cannot open bundles or act for anyone |

`/api/p/{pid}/...` checks that `pid` equals the token's scope, so a participant cannot read or act
on someone else's record, and no other role can act for a participant.

**Login** (`security/auth.py`): no passwords. `POST /api/auth/challenge {sub}` gives a single-use
nonce (120 s, same answer for unknown subjects). The device signs
`agentrail-login|agentrail-api|<sub>|<nonce>` with its enrolled Ed25519 key and sends it to
`POST /api/auth/token`, which returns an HS256 JWT (15 min, `iss`/`aud`/`exp`/`nbf`/`jti`). Tokens
with another `alg` (including `none`) are refused; `POST /api/auth/logout` puts the `jti` on a deny
list; a token stops working if the identity's role or scope changes.

Enrolment: in the demo the server enrols the synthetic staff and participants at start. In
production, enrolment comes from the identity provider (UniQdata / UniQLab accounts and device
registration), not from this API.

## 2. Who holds which key

| Key | Holder | Server sees |
|---|---|---|
| Escrow key K per round (PREIMAGE-SHA-256 condition) | participant's keyring (`ParticipantKeyring`) | condition only; K appears on the ledger when the participant's side finishes the escrow |
| Vault secret (HMAC pseudonym per study, private date offset) | participant's keyring | nothing |
| Study's box key (opens sealed bundles) | the institution (`InstitutionVault`) | public key only; sealed bundles are relayed, never opened |
| Treasury SignerList keys | each approver's device (`ApproverDevice`) | public addresses; signatures |
| JWT signing secret | `AGENTRAIL_JWT_SECRET` (env or `_FILE`) | required in prod |

Keys live in a `KeyStore` (`security/keystore.py`): `LocalKeyStore` keeps them in memory or in
files with 0700/0600 under `AGENTRAIL_KEYSTORE`; `KmsKeyStore` is the seam for KMS / HSM and is not
implemented. The tests check that the engine and the ledger object hold no private key of another
party and that K is not in the database.

A withdrawal deletes the gate's sealed bundles and any escrow key it held for that participant,
and the participant's keyring forgets the keys of rounds not yet released, so they can never be
published.

## 3. Treasury approvals (co-sign)

`security/cosign.py`. The researcher opens an approval (`POST /api/study/approvals`); the server
builds the exact unsigned XRPL transaction (fixed `Sequence`, `Fee`, `LastLedgerSequence` +200) with
a nonce and an expiry. Each approver signs **that transaction** on their own device and posts it
to `/api/study/approvals/{aid}/signatures`. The server checks:

- the signer is on the treasury's SignerList and the token belongs to that signer;
- one signature per signer and per person (database unique keys);
- the signature verifies against the transaction (XRPL multisign payload, checked offline);
- the approval is open and not expired; one approval per spec hash, so repeating goal + approval
  cannot drain the treasury, and an old signature cannot sign a new approval.

Only when the quorum is met does the server combine the signatures and submit. On the ledger the
SignerList quorum is enforced again (`tefBAD_QUORUM` with one signer).

## 4. State changes

- Pause / resume / approve / decline: participant token only, own record only.
- A withdrawn participant comes back only through a **new consent signed on their device**
  (`POST /api/p/{pid}/consent`: the device signs the hash of the consent document; the signature is
  stored next to the version in `consent_signatures`).
- Integrity cases: `reviewer_id` must equal the token subject; a participant can respond only to
  their own case.
- Ledger switch through `/api/reset` needs `AGENTRAIL_ALLOW_LEDGER_SWITCH=1`.

## 5. Audit log

Every event row carries `prev_hash` and `hash` (SHA-256 over the previous hash and the row),
computed inside the same INSERT so concurrent writers cannot fork the chain. Every non-GET API call
is recorded as an `access` event with the token subject, route and status.
`GET /api/ops/audit/verify` recomputes the chain and reports the first edited or missing row.
`POST /api/ops/audit/anchor` (and a background thread every `AGENTRAIL_ANCHOR_S`, default 300 s)
writes the chain head to the ledger as an AccountSet memo, so a rewrite of the whole log is also
detectable against the ledger.

## 6. HTTP basics

- Strict request bodies (pydantic strict models, item ids by pattern, length limits, unknown
  fields refused).
- CORS: exact origins from `AGENTRAIL_CORS_ORIGINS`; `*` is never accepted; empty = same origin.
- Rate limit: login 30/min per IP, API 600/min per token.
- Headers: CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: no-referrer`,
  `Cache-Control: no-store` on `/api`, HSTS behind HTTPS.
- Secrets only from env or `NAME_FILE` (secret manager mount); log and event text is masked
  (XRPL seeds, API keys, JWTs, bearer tokens, private-key hex).

## 7. Production mode

```bash
AGENTRAIL_ENV=prod \
AGENTRAIL_JWT_SECRET_FILE=/run/secrets/jwt \
AGENTRAIL_CORS_ORIGINS=https://app.example.org \
AGENTRAIL_KEYSTORE=/var/lib/agentrail/keys \
uvicorn agentrail.web:app --host 0.0.0.0 --port 8000 --proxy-headers
```

In prod the JWT secret is required (start fails without it), `/docs` and `/openapi.json` answer
404, and the demo harness (`/api/reset`, `/api/run/*`, `/api/study/approve`, `/api/dev/*`) is off.

| Variable | Default | Meaning |
|---|---|---|
| `AGENTRAIL_ENV` | `dev` | `prod` closes the harness and requires secrets |
| `AGENTRAIL_JWT_SECRET` / `_FILE` | random per process (dev) | token signing secret, at least 32 bytes |
| `AGENTRAIL_TOKEN_TTL_S` | 900 | access token lifetime |
| `AGENTRAIL_CORS_ORIGINS` | empty | allowed origins, comma separated |
| `AGENTRAIL_RATE_PER_MIN` / `AGENTRAIL_LOGIN_RATE_PER_MIN` | 600 / 30 | rate limits |
| `AGENTRAIL_KEYSTORE` | memory (`.keystore/` for Testnet approvers) | local key files |
| `AGENTRAIL_ANCHOR_S` | 300 | audit anchoring interval |
| `AGENTRAIL_ALLOW_LEDGER_SWITCH` | off | allow `/api/reset?ledger=` |

Demo login: in dev, `POST /api/dev/login/{sub}` (localhost only) signs the challenge with the
simulated device and returns a token; the dashboard uses it, or a token passed as `#token=...`.

## 8. Attacks reproduced

`tests/test_security.py` reproduces each attack. Run against the code before this layer
(`765c374`), the 23 attack tests failed, most because the attack worked; with this layer all pass
(full suite: 114 passed).

| Attack | Before | Now |
|---|---|---|
| Read a decrypted health bundle without signing in | data returned | 401; only the study team, sealed |
| Call any API route without a token | allowed | 401 on every route |
| Forged / `alg:none` / expired / other-audience token | n/a | 401 |
| Replay a login nonce, log in with another device key | n/a | 401 |
| Participant reads or acts on another participant | allowed | 403 |
| Researcher / operator approves or revokes for a participant | allowed | 403 |
| Reactivate a withdrawn participant without them | allowed | only a device-signed consent |
| One person releases the treasury budget | allowed | needs two approvers' own signatures |
| Replay a signature on another approval or after expiry | n/a | 409 / 410 / 400 |
| Drain the treasury by repeating goal + approval | budget raised each time | one approval per spec; old signatures refused |
| Decide a case under another reviewer's name | allowed | 403 |
| Engine holds participants' escrow keys or the study's box key | yes | no |
| Edit or delete an event row | undetected | chain check finds the row |
| State changes without an actor | yes | `access` event with token subject |
| Other origin gets CORS grant / no security headers | yes | no grant; headers set |
| Extra fields / bad item ids in bodies | accepted | 422 |
| Brute-force login | unlimited | 429 |
| Secret in a log message | stored | masked |
| Demo harness in production | open | 404 |

## 9. Limits (what is not done)

- **KMS / HSM**: keys are in local files or memory; `KmsKeyStore` is an interface only.
- **No external penetration test** and no third-party review yet.
- The 50 participants' personal agents run in the same process as the service (simulation). The
  keys are held by separate objects with their own keystores, but a real deployment runs the
  personal agent on the person's device; the participant's XRPL wallet key is still in the demo
  ledger's wallet table.
- Identity enrolment is done by the server at start; production needs the identity provider and
  device registration.
- Rate limits and the token deny list are in memory per process (one instance); several instances
  need a shared store (e.g. Redis).
- The dashboard needs `'unsafe-inline'` in the CSP; the two app pages should move to external
  scripts.
- The operator's `/api/state` still shows consents and events for the judges' dashboard; in
  production it should be reduced to counts.
- Payout review keys (`payout.py`, `review_keys`) are stored in the database in plain hex; they
  should move to the keystore.
- The co-sign path is tested on the mock ledger and with an offline XRPL multisign check; the live
  Testnet run with the new `*_cosign` treasuries is still to be repeated.
- Re-identification risk is reduced (minimization, HMAC pseudonym per study, private date offset,
  quasi-identifier rule), not eliminated.

## 10. Push, not access: why transfer abroad needs it

A subscription or "view right" means an outside party keeps reading the person's store. Many data-localization and cross-border rules restrict exactly that inbound access from abroad, so that model breaks first for an overseas institution. AgentRail never opens the person's store to anyone:
- For each trade, the person's page assembles exactly the agreed columns and days.
- It seals them with a per-trade key K, derived from the passkey's PRF root, and encrypts the result to the institution's registered P-256 key.
- The engine pushes that sealed record into the institution's own store.
- The escrow condition is SHA-256(K). Publishing K pays the person and opens the copy the institution already holds.

What each party holds:

| party | holds | never holds |
|---|---|---|
| person's page | PRF root (only while the passkey is used), K until the reveal | anything of other people |
| engine | sealed records, conditions, tx hashes | K before the reveal, the clear bundle, the root |
| institution | its P-256 private key, the sealed copy, then K from the ledger | the person's store, other trades' keys |

Withdrawal stops future pushes, and a key not yet revealed is never published. For copies already delivered, the engine sends a deletion request that must come back as a signed deletion confirmation, and a missing one is an audit flag. A decrypted copy cannot be force-deleted; expiry for copies is contractual plus audit. Tests: `tests/test_vault.py`.

## 11. Delegation while the phone is off, and T3 view keys

**Delegation** (`vault/delegation.py`):
- One Touch ID signs a grant listing its scopes (tier × purpose × institution class), an end time and a budget. The page wraps one scope key per scope to the person's hosted agent.
- Inside the grant, the hosted agent executes on its own. Outside it, it queues "needs you" for the next time the phone is on.
- T0–T1 can be delegated. T2 can be delegated only with the person's opt-in. T3 is never delegated.
- Revoking signs a new, empty grant version. The agent drops every key at once, and a replayed older grant is refused.
- **Stealing the hosted agent** yields only the delegated scopes, within budget and time, and never T3.

**T3 view keys** (`vault/viewkey.py`):
- There is one keyring per (owner, institution, study): a versioned manifest the owner signed. Adding scope appends wrapped keys and bumps the version. It never mints separate view keys.
- The wrap comes from what the owner signed at consent time. The key service never holds the owner's root.
- A session is bound to the researcher's credential, the IRB credential, the institution and the contract. It makes one keyring fetch; chunk opens are then local lookups, and later scope arrives as a delta.
- Raw export from the workspace is refused; aggregate export is allowed.
- Expired or removed entries are dropped from the next delta, wiped from the cache, and logged. A stale manifest version is refused.

Benchmark (`benchmark()`, opening N chunks after M scope expansions):

| chunks | expansions | keyring: fetches, time | key per request: fetches, time |
|---|---|---|---|
| 60 | 2 | 3, 0.9 ms | 60, 6.6 ms |
| 240 | 5 | 6, 3.2 ms | 240, 57 ms |
| 594 | 10 | 11, 10.5 ms | 594, 296 ms |

These times are in-process. Over a network each fetch is a round trip, so the gap grows with latency.

**The honest limit.** Expiry is technically enforced only where the plaintext stays in the controlled workspace. A T0–T2 copy is decrypted in the buyer's own store and cannot be force-deleted. For copies, expiry is enforced by the contract plus audit: at the end of retention the engine sends a deletion request, and a missing signed confirmation raises an audit flag and opens a penalty case (`CopyLedger`).
