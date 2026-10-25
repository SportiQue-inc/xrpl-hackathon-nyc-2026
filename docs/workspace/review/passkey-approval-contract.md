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
