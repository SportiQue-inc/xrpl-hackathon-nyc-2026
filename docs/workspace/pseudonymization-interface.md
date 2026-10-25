# UniQdata pseudonymization / de-identification: existing interfaces

Sources read (read-only):
- **Core backend**: shallow clone of `UniQdata/backend` `main` @ `e6b7999f` (2026-10-25), at `.../scratchpad/uqb`. Paths below are relative to that root unless prefixed.
- **Workspace** `/Users/3mln_xx/Developer/SportiQue` (workspace git `main` @ `f9a54fcd5`; `UniQLab/backend` is its own repo, checked out on branch `codex/uniqlab-fix-all-backend-20260727` @ `6807ec28` (2026-08-13) with a local modification, **not main**, so treat the UniQLab citations as possibly stale).
- No secret values were read. Keys are named only by their setting or env name.

**Bottom line:** there is **no single shared de-identification library**. Core has several purpose-specific mechanisms:
- (A) keyed one-way identity refs: HMAC or salted SHA-256 of `person_id`;
- (B) a per-project sequential participant number plus a keyed hash;
- (C) a fail-closed allowlist projector for external-AI egress, with per-request HMAC pseudonyms, date coarsening, age banding, a regex PII scanner and a clinical k-anonymity floor;
- (D) k=5 suppression on aggregate query surfaces.

Downstream repos (AI services, UniQLab Java, SOVI/Dart) only add regex detectors, column masking and small-cell suppression. Nothing anywhere handles DICOM, and no code does date shifting or noise addition.

---

## 1. Keyed one-way identity refs (Core, `app/core/`)

### 1a. `app/core/research_membership_ref.py` (researcher-lane subject ref)
- `derive_research_membership_ref(person_id: uuid.UUID) -> str` (`:52-57`). This wraps `derive_research_membership_ref_with_secret(person_id: uuid.UUID, secret: str) -> str` (`:60-65`).
- Technique: `HMAC-SHA256(key=secret, msg=PURPOSE || person_id.bytes)`. The purpose is `b"uniqdata-core/uniqlab/research-membership/v1\x00"` (`:21`). The output is base64url without padding, prefixed `rmr_v1_`, giving 50 chars. Validator: `is_research_membership_ref` with regex `^rmr_v1_[A-Za-z0-9_-]{43}$` (`:19-20`, `:68-69`).
- Key: `settings.research_membership_ref_secret` (env `RESEARCH_MEMBERSHIP_REF_SECRET`, `app/core/config.py:757-760`). Production startup is blocked when it is empty or the placeholder (`config.py:4393-4405`, also `:3714-3715`). The key is a plain env secret, not KMS.
- Scope: one key and one purpose for the whole plane. The ref is **stable per person across all studies**, so it is not per-study.
- Rotation: the only mechanism is the `v1` purpose or prefix version. No rotation code exists.
- Reversible? No mathematical reversal. Core can re-link by recomputing the ref for candidate `person_id`s, since it holds both the key and the table. UniQLab cannot re-link.
- Tests: `tests/test_research_membership_boundary.py` (8 tests, e.g. `test_research_membership_ref_is_stable_opaque_and_not_uuid` `:36`) and `tests/test_staff_membership_ref.py::test_staff_and_research_membership_refs_are_unlinkable_by_value` (`:28`).

### 1b. `app/core/staff_membership_ref.py`
- `derive_staff_membership_ref(person_id) -> str` (`:18-31`) and `derive_staff_membership_ref_with_secret(person_id, secret) -> str` (`:34-44`). These use the same HMAC construction with purpose `uniqdata-core/sportique/staff-membership/v1\x00` and prefix `smr_v1_` (`:13-15`).
- They **reuse `research_membership_ref_secret`**, with domain separation by purpose only. Tests: `tests/test_staff_membership_ref.py` (2 tests).

### 1c. `app/core/customer_ref.py` (admin and product-analytics ref)
- `customer_activity_ref(person_id: UUID|str) -> str` (`:56-64`) computes `sha256(f"{secret}:customer-activity:{person_id}")` as a hex string of 64 chars. This is a **salted hash, not HMAC**.
- `product_analytics_user_ref(person_id, generation: int = 0) -> str` (`:67-78`). Generation 0 equals the base ref. Generations above 0 add `product-analytics-rotation:{generation}`, which is how **rotation on opt-out** works (docstring `:26-29`).
- Key: `_ref_secret()` returns `settings.participant_hash_secret`, and **falls back to `jwt_secret_key`** when that is empty (`:52-53`). `participant_hash_secret` has placeholder default `change-me-participant-secret` (`config.py:2246`) and is flagged in production (`config.py:3712-3713`).
- Reversible? Core re-links by recompute-and-match (internal admin drilldown). Account deletion severs the mapping (docstring `:26-29`).
- Tests: `tests/test_internal_user_search_customer_ref.py`, `tests/test_internal_customer_activity.py`, `tests/test_telemetry_intake.py`, `tests/test_account_delete.py`.

