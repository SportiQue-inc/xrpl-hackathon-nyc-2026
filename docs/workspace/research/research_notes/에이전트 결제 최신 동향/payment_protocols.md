# Agent Payment Protocols (2025-2026): Structures, Trust Models, Status, and XRPL Relevance

Research date: 2026-10-25. Primary sources were GitHub raw specs (x402-foundation/x402, google-agentic-commerce/AP2, agentic-commerce-protocol, visa/trusted-agent-protocol). Several official doc domains could not be reached from the research environment (xrpl.org, ap2-protocol.org, developers.openai.com, blog.cloudflare.com), so some claims rely on search-result snippets of those pages. Those claims are marked "(snippet)".

## x402 (Coinbase, now x402 Foundation): HTTP 402 flow, headers, facilitator, schemes, v2, XRPL support

### Takeaway
x402 v2, dated 2025-12-09, is a clean JSON-over-HTTP-headers protocol that is easy to borrow:
- The server answers `402` with a `PAYMENT-REQUIRED` header listing `accepts[]` PaymentRequirements.
- The client retries with a `PAYMENT-SIGNATURE` header carrying a PaymentPayload.
- The server calls facilitator `/verify` and `/settle`, then returns `PAYMENT-RESPONSE`.

XRPL is a first-class network in the official spec. `exact` on XRPL uses a presigned `Payment` blob (`payload.signedTxBlob`), and an XRPL `upto` scheme based on payment channels was merged on 2026-10-22. T54 runs the XRPL facilitator (testnet is best-effort).

### Cited Findings

