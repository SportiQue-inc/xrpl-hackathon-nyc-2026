# Engine API for the two app pages

One FastAPI process (`uvicorn agentrail.web:app`) serves both pages and the dashboard. Both pages
read the same engine and the same ledger, so an action on one page shows on the other at the next
poll. All data is synthetic. Amounts are XRP (floats); tx links are explorer URLs (Testnet) or
`null` on the mock ledger.

| Page | Path | Who |
|---|---|---|
| Participant app: research participation request | `/participant?pid=P-017` | one participant (their personal agent) |
| Researcher console | `/console` | the sleep lab (research agent) |
| Dashboard (judges) | `/` | everything, plus the boundary checklist |

Pages are static files the UI owner drops in: `apps/participant/index.html` is served at
`/participant`, `apps/researcher/index.html` at `/console`. Every endpoint below is live on
branch `claude/project-thread-vfr62v` and covered by `tests/test_study.py`.

Typical demo order: `POST /api/reset` -> console `goal` -> `approve` (one signer, refused) ->
`approve` (two signers) -> `send` -> phone `GET /api/p/P-017` -> `preview` -> `approve` ->
console sees the contribution -> `POST /api/run/boundaries` (or phone `revoke`) ->
`POST /api/study/sweep` for the refund.

Live sync: poll `GET /api/events?after=<last id>` every second; refetch the page's main GET when
anything new arrives.

## Sign-in (every call)

Every `/api/*` call except the two login calls needs `Authorization: Bearer <token>`; without it
the answer is 401, with the wrong role or another person's record 403. Who may call which route:
`agentrail/security/rbac.py`; design: [SECURITY.md](SECURITY.md).

1. `POST /api/auth/challenge {"sub": "P-017"}` -> `{"nonce", "expires_in": 120, "aud"}`
2. The device signs `agentrail-login|agentrail-api|<sub>|<nonce>` (Ed25519, hex).
3. `POST /api/auth/token {"sub", "nonce", "signature"}` -> `{"access_token", "expires_in": 900, "role", "scope"}`

`GET /api/auth/me`, `POST /api/auth/logout`. Demo (dev mode, localhost): `POST /api/dev/login/{sub}`
returns a token for a simulated device, e.g. `P-017`, `researcher@org_sleeplab`,
`approver:owner@org_sleeplab`, `operator`.

Treasury approval: `POST /api/study/approvals` (researcher) -> approval with the unsigned tx;
each approver `POST /api/study/approvals/{aid}/signatures {"signer", "signed_tx"}` (XRPL multisign blob; mock ledger: `{"signer", "public_key", "signature"}`); executed when the
quorum is met. New consent after withdrawal: `POST /api/p/{pid}/consent` with the device signature
over the consent document hash. Audit: `GET /api/ops/audit/verify`, `POST /api/ops/audit/anchor`.

## Shared

`POST /api/reset?ledger=mock|testnet` - new world (50 synthetic participants, study set up).

`GET /api/events?after=0` ->
```json
{"events": [{"id": 12, "scene": "H", "actor": "org_sleeplab", "kind": "spec", "message": "...",
             "data": {}, "tx": "ABC...", "url": "https://testnet.xrpl.org/transactions/ABC..."}],
 "last": 12}
```

`POST /api/run/boundaries` -> runs every boundary check on the current study (sets the study up
first if needed) and returns the same shape as `GET /api/boundaries`.

`GET /api/boundaries` -> `{"issues": [{"id": "consent|reidentification|withdrawal|other_domains",
"title", "problem", "solution", "enforced": [..], "moment", "tests": [..], "evidence": [{"label", "tx"?,
"url"?, "result"?, ...}]}], "ledger"}`: the boundary checklist (consent, re-identification, withdrawal, other
domains), each with problem, solution, where it is enforced, demo moment and evidence
(test names and tx links filled in as scenes run).

## Participant app

