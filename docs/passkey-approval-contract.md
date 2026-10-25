# Passkey approval of a research request (proposal, to agree with the UniQdata thread)

Goal: a participant approves a pending request by signing with their own UniQdata passkey, and the
signature is bound to the consent record and to the Escrow. A plain button cannot approve.

## Flow

1. `POST /api/p/{pid}/requests/{rid}/challenge` with body `{items}` (participant token, SELF rule).
   - The engine builds the approval statement: request id, study id, purpose (DUO), items with weeks,
     price in drops, escrow destination and condition hash, and the consent doc hash.
   - The engine asks UniQdata for a WebAuthn assertion challenge, where challenge = sha256(statement).
   - The response is `{statement, statement_hash, publicKey}`, and `publicKey` is the
     PublicKeyCredentialRequestOptions UniQdata returned (rpId, allowCredentials, userVerification "required").
2. The page shows the statement in words. It then calls `navigator.credentials.get({publicKey})`.
3. `POST /api/p/{pid}/requests/{rid}/approve` with body `{items, assertion}`. The assertion is base64url:
   id, rawId, clientDataJSON, authenticatorData, signature, userHandle.
   - UniQdata verifies the assertion. The engine refuses unless clientDataJSON.challenge = statement_hash
     and the items are the same as at step 1.
   - The consent record gets `passkey_credential_id`, `statement_hash` and `uniqdata_verification_id`.
   - The EscrowCreate memo carries `statement_hash`. Audit events are logged: passkey_signed,
     escrow_created, uniqdata_read, delivered.
   - Without a valid assertion the request stays "pending approval".
4. What the participant sees afterwards, from GET /api/p/{pid}:
   - tx hashes with explorer links;
   - which data left (items, weeks, UniQdata record hashes);
   - the sharing history;
   - the audit chain (hash, previous hash).

## Open questions for the UniQdata thread

- **RP ID and origin (blocking).** A passkey registered on UniQdata's domain only works on a page
  served from that domain or a registrable parent of it. Pages served from the engine host cannot
  use it. Which origin and RP ID does the KR dev lane use? Can the participant page be served there
  (a dev-lane path, the UniQdata web app, or the app WebView with that origin)?
- The dev-lane endpoints for the assertion challenge and the verify, plus their request and response shapes.
- daniel's prod account (ehfkehfk07@naver.com) is off limits. His manual run uses a dev-lane account
  with his passkey registered on it. The 50+ seeded test accounts use the engine's simulated devices
  instead of a passkey, and the page marks them that way.

## UniQdata answers

daniel chose option A: UniQdata Core runs locally on the Mac, built from `UniQdata/backend` main and
isolated from production. The signature uses UniQdata's own consent-signing ceremony. UniQdata
derives the challenge from the consent record's hash, verifies the assertion, and stores and
anchors the signature with that exact consent. The engine does not make its own challenge.
Instead, the request's statement is put into the UniQdata consent, so the consent hash covers it.

**RP ID and origin.** RP ID `localhost`, origin `http://localhost:8000`. The engine serves the
participant page at `http://localhost:8000/participant`. The local UniQdata runs with
`WEBAUTHN_RP_ID=localhost` and `WEBAUTHN_ORIGINS=http://localhost:8000`, so a Touch ID passkey
created on that page is a real UniQdata passkey, verified by UniQdata. The browser never calls
UniQdata directly. The engine relays these calls with the person's UniQdata session.

**Endpoints** (participant token, SELF rule). Every WebAuthn binary field is base64url, exactly
as UniQdata returns it.
1. First visit, passkey registration:
   - `POST /api/p/{pid}/passkey/register/options` returns `{publicKey}` (PublicKeyCredentialCreationOptions).
   - Call `navigator.credentials.create`.
   - `POST /api/p/{pid}/passkey/register/complete` with `{credentialId, rawId, attestationObject, clientDataJson, transports}`. It returns `{credential_id}`.
   - `GET /api/p/{pid}/passkey` returns `{registered: bool}`.
2. `POST /api/p/{pid}/requests/{rid}/challenge` with `{items}`:
   - The engine builds the statement: request, study, purpose (DUO), items with weeks, price in drops, and the escrow destination.
   - It creates a pending UniQdata consent that carries the statement.
   - It returns `{statement, statement_hash, uniqdata_consent_id, consent_hash, publicKey}`. `publicKey` is UniQdata's `/consents/{id}/attestation/options` (PublicKeyCredentialRequestOptions, `userVerification: required`).
3. Call `navigator.credentials.get({publicKey})`.
4. `POST /api/p/{pid}/requests/{rid}/approve` with `{items, assertion: {challengeId, credentialId, rawId, authenticatorData, clientDataJson, signature, userHandle}}`:
   - The engine sends it to UniQdata `/consents/{id}/approve` as `passkey_assertion`.
   - It contributes only if UniQdata returns `APPROVED` and the items match step 2.
   - The response is the usual `GET /api/p/{pid}`, plus `signed: {uniqdata_consent_id, consent_hash, statement_hash, credential_id}`.
   - Without a valid assertion nothing is sent, and the request stays pending.
   - Events are logged in this order: `passkey_signed`, then `uniqdata_read`, the escrow, the key, and delivery.

**daniel's account.** A new synthetic account on the local UniQdata, mapped to engine participant
`P-017` (the followed person). It has no passkey until daniel registers one with Touch ID on his
first visit to the page. Its data is synthetic, shaped from a summary of his own export (no real
values). His production account is never touched. The other 49 participants have their own
UniQdata accounts with software passkeys held by their agents. The page labels them "agent-signed".