**Spec location and governance**
- The canonical repo now lives at `github.com/x402-foundation/x402`; the XRPL scheme spec sits there. — [x402-foundation scheme_exact_xrpl.md](https://github.com/x402-foundation/x402/blob/main/specs/schemes/exact/scheme_exact_xrpl.md)
- The Linux Foundation launched the x402 Foundation, which took over the protocol Coinbase contributed. — [Linux Foundation press release](https://www.linuxfoundation.org/press/linux-foundation-is-launching-the-x402-foundation-and-welcoming-the-contribution-of-the-x402-protocol?hs_amp=true)
- The launch date was reported as April 2, 2026. — [autheo](https://www.autheo.com/signals/linux-foundation-x402-protocol-april-2026)
- Reported founding members include Ripple, Visa, Mastercard, American Express, Stripe, Adyen, Fiserv, Shopify, Google, AWS, Cloudflare, Circle, MoonPay, the Solana Foundation and the Stellar Foundation. This list comes from secondary press, and one ticker-laden page claims 40 members. — [KuCoin news](https://www.kucoin.com/news/flash/linux-foundation-launches-x402-foundation-with-visa-mastercard-among-founding-members), [bitcoin.com](https://news.bitcoin.com/fr/la-linux-foundation-et-coinbase-lancent-la-fondation-x402-pour-les-agents-ia/)

**Versions and headers**
- The v2 spec says "Protocol Version: 2", is dated 2025-12-9, and requires `x402Version: 2`. — [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)
- The v1 spec's last history entry is v0.2 "Transport-agnostic redesign", dated 2025-10-3. — [x402 v1 spec](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/x402-specification-v1.md)
- v2 HTTP transport headers:
  - Server to client: `PAYMENT-REQUIRED`, base64 JSON of the PaymentRequired object.
  - Client to server: `PAYMENT-SIGNATURE`, the PaymentPayload.
  - Server to client: `PAYMENT-RESPONSE`, the settlement result.

  Status codes: `402` means payment is required or verify/settle failed; `400` means a malformed payload; `500` means a server error; `200` means success. — [x402 HTTP transport v2](https://raw.githubusercontent.com/coinbase/x402/main/specs/transports-v2/http.md)
- In v1 the client header was `X-PAYMENT` (the v1 spec's error example says "X-PAYMENT header is required"). The v1 spec text does not formally name `X-PAYMENT-RESPONSE`, though v1 SDKs used it (from memory, unverified). — [x402 v1 spec](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/x402-specification-v1.md)
- v1 PaymentRequirements fields: `scheme`, `network`, `maxAmountRequired`, `asset`, `payTo`, `resource`, `description`, `mimeType`, `outputSchema`, `maxTimeoutSeconds`, `extra`. v1 used plain network names such as `base-sepolia`, `base`, `avalanche-fuji`, `avalanche` and `iotex`. — [x402 v1 spec](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/x402-specification-v1.md)

**v2 PaymentRequired object**
- Top-level fields: `x402Version`, `error?`, `resource`, `accepts[]`, `extensions?`.
- `resource` (ResourceInfo) fields:
  - `url`
  - `description`
  - `mimeType`
  - `serviceName` (32 characters or fewer)
  - `tags` (5 or fewer)
  - `iconUrl`
- Source: [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)
- `accepts[]` (PaymentRequirements) fields:
  - `scheme`
  - `network`, as a CAIP-2 id such as `eip155:8453` or `solana:5eykt4...`; non-chain ids such as `ach:us` and `sepa:eu` are also allowed
  - `amount`, a string in atomic units (renamed from v1 `maxAmountRequired`)
  - `asset`, a token address or ISO 4217 code
  - `payTo`
  - `maxTimeoutSeconds`
  - `extra`, with reserved keys `assetTransferMethod` and `paymentFlow`
- Source: [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)

**v2 PaymentPayload object**
- Fields: `x402Version`, `resource?`, `accepted` (the chosen PaymentRequirements, echoed back), `payload` (scheme-specific), `extensions`.
- For EVM `exact`, `payload` holds `signature` (EIP-712) and `authorization` (EIP-3009) with `from`, `to`, `value`, `validAfter`, `validBefore` and `nonce` (32 bytes).
- Source: [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)

**Facilitator API**
- `POST /verify`
  - Request: `{x402Version, paymentPayload, paymentRequirements}`
  - Response: `{isValid, invalidReason?, payer?, extensions?, extra?}`
- `POST /settle`
  - Request: same as `/verify`
  - Response (SettlementResponse): `{success, errorReason?, payer?, transaction, network, amount?, extensions?}`
  - `transaction` is an empty string if nothing was broadcast, and must be non-empty when `errorReason` is `settlement_pending`.
- `GET /supported`
  - Response: `{kinds[]: {x402Version, scheme, network, extra?}, extensions[], signers: {"eip155:*": [addrs]}}`
- Source: [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)

**Payment flows (`extra.paymentFlow`)**
- `authorization` (default): verify, then serve the resource, then settle, then respond.
- `upfront`: settle, then serve, then respond.
- `escrow`: settle, then serve, then settle again, then respond.
- `/verify` is skipped for `upfront` and `escrow`, and `/settle` may be called more than once.
- Source: [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)

**Extensions**
- Each entry is `{info, schema(JSON Schema)}`.
- Clients must echo the server's extension info and may append but not delete.
- Example extension: `bazaar`, a discovery/catalog extension.
- The `EXTENSION-RESPONSES` header carries extension results.
- Source: [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)

**Schemes**
- The v2 spec names `exact`, `upto`, `batch-settlement` and `auth-capture`. — [x402 v2 spec](https://raw.githubusercontent.com/coinbase/x402/main/specs/x402-specification-v2.md)
- `upto` authorizes a maximum amount; the server sets the actual `amount` at settle time.
  - The actual amount must be at most the max and may be zero.
  - The facilitator re-verifies the signature against the authorized max (`permitted.amount`).
  - Bounds are `validAfter` and `deadline`, and each authorization is single-use (on EVM, a Permit2 nonce).
  - The recipient is bound via the Permit2 witness `to`.
  - It cannot use the `upfront` flow.
  - Streaming, recurring payments and open allowances are out of scope.
  - Source: [scheme_upto.md](https://raw.githubusercontent.com/coinbase/x402/main/specs/schemes/upto/scheme_upto.md)

**XRPL `exact` scheme (official spec)**
- Network ids: `xrpl:0` (mainnet), `xrpl:1` (testnet), `xrpl:2` (devnet).
- Asset values: `"XRP"` (amount in drops), a 3-character code, or a 40-hex currency code such as RLUSD `524C555344000000000000000000000000000000` (amount as a decimal string).
- `extra` keys:
  - `areFeesSponsored`: required and must be `false`
  - `assetTransferMethod`: `sequence` (default) or `ticketSequence`
  - `invoiceId`
  - `destinationTag`
  - `issuer`: required for IOUs
- Source: [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)
- The payload has a single field, `payload.signedTxBlob`: a hex-encoded signed XRPL tx. — [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)
- Required transaction fields:
  - `TransactionType=Payment`
  - `Destination=payTo`
  - exactly one of `DeliverMax` or `Amount`
  - `LastLedgerSequence`
  - `Sequence`, or `Sequence=0` plus `TicketSequence`
  - `DestinationTag`, if one is required
  - `InvoiceID` = SHA-256(`invoiceId`) as 64 hex characters, if `invoiceId` is set
  - `SendMax` for IOUs, same currency and issuer and at least the destination amount
- Source: [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)
- Forbidden: `Memos` (invoice binding must not use memos), `Delegate`, `Paths`, `DeliverMin`, `SendMax` on XRP payments, and the `tfPartialPayment` flag (0x00020000). `NetworkID` is omitted for network ids of 1024 or less. — [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)
- Facilitator verification:
  1. Check the envelope and `accepted` match.
  2. Decode with the binary codec.
  3. Check the tx type, destination and tag.
  4. Check network binding.
  5. Check the amount, with exact decimal comparison for IOUs.
  6. Check `LastLedgerSequence` against a policy derived from `maxTimeoutSeconds`.
  7. Check that the sequence matches the current account sequence or the ticket exists.
  8. Check the InvoiceID.
  9. Check fees and forbidden fields.
  10. Check the signature offline.
  11. Simulate, or fall back to account, balance and trust-line checks.

  Source: [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)
- Settlement:
  1. Re-verify.
  2. Run a duplicate guard keyed on tx hash. It must be an atomic, shared store held until `LastLedgerSequence` passes, and duplicates return `"duplicate_settlement"`.
  3. Submit the blob.
  4. Poll `tx` until validated.
  5. Count success only on validated `tesSUCCESS`.
  6. Return the tx hash and payer.

  Fee sponsorship is not supported because the payer pays the fee embedded in the blob. — [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)

**XRPL `upto` scheme (payment channels)**
- PR #3023 adds `scheme_upto_xrpl.md`. — [PR #3023](https://github.com/x402-foundation/x402/pull/3023)
- Mechanism:
  - The payer runs `PaymentChannelCreate` to escrow the ceiling.
  - The payer signs one off-ledger claim over `(channelId, maxAmount)`; the signed bytes are the `CLM\0` prefix, the 32-byte channel id and a uint64 big-endian drops value.
  - After metering, the resource server, as the channel `Destination`, signs a `PaymentChannelClaim` for the actual amount. The claim goes in `payload.settlementTransaction`, and a client-supplied value is rejected at `/verify`.
  - The facilitator relays the claim without holding a key, and the unused remainder returns to the payer.
- Requirements and guards:
  - `CancelAfter` is required.
  - `SettleDelay` must be at least `maxTimeoutSeconds` + 20s.
  - Deduplication is keyed on (network, channelId).
  - The payee needs XRP for fees until the `Sponsor` amendment is live.
- Status: opened 2026-08-02, merged 2026-10-22.
- Source: [PR #3023](https://github.com/x402-foundation/x402/pull/3023)

**T54 facilitator**
- T54 (t54.ai) launched an x402 facilitator on XRPL for XRP, RLUSD and USDC IOUs that uses payer-signed presigned Payment blobs and exposes verify/settle. Coverage dates the launch to around February 2026. T54 claims production use with BlockRunAI; that claim is self-reported. — [TradingView/NewsBTC](https://www.tradingview.com/news/newsbtc:a0db57883094b:0-xrp-ledger-gets-x402-facilitator-for-ai-agent-payments-why-this-is-bullish/), [altFINS](https://altfins.com/crypto-news/crypto-news-summary/216962)
- xrpl.org has a page, `docs/agents/agentic-payments-x402` (snippet). It says:
  - The testnet facilitator is operated by T54 on a best-effort basis with no SLA, and should not be used for production.
  - The three parties are merchant, payer agent and facilitator; the facilitator verifies on-chain payment and issues a signed receipt the merchant trusts.
  - Pin package versions, since it is early stage.

  — [xrpl.org agentic payments x402](https://xrpl.org/docs/agents/agentic-payments-x402)
- The testnet endpoint is reported as `xrpl-facilitator-testnet.t54.ai`, with replay protection via the account Sequence in the blob. This comes from a third-party GitHub issue and is unverified. — [Reallyeasy1/Kevin issue #28](https://github.com/Reallyeasy1/Kevin/issues/28)

**SDKs and tooling**
- Python package `x402-xrpl` on PyPI (for example 0.4.0b1): buyer and seller helpers for the presigned-blob exact flow. — [PyPI x402-xrpl](https://pypi.org/project/x402-xrpl/0.4.0b1/)
- .NET packages `Xrpl.X402` / `Xrpl.X402.AspNetCore` 1.0.0, including a `T54Facilitator` that delegates POST `/verify` and `/settle`. The author is not confirmed as T54. — [NuGet Xrpl.X402](https://www.nuget.org/packages/Xrpl.X402/)
- `mpcp-protocol/x402-xrpl`: a TypeScript settlement verifier and adapter, not a signer or builder. — [mpcp-protocol/x402-xrpl](https://github.com/mpcp-protocol/x402-xrpl)

**Adoption numbers (third-party analytics that disagree; treat with caution)**
- Weekly transactions peaked at 13.7M in November 2025, then fell to 29K–1.1M per week in 2026, based on Dune. — [autheo](https://www.autheo.com/signals/linux-foundation-x402-protocol-april-2026)
- About 167M cumulative transactions by Q1 2026, but only about $28K/day in "real commerce", with roughly half of activity gamified. — [Presenc AI tracker](https://presenc.ai/research/x402-protocol-adoption-tracker-2026)

### Inferences
- For the hackathon, copy the x402 v2 envelope verbatim (`accepts[]`, `accepted`, `PAYMENT-SIGNATURE`/`PAYMENT-RESPONSE`, `/verify`/`/settle`/`/supported`). Use `scheme:"exact"`, `network:"xrpl:1"`, and bind each research-data purchase to an `invoiceId`, which becomes `InvoiceID` = SHA-256 on-chain. This gives an auditable link from purchase to ledger tx without Memos.
- For metered data such as per-query or per-row pricing, the merged XRPL `upto` scheme with payment channels is the natural fit; the server, not the facilitator, signs the final claim.
- Use `ticketSequence` if one agent fires concurrent purchases, because the sequence method breaks under parallelism.
- Treat the T54 testnet as best-effort, and keep a fallback self-hosted facilitator: `exact` verification is small enough to implement with xrpl.js/xrpl-py.

### Gaps
- Could not load xrpl.org or t54.ai directly (DNS failure in the environment). The T54 receipt format, mainnet endpoint and auth requirements are unverified.
- Exact `batch-settlement` and `auth-capture` scheme details were not retrieved.
- No official x402 Foundation volume statistic was found.
- Whether Ripple published its own x402 docs beyond xrpl.org was not confirmed.

## Google AP2 (Agent Payments Protocol): mandates, flows, signing, A2A/x402

### Takeaway
AP2 defines three signed mandate objects, which are A2A DataParts keyed `ap2.mandates.*`:
- IntentMandate: what the user wants.
- CartMandate: the merchant-signed cart, as a W3C PaymentRequest plus a JWT.
- PaymentMandate: the user-signed SD-JWT-VC verifiable presentation over the cart and payment hashes, shared with the network or issuer.

These provide non-repudiable proof of user authorization. The canonical code now lives in `code/sdk/python/ap2/models/` of the GitHub repo, which has no tagged release.

### Cited Findings
- Data keys: `ap2.mandates.IntentMandate`, `ap2.mandates.CartMandate`, `ap2.mandates.PaymentMandate`. — [AP2 mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py)
- **IntentMandate** fields — [mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py):
  - `user_cart_confirmation_required: bool = True`. If false, the agent may buy autonomously once conditions are met. It must be true if the user did not sign the mandate.
  - `natural_language_description: str`
  - `merchants: list[str] | None`
  - `skus: list[str] | None`
  - `requires_refundability: bool | None = False`
  - `intent_expiry: str`, ISO 8601
- The AP2 A2A-extension doc example reportedly spells the refundability field `required_refundability`. Check the spelling against your target version. — [ap2-protocol.org a2a-extension (snippet)](https://ap2-protocol.org/a2a-extension), [docs.rs a2a-ap2](https://docs.rs/a2a-ap2)
- **CartContents** fields: `id`, `user_cart_confirmation_required: bool`, `payment_request: PaymentRequest` (W3C Payment Request: items, prices, accepted methods), `cart_expiry` (ISO 8601), `merchant_name`. — [mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py)
- **CartMandate** fields: `contents: CartContents`, and `merchant_authorization: str | None`. `merchant_authorization` is a base64url JWT: header (alg, kid); payload (iss, sub, aud, iat/exp, jti, `cart_hash`); signature. — [mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py)
- **PaymentMandateContents** fields: `payment_mandate_id`, `payment_details_id`, `payment_details_total: PaymentItem`, `payment_response: PaymentResponse` (W3C), `merchant_agent`, `timestamp` (ISO 8601, auto). — [mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py)
- **PaymentMandate** fields: `payment_mandate_contents`, and `user_authorization: str | None`. `user_authorization` is a base64url verifiable presentation, for example an SD-JWT-VC with a key-binding JWT, signing over the cart-mandate and payment-mandate hashes. — [mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py)
- A2A extension rules (snippet):
  - A message must contain a DataPart keyed `ap2.mandates.IntentMandate`.
  - A Merchant Agent must produce a CartMandate Artifact to request payment.
  - A Merchant Agent must not produce a CartMandate before all payment-impacting info has been collected.
  - Source: [AP2 A2A extension (snippet)](https://ap2-protocol.org/a2a-extension)
- Repo layout: `code/sdk/python/ap2/` holds Pydantic models (`models/cart.py`, `mandate.py`, `payment_request.py`, `contact_picker.py`), `schemas/` holds canonical JSON schemas, and `docs/` holds the spec. There is no release tag, and the PyPI package is "to be published later". — [AP2 GitHub](https://github.com/google-agentic-commerce/AP2)
- UCP (Universal Commerce Protocol) is described as using AP2 as its trust and payment layer. — [pimberly](https://pimberly.com/blog/what-is-ucp/), [IT Brief](https://itbrief.com.au/story/google-unveils-open-ucp-standard-for-ai-driven-shopping)
- Third-party guides that show flat mandates with `max_amount`/`expiration` do not match the official schema. Do not copy them. — [Medium guide](https://medium.com/@visrow/google-agent-payments-protocol-ap2-technical-guide-implementation-73ee772fe349)

### Inferences
- Human-present flow: the user confirms the cart (`user_cart_confirmation_required=true`) and signs the PaymentMandate.
- Human-not-present flow: the user pre-signs an IntentMandate with `user_cart_confirmation_required=false` and `intent_expiry`, and the agent may then execute against matching carts. This is inferred from the field semantics above; the full flow doc was not retrieved.
- IntentMandate has no amount cap field in the official model. A spending limit would have to be expressed through the natural-language description, SKUs and merchants, or via the payment method or credential provider.
- For XRPL: wrap an x402 `PAYMENT-REQUIRED` as the CartMandate's PaymentRequest method data, and put the XRPL tx hash in a receipt. Hashes of CartMandate and PaymentMandate can go in the payment's `InvoiceID`, a 256-bit field, to link the AP2 audit trail to the ledger.

### Gaps
- Could not fetch the AP2 spec docs or A2A x402 extension pages (404 on guessed raw paths; ap2-protocol.org DNS failure). The exact x402 extension URI, the role names (Shopping Agent, Credentials Provider, Merchant Payment Processor), the dispute rules and the partner list (around 60 at the 2025 launch, from memory) are unverified here.
- Launch date (September 2025, from memory) and current version are not confirmed by fetched sources.

## Card-network and Stripe/OpenAI protocols: Visa TAP / Intelligent Commerce, Mastercard Agent Pay, ACP, Skyfire, pay-per-crawl, 2026 entrants

### Takeaway
- Card-side agent trust converged on RFC 9421 HTTP Message Signatures (Web Bot Auth) with public-key directories and browse-versus-pay tags (Visa TAP, Mastercard Agent Pay), plus network tokens bound to agents.
- ACP (OpenAI and Stripe) uses a delegated, single-use, merchant-scoped payment token with an explicit `allowance` (`max_amount`, `expires_at`).
- Skyfire uses JWT KYA/PAY tokens.
- 2026 brought Google UCP (January), Stripe/Paradigm Tempo plus the Machine Payments Protocol (March 18) and the x402 Foundation (April).

### Cited Findings

**Visa Trusted Agent Protocol (TAP)**
- Agents prove identity and authorization to merchants with cryptographic signatures. The repo's README describes the following (header names and tags are not stated there):
  - Signatures include timestamps, a unique session id or nonce, a key id and an algorithm.
  - They are bound to the merchant domain and the operation (browse or pay), and are single-use.
  - The sample implements RFC 9421 verification.
  - An Agent Registry holds public keys.
  - Consented identifiers are passed as query params: consumer ids, Payment Account Reference (PAR), loyalty, email, phone.
  - Source: [visa/trusted-agent-protocol README](https://raw.githubusercontent.com/visa/trusted-agent-protocol/main/README.md)
- Headers per secondary sources:
  - `Signature-Agent`: URL of the operator's key directory
  - `Signature-Input`: keyid, created/expires, tag
  - `Signature`: Ed25519
- Tags per secondary sources: `agent-browser-auth` (browse/cart) and `agent-payer-auth` (purchase).
- Covered components reportedly include `@authority` and `@path`, with params `created`, `expires`, `keyid`, `alg`, `nonce` and `tag`, and a validity window of about 8 minutes.
- Sources (secondary): [eco.com TAP explainer](https://eco.com/support/en/articles/14845482-visa-trusted-agent-protocol-tap-explained), [oscilar](https://oscilar.com/blog/visatap)
- Cloudflare (snippet): Visa and Mastercard both build on Web Bot Auth by adding a tag in `Signature-Input` that marks browsing versus purchasing. Agents must register public keys (the `keyid`) in a well-known directory, and a `nonce` is required for replay protection. — [Cloudflare blog (snippet)](https://blog.cloudflare.com/secure-agentic-commerce/)
- TAP was introduced around 2025-10-14, with Adyen, Cloudflare and Stripe reported as early participants. Dates differ across sources. — [eco.com](https://eco.com/support/en/articles/14845482-visa-trusted-agent-protocol-tap-explained)

**Mastercard Agent Pay**
- Registered agents sign requests so the merchant or CDN recognises them, and pay with a tokenized card credential issued for the agent (an "Agentic Token", an EMV network token). — [ARC protocol matrix](https://www.arcreport.ai/protocols/payments), [Cloudflare (snippet)](https://blog.cloudflare.com/secure-agentic-commerce/)
- A KYA interoperability framework from Ant International, Mastercard and Visa was reportedly announced on 2026-09-09. This is unverified and secondary. — [eco.com agent identity 2026](https://eco.com/support/en/articles/15192005-agent-identity-verification-how-ai-agents-authenticate-purchases-in-2026)

**ACP Delegated Payment (OpenAI + Stripe)**
- Endpoint: `POST /agentic_commerce/delegate_payment`, spec version and `API-Version` 2025-09-29 (Draft). — [ACP rfc.delegate_payment.md](https://raw.githubusercontent.com/agentic-commerce-protocol/agentic-commerce-protocol/main/rfcs/rfc.delegate_payment.md)
- Request body:
  - `payment_method`: type `card`
  - `allowance`:
    - `reason`: `one_time`
    - `max_amount`: integer, minor units
    - `currency`: lowercase ISO 4217
    - `checkout_session_id`
    - `merchant_id`: 256 characters or fewer
    - `expires_at`: RFC 3339
  - `billing_address?`
  - `risk_signals[]`: required; type `card_testing`
  - `metadata`
- Headers: `Authorization: Bearer`, `Idempotency-Key`, `API-Version`, and the recommended `Signature`, `Timestamp`, `Request-Id`.
- Response: `201 {id, created, metadata}`.
- Source: [ACP rfc.delegate_payment.md](https://raw.githubusercontent.com/agentic-commerce-protocol/agentic-commerce-protocol/main/rfcs/rfc.delegate_payment.md)
- Direct integration is for PSPs or PCI DSS L1 merchants with their own vaults; others use Stripe's Shared Payment Token. The token is restricted by the max amount and expiry. — [OpenAI Delegated Payment Spec (snippet)](https://developers.openai.com/commerce/specs/payment)
- Adyen implements this as a PSP. — [Adyen delegated payment spec](https://docs.adyen.com/online-payments/agentic-commerce/delegated-payment-spec)
- A secondary source puts the latest stable ACP spec at 2026-04-17, Apache 2.0, co-maintained by OpenAI and Stripe. This is unverified. — [eco.com ACP explainer](https://eco.com/support/en/articles/14845478-acp-agentic-commerce-protocol-explained)

**Skyfire KYAPay**
- Token types: JWTs whose `typ` is `kya`, `pay` or `kya-pay`.
- Claims to check: `iss` (`https://app.skyfire.xyz`), `env` (production or sandbox), `iat`, `exp`, and `jti` (a UUID).
- PAY token: `val` is the amount as a string.
- KYA token sub-claims: `hid` (human identity), `apd` (agent platform), `aid` (agent).
- PAY token settlement claim: `sti`.
- Transport: the `kyapay-token` header (`skyfire-pay-id` is deprecated), verified against Skyfire's JWKS.
- Sources: [Skyfire verify tokens](https://docs.skyfire.xyz/docs/verify-and-extract-data-from-tokens), [Skyfire pay token](https://docs.skyfire.xyz/docs/pay-token.md), [Skyfire common claims](https://docs.skyfire.xyz/docs/common-token-claims.md)
- IETF individual drafts (not RFCs): `draft-skyfire-oauth-kyapay-token-01`, `draft-skyfire-kyapayprofile-02`, and `draft-skyfire-oauth-using-kyapay-tokens-00` (2026-07-19). — [IETF datatracker](https://datatracker.ietf.org/doc/draft-skyfire-oauth-using-kyapay-tokens/), [draft-00](https://www.ietf.org/archive/id/draft-skyfire-oauth-kyapay-token-00.txt)

**Stripe/Tempo Machine Payments Protocol (MPP)**
- Tempo, a payments L1 incubated by Stripe and Paradigm, launched mainnet and MPP on 2026-03-18; its testnet had run since December 2025.
- MPP is open source and rail-agnostic. Visa extended it to cards; Stripe to cards and wallets; Lightspark to Lightning.
- It supports "sessions" for continuous payments, and launched with 100+ providers including Alchemy, Dune, Anthropic, OpenAI and Shopify.
- Sources: [The Block](https://www.theblock.co/post/394131/tempo-mainnet-goes-live-with-machine-payments-protocol-for-agents), [Decrypt](https://decrypt.co/361573/stripe-backed-tempo-network-launches-ai-agent-payments)
- A streaming-payments primitive was reportedly added at Stripe Sessions, 2026-04-29/30. This is a single secondary source. — [eco.com MPP](https://eco.com/support/en/articles/14845486-stripe-machine-payments-protocol-mpp)

**Google Universal Commerce Protocol (UCP)**
- Open source; launched around January 2026 at NRF (sources say Jan 11 or Jan 20).
- Partners: Shopify, Etsy, Wayfair, Target, Walmart.
- Scope: checkout sessions, OAuth 2.0 identity linking and order webhooks, with REST, MCP and A2A bindings.
- Updates: Cart, Catalog and Identity Linking were added in March 2026; Universal Cart was announced at I/O in May 2026.
- Sources: [IT Brief](https://itbrief.com.au/story/google-unveils-open-ucp-standard-for-ai-driven-shopping), [pimberly](https://pimberly.com/blog/what-is-ucp/), [ppc.land](https://ppc.land/googles-universal-cart-wants-to-follow-you-everywhere-you-shop/)

**Cross-protocol patterns (from the cited structures above)**
- Spending limits:
  - ACP `allowance.max_amount`
  - x402 `upto` max amount
  - XRPL channel `maxAmount`
  - x402 `exact` amount
  - Sources: [ACP](https://raw.githubusercontent.com/agentic-commerce-protocol/agentic-commerce-protocol/main/rfcs/rfc.delegate_payment.md), [upto](https://raw.githubusercontent.com/coinbase/x402/main/specs/schemes/upto/scheme_upto.md), [PR #3023](https://github.com/x402-foundation/x402/pull/3023)
- Expiry:
  - AP2 `intent_expiry` and `cart_expiry`
  - ACP `expires_at`
  - x402 `maxTimeoutSeconds`, EVM `validBefore`, XRPL `LastLedgerSequence` and channel `CancelAfter`
  - Skyfire `exp`
  - TAP `expires`
  - Sources: [mandate.py](https://raw.githubusercontent.com/google-agentic-commerce/AP2/main/code/sdk/python/ap2/models/mandate.py), [scheme_exact_xrpl.md](https://raw.githubusercontent.com/x402-foundation/x402/main/specs/schemes/exact/scheme_exact_xrpl.md)
- Cryptographic user or agent authorization:
  - AP2 `user_authorization` (SD-JWT-VC plus key binding) and merchant `merchant_authorization` (JWT with `cart_hash`)
  - x402 payer signature (EIP-712 or a signed XRPL blob)
  - TAP and Agent Pay RFC 9421 agent signatures
  - Skyfire JWT
- Replay protection:
  - EIP-3009 nonce, Permit2 nonce
  - XRPL Sequence/Ticket plus a tx-hash dedup cache
  - TAP `nonce`
  - Skyfire `jti`
  - ACP `Idempotency-Key`
- Refundability and disputes: AP2 has `requires_refundability`; card rails (ACP, Agent Pay, TAP) inherit chargebacks. x402 `exact` on XRPL is final once validated, and the spec defines no refund message.

### Inferences
- For an XRPL research-data marketplace, a practical stack has five layers:
  1. Agent identity: RFC 9421 signature with a `tag`, or a KYA-style JWT on requests.
  2. User authorization: an AP2-style IntentMandate with an added explicit `max_amount`/currency, since AP2 lacks one, and an expiry.
  3. Offer: an x402 `PAYMENT-REQUIRED` with an XRPL `exact` or `upto` scheme.
  4. Settlement: on XRPL, with `InvoiceID` = the hash of the cart or mandate.
  5. Receipt: `PAYMENT-RESPONSE` with the tx hash.
- Refunds or disputes on XRPL need an app-level design, such as an XRPL Escrow or a payment-channel holdback before claim. No protocol here standardizes crypto refunds.

### Gaps
- No primary Mastercard developer page was retrieved, so the exact Agent Pay tag name and Agentic Token fields are unconfirmed.
- Visa Intelligent Commerce API objects were not retrieved.
- Cloudflare pay-per-crawl (2025) mechanics and its x402 tie-in were not verified by any fetched source this session.
- ACP checkout-session API fields (create/update/complete) were not retrieved. Only the delegate_payment RFC was.
- MPP message structures (HTTP 402 challenge format, session fields) were not retrieved, nor whether MPP is wire-compatible with x402.