`GET /api/p/{pid}` ->
```json
{
  "person": {"id": "P-017", "address": "r...", "study_pseudonym": "S-1a2b3c4d"},
  "requests": [{
    "id": 7, "status": "open|decided",
    "institution": {"id": "org_sleeplab", "name": "Sleep & Fatigue Lab (synthetic)",
                    "badges": [{"kind": "ethics_review", "label": "Ethics review approved",
                                "issuer": "org_ethics", "tx": "...", "url": "..."},
                               {"kind": "verified_org", "label": "Verified organization", "tx": "...", "url": "..."}]},
    "summary": "LLM-written two-sentence reason for asking (source: llm|rules)",
    "summary_source": "llm",
    "purpose": "sleep_research",
    "duo": [{"code": "DUO:0000006", "label": "HMB - health or medical or biomedical research"}],
    "items": [{"item": "fatigue.survey", "label": "Fatigue survey", "weeks": [3, 4, 5],
               "source": "survey_app", "class": "auto|approval|blocked", "reason": "..."}],
    "reward_xrp": 0.6, "settlement": "escrow, released when your agent publishes the key",
    "partial_data_plan": "If you withdraw, person-level copies are destroyed ...",
    "international_transfer": {"planned": false, "countries": [], "recipients": [], "purpose": null,
                               "items": [], "retention": null, "notice": "..."},
    "identity": "The study gets your participant number and the items you agree to ...",
    "records": "Access records are kept 2 years, permission changes 3 years.",
    "if_you_stop": [{"kind": "decline_round|pause|revoke", "label": "Skip this round", "effect": "..."}]
  }],
  "timeline": {"weeks": [1,2,3,4,5,6,7,8],
               "rows": [{"item": "sleep.daily", "label": "Sleep", "source": "wearable",
                         "cells": [{"week": 1, "state": "held|requested|contributed|escrowed|withheld|refunded|missing|not_in_protocol",
                                    "tx": null, "url": null}]}]},
  "gaps": [{"week": 4, "item": "heart_rate.daily", "reason": "LLM reason", "verdict": "kept|removed",
            "code_reason": "empty in the coverage table", "source": "llm|rules"}],
  "contributions": [{"order_id": 31, "weeks": [3], "items": ["fatigue.survey"], "amount_xrp": 0.6,
                     "status": "escrowed|delivered|withheld|refunded",
                     "escrow": {"tx": "...", "url": "..."}, "finish": {"tx": "...", "url": "..."},
                     "cancel": {"tx": null, "url": null}}],
  "licence": {"mpt_id": "...", "held_by_study": true, "txs": [{"kind": "MPTokenIssuanceCreate", "tx": "...", "url": "..."}],
              "clawback": null},
  "withdrawals": [{"kind": "decline_round|pause|revoke", "ts": 0, "ledger": "what happened on the ledger"}],
  "export_fees": [{"amount_xrp": 0.1, "tx": "...", "url": "...", "ok": true}],
  "consent": {"version": 3, "status": "active|paused|revoked", "automation": "auto_all",
              "items": ["..."], "duo": ["DUO:0000006"], "doc_hash": "...",
              "history": [{"version": 1, "status": "active", "doc_hash": "...", "ts": 0}]}
}
```

`GET /api/p/{pid}/preview?request={id}` -> the rows that would leave the person's device for
that request: study pseudonym, shifted days, requested items only.
```json
{"pseudonym": "S-1a2b3c4d", "day_shift_hidden": true, "rows": [{"person": "S-1a2b3c4d", "day": 104, "fatigue.survey": {"score_0_10": 4}}],
 "withheld_items": ["blood_pressure.daily"], "sealed_for": "org_sleeplab"}
```

`POST /api/p/{pid}/requests/{id}/approve` body `{"items": ["fatigue.survey"]}` -> person ticks
items; the agent contributes them, one escrow per week (created by the lab, key published,
reward paid, licence issued on the first contribution). The last week is held in escrow until the
round closes (`POST /api/study/close-round`), so a revoke in between shows the refund path.
Returns the updated `GET /api/p/{pid}`.

`POST /api/p/{pid}/requests/{id}/decline` -> withdrawal 1: decline this round. Nothing leaves,
nothing on the ledger.

`POST /api/p/{pid}/pause` body `{"study": "org_sleeplab"}` -> withdrawal 2: stop future supply.
Past contributions and payments stay. `POST /api/p/{pid}/resume` undoes it.