### 1d. Identity-dedup hashes: `app/services/persona_service.py`
- `PersonaService.build_identity_hash(identity: dict) -> str` (`:620-641`) computes `HMAC-SHA256(document_country | verified_birth_date | normalized document_number)`.
- `build_name_hash(verified_name) -> str|None` (`:643-660`).
- Key: `persona_identity_hash_secret`, falling back to `participant_hash_secret`.
- Purpose: duplicate-identity detection. It is not a research pseudonym, but it shows the codebase already uses HMAC over **birth date and ID number**.

## 2. Study participant pseudonym: `app/services/enrollment_service.py` + `app/models/uq_mapping.py`
- `EnrollmentService._create_enrollment_transaction(db, person_id, project_id, project_prefix="UQ", ...)` (`:235`) inserts into `uq_mapping.research_participant` (model `ResearchParticipant`, `uq_mapping.py:42-61`).
- **`participant_number`** = `f"{project_prefix}-{sequence:04d}"`, where the sequence is `count(project rows)+1` with a collision retry (`enrollment_service.py:316`). This is a **tokenization with a lookup table**. It is per project (per study), sequential and not keyed. Its order reveals enrolment order.
- **`participant_hash`** comes from `_compute_hash(person_id, project_id)`, which is `sha256(f"{participant_hash_secret}:{person_id}:{project_id}")` (`:1037-1041`). This is per person per study, and its getattr fallback is the literal `"default-secret"`.
- Reversible? **Yes, for Core only**, through the `research_participant` table (`person_id` maps to `participant_number`). UniQLab receives only `participant_number`, as stated in the 3-layer ID model in the module docstring `:1-9`. Withdrawal then re-consent reuses the same number (`:263-293`).
- `compute_age_group(year_of_birth) -> "40-49"` (`:1113-1119`) generalizes age to decade bands for enrolment pushes.
- Tests: `tests/test_enrollment_service.py` (`test_hash_is_deterministic` `:67`, `test_different_inputs_different_hash` `:74`, `test_hash_is_sha256_hex` `:80`) and `tests/test_enrollment_service_db.py`.

## 3. External-AI egress de-identification (the closest thing to a general de-id function)

### 3a. `app/services/ai_egress_deid.py`
Public API:
- `deidentify_for_ai_egress(payload: dict[str, Any], *, call_purpose: str|None=None, salt: str|None=None, concept_prevalence: ConceptPrevalence|None=None) -> EgressDeidResult` (`:829-958`). This is a pure function with no I/O.
- `EgressDeidResult(allowed: bool, payload: dict|None, denial_reason: str|None, ledger: dict)` (`:601-608`). The ledger is PHI-free (`_build_ledger` `:961-1003`) and records dropped, coarsened, pseudonymized and placeholder key paths plus sha256 hashes of the payload before and after.
- `async enforce_mn_ai_egress(payload, *, call_purpose, provider_ref, audit_db=None, commit_audit=True, subject_person_id=None) -> dict` (`:1151-1279`). This is the MN-plane-only gate (`is_mn_plane()` `:1006-1015`). Off MN it **returns the payload unchanged** (`:1176-1177`). It raises `AIEgressResidencyError(reason, ledger)` (`:574-589`).
- `coarsen_age_group(value: Any) -> str` (`:296-378`), plus `has_coded_clinical_items` (`:432`) and `collect_clinical_concept_candidates` (`:455`).

Field coverage and technique:

