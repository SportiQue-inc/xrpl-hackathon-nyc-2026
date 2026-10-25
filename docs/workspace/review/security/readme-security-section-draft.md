<!-- README 초안: §10 "Safety, privacy, limits"를 이 섹션으로 교체하거나 그 앞에 넣는다. M1~M8 반영을 전제로 쓴 문장은 [M#]로 표시했다. 반영하지 못한 항목은 해당 문장을 "Limits"로 옮긴다. -->

## 10. Security design

**Ledger enforces, code verifies, the LLM only proposes.** Each control below names the layer that
enforces it.

| Threat | Control | Enforced by | Evidence |
|---|---|---|---|
| An agent raises its own budget | Study treasury: SignerList (PI + compliance, quorum 2), master key disabled. Each signer approves separately; one approval per spec [M7] | XRPL | `tefBAD_QUORUM` single signer; co-signed top-up tx |
| An agent spends beyond what the owner signed | Owner-signed delegation (Verifiable Intent L1 -> L2 -> L3, ES256). Checked right before every payment and escrow: per-payment max, total, purpose, payee, expiry. The signed ceiling never rises by itself [M7] | code | `tests/test_mandate.py` |
| Paying twice | Order key is idempotent; signed blob and hash stored before submit; lost response -> look up by hash and resubmit the same blob; validated ledger checked for destination, amount, InvoiceID and Condition; sequence re-read after any autofilled tx [M8] | code + XRPL | `test_lost_response_*`, recovery tests |
| Data without payment, or payment without data | Bundle sealed to the study's key, then locked with K; escrow condition = SHA-256(K); the participant's agent publishes K in EscrowFinish to get paid, and the study reads K from the ledger | XRPL | EscrowCreate/Finish tx |
| Delivery after consent changes | Before K is published, code re-checks revocation, the study's licence MPT, the verified-organization and ethics credentials on the ledger, the prohibited-purpose list and the consented period [M4]. A revoke is final; only a newly signed consent reopens supply [M5] | code + XRPL | `test_clawed_back_licence_alone_stops_the_key`, new delivery-recheck test |
| Onward transfer of the licence | MPT supply 1, RequireAuth, no CanTransfer, CanClawback | XRPL | `tecNO_AUTH` tx, Clawback tx |
| Unverified organizations | VERIFIED_ORG credential; DepositAuth + DepositPreauth by credential on the participant's account | XRPL | `tecNO_PERMISSION` tx |
| Linking a person across studies | Per-study pseudonym and date shift = HMAC with a secret only the person's agent holds [M3]; the researcher console shows pseudonyms only | code | `test_pseudonym_differs_per_study`, keyed-pseudonym test |
| Re-identification by combination | Two or more quasi-identifiers are never released together | code | `test_quasi_identifier_combination_is_never_released` |
| Someone acting for another person | API calls carry a role token (participant, researcher, each signer); a participant can act only on their own requests [M1, M6] | code | 401/403/404 tests |
| Cross-site requests | Every call needs an `Authorization` header, so browsers force a CORS preflight, which the server does not allow [M1] | code | |
| LLM manipulation | Proposals are JSON, schema-checked, stored with hashes, and recomputed from the coverage table. Budget, purpose and sensitive fields are clamped to the owner's limits. Licence readings are ANDed with the seller's own terms. The LLM never sees record values, and its output never widens money or permission | code | `test_hostile_llm_can_only_narrow`, `test_hostile_llm_cannot_widen_the_study` |
| Secrets in the repository | `.env`, seeds and `wallets.local.json` are git-ignored (0600); the history has no keys; signed blobs and hashes only in the DB | repo | |

**What goes on-chain:** order id, bundle hash, consent or terms hash, and the licence MPT with the
study as a hash. No health values, names, study topics or consent text.

### Limits of this demo (read before judging)

- **One process holds every party's keys.** The study, both treasury signers, the participants'
  agents and the operator run in one server. So anyone with that server's database could open
  bundles without the ledger step. In production, K is created and kept on the participant's phone,
  the study's box key lives in the institution's KMS, and each signer signs on their own device
  (XRPL multisign). The ledger rules shown here do not change.
- **Authentication is demo tokens**, not accounts. In production it is the UniQdata (participant) and
  UniQLab (researcher) login, behind a gateway with rate limits.
- **Destruction on withdrawal** removes the study's person-level copies held by this demo. K stays
  public on the ledger for rounds already delivered; without the bundle copy it opens nothing.
  Delivered rounds cannot be recalled, and the person is told so before approving.
- **On-chain payments are visible.** Amounts and addresses are public, so participation can be
  inferred from the ledger. Production uses per-study addresses or a payout service.
- **The event log is append-only but not hash-chained** (proposals and consent versions are hashed
  one by one).
- **The LLM summary on the request card is labelled as an AI summary.** The binding terms are the
  DUO codes, items, weeks and recipient listed under it.
- All data, people and institutions are synthetic. XRPL Testnet only. Not a medical device.