`POST /api/p/{pid}/revoke` body `{"study": "org_sleeplab"}` -> withdrawal 3: data access consent
revoked. Licence MPT clawed back (tx), undelivered escrowed rounds withheld and refunded to the lab
after their deadline (tx), consent history kept. The agent sends the study a deletion request; the
study destroys every person-level copy (contributed bundles, its own cells for that participant) and
confirms (`deletion_request` and `deletion_confirmed` events). Only aggregate statistics remain; the
participant's heatmap row shows `withdrawn`. Returns
`{"clawback": {"tx", "url"}, "withheld": [order ids], "refunds": [{"order_id", "tx", "url"}],
"deletion": {"bundles_destroyed", "cells_destroyed", "confirmation_hash"}, "kept": "..."}`.

## Researcher console

`GET /api/study` ->
```json
{
  "study": {"id": "org_sleeplab", "name": "...", "ledger": "mock|testnet", "protocol": "...", "purpose": "sleep_research",
            "duo": [...], "credentials": [{"kind": "ethics_review", "tx": "...", "url": "..."}],
            "treasury": {"address": "r...", "multisig": true, "quorum": 2, "signers": ["owner", "compliance"]},
            "budget_xrp": 80, "spent_xrp": 0, "reserved_xrp": 0},
  "goal": "free text the researcher typed",
  "heatmap": {"weeks": [...], "rows": [{"person": "P-001", "cells": [{"s": "held|contributed|waiting|missing|withdrawn", "tx": null, "url": null}]}],
              "complete_pairs": 280, "total": 400, "power": 0.65, "power_before": 0.65, "pairs_before": 280},
  "power_target": 0.8,
  "proposal": {"source": "llm|rules", "hash": "...", "raw": {}, "verdict": "accepted|narrowed|rejected",
               "gaps": {"fatigue.survey": [3,4,5]}, "evidence": {}, "notes": ["..."],
               "claims": [{"item": "fatigue.survey", "weeks": [3,4,5], "llm_evidence": "w3 16/50 ...",
                           "verdict": "kept|narrowed|removed", "kept_weeks": [3,4,5], "code_reason": "table: w3 16/50, ..."}],
               "person_claims": {"P-017": [{"week": 4, "item": "heart_rate.daily", "verdict": "kept", "code_reason": "..."}]},
               "people": 36, "cells": 75, "budget_xrp": 40, "summary_for_participants": "..."},
  "spec_status": "none|draft|approved|sent",
  "approval": {"signers": ["owner", "compliance"], "tx": "...", "url": "..."},
  "responses": {"auto": 30, "approval": 14, "blocked": 0, "declined": 0,
                "people": [{"person": "P-008", "class": "approval", "status": "open", "items": [...], "reason": "outside your consent"}]},
  "contributions": [{"order_id": 31, "person": "P-017", "pseudonym": "S-...", "weeks": [3,4,5], "amount_xrp": 0.6,
                     "status": "...", "escrow": {}, "finish": {}, "cancel": {}, "bundle_hash": "..."}],
  "licences": {"P-017": {"mpt_id": "...", "clawed_back": false}},
  "settlement": {"paid_xrp": 21.0, "refunded_xrp": 0.6, "people_paid": 35, "export_fees_xrp": 0.1}
}
```

`POST /api/study/goal` body `{"goal": "..."}` -> LLM proposes gaps from the coverage table and
analysis note; code recomputes and narrows. Sets `spec_status = draft`.

`POST /api/study/approve` body `{"signers": ["owner", "compliance"]}` -> co-signed approval of
the spec budget (multi-signed top-up from the treasury to the agent account). One signer is
refused by the ledger; HTTP 200 with `{"ok": false, "engine_result": "tefBAD_QUORUM" (mock) or
"tefBAD_SIGNATURE" (Testnet), "signers": [...], "message": "..."}`. Success: `{"ok": true, ...GET /api/study}`.

`POST /api/study/send` -> participation requests to every participant in the spec. Their agents
answer: auto, needs the person, or blocked. Auto ones contribute right away.

`POST /api/study/close-round` -> participants' agents publish the keys of held rounds (rewards
paid, bundles open). A revoked participant's held round is withheld instead.

`POST /api/study/sweep` -> `{"refunded": [order ids]}`. On the mock ledger the clock jumps past the
deadline; on Testnet call it again after the deadline (2 minutes). Refund escrows whose deadline passed (withheld rounds).

