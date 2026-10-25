# AI Agent Payments and Stablecoin Rails, with XRPL Specifics (as of Oct 25, 2026)

Method note: Direct WebFetch failed in this environment (DNS ENOTFOUND for chainalysis.com, docs.cdp.coinbase.com, xrpl.org). Every figure below comes from WebSearch result summaries, so all of them count as **secondary (search-summary)** unless the URL itself is a primary domain. Even then the content was not read in full and should be re-checked before publication. "[crypto-press only]" marks figures seen only in crypto or exchange-news outlets (KuCoin, crypto.news, CryptoDaily, Coinspeaker, MEXC and similar).

## 1. x402: scale, micro-payment share, Foundation, XRPL facilitator (t54)

### Takeaway
x402 has hundreds of millions of machine-initiated transactions across Base, Solana and XRPL, so the rail is real. Real commercial value is still small, though: tens of millions of USD in total, and much of the count is gamified, wash or "signaling" traffic. On XRPL, agentic x402 payments grew from about 1M (July 2026) to about 13.4–13.6M (October 2026), and RippleX says they are about 25% of ledger activity.

### Cited Findings
- Cumulative x402 transactions passed 200M as of June 2026 (citing the Major Matters tracker). The same piece says Artemis found more than 95% of activity is "protocol signaling" rather than buyer-seller exchange. Secondary, 2026. [Yahoo Finance](https://finance.yahoo.com/markets/crypto/articles/x402-foundation-activated-27-old-152440828.html)
- About 165M transactions and about $50M cumulative volume by late April 2026. Secondary blog, 2026. [DEV Community](https://dev.to/t49qnsx7qtkpanks/x402-hit-165-million-transactions-heres-what-it-still-cant-do-4f4d)
- More than 119M transactions on Base and about 35M on Solana (around March 2026). Secondary, 2026. [Sherlock](https://sherlock.xyz/post/x402-explained-the-http-402-payment-protocol)
- A CoinDesk analysis (March 2026), cited by several outlets, put real daily commercial x402 volume at about $28,000/day. Secondary-of-secondary; the original CoinDesk piece was not retrieved. [Yahoo Finance](https://finance.yahoo.com/markets/crypto/articles/x402-foundation-activated-27-old-152440828.html); [Sherlock](https://sherlock.xyz/post/x402-explained-the-http-402-payment-protocol)
- The x402.org dashboard reportedly showed about 75M transactions and about $24M trailing-30-day volume in mid-July 2026. Vendor-reported, relayed by a third party. [presenc.ai tracker](https://presenc.ai/research/x402-protocol-adoption-tracker-2026)
- Chainalysis ("Inside x402: 100M Agentic Payments on Base") says growth on Base was driven largely by meme-coin activity and has plateaued. Payments of $1 or more are now about 95% of volume (up from 49% in early 2025), and the $0.10–$1 band fell to about 4%. Primary analytics firm, but read only via search summary; date approximately 2026. [Chainalysis](https://www.chainalysis.com/blog/x402-agentic-payments-adoption/)
- **x402 Foundation:**
  - Cloudflare announced it was co-founding the x402 Foundation with Coinbase in September 2025, the same week it announced the "NET Dollar" stablecoin for agent pay-per-use and micropayments. [CoinDesk, Sep 25 2025](https://coindesk.com/business/2025/09/25/cloudflare-unveils-u-s-dollar-stablecoin-for-ai-powered-internet-economy); [Benzinga](https://www.benzinga.com/markets/equities/25/09/47873086/cloudflare-unveils-net-dollar-stablecoin-to-power-agentic-web)
  - Coinbase docs say the Foundation launched under the Linux Foundation on April 2, 2026, with 40 organizations at launch. Premier members listed: AWS, American Express, Cloudflare, Coinbase, Google, Mastercard, Shopify, Solana Foundation, Stripe, Visa. Primary domain, read via search summary. [Coinbase CDP docs](https://docs.cdp.coinbase.com/x402/support/x402-foundation)
  - Other reports list 17 premier members, including Adyen, Circle, Fiserv, Monad Foundation, MoonPay, **Ripple** and Stellar Development Foundation. Some outlets give an "operational launch" of July 14, 2026. Secondary. [The Defiant](https://thedefiant.io/news/infrastructure/coinbase-x402-payment-protocol-moves-to-linux-foundation); [Decrypt](https://decrypt.co/363173/coinbase-linux-foundation-launch-x402-foundation); [KuCoin [crypto-press only]](https://www.kucoin.com/news/flash/linux-foundation-launches-x402-foundation-with-visa-mastercard-among-founding-members)
  - Technical Steering Committee (as of July 15, 2026): Erik Reppel (Coinbase), Rohin Lohe (Cloudflare), Steve Kaliski (Stripe). Secondary. [Solana Compass](https://solanacompass.com/news/linux-foundation-launches-x402-foundation-as-open-standards-body-for-ai-agent-payments)
  - A Substack post claims NET Dollar still had no issuer or chain about six months after the announcement. Unverified. [Stablecoin Brief](https://stablecoinbrief.substack.com/p/for-cloudflare-stablecoin-is-optional)
- **XRPL / t54:**
  - xrpl.org documents x402 on XRPL. t54 maintains `x402-xrpl`, the reference implementation, which uses presigned Payment transactions and settles in XRP or RLUSD. t54 runs a hosted mainnet facilitator (xrpl-facilitator-mainnet.t54.ai) listed in x402's facilitator directory. Primary domain, via search summary. [xrpl.org: Agentic Payments with x402](https://xrpl.org/docs/agents/agentic-payments-x402); [t54 Trustline](https://www.t54.ai/trustline)
  - In July 2026 t54 added optional support for Mastercard's "Verifiable Intent" standard: a credential attached to a payment proves who authorized it, under what limits and for which purchase. t54's "Trustline" screens the payment before settlement. [t54 on X](https://x.com/t54ai/status/2080708873178992737); [Stablecoin Insider](https://stablecoininsider.org/xrpl-mastercard-verifiable-intent-agent-payments/)
  - 1.4M agentic transactions settled through the facilitator, up from 1M on July 8, 2026 [crypto-press only]. [Coinspeaker](https://www.coinspeaker.com/x402-protocol-xrpl-ai-agent-transactions-ripple/)
  - At an XRPL fee of about $0.0002, those 1.4M payments cost about $280 in total network fees [crypto-press only]. [crypto.news](https://crypto.news/ai-agents-made-1-4m-payments-on-xrpl-total-fees-280/)
  - More than 13.4M XRPL agentic x402 payments, confirmed October 10, 2026 by RippleX head of engineering J. Ayo Akinyele, who said agentic transactions are about 25% of all ledger activity. A later check showed more than 13.6M. The counts come from third-party trackers such as XRPL AI Hub, not an official RippleX dashboard [crypto-press only]. [KuCoin](https://www.kucoin.com/news/flash/xrp-ledger-surpasses-13-4-million-agentic-payments-milestone); [crypto.news](https://crypto.news/ex-ripple-exec-on-xrps-13m-ai-payments-whats-next/); [CryptoDaily, Jul 2026](https://cryptodaily.co.uk/2026/07/xrpl-nears-10m-agentic-transactions)

### Inferences
- High transaction counts with low value (about $24–50M against 100M+ transactions) mean the average x402 payment is well under $1, while Chainalysis says $1+ payments dominate value. Both are true at once: there are many tiny calls, and a few larger payments carry most of the value. This fits "small, frequent" settlement, but the "real demand" claim should be stated cautiously.
- XRPL went from 1M to 13M+ in about 3 months, so XRPL is now a meaningful x402 chain, though Base remains the largest by count.

### Gaps
- Could not confirm the official x402.org member roster or reconcile the April 2 and July 14, 2026 launch dates.
- No primary RippleX blog post with the 13.4M figure was retrieved; the figure came via exchange news.
- No reliable x402 USD value settled on XRPL specifically.

## 2. Agent payment standards: AP2, Visa, Mastercard, ACP, PayPal

### Takeaway
All major networks shipped agent-payment standards between April and October 2025. These are card or token-based: they deal with authorization, intent and identity, not cheap settlement. That leaves room for stablecoin rails such as x402 for sub-dollar payments.

### Cited Findings
- **Mastercard Agent Pay**: announced April 29, 2025 with Microsoft, IBM and Braintree. It uses "Agentic Tokens" bound to an agent, a merchant scope and a consent policy. Secondary explainer. [eco.com](https://eco.com/support/en/articles/15192001-what-is-mastercard-agent-pay-ai-agent-commerce-protocol-in-2026)
- **Visa Intelligent Commerce**: launched April 2025. It gives agents tokenized cards with user spending limits; reported partners include Anthropic, IBM, Microsoft, Mistral AI, OpenAI, Perplexity, Samsung and Stripe. In September 2025 Visa added an MCP Server and piloted an Acceptance Agent Toolkit. [AI Business](https://aibusiness.com/agentic-ai/visa-launches-ai-developer-tools-for-agentic-commerce); [Visa (primary)](https://corporate.visa.com/en/sites/visa-perspectives/innovation/visa-mcp-server-agent-acceptance-toolkit.html)
- **Google AP2**: announced September 16, 2025 with 60+ partners, including Mastercard, American Express, PayPal, Coinbase, Adyen, Worldpay, MetaMask, Salesforce, ServiceNow, Intuit and Etsy. It has an x402 extension for stablecoins. Partner list from a secondary explainer. [eco.com](https://eco.com/support/en/articles/14845479-ap2-agent-payments-protocol-explained)
- **OpenAI + Stripe ACP**: launched September 29, 2025 and open-sourced. Its first use was ChatGPT Instant Checkout, with Etsy as the first merchant. It uses Shared Payment Tokens. Secondary. [eco.com](https://eco.com/support/en/articles/14839400-what-is-agentic-commerce-the-2026-guide); [digitalapplied](https://www.digitalapplied.com/blog/agentic-commerce-standards-ucp-acp-ap2-2026-merchant-guide)
- **Visa Trusted Agent Protocol**: launched October 14, 2025 with Cloudflare, backed by Microsoft, Nuvei, Shopify, Stripe and Worldpay. It verifies agent identity to merchants; it does not move money. Mastercard launched similar agent tools the same week. [Digital Commerce 360, Oct 16 2025](https://www.digitalcommerce360.com/2025/10/16/visa-mastercard-both-launch-agentic-ai-payments-tools/)
- **PayPal**: was an AP2 launch partner, and launched agentic integrations the same week as Visa and Mastercard. [Retail TouchPoints](https://www.retailtouchpoints.com/topics/payments/visa-mastercard-paypal-dive-into-agentic-era-with-tools-that-help-consumers-use-ai-to-buy)

### Inferences
- The networks themselves now sit on the x402 Foundation (Visa, Mastercard, Amex). Card standards and stablecoin rails are converging rather than competing. Mastercard Verifiable Intent running on XRPL via t54 is a concrete example.

### Gaps
- No primary press releases were retrieved for AP2, ACP or Agent Pay; dates come from secondary explainers that agree with each other.
- The PayPal Agent Toolkit launch date was not confirmed in this pass (from memory it is about April 2025; unverified).

## 3. XRPL: Starter Kit, RLUSD, fees and settlement, amendments

### Takeaway
XRPL has the features per-contribution settlement needs: fees of fractions of a cent (about $0.0002), settlement in 3–5 seconds, an RLUSD stablecoin of about $2.5B, and native amendments now live for Credentials (September 2025), MPT (October 2025), TokenEscrow (February 2026) and PermissionedDomains (February 2026). Batch was pulled over a flaw and resubmitted as BatchV1_1 in xrpld 3.3.0; whether it is active on mainnet is unclear as of late October 2026.

### Cited Findings
- **XRPL AI Starter Kit**: launched by Ripple around June 10, 2026 as "phase 1". It supports x402 payments in XRP and RLUSD and includes the XRPL Docs MCP Server (for Claude Code, Claude Desktop and Cursor) plus Claude-compatible skills for wallet management and payments. Agents can pay "without API keys or accounts". [The Block, Jun 10 2026](https://www.theblock.co/news/business/2026-06-10-ripple-launches-toolkit-for-agentic-payments-on-xrpl-404243); [American Banker](https://www.americanbanker.com/payments/news/ripple-launches-agentic-payment-tech-toolkit); [crypto.news](https://crypto.news/ripple-introduces-xrpl-toolkit-to-support-ai-agent-transactions/)
- **Settlement and fees**: Ripple cites 3–5 second settlement [DEXTools [crypto-press only]](https://www.dextools.io/news/ripple-xrpl-ai-starter-kit-xrp-rlusd-agentic-payments-june-2026). The fee is about $0.0002 per transaction [crypto.news](https://crypto.news/ai-agents-made-1-4m-payments-on-xrpl-total-fees-280/). The protocol base fee is 10 drops (0.00001 XRP); this comes from background knowledge of xrpl.org docs and was not re-fetched.
- **RLUSD**:
  - Market cap about $2.49B on September 28, 2026, up about 86% from about $1.34B at the start of 2026. Roughly 56% sits on Ethereum and 44% on XRPL. PYUSD was about $2.74B at the time [crypto-press only]. [KuCoin](https://www.kucoin.com/news/flash/rlusd-market-cap-hits-2-49b-surpasses-86-growth-since-start-of-2026)
  - On-chain supply hit an all-time high of about $1.7B in May 2026. [Stablecoin Insider Q2 2026](https://stablecoininsider.org/rlusd-q2-2026-report-supply-growth-regulatory-wins-and-a-three-jurisdiction-footprint/)
- **Amendment activation dates** (secondary aggregator; xrpl.org could not be fetched): [xrpl.to](https://xrpl.to/insights/xrpl-amendments-explained); [xrpldashboard, Oct 24 2026 snapshot](https://xrpldashboard.com/amendments)

  | Amendment | Mainnet activation |
  |---|---|
  | Credentials | Sep 4, 2025 |
  | MPTokensV1 | Oct 2025 |
  | TokenEscrow | Feb 12, 2026 |
  | PermissionedDomains | Feb 4, 2026 |
  | PermissionedDEX | Feb 18, 2026 |

  Live status of Credentials, PermissionedDomains, PermissionedDEX and TokenEscrow is confirmed by xrpldashboard.
- **Batch**: the original Batch amendment was pulled before activation over an authorization flaw. xrpld 3.3.0 bundles BatchV1_1, PermissionDelegationV1_1, Confidential MPT, Dynamic MPT, and Sponsored Fees and Reserves. **Conflict:** xrpl.to says BatchV1_1 and PermissionDelegationV1_1 activated in early October 2026, but xrpldashboard (Oct 24, 2026) shows them still waiting on the 80%-for-14-days validator threshold. [CryptoSlate](https://cryptoslate.com/how-xrpl-validators-quietly-killed-a-silent-exploit-that-could-have-drained-victim-accounts-through-transaction-fees-alone/); [Cryip](https://cryip.co/xrpls-next-upgrade-resubmits-two-amendments-that-failed-security-review/); [intokened](https://intokened.com/en/news/xrpl-v330-six-upgrades-privacy-batch)
- **Escrow and multisig**: XRP escrow and multisign (SignerListSet) are long-standing features (multisign since 2016). TokenEscrow extends escrow to IOU and MPT tokens such as RLUSD. Based on the activation sources above; the multisign date is background knowledge and was not re-verified.

### Inferences
- What fits per-contribution settlement: escrow (conditional or time release of RLUSD via TokenEscrow), Credentials plus PermissionedDomains (KYC- or role-gated participants, such as verified data contributors), MPT (compact tokens carrying metadata), multisig (multi-party approval), and fees of about $0.0002. A $0.01 payment loses about 2% to the network fee, against a card loss far above 100%. Do not depend on Batch for a demo unless it is checked live.

### Gaps
- Exact BatchV1_1 and DynamicMPT mainnet status needs checking against xrpl.org/resources/known-amendments or a live `feature` RPC.
- No primary RippleX source for the 3–5 s settlement figure or the 25% share.

## 4. Stablecoins: supply, volume, GENIUS Act, MiCA

### Takeaway
Stablecoin supply is about $310–325B in mid-2026, a record. Adjusted annual volume was about $9T in 2025; the unadjusted headline figure is $33–46T. The GENIUS Act (signed July 18, 2025) takes effect January 18, 2027, and the OCC final rule came on October 21, 2026. MiCA stablecoin rules have applied in the EU since June 30, 2024.

### Cited Findings
- **Supply**:
  - About $320.0B on April 16, 2026 (DefiLlama) and a record of about $323B in May 2026. [Transak](https://transak.com/blog/stablecoin-market-cap-2026)
  - About $316B on June 12, 2026 (DefiLlama via a guide). [datawallet](https://www.datawallet.com/de/krypto/stablecoin-statistik)
  - The BIS used a conservative March 2026 snapshot of about $270B, with USDT plus USDC above 95%. [Transak](https://transak.com/blog/stablecoin-market-cap-2026)
  - More than $250B in mid-2025. [The Block, 2025](https://www.theblock.co/post/356545/stablecoin-market-capitalization-surpasses-250-billion-amid-accelerating-regulatory-momentum)
- **Volume**:
  - a16z State of Crypto 2025: $46T unadjusted, about $9T adjusted (up 87% year over year), with an adjusted monthly peak of about $1.25T in September 2025. [DL News, 2025](https://www.dlnews.com/articles/markets/stablecoin-volumes-triple-visa-as-a16z-projects-digital-dollars-to-hit-3tn-by-2030/)
  - Morph report: $33T in 2025 against Visa $15.7T and Mastercard $9.8T. [BitPinas](https://bitpinas.com/feature/morph-stablecoin-report/)
- **GENIUS Act provisions**:
  - Signed July 18, 2025.
  - 1:1 reserves in USD, demand deposits, Treasury bills of 93 days or less, or Treasury-backed repos.
  - Monthly public reserve reports.
  - No yield for simply holding.
  - Holders have priority in insolvency.
  - Only permitted issuers (subsidiaries of insured depository institutions, and federally or state-qualified issuers).
  - A three-year transition for digital-asset service providers, to about July 2028.

  Sources: [Fenwick](https://www.fenwick.com/insights/publications/congress-enacts-comprehensive-stablecoin-legislation-key-provisions-and-implications-of-the-genius-act); [Paxos](https://www.paxos.com/blog/genius-act); [Tazapay](https://tazapay.com/blog/genius-act-one-year-later-stablecoin-rules-2026). The primary Congress.gov text was not retrieved; the bill is S.1582, 119th Congress.
- **GENIUS Act implementation**:
  - Regulators missed the July 18, 2026 rulemaking deadline, so the effective date is the earlier of January 18, 2027 or 120 days after final rules. [Motley Fool](https://www.fool.com/research/banks-payment-processors-stablecoins/)
  - OCC proposed rules in March and April 2026 [Sullivan & Cromwell](https://www.sullcrom.com/insights/memo/2026/March/OCC-Proposes-Regulations-Implement-GENIUS-Act) and finalized them on October 21, 2026: effective January 18, 2027, with monthly public reserve disclosure and weekly confidential reports. [CoinDesk, Oct 21 2026](https://www.coindesk.com/policy/2026/10/21/occ-s-final-rule-to-start-fresh-in-weighing-stablecoin-rewards-against-genius-act-ban); [Forbes, Oct 23 2026](https://www.forbes.com/sites/ajdhaliwal/2026/10/23/occ-finalizes-stablecoin-rules-that-supervise-issuers-like-banks/)
  - Treasury proposed an illicit-finance rule [Treasury (primary)](https://home.treasury.gov/news/press-releases/sb0435) and a "substantially similar" state-regime proposal, with comments due June 2, 2026. [Stinson](https://www.stinson.com/newsroom-publications-occ-and-treasury-department-issue-requests-for-comments-on-genius-act-proposed-implementation-rulemakings)
  - The Fed issued proposals on September 24, 2026, published September 29, 2026. [Federal Register (primary)](https://www.federalregister.gov/documents/2026/09/29/2026-19860/implementing-the-federal-reserve-boards-responsibilities-under-the-genius-act)
- **MiCA**: stablecoin titles (ART and EMT, Titles III and IV) have applied since June 30, 2024, and CASP rules since December 30, 2024, with grandfathering into 2026. Only credit institutions or EMIs may issue EMTs, and USDT was delisted for EU users from late 2024 into Q1 2025. Secondary; one source says March 2024, so there is a conflict. [AMLBot](https://blog.amlbot.com/understanding-eu-mica-regulation-stablecoins-compliance-challenges-and-circle-case-study/); [BlindPay](https://blindpay.com/resources/more/mica-stablecoin-rules-explained)

### Inferences
- RLUSD is issued under a NYDFS trust charter (background knowledge, not verified here) and is positioned for GENIUS-compliant status from 2027. That makes it a credible USD settlement asset for regulated (for example, healthcare) data markets.

### Gaps
- No verified October 2026 total supply figure; check DefiLlama directly.
- No Chainalysis or Visa primary figure for 2026 volume year to date.

## 5. Agentic commerce forecasts (with caveats)

### Takeaway
Forecasts range about 35x depending on scope (US B2C versus global versus B2B). Cite them as directional only.

### Cited Findings
- McKinsey: up to about $1T of US B2C "orchestrated revenue" by 2030 (sometimes given as $900B–$1T), and $3–5T globally. Primary domain. [McKinsey](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-agentic-commerce-opportunity-how-ai-agents-are-ushering-in-a-new-era-for-consumers-and-merchants)
- Morgan Stanley: $190–385B of US agentic e-commerce (by about 2030). Secondary only; the original report was not linked. [Stellagent](https://stellagent.ai/insights/agentic-commerce-market-size-forecast-2030)
- Gartner: about $15T of B2B purchases mediated by AI agents by 2028. Secondary only; no primary Gartner source found. [Stellagent](https://stellagent.ai/insights/agentic-commerce-market-size-forecast-2030)

### Inferences
- These forecasts cover gross merchandise value moving through agents, mostly on card rails. They say little about sub-dollar machine-to-machine payments, which is the x402 and XRPL niche.

### Gaps
- No primary Morgan Stanley or Gartner documents.

## 6. Card fee baseline and micropayment infeasibility

### Takeaway
Stripe's standard 2.9% + $0.30 makes any payment under about $1 uneconomic: a $0.10 payment would cost $0.303, which is 303%. XRPL's fee of about $0.0002 is about 1,500x lower than the $0.30 fixed fee alone.

### Cited Findings
- Stripe US online cards cost 2.9% + $0.30, and Terminal costs 2.7% + $0.05. [NerdWallet](https://www.nerdwallet.com/business/software/learn/stripe-fees)
- A $5 charge loses 8.9%; a $500 charge loses about 3%. [Sellfy calculator](https://sellfy.com/tools/stripe-fee-calculator/)
- PayPal's Micropayments rate of 4.99% + $0.09 is reported to be cheaper below about $10. Third-party claim. [WebsitePlanet](https://www.websiteplanet.com/blog/stripe-fees/)
- Worked example (my arithmetic from the cited rates): a $0.01 payment costs about $0.30 on Stripe (about 3,000%) and about $0.0002 on XRPL (about 2%). 1.4M XRPL agent payments cost about $280 in total fees [crypto.news](https://crypto.news/ai-agents-made-1-4m-payments-on-xrpl-total-fees-280/), whereas the same count at $0.30 fixed would be about $420,000.

### Inferences
- Per-contribution settlement, such as paying each contributor per record or per query in cents, is not economic on card rails and is economic on XRPL or x402.

### Gaps
- Not verified: the US Regulation II (Durbin) regulated debit cap (21¢ + 0.05% + 1¢ fraud adjustment). It is commonly cited but no source was retrieved in this pass. The Fed has proposed lowering it (2023–2025); its status is unknown.
