# Agent-driven data marketplaces and agentic-payment hackathon winners (2025-2026), for a consented-health-data-on-XRPL project

> Method note: researched 2026-10-25. Page fetching (WebFetch/curl) was blocked in this environment: DNS failures, and a proxy 403 on CONNECT. So every finding below comes from search-engine result summaries of the cited URLs, not from reading the full pages. Treat exact prize amounts and placements as "reported", and open the URL before quoting it on stage. Many secondary sources are crypto-news aggregators (Bitget, Phemex, MEXC); they are flagged where used.

## Q1. Comparable agent/data marketplaces (Ocean, Vana, Story/Poseidon, Cloudflare pay-per-crawl, x402 data APIs, health data exchanges, dynamic consent, DCTs)

### Takeaway
"Monetize private data without moving it" is already claimed in general by others: Ocean has compute-to-data, Vana has DataDAOs with TEE validation, and Story/Poseidon has on-chain consented licensing. In health, the incumbents (PicnicHealth, GA4GH Passports) do consent and access control with no payments or agents. No source found combines (a) per-query consent negotiated by a patient-side agent, (b) a machine-payable request from a research institution's agent, and (c) settlement on XRPL. That combination is the open lane.

### Cited Findings
**Ocean Protocol (compute-to-data)**
- Ocean's docs say health records are too sensitive to sell outright. Compute-to-data (C2D) lets owners sell compute access instead of raw data, for example letting an algorithm compute patients' average age without revealing anything else. — [Ocean docs: Compute to data](https://docs.oceanprotocol.com/developers/compute-to-data)
- In May 2025 Ocean promoted C2D for training AI on private datasets without exposing them. — [Ocean Protocol on X](https://x.com/oceanprotocol/status/1921959202362208470)
- An Ocean blog post mentions a prototype that pairs Ocean with multi-party computation (MPC) for healthcare image classification. — [Ocean blog](https://blog.oceanprotocol.com/how-does-ocean-compute-to-data-relate-to-other-privacy-preserving-approaches-b4e1c330483)
- Brainstem Health is described as using Ocean technology so users can manage and monetize personal health data from a wearable. The source is a third-party review, and the project's current status is unverified. — [Coin Bureau review](https://coinbureau.com/review/ocean-protocol)
- Uncertainty: I found no documented 2025-2026 production deployment of C2D with a named hospital. The hospital "train model, get weights back" scenario in reviews is illustrative only. — [Zipmex 2026 guide](https://zipmex.com/blog/what-is-ocean-protocol-the-2026-expert-guide-to-ocean/)

**Vana (DataDAOs, personal data)**
- Users write their data to Vana under their own wallet, then grant a DataDAO access for AI training. Vana's example: a user's health history in one DataDAO and genetic data in another can be linked through one shared identity. — [Vana: Accelerating the AI data revolution (Nov 2024)](https://vana.org/blog/accelerating-ai-data-revolution)
- Vana uses trusted execution environments (TEEs) to validate, anonymize and score data before it is accepted. Its VRC-20 tokens can represent ownership of health data, among other data types. — [QuickNode builders guide: Vana](https://www.quicknode.com/builders-guide/tools/vana)
- Binance Research lists DNA DataDAO (genetics), MindDAO (mental health) and an Oura sleep-data DAO as health DataDAOs. This is an older snapshot; current activity is unverified. — [Binance Research: Vana](https://www.binance.com/en/research/projects/vana)
- Vana's 2025 call for DataDAOs does not mention health as a priority category. — [Vana 2025 call for DataDAOs](https://vana.org/posts/2025-call-for-datadaos)

**Story Protocol / Poseidon / DATA Foundation (licensing)**
- Poseidon is an AI data layer built on Story. It raised a $15M seed led by a16z crypto (announced July 22, 2025, per reports). Data contributions are consented, registered on-chain as IP, and licensed to AI companies. — [Blockworks](https://www.blockworks.co/news/poseidon-raises-15m-ais-data-layer); [Pulse 2.0](https://pulse2.com/poseidon-15-million-seed-funding-raised-for-ai-data-licensing)
- In June 2026 Story rebranded as the "DATA Foundation", with Poseidon as its processing layer and "Trace" as an on-chain registry that lets AI companies verify whole datasets. — [Cointelegraph](https://regional-front.cointelegraph.com/news/story-protocol-pivots-to-ai-with-rebrand-to-data-foundation)
- An aggregator reports that Story's token fell about 98% from its September 2025 high. The 1.1B Kled records figure is secondary. Both are unverified. — [LetsDataScience](https://letsdatascience.com/news/story-protocol-rebrands-as-data-foundation-targets-ai-traini-5bcf45de)

**Cloudflare pay-per-crawl and the x402 Foundation**
- Cloudflare launched pay-per-crawl in private beta on July 1, 2025. Publishers can allow, charge or block each crawler. — [PPC Land](https://ppc.land/cloudflare-launches-pay-per-crawl-to-monetize-ai-content-access/)
- Cloudflare and Coinbase announced the x402 Foundation in September 2025 to standardize HTTP 402 payments. Cloudflare said it was already returning more than 1B HTTP 402 responses a day that bots largely ignored, and it was piloting deferred payments in pay-per-crawl. — [4 Pillars research](https://research.4pillars.io/en/research/cloudflare-and-x402-the-future-of-the-agent-web); [CryptoSlate](https://cryptoslate.com/cloudflare-and-coinbase-plan-to-tax-ai-bots-crawling-20-of-the-internet/?rand=6792)
- Ripple joined the x402 Foundation as a Premier Member on July 14, 2026. Per reports, the foundation sits under the Linux Foundation and launched with 40 members. — [Börse Express (DE)](https://www.boerse-express.com/news/articles/xrp-ripple-tritt-x402-foundation-bei-928251); [Bitcoin.com (SK)](https://news.bitcoin.com/sk/xrp-sa-zapaja-do-iniciativy-zameranej-na-platby-prostrednictvom-agentov-umelej-inteligencie-kedze-spolocnost-ripple-vstupila-do-nadacie-x402/)

**x402 on XRPL (directly relevant rails)**
- t54's x402 facilitator went live on XRPL around February 2026. Agents pay in XRP or RLUSD without API keys or accounts, and the facilitator does verification and on-chain settlement. — [MEXC news (aggregator)](https://www.mexc.com/tr-CT/news/971374)
- Ripple launched an "XRPL AI Starter Kit" for x402 agent payments in XRP and RLUSD on June 10, 2026, citing about 3-5s settlement. — [DEXTools (ES)](https://www.dextools.io/news/ripple-xrpl-ai-starter-kit-xrp-rlusd-agentic-payments-june-2026-es)
- Virtuals' Agent Commerce Protocol (escrowed jobs, evaluator verification) is paired with t54's facilitator for settlement in XRP and RLUSD. — [cryptonews.net](https://cryptonews.net/news/market/32460348/)
- The `r402-xrpl` Rust crate implements an XRPL "exact" x402 scheme with RLUSD and XRP helpers, a default fee cap and ledger-timeout settings. — [docs.rs r402-xrpl](https://docs.rs/r402-xrpl)
- XRPL Commons reports that more than 5.6M x402 transactions have settled on XRPL. This figure is from organizer material relayed by search; I could not open the page to confirm it. — [Developer Tech](https://www.developer-tech.com/news/xrpl-commons-hackathon-puts-ai-agent-payments-to-the-test/)

**Health data exchanges, consent and cooperatives**
- PicnicHealth collects medical records from consenting patients, de-identifies and aggregates them, and gives researchers access only on patient opt-in. — [PicnicHealth Research Platform](https://picnichealth.com/blogs/introducing-the-picnichealth-research-platform)
- PicnicHealth launched "ThumbPrint" in March 2026 as a "patient-anchored alternative to tokenization": consent-first enrollment of identified trial participants with ongoing engagement. — [PR Newswire](https://www.prnewswire.com/news-releases/picnichealth-launches-thumbprint-a-patient-anchored-alternative-to-tokenization-302725366.html)
- Orsini and PicnicHealth partnered in January 2025 on drug-specific rare-disease registries that combine EMR data with patient-reported data. — [Orsini](https://www.orsini.com/orsini-picnichealth-partnership/)
- Under the GA4GH Passport standard, data stewards issue signed "visas" that carry a researcher's roles and permissions in machine-readable form, so access can be federated across clouds and institutions. — [GA4GH Passport paper (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8591913/); [Google healthcare-federated-access-services](https://github.com/GoogleCloudPlatform/healthcare-federated-access-services)
- ELIXIR AAI (the Finnish and Czech ELIXIR nodes) was the first implementer of Passports. — [CSC](https://csc.fi/en/news/ga4gh-passport-accelerates-sharing-of-biomedical-datasets-for-research/)

### Inferences
- Positioning: Ocean, Vana and Poseidon sell datasets or compute in bulk to AI labs. This project sells per-request, per-purpose, revocable access, negotiated agent to agent. Borrowing GA4GH vocabulary (visa = researcher credential, purpose of use) makes it legible to research judges and to institutions.
- PicnicHealth's ThumbPrint frames tokenization as a privacy liability. A demo that shows no raw PHI on-chain, with only consent hashes, a payment and a receipt on the ledger, answers that objection directly.
- The XRPL rails exist (t54 facilitator, the Ripple starter kit, RLUSD). Judges will expect you to use them rather than invent your own payment protocol.

### Gaps
- No primary source found for Hu-manity's current status, or for named 2025-2026 health "data cooperatives" (for example MIDATA or Driver), or for dynamic-consent vendors in clinical research. Searches returned nothing usable.
- No source found for decentralized clinical trials using agent automation in 2025-2026.
- I found no live volume data for x402 data-feed APIs specifically.

## Q2. Hackathon winners 2025-2026 (XRPL, Coinbase x402/CDP, ETHGlobal, Solana/Cronos/EF x402, AP2)

### Takeaway
Winners cluster around three things. (1) Infrastructure or primitives other agents can reuse: execution fabrics, payment channels, MCP paywalls. (2) Security and guardrails for agents: Cronos Shield took 2nd place. (3) Commerce that clearly works end to end: Shopify, marketplaces. Health or data-consent entries are absent from every winner list I found, which is both a whitespace and a risk: you have to prove the payments are real.

### Cited Findings
**XRPL**
- XRPL Commons is running a 36-hour AI & Fintech XRPL Hackathon in New York on Oct 24-25, 2026, with more than $40K in prizes. It has an "Agentic Finance" track for agents that make payments and manage funds, and winners get access to grants and incubation. Results were not yet published at research time. — [HackerNoon](https://hackernoon.com/xrpl-commons-hosts-36-hour-nyc-hackathon-to-build-on-chain-lending-and-ai-payments-on-xrpl); [Developer Tech](https://www.developer-tech.com/news/xrpl-commons-hackathon-puts-ai-agent-payments-to-the-test/)
- Builders at the same event test proposed native lending tools before validator approval. — [crypto.news](https://crypto.news/xrp-ledger-builders-native-lending-before-approval/); [TokenPost](https://www.tokenpost.com/news/technology/31933)
- Ledger's bounty at XRPL NYC: an Agentic Finance track for agents that pay for APIs, tools or services through Ledger-secured flows, including x402-style pay-per-use, with a $10K pool across three categories. — [Ledger Developer Portal](https://developers.ledger.com/xrplnyc)
- The Italian XRPL Hackathon (IXH25, Nov 8, 2025) lists PermiX in 1st place and Nexgen in 2nd. Agent Octopus, an energy-payments agent, is also listed, placement unclear. — [XRPL Commons projects](https://hackathons.xrpl-commons.org/projects)
- Older XRPL hackathon results: [DoraHacks XRPL Summer Hackathon results](https://dorahacks.io/hackathon/xrpl-hackathon/results); [XRPL Impact Devpost](https://xrplimpact.devpost.com/)

**Coinbase CDP**
- The Agents in Action hackathon ran May 14 - Jun 26, 2025, built on x402, CDP Wallet and AgentKit, with Coinbase, AWS, Akash and Pinata tracks. Reported Coinbase-track winners: Best Use of x402 + CDP Wallet went to Cash Drive, Snack Money API and Infinite Bazaar. Best Use of x402 went to MCPay.fun, 1shot API and M2m. Demo Day was at AWS Loft on July 10. Placement labels on the page are ambiguous. — [Coinbase: Agents in Action winners](https://www.coinbase.com/developer-platform/discover/launches/agents-in-action-winners); [Demo Day preview](https://www.coinbase.com/en-mx/developer-platform/discover/launches/agents-in-action-demo-day)
- The CDP AI Hackathon in early 2025 was won by Mamoriko. — [ChainCatcher](https://www.chaincatcher.com/en/article/2165642); [CoinbaseDev on X](https://x.com/CoinbaseDev/status/1886468701689631006)
- The SF Agentic Commerce x402 Hackathon (SKALE-led) offered more than $50K across Coinbase, Google and Virtuals tracks. The Coinbase track was reportedly won by Superpage, with Pincer second. — [SKALE recap](https://www.skale.space/blog/san-francisco-agentic-commerce-x402-hackathon-recap-winners); [DoraHacks report](https://dorahacks.io/hackathon/x402/report)

**Solana, Cronos and Ethereum Foundation x402 hackathons**
- Solana x402 Hackathon main-track winners (announced Nov 25, 2025): Intelligence Cubed (reported #1 and/or Best x402 API Integration, about $20K), PlaiPin, x402 Shopify Commerce, Amiko Marketplace and MoneyMQ. Partner tracks (Dec 2, 2025) included Sentinel Agent and Galaksio (Best use of CDP Embedded Wallets). Sources on the categories conflict. — [Solana on X](https://x.com/solana/status/1993377018487230845); [Solana Devs on X](https://x.com/solana_devs/status/1995884095705059548); [Phemex (aggregator)](https://phemex.com/news/article/solana-x402-hackathon-announces-five-winning-projects-40873)
- Solana's ESP32 Native x402 (a hardware device that pays) is also named among the winners. — [Bitget (aggregator)](https://www.bitget.com/news/detail/12560605084078)
- Cronos x402 PayTech Hackathon (191 submissions):
  - 1st: AgentFabric, an "agent-native x402 execution fabric" (a $24K residency).
  - 2nd: Cronos Shield, security for AI agents ($5K).
  - 3rd: CroIgnite, x402 creator micropayments ($2K).
  - Track winners: SoulForge Market (Best x402 AI Agentic Finance) and Faktory (Best ecosystem integration).
  - Criteria (from a third-party aggregator only): innovation, agentic functionality, execution quality, ecosystem value.
  - [Cronos blog](https://blog.cronos.org/p/announcing-the-cronos-x402-hackathon); [DoraHacks winners](https://dorahacks.io/hackathon/cronos-x402/winner); [CompeteHub](https://www.competehub.dev/en/competitions/dorahackscronos-x402)
- The Ethereum Foundation x402 hackathon (reported around January 2026) named winners including x402-sf (Superfluid streaming) and Cheddr Payment Channels x402. — [Bitget (aggregator)](https://www.bitget.com/news/detail/12560605158202); [Phemex](https://phemex.com/news/article/ethereum-foundation-concludes-x402-hackathon-announces-winning-projects-54134)

**ETHGlobal**
- Agentic Ethereum 2025 had 10 finalists from 518 projects (Feb 14, 2025): AIMen, Nimble (an agent solver network for swaps and Morpho vaults), SecretAgent, Smol Universe, Synapze, bouncer.ai, PvPvAI, Shaman, Streme.fun and YieldSeeker. CDP, Autonome and Nethermind each put up $20K in prizes. — [ETHGlobal on X](https://x.com/ETHGlobal/status/1890448806975795550); [ETHGlobal Agents prizes](https://ethglobal.com/events/agents/prizes)
- AI agents, privacy and prediction markets dominated the ETHGlobal Cannes 2026 finalists. — [crypto.news](https://crypto.news/ai-agents-privacy-and-prediction-markets-define-ethglobal-cannes-2026-finalists/)
- A third-party analysis of about 8,200 ETHGlobal projects claims agent projects at Agentic Ethereum won sponsor prizes at higher rates. It is not rigorous. — [Medium (simbro)](https://simbro.medium.com/what-8-200-hackathon-projects-reveal-about-what-actually-wins-f105346ec97c)

**Google AP2 / A2A**
- AP2 was announced in September 2025. It uses signed "mandates" that record what the user authorized and within what limits. Google donated AP2 to the FIDO Alliance in April 2026, together with v0.2 and human-not-present updates. — [FIDO Alliance](https://fidoalliance.org/google-donates-agent-payments-protocol-to-fido-alliance/); [Allium](https://www.allium.so/blog/ap2-googles-agent-payments-protocol/)
- Uncertainty: I found no AP2-specific hackathon winner list. Google sponsored a track at the SF x402 hackathon (see SKALE above). — [awesome-agent-payments-protocol](https://github.com/aronaplana-os/awesome-agent-payments-protocol)

### Inferences
- Patterns in what judges rewarded:
  - Reusable infrastructure won 1st place in more than one event: AgentFabric, payment channels, MCP paywalls, API wrappers.
  - Agent security is a placing category in its own right (Cronos Shield, Sentinel Agent).
  - A tangible, real-world surface beats abstract demos: Shopify checkout, hardware ESP32, Cash Drive.
- For this project:
  - Frame the institution-side "consented data API behind x402 on XRPL" as reusable infrastructure.
  - Frame consent and spend guardrails as the security story.
  - Treat "health" as the vivid use case.
  - Map the patient's consent artifact to an AP2-style "mandate". It is the vocabulary judges now know.
- The XRPL NYC Agentic Finance and Ledger tracks explicitly reward x402-style pay-per-use with secure signing. Ledger-secured approval of the patient's consent policy, or of the institution's budget, could target the Ledger bounty as well.

### Gaps
- Official judging rubrics for XRPL Commons NYC 2026, Agents in Action and Solana x402 were not retrievable, because page fetch was blocked.
- Exact Coinbase placements are ambiguous on the source page.
- Final NYC 2026 results did not exist at research time.

## Q3. Common failure modes judges and builders flag in agent payment demos

### Takeaway
I found no published judge write-ups. Builder post-mortems and winning-repo READMEs point to the same failure modes, and avoiding them visibly makes a strong demo:
- spend checks that are not atomic
- caps per transaction only
- limits enforced inside the agent's own process, where prompt injection can bypass them
- dry-run activity mixed with live activity
- vague testnet labeling

### Cited Findings
- A dry-run mode that logged to the same store as real payments made a dashboard show about 4x the actual spend. — [jaklabs.io](https://jaklabs.io/blog/i-gave-an-ai-agent-a-debit-card)
- In a test of 40 concurrent payments, 28 succeeded and an agent spent $70 against a $10 remaining budget, because the check and the spend were not one atomic step. — [DEV Community](https://dev.to/quinn_854b15f517d8632ed4f/we-fired-40-payments-at-our-own-agent-at-the-same-instant-28-got-through-12-didnt-75m)
- Per-transaction caps don't bound the total: 100 compliant $500 transactions in a minute add up to a catastrophe, so daily and aggregate limits are needed. — [Proxy post-mortem](https://www.useproxy.ai/blog/ai-agent-overspend-postmortem)
- Limits should be enforced outside the agent, by the contract or ledger, because limits in the same process can be bypassed by content the agent reads. The reference example enforces a cap, an allowlist, an approval threshold and idempotency before the payment executes. — [Misthos (Circle Agent Wallets / ERC-8004 hackathon)](https://github.com/AZAR2305/Misthos); [Pink-Agentic-Payments spending-limit example](https://github.com/Pink-Agentic-Payments/agent-spending-limit-example)
- Testing the payment loop on testnet before going live is recommended practice. Credible hackathon repos label themselves "Unaudited. Testnet only." and mark team-run activity. — [DEV: test on testnet](https://dev.to/openclawcash/test-your-agents-payment-loop-on-a-testnet-before-it-goes-live-3n0a); [Misthos](https://github.com/AZAR2305/Misthos)
- Other practical issues: misleading error messages, and calls written against SDKs that have moved on by major versions. — [jaklabs.io](https://jaklabs.io/blog/i-gave-an-ai-agent-a-debit-card)

### Inferences
- Demo checklist derived from the above:
  - Show real XRPL testnet or devnet transaction hashes in an explorer, live.
  - Enforce the institution's budget and the patient's price floor and consent scope in a place the LLM cannot override. Candidates: XRPL native features (escrow, deposit authorization, credentials) or a policy service separate from the LLM.
  - Show one refused request (out of scope or over budget) as well as one successful one.
  - Make payments idempotent per request ID.
  - Put revocation on stage: the patient revokes, and the next request fails.
  - Never put PHI on-chain; only hashes and receipts go on the ledger.
  - Label testnet clearly.

### Gaps
- No primary judge or organizer statement found on the reasons they rejected agent-payment demos. The lessons above come from builders, not judges.