| Field / class | Technique | Ref |
|---|---|---|
| `person_id`, `wallet_address`, `participant_number`, email, phone, names, `dob`/`birth_date`/`year_of_birth`, `national_id`/`rrn`/`ssn`/`passport`, address, `postal_code`/`zip`, `ip`, **`device_id`**, `user_id`, `account_id` | **Suppression** at any nesting depth (hard deny list) | `NEVER_EGRESS_KEYS` `:82-115` |
| Any key not on the allowlist | Suppression (allowlist) | `:120-141`, `:158-217`, `:235-244` |
| `data_manifest[].stable_key` | **Keyed HMAC-SHA256 with a fresh random 16-byte salt per request**, output `pseudo_<24 hex>`. No mapping is stored. | `_pseudonymize` `:618-626`, salt `:853`, `:1240` |
| Timestamps (ISO datetime strings, `datetime`, `date`) | **Generalization to `YYYY-MM-DD`**. This is truncation, not date shifting. | `_coarsen_datetime` `:629-644`, `_looks_like_timestamp` `:647-653` |
| `age_group` | Generalization to `<40` / `40-64` / `65+` / `unknown` | `coarsen_age_group` `:296-378` |
| Labels (`name`, `concept_name`, `metric`, `label`, signal labels, `observation_ko`, `prompt_ko`) | Regex PII scan; on any hit the **whole value is replaced** by a placeholder such as `coded_metric` | `_LABEL_KEYS` `:221-232`, `_clean_label` `:656-669` |
| Free-text `message` | **Fails closed by default.** With `MN_AI_EGRESS_ALLOW_STRIPPED_FREETEXT=true` it is strict-stripped and re-scanned, and allowed only when the re-scan is clean. | `:789-826`, `config.py:1742-1745` |
| Coded clinical items (conditions, medications, observations, metrics, routines) | **k-anonymity floor k=5**: the whole item is dropped unless at least 5 distinct in-plane subjects carry the concept. Denied when no counts are available. | `:479-516`, `:928-935`; `mn_clinical_prevalence.py:98`, `:184-206`, `:242` |
| `alerts` | Explicitly out of k-anonymity scope (no concept id) | `:390-395` |

- Optional consent gate: `MN_AI_EGRESS_REQUIRE_CROSS_BORDER_CONSENT` (`config.py:1761-1764`, logic `:1248-1262`).
- Reversible? **No.** The per-request salt is discarded, and Core cannot re-link `pseudo_*` tokens across requests by design.
- Tests: `tests/test_mn_ai_egress_deid.py` (58 tests, e.g. `test_identifiers_never_egress_when_nested` `:248`, `test_pseudonym_uses_per_request_salt` `:302`, `test_datetime_value_under_allowed_key_coarsened_to_date` `:291`, `test_chat_message_fails_closed_by_default` `:311`) and `tests/test_mn_clinical_k_anon_floor.py` (17 DB tests, e.g. `test_the_real_count_source_cuts_at_exactly_k` `:221`).

### 3b. `app/core/pii_stripper.py` (regex PII tokenizer)
- `PiiStripper(mask_names: bool=False)` (`:520-541`) provides:
  - `strip_text(text) -> StripResult(stripped_text, token_map, pii_count, pii_types_found)` (`:548-618`);
  - `strip_dict(dict) -> PatientContextStripResult` (`:620-653`);
  - `restore_text` and `restore_dict(…, token_map)` (`:655-690`).
- Singletons: `pii_stripper` (names off) `:693` and `pii_stripper_strict` (names on) `:696`.
- Detects email, KR RRN, MN/KR phone, MN register number, UUID, XRPL wallet, IPv4, and Korean and Mongolian names (heuristic), in that order (`_PII_PATTERNS` `:466`). Text is NFC-normalized first (`:589`).
- Token: `[TYPE_<sha256(value)[:8]>]` (`_make_token` `:543-546`). This is **unkeyed and only 32 bits**, so small domains such as phone numbers can be brute-forced. It is suitable only as a local placeholder.
- **Reversible locally**: `token_map` holds the original values and must stay in Core (docstring `:7-10`).
- Tests: `tests/unit/test_pii_stripper.py` (26 tests).

### 3c. `app/services/external_safe_packet.py` (KR hosted LLM)
- `build_external_safe_packet(*, patient_context: dict, approved_manifest: list[dict], salt: str|None=None) -> ExternalSafePacket` (`:765-821`).
- It calls `deidentify_for_ai_egress` and **rejects** the packet if any transform was needed (`:782-794`). It then runs `lint_external_safe_packet` (`:277`).
- `project_chat_message(message) -> str` (`:384-398`) maps free text to a fixed intent token, so no substring of the input survives.
- The module docstring states explicitly that this is "not … an anonymization guarantee" (`:9-10`).
- Tests: `tests/test_external_safe_packet.py` (12 tests, e.g. `test_same_stable_key_uses_unlinkable_request_pseudonyms` `:66`).

