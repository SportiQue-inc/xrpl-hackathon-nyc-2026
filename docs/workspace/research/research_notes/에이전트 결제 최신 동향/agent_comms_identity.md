# Agent-to-Agent Communication and Agent Identity/Delegation Standards (state as of 2026-10-25)

Scope: A2A, MCP, agent identity/KYA, delegation tokens, consent receipts, GA4GH, ledger-enforceable mandates. For a hackathon decision on exposing an institution agent + personal agents via A2A and/or MCP, and proving delegated authority (spending limits, consent scope).

Method note: a2a-protocol.org, modelcontextprotocol.io, ap2-protocol.org, xrpl.org and opensource.googleblog.com did not resolve from the research sandbox (DNS failure), so primary specs were read from their GitHub raw sources instead. Items marked **[training knowledge, unverified 2026]** come from pre-2026 knowledge and were not re-checked live.

## 1. Google A2A (Linux Foundation): Agent Card, methods, auth, versions, SDK, extensions

### Takeaway
A2A is now at **v1.0 (stable, released around March/April 2026)**. v1.0 renamed the JSON-RPC methods to PascalCase (`SendMessage`, `GetTask`, ...), replaced `url`/`preferredTransport` with a `supportedInterfaces[]` list, and added JWS-signed Agent Cards. The Python `a2a-sdk` 1.2.x implements 1.0 and has a 0.3 compatibility mode. AP2 (mandates) and x402 (crypto payment) ship as A2A extensions. Most tutorials still show 0.3-style `message/send`, so pin to one version.

