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

Live sync: poll `GET /api/events?after=<last id>` every second; refetch the page's main GET when
anything new arrives.

## Shared

`POST /api/reset?ledger=mock|testnet` - new world (50 synthetic participants, study set up).

`GET /api/events?after=0` ->
```json
{"events": [{"id": 12, "scene": "H", "actor": "org_sleeplab", "kind": "spec", "message": "...",
             "data": {}, "tx": "ABC...", "url": "https://testnet.xrpl.org/transactions/ABC..."}],
 "last": 12}
```

`GET /api/boundaries` -> the boundary checklist (consent, re-identification, withdrawal, other
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
    "reward_xrp": 0.6, "settlement": "escrow, released when your agent publishes the key"
  }],
  "timeline": {"weeks": [1,2,3,4,5,6,7,8],
               "rows": [{"item": "sleep.daily", "label": "Sleep", "source": "wearable",
                         "cells": [{"week": 1, "state": "held|requested|contributed|escrowed|missing|blocked",
                                    "tx": null, "url": null}]}]},
  "contributions": [{"order_id": 31, "weeks": [3,4,5], "items": ["fatigue.survey"], "amount_xrp": 0.6,
                     "status": "escrowed|delivered|withheld|refunded",
                     "escrow": {"tx": "...", "url": "..."}, "finish": {"tx": "...", "url": "..."},
                     "cancel": {"tx": null, "url": null}, "consent_hash": "..."}],
  "licence": {"mpt_id": "...", "held_by_study": true, "txs": [{"kind": "MPTokenIssuanceCreate", "tx": "...", "url": "..."}],
              "clawback": null},
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
items; the agent contributes them (escrow created by the lab, key published, reward paid,
licence issued on the first contribution). Returns the updated `GET /api/p/{pid}`.

`POST /api/p/{pid}/requests/{id}/decline` -> withdrawal 1: decline this round. Nothing leaves,
nothing on the ledger.

`POST /api/p/{pid}/pause` body `{"study": "org_sleeplab"}` -> withdrawal 2: stop future supply.
Past contributions and payments stay. `POST /api/p/{pid}/resume` undoes it.

`POST /api/p/{pid}/revoke` body `{"study": "org_sleeplab"}` -> withdrawal 3: data access consent
revoked. Licence MPT clawed back (tx), undelivered escrowed rounds withheld and refunded to the lab
after their deadline (tx), consent history kept. Returns
`{"clawback": {"tx", "url"}, "withheld": [order ids], "refunds": [{"order_id", "tx", "url"}], "kept": "..."}`.

## Researcher console

`GET /api/study` ->
```json
{
  "study": {"id": "org_sleeplab", "name": "...", "protocol": "...", "purpose": "sleep_research",
            "duo": [...], "credentials": [{"kind": "ethics_review", "tx": "...", "url": "..."}],
            "treasury": {"address": "r...", "multisig": true, "quorum": 2, "signers": ["owner", "compliance"]},
            "budget_xrp": 80, "spent_xrp": 0, "reserved_xrp": 0},
  "goal": "free text the researcher typed",
  "heatmap": {"weeks": [...], "rows": [{"person": "P-001", "cells": [{"s": "held|bought|waiting|missing", "tx": null}]}],
              "complete_pairs": 280, "total": 400, "power": 0.65},
  "power_target": 0.8,
  "proposal": {"source": "llm|rules", "hash": "...", "raw": {}, "verdict": "accepted|narrowed|rejected",
               "gaps": {"fatigue.survey": [3,4,5]}, "evidence": {}, "notes": ["..."],
               "people": 36, "cells": 75, "budget_xrp": 40, "summary_for_participants": "..."},
  "spec_status": "none|draft|approved|sent",
  "approval": {"signers": ["owner", "compliance"], "tx": "...", "url": "..."},
  "responses": {"auto": 30, "approval": 14, "blocked": 0, "people": [{"person": "P-008", "class": "approval", "items": [...]}]},
  "contributions": [{"order_id": 31, "person": "P-017", "pseudonym": "S-...", "weeks": [3,4,5], "amount_xrp": 0.6,
                     "status": "...", "escrow": {}, "finish": {}, "cancel": {}, "bundle_hash": "...",
                     "verified": true, "rows": 21}],
  "settlement": {"paid_xrp": 21.0, "refunded_xrp": 0.6, "people_paid": 35, "export_fees_xrp": 0.1}
}
```

`POST /api/study/goal` body `{"goal": "..."}` -> LLM proposes gaps from the coverage table and
analysis note; code recomputes and narrows. Sets `spec_status = draft`.

`POST /api/study/approve` body `{"signers": ["owner", "compliance"]}` -> co-signed approval of
the spec budget (multi-signed top-up from the treasury to the agent account). One signer is
refused by the ledger (`tefBAD_QUORUM`), shown as an error.

`POST /api/study/send` -> participation requests to every participant in the spec. Their agents
answer: auto, needs the person, or blocked. Auto ones contribute right away.

`POST /api/study/sweep` -> refund escrows whose deadline passed (withheld rounds).

`GET /api/study/bundle/{order_id}` -> the lab opens a delivered bundle with the key read from the
ledger: `{"rows": [...], "bundle_hash": "...", "hash_matches_memo": true, "fulfillment_tx": "..."}`.