### 3d. `app/services/mn_external_safe_v2.py` (MN sealed packet)
- `build_mn_external_safe_packet(*, message, locale, caller, session_id, consent, inventory_items, now=None, request_nonce=None) -> MNExternalSafePacket` (`:310`).
- `_request_pseudonym(stable_key, request_nonce)` computes `HMAC-SHA256(key=settings.jwt_secret_key, "mn-external-safe-v2\0{nonce}\0{stable_key}")[:24]` (`:241-244`). **It reuses the JWT signing key as the pseudonym key.**
- Tests: `tests/test_mn_external_safe_v2.py` (18 tests).

## 4. Aggregate / small-cell suppression (k=5)
- `app/services/tier1_service.py`:
  - `K_ANONYMITY_FLOOR = 5`;
  - `_enforce_k_floor()` clamps any caller value up to 5 (`:34-43`);
  - suppression happens in `query_overview`, `query_table` and `query_distribution` (`:130`, `:241`, `:381`);
  - UniQLab receives `participant_number` only.
  - Tests: `tests/test_tier1_service.py` (`test_below_floor_is_clamped_up` `:126`).
- `app/services/anonymous_statistics_service.py`:
  - k=5 primary suppression, **complementary suppression** and a fixed suppressed grid when the population is below k (`:61`, `:482-511`);
  - audit refs use `HMAC(ANONYMOUS_STATISTICS_AUDIT_HMAC_SECRET, …)`, requiring at least 32 bytes (`:533-541`, `config.py:2137-2140`).
  - Tests: `tests/test_anonymous_statistics_domain.py` (`test_primary_suppression_below_k` `:301`, `test_complementary_suppression` `:318`).
- `app/services/usability_gap_report_service.py` (`K_ANON_MIN = 5`, `:40`) and `analytics_kpi_service.py:51` (`K_ANON_FLOOR = 5`). Note: `STAFF_ANALYTICS_MIN_CELL_SIZE = 1` at `:52`.

## 5. Images / uploads (Core)
- `app/services/dataq_artifact_service.py:_build_image_derivatives` (`:5777-5810`) uses Pillow to apply `exif_transpose`, strip EXIF by re-encoding to JPEG (`_encode_jpeg` `:5907`), then crop and rotate per user metadata. It records `exif_removed: True`. The **original upload is stored privately and unchanged**, and only the derivatives are EXIF-free.
- **There is no burned-in-text detection or redaction and no face blurring.**

## 6. Other repos (SportiQue workspace)
- `UniQdata/AI/health-ai/shared/privacy.py` (identical copies at `UniQLab/AI/research-ai/shared/privacy.py` and `UniQLab/AI/copilot-router/shared/privacy.py`, same md5). `contains_direct_identifier(text) -> bool` and `validate_deidentified_text(text, field_name)` reject text matching email, KR phone, UUID, wallet or identifier keywords (`:23-42`). **Detection only, no transformation.**
- `UniQLab/AI/research-ai/services/research_common/privacy.py`:
  - `K_ANON_THRESHOLD = 5` (`:10`);
  - `redact_research_text` replaces participant numbers with `[REDACTED_PARTICIPANT]` (`:24-28`);
  - `detect_external_ai_prohibited_input` covers participant number, RRN, MRN and medical-note text (`:31-57`);
  - `sanitize_*` functions band small counts as `"<5"` (`:60-177`).
  - The copilot-router copy (210 lines) differs.
- `UniQLab/backend/.../service/DatasetProfileService.java`:
  - `maskPreviewRowsForStorage(rows)` (`:557`) and `maskRow` (`:484-506`) drop columns whose names look like person identifiers. This includes `*_id`, `name`, `birth`, `dob`, `address`, `study_id` and Korean name hints (`shouldMask` `:581-604`).
  - Cell values that look like RRN, email or phone become `[redacted]`, and strings longer than 48 chars are truncated.
  - Small-group preview suppression uses `SMALL_GROUP_THRESHOLD = 5` (`:21`).
  - Also: `MatchingService.java:134-137` (k=5) and `ResearchExportBundleService.java:65` (`MIN_COUNTRY_GROUP_SIZE = 5`, documentation only).
- `SOVI/packages/core/src/packet.ts` is a packet schema plus linter, described as "NOT anonymized raw data" (`:6`). `UniQdata/app/.../sovi_safe_external_prompt_service.dart` has no pseudonymization primitive.
- No shared Python, Java or Dart de-identification library exists. No module uses `pydicom`, `dcm4che` or `orthanc`.