### Cited Findings
**Version / governance**
- Latest released spec version is `1.0.0`. Clients MUST send an `A2A-Version` header (Major.Minor, e.g. `1.0`), or the same value as a query param. An empty value is treated as `0.3`. An unsupported version returns `VersionNotSupportedError`. — [A2A spec (GitHub)](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)
- Release month of v1.0: sources conflict. A Google OSS blog post (April 2026) and others say March 2026; an Alice Labs guide says April 2026. — [Google Open Source Blog](https://opensource.googleblog.com/2026/04/a-year-of-open-collaboration-celebrating-the-anniversary-of-a2a.html?m=0); [Alice Labs](https://alicelabs.ai/en/insights/a2a-protocol-guide-2026)
- Linux Foundation one-year press release (Apr 9, 2026): more than 150 supporting organizations. The update added multi-protocol support, multi-tenancy, "modernized security flows", a migration path, and Signed Agent Cards. It is integrated in Azure AI Foundry / Copilot Studio and AWS Bedrock AgentCore Runtime. — [Linux Foundation press](https://linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)
- Claim that A2A moved under the Agentic AI Foundation (AAIF) on Aug 17, 2026: this comes from a single blog source and is unconfirmed. — [Pebblous blog](https://blog.pebblous.ai/blog/a2a-mcp-agentic-ai-foundation-authorization/en/)

**Agent Card** (served at `/.well-known/agent-card.json`) — all from [A2A spec](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)
- Top-level fields: `name`, `description`, `supportedInterfaces`, `version`, `capabilities`, `defaultInputModes`, `defaultOutputModes`, `skills`, `securitySchemes`, `security`, `signatures`.
- `supportedInterfaces[]` holds `AgentInterface` objects `{url, protocolBinding, protocolVersion}`. The `protocolBinding` values are `"JSONRPC"`, `"HTTP+JSON"` and gRPC; custom bindings are named by URI. The first entry is the preferred interface.
- `capabilities`: `streaming`, `pushNotifications`, `extensions`, `extendedAgentCard`.
- Skill: `id`, `name`, `description`, `tags`, `examples`, `inputModes`, `outputModes`.
- Security scheme types: `APIKeySecurityScheme`, `HTTPAuthSecurityScheme`, `OAuth2SecurityScheme`, `OpenIdConnectSecurityScheme`, `MutualTlsSecurityScheme`. The JSON key style is like `openIdConnectSecurityScheme`.
- `signatures[]` holds `AgentCardSignature` objects `{protected (req), signature (req), header (opt)}`. They are JWS (RFC 7515) over the JCS-canonicalized card (RFC 8785). The protected header MUST have `alg` and `kid`, SHOULD have `typ: "JOSE"`, and MAY have `jku`. The `signatures` field itself is excluded from the signed content.

**Methods (JSON-RPC binding, v1.0)** — [A2A spec](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)
- `SendMessage`, `SendStreamingMessage` (SSE), `GetTask`, `ListTasks`, `CancelTask`, `SubscribeToTask`, `CreateTaskPushNotificationConfig`, `GetTaskPushNotificationConfig`, `ListTaskPushNotificationConfigs`, `DeleteTaskPushNotificationConfig`, `GetExtendedAgentCard`.
- The 0.3 names were `message/send`, `message/stream`, `tasks/get`, `tasks/cancel`, `tasks/resubscribe`, `tasks/pushNotificationConfig/*`, `agent/getAuthenticatedExtendedCard`. **[training knowledge, unverified 2026]** The spec fetched does not use slash names.

**Objects** — [A2A spec](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)
- Task: `id`, `contextId`, `status{state, message, timestamp}`, `artifacts`, `history` (controlled by `historyLength`).
- Message: `role` (`ROLE_USER` | `ROLE_AGENT`), `parts`, `messageId`, `taskId`, `contextId`, `referenceTaskIds`, `extensions`, `metadata`.
- Part (v1.0 unified): `text` | `raw` | `url` | `data`, plus `filename`, `mediaType`, `metadata`. In 0.3 these were separate kinds: TextPart, FilePart and DataPart.
- Artifact: `artifactId`, `name`, `parts`, `extensions`, `metadata`.
- TaskState: `TASK_STATE_SUBMITTED`, `_WORKING`, `_COMPLETED`, `_FAILED`, `_CANCELED`, `_REJECTED`, `_INPUT_REQUIRED`, `_AUTH_REQUIRED`. `AUTH_REQUIRED` and `INPUT_REQUIRED` are the natural hooks for "user must approve this spend".

**Extensions**
- Declared in `AgentCard.capabilities.extensions[]` as `AgentExtension{uri, description, required, params}`. Clients activate extensions with the `A2A-Extensions` request header (comma-separated URIs). — [A2A spec](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)
- **AP2 extension**: an IntentMandate is sent as a DataPart keyed `ap2.mandates.IntentMandate`. A Merchant Agent MUST produce a `CartMandate` Artifact before requesting payment. The three mandates are IntentMandate (user intent + constraints, signed by the user), CartMandate (items/price, merchant-signed) and PaymentMandate (payment method + amount, for the network/issuer). Together they form a non-repudiable audit chain. — [AP2 A2A extension](https://ap2-protocol.org/a2a-extension) (search snippet; the page itself was unreachable); [Affinidi AP2 docs](https://docs.affinidi.com/products/affinidi-trust-fabric/agent-gateway/concepts/protocols/ap2/)
- Mandates are W3C Verifiable Credentials, and IntentMandate fields include `natural_language_description`, `merchants`, `skus`, `requires_refundability`, `intent_expiry` and `user_cart_confirmation_required`. **[training knowledge, unverified 2026]**
- An IETF individual draft (Sep 2026) binds "VCAP" to AP2. It positions AP2 as an authorization/security layer inside commerce protocols such as UCP and references x402 v2. — [draft-stone-vcap-ap2-binding-01](https://www.ietf.org/archive/id/draft-stone-vcap-ap2-binding-01.html)
- **A2A x402 extension** (google-agentic-commerce/a2a-x402, v0.1.0): an official x402 extension for A2A, co-developed with Coinbase and MetaMask. In the embedded flow it scans `task.artifacts` for a higher-level artifact (for example an AP2 CartMandate) that carries x402 payment requirements. — [a2a-x402 docs index](https://docsearch.algolia.com/mcp/docs/repo/google-agentic-commerce/a2a-x402)

**Python SDK**
- `a2a-sdk` latest version is 1.2.3. It implements spec 1.0 with a compatibility mode for 0.3, and supports JSON-RPC, HTTP+JSON/REST and gRPC on both client and server. — [PyPI a2a-sdk](https://pypi.org/project/a2a-sdk/)
- The official helloworld sample pattern: define an `AgentSkill`, then a public `AgentCard` and an optional extended card with a JSON-RPC interface at `http://127.0.0.1:9999` and `streaming=True`. An `AgentExecutor` subclass goes into `DefaultRequestHandler(agent_executor=..., task_store=InMemoryTaskStore())`. Agent-card routes and JSON-RPC routes are mounted in a Starlette app and run with uvicorn. — [a2a-samples helloworld](https://github.com/a2aproject/a2a-samples/tree/main/samples/python/agents/helloworld)
- Minimal shape, 0.3-era API. **[training knowledge; class and module names may have moved in 1.x, so check against the sample]**
  ```python
  from a2a.server.agent_execution import AgentExecutor, RequestContext
  from a2a.server.events import EventQueue
  from a2a.server.request_handlers import DefaultRequestHandler
  from a2a.server.tasks import InMemoryTaskStore
  from a2a.server.apps import A2AStarletteApplication
  from a2a.types import AgentCard, AgentSkill, AgentCapabilities
  from a2a.utils import new_agent_text_message
  import uvicorn

  class Exec(AgentExecutor):
      async def execute(self, ctx: RequestContext, q: EventQueue):
          await q.enqueue_event(new_agent_text_message(f"echo: {ctx.get_user_input()}"))
      async def cancel(self, ctx, q): raise Exception("unsupported")

  card = AgentCard(name="Institution Agent", description="...", url="http://localhost:9999/",
      version="0.1.0", default_input_modes=["text"], default_output_modes=["text"],
      capabilities=AgentCapabilities(streaming=True),
      skills=[AgentSkill(id="pay", name="Pay", description="...", tags=["payments"])])
  app = A2AStarletteApplication(agent_card=card,
      http_handler=DefaultRequestHandler(agent_executor=Exec(), task_store=InMemoryTaskStore()))
  uvicorn.run(app.build(), host="0.0.0.0", port=9999)
  ```

### Inferences
- For a demo, target A2A 1.0 with `a2a-sdk` 1.2.x and the JSON-RPC binding. Remember that 0.3 clients (many samples, ADK versions) send no `A2A-Version` header and get 0.3 semantics. The SDK's compat mode covers this, but test cross-version calls.
- Signed Agent Cards (JWS with a `kid`/`jku` resolving to a JWKS or a `did:web`/`did:xrpl` doc) let the institution agent prove "who I am". Mandates (AP2-style VCs in DataParts) prove "what I'm allowed to do".
- `TASK_STATE_AUTH_REQUIRED` / `INPUT_REQUIRED` can model the step where a personal agent obtains user consent before a spend.

### Gaps
- Could not load ap2-protocol.org directly, so the exact current AP2 version and mandate JSON schemas need verification on GitHub (google-agentic-commerce/AP2).
- Exact a2a-sdk 1.x import paths were not verified.
- The AAIF move of A2A is unconfirmed.

## 2. Anthropic MCP: spec versions, authorization, elicitation, structured output, SDK, MCP vs A2A, payment servers

### Takeaway
The **latest MCP spec is `2026-07-28`**, a breaking, **stateless** revision. It removes `initialize` and `Mcp-Session-Id`, and replaces server-initiated elicitation/sampling with Multi Round-Trip Requests. Tasks become an extension, DCR is deprecated in favor of CIMD, and Roots/Sampling/Logging are deprecated. The previous version, `2025-11-25`, added URL-mode elicitation, experimental tasks, CIMD and incremental scope consent. Authorization is OAuth 2.1 + RFC 9728 + RFC 8707, with token passthrough prohibited.

### Cited Findings
**2025-11-25 changes** — [MCP changelog 2025-11-25](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/changelog.mdx)
- OpenID Connect Discovery 1.0 for authorization server discovery.
- Icons metadata (SEP-973).
- Incremental scope consent via `WWW-Authenticate` (SEP-835).
- Tool naming guidance (SEP-986).
- Enum schema updates for elicitation (SEP-1330).
- **URL mode elicitation** (SEP-1036): send the user to a URL, for example for a payment or OAuth step, instead of collecting data in-band.
- Tool calling in sampling via `tools`/`toolChoice` (SEP-1577).
- **Client ID Metadata Documents** recommended (SEP-991).
- **Experimental tasks** (SEP-1686).

**2025-06-18**: added structured tool output (`outputSchema` + `structuredContent`), form-mode elicitation (`elicitation/create` with a flat JSON schema), resource links, the requirement to classify MCP servers as OAuth Resource Servers (RFC 9728), the RFC 8707 requirement, and removal of JSON-RPC batching. **[training knowledge, unverified 2026]**

**2026-07-28 (current)** — [MCP blog: 2026-07-28 spec](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- Stateless core: the `initialize`/`initialized` exchange and the `Mcp-Session-Id` header are retired (SEP-2575, SEP-2567). Each request carries protocol version, client identity and capabilities in `_meta`. An optional `server/discover` RPC exists. Server-side state uses explicit handles returned by tools.
- Streamable HTTP requests must include `Mcp-Method` and `Mcp-Name` headers (SEP-2243).
- **Multi Round-Trip Requests (SEP-2322)** replace server-initiated `elicitation/create`, `sampling/createMessage` and `roots/list`. The server returns `resultType: "input_required"`, and the client retries the original call with `inputResponses`.
- `ttlMs`/`cacheScope` are added on list/read results (SEP-2549).
- Auth: RFC 9207 `iss` validation (SEP-2468); `application_type` in DCR (SEP-837); client credentials bound to their issuer (SEP-2352). **DCR is deprecated in favor of CIMD.**
- Tasks moved to the `io.modelcontextprotocol/tasks` extension (SEP-2663), with `tasks/get`, `tasks/update` and `subscriptions/listen`. MCP Apps and Enterprise Managed Authorization (EMA) are extensions.
- Roots, Sampling and Logging are deprecated (SEP-2577), with a minimum 12-month window. HTTP+SSE transport is deprecated.
- TypeScript, Python, Go and C# SDKs support 2026-07-28; Rust is in beta.
- Adoption is early. Cloudflare, GitHub and Google Cloud are reported early adopters, and Microsoft shipped C# SDK v2.0. — [Composio](https://composio.dev/blog/mcp-2026-07-28-update-statelessness-apps-auth); [MS devblog](https://devblogs.microsoft.com/dotnet/announcing-v20-of-the-official-mcp-csharp-sdk/)

**Authorization (normative, 2025-11-25 text)** — [MCP authorization 2025-11-25](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/basic/authorization.mdx)
- Built on OAuth 2.1 (draft-ietf-oauth-v2-1-13), RFC 8414, RFC 7591, RFC 9728 and the CIMD draft. It applies to HTTP transports only; STDIO takes credentials from the environment.
- The server MUST serve RFC 9728 metadata (`/.well-known/oauth-protected-resource`, `authorization_servers`) and advertise it via `WWW-Authenticate: ... resource_metadata=...` on 401.
- Clients MUST send `resource` (RFC 8707, the canonical server URI) in authorization and token requests. PKCE `S256` is MUST.
- Servers MUST validate the token audience. **Token passthrough to upstream APIs is prohibited**, so upstream calls need a separate token.
- Step-up: return 403 with `error="insufficient_scope"`, `scope` and `resource_metadata`. A client acting for a user SHOULD do step-up authorization.
- Client registration priority: pre-registered client, then CIMD (`client_id_metadata_document_supported`), then DCR, then asking the user.

**Python SDK FastMCP minimal example** **[training knowledge; verify against the current `mcp` package, which supports 2026-07-28 per the blog]**
```python
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("institution-agent")

class Quote(BaseModel):
    amount_drops: int
    destination: str

@mcp.tool()
def quote_payment(dest: str, usd: float) -> Quote:   # typed return -> structuredContent + outputSchema
    """Quote an XRPL payment."""
    return Quote(amount_drops=int(usd * 1_000_000), destination=dest)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")   # or "stdio"
```

**MCP vs A2A positioning**
- MCP is agent-to-tool/context (a client calls a server's tools, resources and prompts). A2A is agent-to-agent between opaque peers, with tasks, streaming and multi-turn exchanges. Google positions them as complementary. **[training knowledge; widely stated]**
- 2026-07-28 MCP adds a Tasks extension and MRTR, which narrows the gap. A2A keeps peer discovery (Agent Card), signed identity cards and the commerce extensions (AP2/x402). — [MCP blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/); [A2A spec](https://raw.githubusercontent.com/a2aproject/A2A/main/docs/specification.md)

**Payment-related MCP servers**
- x402 v2 over HTTP uses base64 headers: `PAYMENT-REQUIRED` (PaymentRequired), `PAYMENT-SIGNATURE` (PaymentPayload) and `PAYMENT-RESPONSE` (SettlementResponse). v2 renamed `maxAmountRequired` to `amount` and uses CAIP-2 network IDs (e.g. `eip155:84532`). — [x402 docs](https://docs.x402.org/core-concepts/http-402); [Alchemy guide](https://www.alchemy.com/overviews/how-to-add-x402-payments-to-an-mcp-server)
- x402 over MCP: an unpaid call returns `isError: true` with a PaymentRequired object in `structuredContent`. The client retries with `_meta["x402/payment"]`, and the server returns `_meta["x402/payment-response"]`. — [Alchemy guide](https://www.alchemy.com/overviews/how-to-add-x402-payments-to-an-mcp-server)
- The x402 `upto` scheme has the client sign once against a ceiling, and the facilitator settles the actual amount, which must be at or below that ceiling. This is directly relevant to "spending limits". — [skills.cat x402 summary](https://skills.cat/skills/thegreataxios/agent-skills/x402) (secondary)
- XRPL MCP servers (all third-party; claims unverified):
  - RomThpt `mcp-xrpl`: TypeScript; reads accounts and transactions and submits transactions on Mainnet/Testnet/Devnet. — [Glama](https://glama.ai/mcp/servers/@RomThpt/mcp-xrpl/blob/db7cc873f3bfde33e10851066f7de34c9493c13e/README.md)
  - ScriptMasterLabs `mcp-x402-xrpl`: x402 middleware for paying per tool call in XRP/RLUSD/XAH, with on-ledger proof. Its claim to be the "only x402 for XRPL" is vendor marketing. — [mcp.so](https://mcp.so/ja/servers/mcp-x402-xrpl)
  - XRPL Agent Wallet MCP (design docs, Jan 2026): Regular Keys, encrypted key store, and a three-tier policy (auto-approve / require-review / deny). — [Glama docs](https://glama.ai/mcp/servers/@ClecknerT/xrpl-wallet-mcp/blob/b17a60004a6293d1bcf15a6ffc4c31ace92fd351/docs/index.md)
  - No official XRPL Foundation/Ripple x402 announcement was found.

### Inferences
- If the demo uses MCP, decide between 2025-11-25 (stateful; form/URL elicitation via server request) and 2026-07-28 (MRTR `input_required`). Many hosts (Claude Desktop, IDEs) may still be mid-migration in Oct 2026, so test with the actual client.
- URL-mode elicitation (2025-11-25) and MRTR `input_required` (2026-07-28) are the protocol-native ways to show a "consent / approve spend" screen to the human.
- Because token passthrough is prohibited, an MCP server that pays on XRPL for a user must hold its own credential (or a delegated mandate), not reuse the user's token. That is a natural fit for a separate signed mandate.

### Gaps
- The full normative 2026-07-28 authorization page was not read (the official domain did not resolve). The current Python `mcp` package version was not verified.
- Confirmation is needed on whether 2026-07-28 changed structured output (`outputSchema`/`structuredContent`). It is presumably retained, but this was not verified.

## 3. Agent identity and delegation: KYA, VC 2.0, DIDs, RFC 8693 and IETF agent drafts, Web Bot Auth, consent receipts, GA4GH

### Takeaway
The 2026 stack layers three things. (1) **Agent/bot authentication** via HTTP Message Signatures (RFC 9421), through Web Bot Auth (now an IETF WG draft), Visa TAP, and Cloudflare signed agents. (2) **Delegated authorization** via OAuth (RFC 8693 token exchange with an `act` claim, the OBO-for-agents draft, the OAuth Actor Profile, attenuating agent tokens, AAuth). (3) **Portable credentials/mandates** via W3C VC 2.0 + DIDs, AP2 mandates, and GA4GH Visas. No single standard yet governs "agent spending limits". AP2 IntentMandate and x402 `upto` are the closest.

### Cited Findings
**KYA / network programs**
- Skyfire KYAPay verifies to both the consumer and merchant that an agent is acting for a real, authorized user. A Dec 2025 demo combined KYAPay with Visa Intelligent Commerce and the Trusted Agent Protocol, where Skyfire gives the agent access to a Visa credential without exposing it. — [BusinessWire Dec 18 2025](https://www.businesswire.com/news/home/20251218520399/en/Skyfire-Demonstrates-Secure-Agentic-Commerce-Purchase-Using-the-KYAPay-Protocol-and-Visa-Intelligent-Commerce)
- Visa Trusted Agent Protocol is based on HTTP Message Signatures (RFC 9421) and aligned with Web Bot Auth. Merchants rebuild the signature base and verify it against keys from Visa's Key Store. It defines three signatures: agent recognition, consumer/device identity, and payment container. — [Visa TAP spec](https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications)
- TAP went live Oct 14, 2025 with 12 partners. Mastercard Agent Pay was unveiled Apr 29, 2025, ties agent identity into "agentic" network tokens, and reached full US rollout Nov 2025. — [eco.com explainer](https://eco.com/support/en/articles/14846277-know-your-agent-kya-identity-for-agent-payments) (secondary; treat dates as unverified)
- Trulioo KYA: no reliable source was found in this pass.

**HTTP-level agent auth**
- Web Bot Auth: started as draft-meunier-web-bot-auth-architecture (Cloudflare, Apr–Aug 2025, Informational). It is now the working-group draft **draft-ietf-webbotauth-httpsig-protocol-00 (Sep 2026, Standards Track; Meunier/Cloudflare + Major/Google)**. It defines the `Signature-Agent` header, a JWKS-based key directory, and a well-known URI for that directory, built on RFC 9421. — [IETF draft](https://datatracker.ietf.org/doc/html/draft-ietf-webbotauth-httpsig-protocol-00)
- Cloudflare "signed agents" (2025) is the commercial program on top of Web Bot Auth: verified bots/agents sign requests with Ed25519 via RFC 9421 and `Signature-Agent`. **[training knowledge, unverified]**
- RFC 9421 (HTTP Message Signatures, Feb 2024) covers the `Signature-Input`/`Signature` headers and covered components such as `@method`, `@authority` and `@path`. **[training knowledge]**

**OAuth delegation drafts**
- draft-oauth-ai-agents-on-behalf-of-user-02 (WSO2, Aug 2025; expired Feb 2026; not adopted by the WG) adds `requested_actor` to the authorization request and `actor_token` to the token request, for front-channel user consent to a specific agent. — [IETF datatracker](https://datatracker.ietf.org/doc/html/draft-oauth-ai-agents-on-behalf-of-user-02)
- A suggested combination is OBO for the initial consent, then RFC 8693 token exchange downstream. RFC 8693 issues tokens with an `act` (actor) claim, and nested `act` claims form the delegation chain. — [WorkOS](https://workos.com/blog/oauth-on-behalf-of-ai-agents); [MojoAuth worked example](https://mojoauth.com/blog/oauth-2-0-token-exchange-rfc-8693-for-agent-delegation-a-worked-example)
- Newer drafts:
  - draft-mcguinness-oauth-actor-profile ("OAuth Actor Profile", Apr 2026). — [datatracker](https://datatracker.ietf.org/doc/draft-mcguinness-oauth-actor-profile/)
  - draft-niyikiza-oauth-attenuating-agent-tokens-01 (Jun 2026): attenuating tokens without a per-hop AS round trip, macaroon/biscuit-like. — [WorkOS (cites it)](https://workos.com/blog/oauth-on-behalf-of-ai-agents)
- AWS AgentCore Identity reportedly shipped RFC 8693 on-behalf-of exchange (GA Apr 2026). — Single secondary source via [Oleria blog](https://www.oleria.com/blog/on-behalf-of-identity-at-machine-speed); unverified.
- **AAuth** (Dick Hardt): draft-hardt-oauth-aauth-protocol, from -00 (Apr 29, 2026) to -10 (Aug 2026). It covers agent-to-resource auth and identity claims, builds on the HTTP Signature Keys draft, and defines four modes (identity-based, resource-managed, PS-managed, federated) and the headers `AAuth-Requirement`, `AAuth-Access` and `AAuth-Capabilities`. Repo: github.com/dickhardt/AAuth. — [IETF draft -10](https://www.ietf.org/ietf-ftp/internet-drafts/draft-hardt-oauth-aauth-protocol-10.html)

**VCs and DIDs**
- W3C Verifiable Credentials Data Model 2.0 became a W3C Recommendation (May 2025). It covers `@context` `https://www.w3.org/ns/credentials/v2`, `issuer`, `validFrom`/`validUntil`, `credentialSubject` and `credentialStatus`, secured with Data Integrity or VC-JOSE-COSE (SD-JWT/COSE). — [W3C TR](https://www.w3.org/TR/vc-data-model-2.0/) **[training knowledge; URL not re-fetched]**
- **did:xrpl (XLS-40, Final)**:
  - Syntax is `did:xrpl:<network-id>:<r-address or hex master pubkey>`, e.g. `did:xrpl:1:rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh`.
  - The DID ledger object (`LedgerEntryType 0x0049`) has optional fields `URI`, `Data` and `DIDDocument`, each at most 256 bytes and not validated. It costs one owner reserve.
  - Transactions are `DIDSet` (type 40: create/update; an empty string deletes a field) and `DIDDelete` (type 41).
  - Source: [XLS-40](https://raw.githubusercontent.com/XRPLF/XRPL-Standards/master/XLS-0040-decentralized-identity/README.md)
- did:web resolves `did:web:example.com` to `https://example.com/.well-known/did.json`. **[training knowledge]**
- XRPL Credentials (XLS-70: `CredentialCreate`/`CredentialAccept`, with issuer+subject+`CredentialType` on-ledger) and Permissioned Domains (XLS-80) provide on-ledger attestations usable for KYA gating. **[training knowledge; amendment activation status on mainnet unverified]**

**Consent receipts**
- ISO/IEC TS 27560:2023 defines an interoperable, extensible structure for consent records and receipts, with listed fields and cardinality. It complements ISO/IEC 29184. No 2025 revision was found. Kantara's Consent Receipt v1.1 was the predecessor input. — [arXiv 2405.04528](https://arxiv.org/pdf/2405.04528)

**GA4GH Passports/Visas**
- A Passport is the JWT claim `ga4gh_passport_v1`, holding an array of signed Visa JWTs. The Visa types are `AffiliationAndRole`, `AcceptedTermsAndPolicies`, `ResearcherStatus`, `ControlledAccessGrants` and `LinkedIdentities`. Approved 2019; AAI defines the exchange. — [PMC8591913](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8591913/)
- Implementations map a `ControlledAccessGrants` visa to permissions; for example, Pathling grants `pathling:aggregate/search/extract`. Implementations vary in claim structure. — [Pathling docs](https://pathling.csiro.au/docs/server/authorization); [beacon-python](https://beacon-python.readthedocs.io/en/latest/permissions.html)
- Each Visa carries `ga4gh_visa_v1{type, asserted, value, source, by, conditions}`. **[training knowledge]**

### Inferences
- A practical demo identity stack:
  - Personal agent identity: an XRPL account + `did:xrpl` DID whose `URI` points to a did.json with a verification key.
  - Institution agent identity: a signed A2A Agent Card (JWS `kid` resolving to the DID doc or a JWKS).
  - Transport auth: RFC 9421 signatures with `Signature-Agent` (Web Bot Auth style).
  - Delegation: a VC 2.0 "mandate" credential issued by the user's DID to the agent's DID, carrying the spending cap, expiry and consent scope (for example ISO 27560-shaped purpose/data fields).
- GA4GH Visas are a good analog for "consent-scoped access to sensitive data" (health/research). A `ControlledAccessGrants`-style visa can be modeled as a VC.

### Gaps
- Trulioo and Mastercard KYA specifics were not found from primary sources. Cloudflare signed-agents details were not re-verified. The VC 2.0 recommendation date was not re-fetched. XLS-70/80 mainnet status is unverified.

## 4. Patterns for verifiable spending limits / delegated mandates that a ledger can enforce

### Takeaway
Combine off-ledger signed mandates (AP2 IntentMandate VC or x402 `upto` signature) for intent/consent with **on-ledger enforcement primitives**, so a cap holds even if the agent misbehaves. Standards don't yet define ledger-enforced agent caps, so this is a design choice.

### Cited Findings
- AP2: the IntentMandate (user-signed constraints) is followed by a merchant-signed CartMandate and then the PaymentMandate. The verifier checks that the cart falls within the intent constraints. — [Affinidi AP2](https://docs.affinidi.com/products/affinidi-trust-fabric/agent-gateway/concepts/protocols/ap2/); [AP2 A2A ext](https://ap2-protocol.org/a2a-extension)
- x402 `upto`: the payer signs a ceiling, and the facilitator settles at most that amount. — [skills.cat x402](https://skills.cat/skills/thegreataxios/agent-skills/x402)
- Policy-controlled signing for XRPL agents uses Regular Keys and auto/review/deny tiers. — [XRPL Agent Wallet MCP docs](https://glama.ai/mcp/servers/@ClecknerT/xrpl-wallet-mcp/blob/b17a60004a6293d1bcf15a6ffc4c31ace92fd351/docs/index.md)
- Attenuating agent tokens: each hop can narrow scope offline. — [WorkOS citing draft-niyikiza](https://workos.com/blog/oauth-on-behalf-of-ai-agents)
- MCP step-up via `insufficient_scope` allows incremental consent when an agent exceeds its current scope. — [MCP auth](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/basic/authorization.mdx)

### Inferences
These XRPL primitive descriptions come from training knowledge and should be verified on xrpl.org.
- **Funded sub-account**: the agent gets its own XRPL account funded only up to the cap. This is the simplest hard limit, enforced by the ledger.
- **Payment Channels**: the user opens a channel with amount = cap. The agent or institution redeems signed claims, which can never exceed the channel amount. `SettleDelay`/`Expiration` give time bounds. This is a good fit for metered or streaming payments, and the closest XRPL analog to x402 `upto`.
- **Escrow** (`EscrowCreate` with `FinishAfter`/`CancelAfter`/crypto-condition, including IOU/MPT escrow if enabled) gives conditional release.
- **Checks** (`CheckCreate` with `SendMax`): the institution can cash up to `SendMax` and no more, with `Expiration`. This is a "pull with a ceiling" pattern.
- **Multisig / SignerList**: payments above a threshold need the user's co-signature, giving human-in-the-loop for large spends.
- **Credentials + Permissioned Domains/DEX**: only KYA-credentialed agent accounts can transact.
- **Binding mandate to ledger**: put the mandate VC hash (or AP2 IntentMandate hash) in the transaction `Memos` field. The audit trail then links the on-ledger payment to the signed consent. Store the user's DID in `did:xrpl` so verifiers resolve keys from the ledger.

Recommended demo shape:
- Personal agent ⇄ institution agent over A2A 1.0, with a signed Agent Card and an AP2-style IntentMandate DataPart.
- Institution agent exposes its tools to LLM hosts via MCP (OAuth 2.1 / CIMD).
- Settlement via an XRPL Payment Channel or Check sized to the mandate cap, with the mandate hash in Memos.

### Gaps
- No standard defines how a ledger verifies an AP2/VC mandate natively. The enforcement shown here comes from the funding/ceiling primitives, not from on-chain verification of the VC.
- XRPL Hooks/smart-escrow (programmable enforcement) status on mainnet was not verified.