`GET /api/study/bundle/{order_id}` -> the lab opens a delivered bundle with the key read from the
ledger: `{"ok": true, "rows": [...], "bundle_hash": "...", "hash_matches": true, "key_from": {"tx", "url"}}`.
Before the key is on the ledger: `{"ok": false, "message": "..."}`.

## Pay in two parts, review, penalties

Each round pays 80% with each week's key-reveal escrow (`amount_xrp` on contributions is that 80%).
The other 20% of the round is held in its own escrow (`kind: "round"`) until the review ends; the
default is to pay. A completion bonus (`kind: "bonus"`) is a separate escrow on the followed
participant's request. Mock ledger: review 7 days, +14 days if fraud is suspected, response period
3 days. Testnet: the same steps in seconds (`HOLDBACK_REVIEW_S`, `HOLDBACK_EXTEND_S`,
`HOLDBACK_GRACE_S`, `HOLDBACK_RESPOND_S`, `BONUS_WINDOW_S`).

Request card adds:
```json
"payment": {"immediate_pct": 80, "held_pct": 20, "review": "7 days", "extension_if_fraud_suspected": "14 days",
            "text": "...", "you_can_always_stop": "Declining or withdrawing never affects ...",
            "trust_on_ledger": "Trust information is never written to the public ledger."},
"completion_bonus_xrp": 0.2
```

`GET /api/p/{pid}` and `GET /api/study` add `payout`:
```json
{"split": {"immediate_pct": 80, "held_pct": 20},
 "holdbacks": [{"id": 3, "person": "P-017", "kind": "round|bonus", "request_id": 1, "amount_xrp": 0.04,
                "status": "held|suspected|earned|released|withheld|returning|returned",
                "review": "pass | signals found | pass: data destroyed on withdrawal ... | fraud confirmed",
                "create": {"tx", "url"}, "release": {"tx", "url"} | null, "return": {"tx", "url"} | null}],
 "cases": [{"id": 1, "person": "P-047", "signals": [{"code": "impossible_value|copied_series", "item": "...",
            "week": 4}], "status": "suspected|confirmed|cleared", "respond_by": 0, "response": null,
            "reviewer_id": null}],
 "automatic_requests": "on|paused",             // participant view only; trust level is never returned
 "repayment_claims": [{"person", "case_id", "amount_drops", "status": "recorded"}]   // console only
}
```
The participant also sees `integrity_notice` lines in `/api/events` (why the part is held, by when to respond).

- `POST /api/study/payout/release` -> `{"released": [...], "returned": [...], "waiting": [...]}`. On the
  mock ledger the clock moves to the next due time (never past an undecided case's payment).
- `POST /api/study/cases/{id}/decide` body `{"reviewer_id": "reviewer-1", "confirm": true}`. Refused
  without a reviewer id, and refused to confirm before `respond_by`. Confirm: held part withheld
  (returned after its deadline), excluded for 180 days, repayment claim recorded off the ledger.
  `confirm: false` clears the case and the held part is paid.
- `POST /api/p/{pid}/cases/{id}/respond` body `{"text": "..."}`.
- `POST /api/p/{pid}/resume-requests`: one tap after two missed accepted rounds paused automatic requests.

## Robot scene (other domains)

`POST /api/run/a-guarded` then `GET /api/state` (`orders` with tx `url`, `events`). Same engine,
consent layer replaced by seller licence terms.

## Agent Cards (A2A v1.0 shape)

`GET /.well-known/agent-card.json` (research agent), `GET /agents/{pid}/.well-known/agent-card.json`
(personal agent). Events from agent dialogue carry `data.a2a = {"method": "SendMessage", "taskState":
"TASK_STATE_INPUT_REQUIRED|TASK_STATE_REJECTED|TASK_STATE_WORKING|TASK_STATE_SUBMITTED", "message": {...}}`.

## Signed delegation

Each order of a buyer with an owner-signed mandate has a row in `mandate_actions` (L1, L2, L3, hash,
verdict). Events of kind `mandate` show when the owner signs; a refused order's note starts with
`mandate check failed:`. The memo of its escrow or payment ends with `|mandate:<hash>`.