## 7. Imaging / DICOM: **not covered**
- Core rejects DICOM uploads: `docs/RESEARCH_FILE_CONTRIBUTION.md:19-21` says "DICOM/EDF/ZIP are not currently accepted".
- MyHealthway import does not download binary or DICOM attachments (`app/integrations/ehr/myhealthway.py:39`, `docs/MYHEALTHWAY_IMPORT.md:84-87`).
- `dicom` appears only as a routing label (`app/services/dailyq_service.py:5642`) and as vocabulary metadata (`app/reference_data/sources.json:119-121`).
- No dependency on `pydicom` exists (`requirements.txt`, `pyproject.toml`). There is no DICOM tag handling, UID remapping, pixel-data scrubbing or burned-in-text OCR anywhere.

---

## How to wrap it for DICOM (gap note)

None of the functions above accepts DICOM. A wrapper (for example `pydicom`, following the DICOM PS3.15 Annex E Basic Profile) would reuse the existing primitives as follows:

| DICOM tags | Reuse | Notes |
|---|---|---|
| PatientID (0010,0020), OtherPatientIDs, IssuerOfPatientID | Replace with the study's **`participant_number`** from `uq_mapping.research_participant` (§2). Use **`derive_research_membership_ref`** (§1a) only if a cross-study researcher-lane ID is intended. | `participant_number` is per study and re-linkable only by Core, which is the right property for research release. Do **not** use `_pseudonymize` (§3a): its per-request salt would give every file in the same study a different ID. |
| PatientName (0010,0010) | Set to the same `participant_number`, or empty | Never derive from the name. `NEVER_EGRESS_KEYS` treats names as suppress-only. |
| PatientBirthDate (0010,0030), PatientAge (0010,1010) | Remove the birth date. Age: `coarsen_age_group(age)` (§3a, wide bands) or `compute_age_group` (§2, decade bands) | Matches the existing policy (`birth_date` and `dob` are hard-denied). |
| PatientSex | Keep, or map as in `gender_to_string` (`enrollment_service.py:1122`) | |
| StudyDate, SeriesDate, AcquisitionDate, ContentDate, and the matching *Time tags | Only `_coarsen_datetime` exists, which **truncates to the day** | **Missing: per-subject consistent date shifting.** No offset key or derivation exists yet. A new keyed per-(participant, study) offset would be needed, for example HMAC under a new secret, so that intervals are preserved. |
| InstitutionName and Address, ReferringPhysician, PerformingPhysician, OperatorsName, StationName, DeviceSerialNumber, AccessionNumber | Suppress or empty, in the spirit of the `NEVER_EGRESS_KEYS` allowlist approach (§3a) | AccessionNumber needs a mapping if re-linking is required. No existing helper does this. |
| StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID, FrameOfReferenceUID, and referenced UIDs | **Missing.** | Needs a deterministic remap that stays consistent within a study, such as `2.25.<int(HMAC(new_secret, purpose ‖ project_id ‖ uid))>`, applied to every referencing sequence. The HMAC-with-purpose pattern in `research_membership_ref.py:60-65` is the model to copy, but it uses a **new** dedicated secret: do not reuse `research_membership_ref_secret` or `jwt_secret_key`. |
| Free-text tags (StudyDescription, SeriesDescription, ImageComments, private tags) | `pii_stripper_strict.strip_text` as a detector (§3b), then drop on any hit, as `_clean_label` does | Drop private tags wholesale. The stripper's `token_map` is reversible and must not leave Core. |
| Pixel data (7FE0,0010) with burned-in annotations; BurnedInAnnotation (0028,0301) | **Missing.** | No OCR or redaction exists. The Pillow pipeline only strips EXIF from JPEG/PNG derivatives (§5). At minimum, reject files where BurnedInAnnotation is YES or the modality is US/SC/OT, unless they are reviewed. |
| Aggregate release of imaging cohorts | `tier1_service._enforce_k_floor` / k=5 conventions (§4) | |

Other gaps:
- No key-rotation procedure exists for any HMAC secret beyond the `v1` purpose prefix.
- `participant_hash` and `customer_ref` use salted SHA-256 rather than HMAC, and have fallbacks to `"default-secret"` and `jwt_secret_key` respectively.
- MN v2 pseudonyms are keyed with `jwt_secret_key`.
