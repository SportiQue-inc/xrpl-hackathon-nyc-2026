# UniQdata backend PR #1585: batch consent approval with one passkey. Security review

Reviewed head `00b851c` (draft). Not merged, not commented on GitHub. Reviewed by reading the
code: the diff plus the single-consent path it reuses (`consent.py`, `consent_attestation_service.py`,
`consent_service.py`, `consent_signature_evidence.py`, `passkey_service.py`).

**Verdict:** the cryptographic binding is sound. One assertion covers exactly the signed set of
consent ids and consent hashes. It is single-use and tied to the person. A changed consent, a
subset, or an extra id is refused, and the approval is all-or-none. Two issues should still be
fixed before merge, because merging to main deploys to production: what may go into a batch, and
what each study's archive reveals.

## Findings

| # | Severity | Finding | Where | Fix |
|---|---|---|---|---|
| 1 | **High** | **Any pending consent of the person can go into a batch, not only research consents.** `generate_options` checks only owner, PENDING and hash. So a batch can carry chat disclosure, AI visit, DataQ action, file delivery or `cross_border_ai` consents, up to 10, behind one Touch ID. The WebAuthn prompt shows nothing about what is being signed, so the client UI is the only thing that shows the person the content. A buggy or compromised research tab (XSS, a wrong list) can slip in a consent the person never opened. On the single path, each of these lanes needs its own exact assertion (`_requires_consent_bound_attestation`) or a cross-border step-up. | `consent_batch_attestation_service.py` `generate_options` (loop over items) | Allow-list the batch to `research_participation` consents only, and refuse everything `consent_bound_attestation_required` flags as high-risk, `cross_border_ai`, and file consents (`CONSENT_TYPE`). Optionally require that all items come from one research sheet (same app_id / requesting org). |
| 2 | **Medium** | **The text hashes of the separate consents are taken from the client unchecked.** Any 64 hex characters pass (the tests use `"a"*64`). The signature commits to what the client says it showed, not to the third-party, sensitive or abroad text the server holds. Also, `international` is optional even when the study transfers data abroad. | `normalize_separate_consents` | Compare each `text_sha256` with the server's catalog text for that consent's policy and version (`consent_scope_catalog` notice manifests). Require `international` whenever the consent's scopes or policy involve transfer abroad. |
| 3 | **Medium (privacy)** | **Each study's archive contains the whole batch manifest,** i.e. the consent ids and hashes of the other studies signed in the same tap. If an archive is ever shown to one study or regulator as proof of consent, it reveals participation in the others. | `build_research_consent_evidence(..., batch_manifest=manifest)` | Build the manifest as a Merkle tree over items. The challenge is the root plus the nonce, and each archive keeps only its own leaf and proof path. Offline verification still works per consent. |
| 4 | Low | Non-research consents in a batch get no private archive. Their record holds `batch_hash` but not the manifest, so it cannot be re-verified on its own later. | `verify_assertion` (`private_evidence` only if `research_signature_required`) | Disappears with fix 1 (research only), or store the leaf and proof (fix 3) for every item. |
| 5 | Low | The single-use identifier HMAC is keyed with `settings.jwt_secret_key`. This copies the existing single path (`consent_attestation_service.py:89`), which was already flagged as a key-reuse pattern not to carry over. | `batch_credential_hmac` | Use a dedicated secret (e.g. `CONSENT_ATTESTATION_HMAC_KEY`) for both paths. |
| 6 | Low | The challenge has no domain tag or person id: `sha256(stable_hash(manifest) || nonce)`, the same shape as the single path's `sha256(consent_hash || nonce)`. A cross-use cannot happen today (separate challenge keys, fresh nonces, a manifest hash is never a consent hash). Still, the offline verifier tells them apart only by `version`. | `derive_challenge(batch_hash, nonce)` | Add `"consent-batch.v1"` and person_id inside the manifest. The version is already there, so only person_id is missing. |
| 7 | Info | The audit proof records only the first item's credential. `target_ref_hash` is `person_ref_hash(batch_id)`, which mirrors the single path's use of `person_ref_hash(consent_id)`. | `approve_consent_batch` | Include the list of consent ids (hashed) in the proof. |

## The four questions

- **Can one assertion approve consents the user didn't see or select?** Not ones outside the
  signed set: the approved set must equal the manifest, and the manifest is fixed at options time.
  But the server cannot know what was *shown*, and today any pending consent type is eligible
  (finding 1), with unchecked text hashes (finding 2). Fixing 1 and 2 closes this as far as the
  server can.
- **Per-study consent records:** yes. Every consent goes through `consent_service.approve_consent`
  in one transaction (snapshot, audit, signature). Research consents get their own archive, which
  re-verifies offline, and tests show tampering is detected. Findings 3 and 4 still apply.
- **Replay protection:** good. The batch meta is bound to person_id, the redis challenge is
  consumed by `verify_authentication_locked`, the single-use credential is consumed in the DB, the
  meta is deleted, and the sign count advances. A second POST with the same assertion fails
  (tested).
- **Scope binding of the challenge to the exact study set:** good. The manifest is sorted by
  consent_id and holds each consent_hash, the challenge is derived from it, and verify re-reads
  each consent and compares hashes in constant time. The approve request must list exactly the
  signed ids (tested for subset and foreign id).

## Suggested tests to add

- A batch containing a `cross_border_ai` / DataQ / file / chat-disclosure consent is refused at options.
- A `text_sha256` not matching the catalog text is refused.
- A study with transfer abroad and no `international` mark is refused.
- One study's archive does not contain other studies' consent ids (after fix 3).
