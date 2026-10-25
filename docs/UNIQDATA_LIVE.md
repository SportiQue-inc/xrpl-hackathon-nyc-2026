# UniQdata live connection: upload -> personal DB -> trade

The followed participant (`P-017`) keeps their records in a real UniQdata account. The records
are written through UniQdata's own API into UniQdata's database, and the engine's personal agent
reads them back from there when the study asks. Nothing about the person is stored in the engine
before the trade. Everything is synthetic, and UniQdata runs as its own local sandbox on the Mac.

```
participant app ──POST /api/p/P-017/data/upload──► engine ──/api/v1/data/write/batch──► UniQdata (Postgres)
participant app ──GET  /api/p/P-017/data─────────► engine ──/api/v1/data/query──────────► UniQdata
researcher goal -> request -> preview ("from": UniQdata record hashes) -> approve -> Escrow -> key -> delivery
```

Each UniQdata call that touches health data is approved with the person's passkey. UniQdata
returns a challenge bound to that exact request, the person's agent signs it, and the same request
is sent again. A sensitive-health collection consent (`sensitive_health_collection`, approved
through UniQdata's consent API) must be active before any write.

## Endpoints for the "My data" screen

Both endpoints use the same auth rule as `GET /api/p/{pid}`: the participant themself.

### `GET /api/p/{pid}/data`: what the person's UniQdata holds (counts only, no values)

```json
{
  "person": "P-017",
  "system": "UniQdata",
  "connected": true,
  "base_url": "http://localhost:8001",
  "records": 180,
  "period": {"from": "2026-09-07", "to": "2026-11-01"},
  "sources": [
    {"source": "wearable", "items": [
      {"item": "heart_rate.daily", "label": "Resting heart rate (wearable)", "days": 56, "records": 56,
       "weeks": [1, 2, 3, 4, 5, 6, 7, 8]}
    ]},
    {"source": "survey_app", "items": [
      {"item": "fatigue.survey", "label": "Fatigue survey", "days": 8, "records": 8, "weeks": [1, 2, 3, 4, 5, 6, 7, 8]}
    ]},
    {"source": "clinic_export", "items": [
      {"item": "blood_pressure.daily", "label": "Blood pressure (clinic visit)", "days": 2, "records": 4, "weeks": [2, 4]}
    ]}
  ],
  "sharing": "Stored in your UniQdata account. Nothing is shared until you approve a request."
}
```

Before any upload, `records` is 0, `period` is null, and each source has `items: []`. The
response is 404 when no UniQdata account is connected (the engine was started without
`UNIQDATA_PERSON`).

### `POST /api/p/{pid}/data/upload`: the person stores synthetic records in UniQdata

The body is optional. By default it uploads all five items for weeks 1-8.
```json
{"weeks": [1, 2, 3, 4, 5, 6, 7, 8], "items": ["heart_rate.daily", "fatigue.survey", "sleep.daily",
                                              "activity.daily", "blood_pressure.daily"]}
```
It returns `{"written": 180, "receipts": [{"record_id": "...", "record_hash": "..."}], ...same as GET /data}`.
`receipts` lists the first five UniQdata record ids and hashes. Records that are already stored
are not written again, so a second call writes 0.

### How a stored record becomes a trade

- Participant `pid` = `P-017`, study id = `org_sleeplab`. The demo order is unchanged:
  `POST /api/study/goal` -> approve -> `POST /api/study/send` -> `GET /api/p/P-017`.
- The study's gap reading only offers what the person's UniQdata holds (`sources_hold`), so upload
  first, then run the goal.
- `GET /api/p/P-017/preview?request={id}` now has
  `"from": {"system": "UniQdata", "records": 12, "record_hashes": ["..."]}`: the UniQdata records
  behind the rows that would leave.
- On approval the agent reads the rows from UniQdata for each week. The event feed shows
  `uniqdata_upload` and `uniqdata_read` (record count and a hash of the record hashes) next to the
  escrow, key and delivery events.

## Run it on the Mac

1. UniQdata sandbox, from a clone of `UniQdata/backend` main. It needs a gitignored
   `.env.sandbox.local` with local-only values: `DATABASE_MODE=dev`, `DATABASE_SSL=false`, the
   `UNIQDATA_DB_*` and `VOCAB_DB_*` settings pointing at the `postgres` service, a random
   `JWT_SECRET`, and `REDIS_URL=redis://redis:6379/0`.
   ```
   docker compose -p uniqdata-hk -f docker-compose.sandbox.yml up -d --build
   docker exec uniqdata-hk-postgres-1 psql -U core_app -d uniqdata_sandbox_db -c 'CREATE DATABASE uniqdata_sandbox_db_dev'
   docker cp scripts/sandbox_bootstrap.py uniqdata-hk-core-1:/tmp/ && docker exec -w /app -e PYTHONPATH=/app uniqdata-hk-core-1 python /tmp/sandbox_bootstrap.py
   docker restart uniqdata-hk-core-1
   ```
2. A fresh synthetic person. Run this once per recording, so the upload starts from an empty account:
   `python scripts/uniqdata_sandbox_person.py` (writes the gitignored `.uniqdata_person.json`).
3. Engine: `UNIQDATA_PERSON=.uniqdata_person.json uvicorn agentrail.web:app`.
4. Check: `UNIQDATA_PERSON=.uniqdata_person.json pytest tests/test_uniqdata_live.py` (a fresh person is needed).

Limits: signup is not part of the flow. UniQdata's signup needs email codes and identity
providers that the sandbox does not have, so the person's account row and first session token
are created inside the sandbox container, as UniQdata's own sandbox scripts do. Everything after
that goes through UniQdata's public API: the passkey, the consent, and the writes and reads.
Sleep has no concept that UniQdata accepts without a vocabulary load, so it is stored as
UniQdata's generic typed answer, with the item named in `source_value`.

## The whole cohort on UniQdata (50 accounts)

- `python scripts/uniqdata_sandbox_person.py --cohort --out .uniqdata_roster.json` creates one
  UniQdata account per cohort participant (P-001 to P-050). Each account gets its agent's
  passkey and an approved sensitive-health collection consent. The approval goes through
  UniQdata's consent-signing ceremony: the passkey signs a challenge derived from the consent's own
  hash, and UniQdata verifies the signature.
- `python scripts/uniqdata_fill_cohort.py [--catalog]` writes eight weeks of synthetic records
  into each account. The first pass covers sleep, heart rate, steps, the weekly survey and clinic
  blood pressure. Wear adherence differs per person, about one in five people wear the device less
  and less after week 4, and about one in ten have bad records: a flat heart-rate week, implausible
  readings, or a survey answered twice. `--catalog` adds the T0-T3 catalog:
  - T0: SpO2, weight and temperature
  - T1: meals, medication taken, mood and energy
  - T2: glucose, HbA1c, diagnoses and prescriptions
  - T3: PHQ-9, genomic variants and CT/MRI metadata

  Each person also gets a pre-consent tier: T0-T3, T0-T2, T0-T1 or T0. UniQdata allows ten writes
  a minute, so the script paces itself.
- `UNIQDATA_ROSTER=.uniqdata_roster.json` makes every participant's vault read from their own
  UniQdata account.
- `AGENTRAIL_KEYSTORE=runs/keystore python scripts/fund_participant_wallets.py` gives each
  participant their own Ed25519 XRPL Testnet wallet, funded from the faucet. The same key signs
  their consent documents and logins, and on Testnet the rewards go to that wallet. Seeds stay in
  the keystore and only the addresses are written to `.participant_wallets.json`.

The participant page's passkey approval relays six calls to UniQdata through `UniQdataClient`
(see `docs/passkey-approval-contract.md`). When the account already has its agent's passkey, a
person's own Touch ID passkey is added through UniQdata's managed path, which the existing passkey
approves, and the engine accepts an approval only when it is signed by that Touch ID credential.
