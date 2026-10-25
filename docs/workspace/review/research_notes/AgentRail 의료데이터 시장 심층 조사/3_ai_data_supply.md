# AI Training/Evaluation Data Supply Chain & Licensing Market (health/medical emphasis), as of Oct 2026

Method note: Direct fetch failed in this environment (presenc.ai DNS failure). Almost all items below come from WebSearch result summaries, so treat them as **secondary** unless marked [PRIMARY]. "[PK]" marks facts from prior knowledge whose URL was not re-checked this session. Verify those before publishing.

## 1. Data wall evidence: Epoch AI estimates and synthetic-data limits

### Takeaway
Epoch AI's main estimate is still the 2024 one. It puts the stock of usable public human-written text at about 300T tokens (90% CI 100T–1,000T) and expects frontier training to use it all up between 2026 and 2032. As of Oct 2026 we are inside that window. Model-collapse research shows that synthetic data does not cleanly replace human data: it works when mixed with real data and fails when it replaces real data.

### Cited Findings
- Epoch AI (2024 paper, "Will we run out of data? Limits of LLM scaling based on human-generated data"): effective stock of quality public human text ≈ **300 trillion tokens**, 90% CI **100T–1,000T**. LMs are projected to fully use it **between 2026 and 2032**, or sooner if models are heavily overtrained. The figure allows for multi-epoch training. [PRIMARY, 2024] — [Epoch AI](https://epoch.ai/blog/will-we-run-out-of-data-limits-of-llm-scaling-based-on-human-generated-data); [Epoch publication page](https://epoch.ai/publications/will-we-run-out-of-data-limits-of-llm-scaling-based-on-human-generated-data)
- Epoch's earlier 2022 working paper had projected high-quality text exhaustion around **2026**. The 2024 revision pushed this out because of better data use, such as repeated epochs. AP coverage (2024) described the window as "2 to 8 years." [secondary, 2024] — [MoneySense/AP](https://www.moneysense.ca/news/will-the-ai-gold-rush-last); [Epoch 2022 blog](https://epoch.ai/blog/will-we-run-out-of-data)
- Nature news feature (Dec 2024): data owners are increasingly restricting crawler access, which shrinks the usable stock further. One researcher said he suspects the shortage "is already starting." [secondary, 2024] — [Nature d41586-024-03990-2 (PDF mirror)](https://fisherp.mit.edu/wp-content/uploads/2025/01/d41586-024-03990-2.pdf)
- No Epoch 2025 or 2026 revision of the stock estimate turned up in searches. Some secondary blogs cite different Epoch timelines, such as "exhausted before 2026, low-quality data to 2030–2050," which mixes up the 2022 figures. [secondary] — [envisioning.com "data wall"](https://www.envisioning.com/vocab/data-wall)
- Shumailov et al., *Nature* (July 2024): "indiscriminate use of model-generated content in training causes irreversible defects… tails of the original content distribution disappear" (model collapse), shown for VAEs, GMMs and LLMs. [secondary summary of a primary paper, 2024] — [SAS blog summary](https://blogs.sas.com/content/iml/2024/07/31/synthetic-data-model-collapse.html); [AI Singapore/Gretel commentary](https://learn.aisingapore.org/2024/08/addressing-concerns-of-model-collapse-from-synthetic-data-in-ai-by-alexander-watson-aug-2024/)
- Gerstgrasser et al., "Is Model Collapse Inevitable?" (arXiv 2404.01413, 2024): when real data is **accumulated** alongside synthetic data rather than **replaced**, test error stays bounded and collapse is avoided. [secondary] — [Towards AI summary](https://pub.towardsai.net/model-collapse-is-real-the-version-everyone-repeats-is-wrong-ed4e4b60c28c)
- Seddik et al. (2024): collapse cannot be avoided when training **solely** on synthetic data. With mixed real and synthetic data, there is a maximum synthetic fraction below which collapse can be avoided. [PRIMARY, arXiv] — [arXiv 2404.05090](https://arxiv.org/html/2404.05090v1)
- Further 2024 theoretical work on collapse — [arXiv 2410.12954](https://arxiv.org/pdf/2410.12954)

### Inferences
- The "data wall" now limits *fresh, high-quality, rights-cleared human data* more than it limits raw volume. That pushes value toward (a) proprietary or licensed corpora, (b) expert-generated data (RLHF, rubrics, evals) and (c) domains that are under-represented on the open web, especially clinical and longitudinal patient data, which is mostly behind HIPAA and EHR walls.
- The collapse literature implies that synthetic medical data needs a continuing supply of real, verified data as an anchor. That supports demand for real-world clinical data even as synthetic generation grows.

### Gaps
- No Epoch 2025–2026 update to the 300T estimate was found. Epoch's site should be checked directly.
- No quantitative estimate was found of the share of the medical or clinical text stock that is publicly crawlable versus private.

## 2. Major AI data licensing deals (amounts, dates, counts per year)

### Takeaway
Disclosed deals are few and large. Typical news-publisher deals run $1–25M/yr, and the outliers are News Corp at ~$250M over 5 years and Reddit at ~$60–70M/yr per lab. Trackers count roughly 12 public deals in 2023 and about 91–104 cumulative by 2025–mid-2026. Most deal values are undisclosed.

### Cited Findings
**Deal list (amounts are reported, not company-confirmed, unless noted)**
| Deal | Date | Reported value | Source type |
|---|---|---|---|
| Reddit–Google | Feb 2024 | ~$60M/yr (Reuters) | secondary — [The Decoder](https://the-decoder.com/reddit-signs-60-million-annual-training-data-deal-with-google/) |
| Reddit–OpenAI | May 2024 | ~$70M/yr (analyst estimate from Reddit's disclosure that AI licensing ≈10% of ~$1.3B revenue ≈ $130M total) | secondary — [Search Engine Land](https://searchengineland.com/openai-may-pay-reddit-70m-for-licensing-deal-451882); [Slashdot/Adweek](https://tech.slashdot.org/story/25/02/14/0019213/) |
| Reddit aggregate (IPO S-1) | Feb 2024 | $203M total contract value disclosed | secondary — [LLM Pulse](https://llmpulse.ai/blog/ai-content-licensing-deals/) |
| News Corp–OpenAI | May 2024 | >$250M over 5 yrs, cash + credits (WSJ) | secondary — [Yahoo/WSJ](https://malaysia.news.yahoo.com/news-corp-inks-openai-licensing-211417483.html) |
| Axel Springer–OpenAI | Dec 2023 | Reports vary: ~$13M/yr over 3 yrs, "tens of millions of euros," or $25M | secondary, conflicting — [heise](https://heise.de/-10051681); [Media and the Machine](https://mediaandthemachine.substack.com/p/the-top-10-media-companies-profiting) |
| Financial Times–OpenAI | Apr 2024 | $5–10M/yr | secondary — [heise](https://heise.de/-10051681) |
| Dotdash Meredith–OpenAI | May 2024 | ≥$16M/yr plus variable (IAC earnings call) | secondary of a primary earnings call — [heise](https://heise.de/-10051681) |
| OpenAI "standard" publisher offer | 2024 | ~$1–5M/yr | secondary — [Search Engine Land](https://searchengineland.com/openai-may-pay-reddit-70m-for-licensing-deal-451882) |
| Shutterstock (all AI customers) | 2023 | $104M AI licensing revenue in 2023 | secondary — [heise](https://heise.de/-10051681) / [LLM Pulse](https://llmpulse.ai/blog/ai-content-licensing-deals/) |
| Taylor & Francis–Microsoft (+1 other) | 2024 | ~$10M (Microsoft); $75M expected from 2 AI deals | secondary — [Books+Publishing](https://www.booksandpublishing.com.au/articles/2024/09/04/258068/wiley-expects-to-make-us44-million-from-ai-partnership-authors-unable-to-opt-out/) |
| Wiley (unnamed AI cos.) | FY2024–25 | $44M ($23M earned + $21M expected); authors have no opt-out | secondary — [The Bookseller](https://thebookseller.com/news/wiley-set-to-earn-44m-from-ai-rights-deals-confirms-no-opt-out-for-authors) |
| Wiley FY2026 (yr to 30 Apr 2026) | 2026 | $49M AI licensing revenue in FY26; lifetime >$110M | secondary, page text partly garbled — [CASRAI](https://casrai.org/news/scholarly-publisher-ai-licensing-deals-2026) |
| OUP, CUP (opt-in) | 2024 | undisclosed | secondary — [The Bookseller](https://www.thebookseller.com/news/wiley-cambridge-university-press-and-oxford-university-press-confirm-ai-partnerships) |
| NYT–Amazon | May 2025 | $20–25M/yr (WSJ) | secondary — [LLM Pulse](https://llmpulse.ai/blog/ai-content-licensing-deals/) |
| News Corp–Meta | Mar 2026 | up to $50M/yr × 3 yrs (~$150M) (WSJ) | secondary — [LLM Pulse](https://llmpulse.ai/blog/ai-content-licensing-deals/) |
| AP–OpenAI, Stack Overflow–OpenAI/Google, Shutterstock–OpenAI | 2023–24 | no amounts found | — gap |

**Counts and aggregates**
- Publicly disclosed AI content licensing deals: **12 in 2023 → 91 cumulative by end-2025**. Another tracker counts 91 through June 2026, so the definitions differ. [secondary] — [LLM Pulse](https://llmpulse.ai/blog/ai-content-licensing-deals/); [Presenc AI tracker June 2026 (not fetchable)](https://presenc.ai/research/ai-content-licensing-deals-tracker-june-2026)
- A 2026 statistics report lists news publishers at 104 deals, 47 with disclosed value, and a median annual value of ~$4.2M. Its table was only partly legible. [secondary, low confidence] — [AI Industry Reviews](https://ai-industry-reviews.com/research/ai-training-data-licensing-deal-statistics-2026/)
- Total disclosed licensing value is "approaching ~$2B" (no methodology given). [secondary, low confidence] — [The Brief Script](https://thebriefscript.com/ai-content-licensing-deals/)
- Deal structure is shifting from one-time training dumps to real-time access and usage-based pricing (2026). [secondary] — [SellYourInfo](https://sellyourinfo.com/news/ai-data-licensing-shift-real-time-2026.html); 2025 timeline — [Digiday](https://digiday.com/media/a-timeline-of-the-major-deals-between-publishers-and-ai-tech-companies-in-2025/)
- Reddit renewals in 2026: in July 2026 the WSJ reported that renewal talks with Google had hit turbulence, and Reddit shares fell ~6%. CEO Huffman wants higher fees and a move from flat to usage-based pricing. Wells Fargo estimates renegotiated deals could reach **~$550M/yr**, versus a ~$130M run-rate. RBC says the Google renewal isn't due until early 2027. No new deal had been reported as of Sept 2026, when Baird said the risk was priced in. [secondary, 2026] — [TIKR](https://www.tikr.com/blog/reddit-fell-6-as-its-550m-ai-deal-renewal-looms-heres-where-the-stock-could-go-in-2026); [CJR](https://cjr.org/analysis/reddit-winning-ai-licensing-deals-openai-google-gemini-answers-rsl.php); [247wallst Sept 2026](https://247wallst.com/investing/2026/09/02/reddit-rallies-7-as-baird-says-renewal-risk-is-already-priced-in-pinterest-holds-flat/); [Placera/RBC](https://www.placera.se/telegram/reddit-may-benefit-from-google-ai-search-changes-rbc-says-20260512)

### Inferences
- The market is a **few rare, large, bilateral contracts** concentrated among about 5 labs as buyers, with high variance in price. There is no clearing price, and sellers who hold unique, fresh or high-signal data (Reddit, News Corp, the academic STM publishers) get a premium.
- Academic and STM publishers such as Wiley and T&F are the closest analog to medical-literature data. They earn tens of millions per year, which signals that labs pay for expert-domain text.

### Gaps
- No verified amounts for AP, Stack Overflow, Shutterstock–OpenAI, or Le Monde/Prisa deals.
- No reliable per-year count for 2024 alone, or for 2026 YTD.
- No disclosed deals were found where a frontier lab licenses de-identified EHR data directly.

## 3. Expert data vendors (Scale, Surge, Mercor, Turing, Handshake, Invisible), with medical-expert pay

### Takeaway
Expert data is now a multi-billion-dollar line item. Mercor (~$2B annualized GMV, valued at $10B→talks at $20B) and Surge (~$1.2B revenue in 2024) overtook Scale after Meta's $14.3B deal for 49% of Scale in June 2025. Physicians are advertised at **$120–$300/hr** for AI evaluation and RLHF rubric work.

### Cited Findings
- **Scale AI:** Meta bought a **49% stake for $14.3B** (June 2025). Founder Alexandr Wang joined Meta's superintelligence unit, and Jason Droege became interim CEO. In July 2025 Scale laid off ~14% of full-time staff (~200) and 500 contractors. Some clients, including OpenAI and Google, reportedly scaled back work after the Meta tie-up. Revenue was ~$870M in 2024 with a $2B projection for 2025 (projection, not actual). [secondary, 2025] — [TechRepublic](https://www.techrepublic.com/article/news-scale-ai-layoffs/); [SF Examiner](https://www.sfexaminer.com/news/technology/scale-ai-cutting-hundreds-of-workers-after-meta-investment/article_f6e4ff0f-0cc6-4075-991d-4d007ffc5e80.html); [YourStory](https://yourstory.com/ai-story/scale-ai-layoffs-meta-deal-alexandr-wang)
- **Mercor:** annualized revenue of **~$2B by June 2026**, with **H1 2026 ≈ $614–615M**, per a financial document reported by The Information. ~90% of it comes from OpenAI and other big labs. Analysts note the figure is gross payment volume, not net revenue. Series C in Oct 2025 raised $350M at a **$10B** valuation. In July 2026 it was reportedly in talks to raise $500M at **$20B**. Average expert pay is ~$85/hr, with physicians and senior specialists at $200+. [secondary, 2026] — [Sacra](https://sacra.com/c/mercor/); [36Kr](https://eu.36kr.com/en/p/3904682268034947); [BigGo/The Information](https://finance.biggo.com/news/865c23cb-3e0d-4c21-aa0d-6bf2a7fc8d1a); [HeroHunt](https://www.herohunt.ai/blog/mercor-2026-how-it-works-pay-alternatives/)
- **Mercor physician job postings (advertised rates)** [PRIMARY postings, dates may be stale]: Senior Attending Physician **$120–150/hr** — [work.mercor.com](https://work.mercor.com/jobs/list_AAABl5_20bBT9868jENPlLVN/senior-attending-physician-mds); General Clinician (MD/DO) for "developing and evaluating clinical AI systems" **$150/hr** — [work.mercor.com](https://work.mercor.com/jobs/list_AAABoKZfgKtRZhmavsFEsoAk); primary care documentation and AI evaluation **$170–190/hr** — [Remotive](https://remotive.com/remote/jobs/medical/primary-care-physician-5757960); internal medicine **$130–300/hr** — [Remotive](https://remotive.com/remote/jobs/medical/internal-medicine-physician-4697510). Tasks: write clinically realistic prompts and cases, write rubrics, and grade model responses for "one of the world's top AI labs."
- **Surge AI:** **~$1.2B revenue in 2024**, bootstrapped and profitable, with late-2025 run-rate ~$1.4B. It was reportedly in talks at a $25–30B valuation, unconfirmed as of June 2026. Its worker arm advertised **$75–150/hr** for medical, legal, finance and engineering specialists (Aug 2026). [secondary] — [Contrary Research](https://research.contrary.com/company/surge-ai); [Teahose](https://www.teahose.com/guides/scale-ai-competitors); [HeroHunt buyer guide](https://www.herohunt.ai/blog/mercor-vs-surge-vs-scale-ai-2026-buyer-guide/)
- **Handshake AI:** Sacra estimates **~$1.1B gross annualized revenue by Apr 2026**, about $450M net of contractor payouts. Experts earn $100–125/hr. The last known valuation is $3.3B (2022, stale). [secondary, 2026] — [Teahose](https://www.teahose.com/guides/scale-ai-competitors)
- **Turing:** **$2.2B valuation (Mar 2025)**, ~$300M ARR. [secondary] — [Teahose](https://www.teahose.com/guides/scale-ai-competitors)
- Founders of these vendors have become billionaires, which reflects the size of lab spending on human data. [secondary] — [TechBuzz](https://www.techbuzz.ai/articles/meet-the-billionaires-selling-ai-its-training-data)
- 2026 benchmark of annotation vendors — [HeroHunt](https://www.herohunt.ai/blog/top-10-data-annotators-for-ai-labs-2026-benchmark/)

### Inferences
- Labs buy medical expertise by the **hour** through intermediaries, not as durable data assets. At $120–300/hr, a 1,000-physician-hour rubric or eval set costs ~$0.1–0.3M before vendor margin. Vendors take a large spread: Handshake keeps ~40% of gross by this estimate.
- Buyers are very concentrated. About 90% of Mercor's revenue comes from a handful of labs, and Scale's customer losses after the Meta deal show that labs treat vendor neutrality as critical.

### Gaps
- No verified data on Invisible Technologies' 2025–26 revenue or valuation (not covered by searches).
- No 2026 revenue figure for Scale AI.
- Not confirmed: which lab is the client in the Mercor physician postings, and how OpenAI HealthBench's physician panel was sourced. [PK] HealthBench (May 2025) was built with 262 physicians from 60 countries, 5,000 conversations and ~48,562 rubric criteria — see [OpenAI HealthBench](https://openai.com/index/healthbench/) (not fetched this session).

## 4. Health-AI specific: clinical/longitudinal data demand and lab–health deals

### Takeaway
In Jan 2026 OpenAI (ChatGPT Health plus the Torch acquisition) and Anthropic (Claude for Healthcare plus HealthEx record connectors) both moved to connect consumer and patient longitudinal records into chat assistants. The main route to clinical data is consumer-consented record aggregation and enterprise software deals, not bulk EHR licensing. FDA AI-enabled device authorizations reached ~1,451 by end-2025 and ~1,614 by June 2026.

### Cited Findings
- **OpenAI–Torch (Jan 2026):** OpenAI acquired Torch Health, a 4-person startup whose app aggregates a user's medical data from hospitals, labs, wearables and consumer testing into a "unified medical memory," to power **ChatGPT Health**. Price was undisclosed: The Information reported **~$100M**, CNBC **~$60M** (conflicting). [secondary, 2026] — [TechCrunch](https://techcrunch.com/2026/01/12/openai-buys-tiny-health-records-startup-torch-for-reportedly-100m/); [Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/openai-acquires-healthcare-startup-torch-build-out-chatgpt-health); [Computerworld](https://www.computerworld.com/article/4116050/openai-acquires-torch-health-to-boost-its-healthcare-offerings.html); [HLTH](https://hlth.com/insights/news/openai-acquires-torch-building-the-unified-medical-memory-for-chatgpt-health-2026-01-13)
- **Anthropic Claude for Healthcare (11 Jan 2026):** HIPAA-ready tools for providers, payers and consumers. US Pro and Max subscribers can connect their medical records through **HealthEx**, a record aggregator. [secondary, 2026] — [Techstrong.ai](https://techstrong.ai/features/anthropic-launches-claude-for-healthcare-as-openai-acquires-medical-data-startup/); [Upstarts Media (JPM takeaways)](https://www.upstartsmedia.com/p/8-takeaways-anthropic-openai-health-jpm)
- **Abridge (ambient scribe):** valued at **$5.3B (Series E, June 2025)**. ARR was ~$100M in May 2025 (Sacra), up from $60M at end-2024, and another source gives $117M contracted ARR in early 2025. It serves 100–150+ health systems, including UPMC and Mass General Brigham. Eli Lilly made a strategic investment in June 2026 (amount undisclosed). Epic launched its own native AI scribe, which creates platform risk. [secondary] — [Sacra](https://sacra.com/research/abridge); [Multiples.vc](https://multiples.vc/private-comps/abridge); [Enterprise DNA](https://enterprisedna.co/resources/ai-map/company/abridge)
- **Pharma–data AI deals in 2026:** Merck–Mayo Clinic (Feb 2026) combines Mayo's clinical and genomic data with Merck's AI platform. GSK licensed Noetik's cancer foundation models (Jan 2026). [secondary] — [IntuitionLabs](https://intuitionlabs.ai/articles/pharma-ai-data-licensing-deal-structures)
- **Tempus AI:** agreed in July 2026 to acquire Personalis for ~$1.5B, which consolidates multimodal genomic and clinical data assets. [secondary] — [Wikipedia](https://en.wikipedia.org/wiki/Tempus_AI)
- Health-system enterprise AI deals in 2026 are mostly ambient documentation and clinical decision support, for example OpenEvidence at Mount Sinai and Cedars-Sinai. They are software contracts, not data licensing. [secondary] — [Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/ai/15-health-systems-that-have-signed-enterprise-ai-deals-in-2026/)
- **Menlo Ventures, State of AI in Healthcare (Oct 2025):** healthcare AI spending reached **$1.4B in 2025**, ~3× 2024. Ambient documentation took $600M and coding/billing $450M. Providers account for ~75% (~$1B), and startups capture 85% of spend. Healthcare adopts AI 2.2× faster than other industries. [secondary of a primary survey, 2025] — [eWeek](https://www.eweek.com/artificial-intelligence/healthcare-ai-spending/); [HealthExec](https://healthexec.com/topics/artificial-intelligence/healthcare-ai-spending-unitedhealth-ai-claims-processing)
- **Healthcare AI market size (forecasts, not comparable):** MarketsandMarkets **$21.66B (2025) → $110.61B (2030)**, 38.6% CAGR — [MarketsandMarkets](https://www.marketsandmarkets.com/PressReleases/artificial-intelligence-healthcare.asp) [PRIMARY press release]; Grand View **$187.7B by 2030**, 38.5% CAGR — [Abto summary](https://www.abtosoftware.com/?p=13082) [secondary]; Allied **$194.14B by 2030** (older 2021 report) — [Allied](https://alliedmarketresearch.com/press-release/artificial-intelligence-in-healthcare-market.html); US only: $11.57B (2025) → $268.9B (2035) — [Towards Healthcare](https://www.towardshealthcare.com/outlook/us-ai-in-healthcare-market)
- **FDA AI-enabled devices:** The FDA's official list includes entries through May 2026 and says it is not comprehensive [PRIMARY] — [FDA list](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/list-artificial-intelligence-enabled-medical-devices). Third-party tallies: **1,451 cumulative through 2025**, a record 295 in 2025, radiology 76% (Imaging Wire via IntuitionLabs) — [IntuitionLabs](https://intuitionlabs.ai/articles/fda-approved-ai-medical-devices-list); **1,524 through Mar 2026**, radiology ~1,163 — [AI2Work](https://ai2.work/blog/fda-ai-device-list-hits-1-524-as-radiology-dominates-but-evidence-lags); **1,614 as of 29 June 2026**, with 335 in 2025 (conflicts with 295) and 181 in H1 2026 — [Complizen](https://www.complizen.ai/post/fda-has-cleared-1614-ai-medical-devices). All secondary and approximate.
- [PK, not verified this session] Microsoft acquired Nuance for ~$19.7B (closed Mar 2022), now offered as Dragon Copilot integrated with Epic. Google Cloud–HCA Healthcare signed a generative-AI partnership in 2023 covering nurse handoff and clinical documentation. Sources to check: [Microsoft news](https://news.microsoft.com/2022/03/04/microsoft-completes-acquisition-of-nuance-ushering-in-new-era-of-outcomes-based-ai/); [HCA/Google Cloud](https://investor.hcahealthcare.com/news/news-details/2023/HCA-Healthcare-and-Google-Cloud-Bring-Generative-AI-to-Hospitals/default.aspx).

### Inferences
- Frontier labs are going after **patient-consented, longitudinal personal health records** (Torch, HealthEx) rather than buying bulk EHR data from hospitals, probably because of HIPAA and liability. That points to demand for consented, patient-directed data pipes, which are rare.
- Health spending (Menlo's $1.4B) goes to workflow software. The data in those workflows (scribe audio and notes) becomes a byproduct asset for vendors like Abridge, Microsoft/Nuance and Epic.
- FDA AI devices are ~76% radiology. Non-imaging clinical domains with longitudinal outcomes are thinly covered, which is consistent with a scarcity of labeled longitudinal data outside imaging.

### Gaps
- Disclosed prices or terms for frontier-lab purchases of de-identified clinical data (Truveta, Datavant, Tempus, IQVIA, health systems) were not found.
- Google–HCA, Microsoft–Epic and Nuance details were not re-verified this session.
- No 2026 Abridge valuation or ARR was found.

## 5. Market size forecasts: AI training datasets and data licensing

### Takeaway
Forecasts for the AI training dataset market cluster at **~$2.7–3.6B in 2024–25 and $5.8–11.2B by 2029–30 (20–28% CAGR)**. These are much smaller than the healthcare AI market and probably undercount spend on expert human data. Mercor plus Surge alone exceeded ~$3B in annualized gross revenue in 2026.

### Cited Findings
- Grand View Research: **$8.60B by 2030**, 21.9% CAGR (2025–30). [secondary] — [GII Korea listing](https://www.giikorea.co.kr/report/grvi1611213-ai-training-dataset-market-size-share-trends.html)
- MarketsandMarkets: **$2.68B (2024) → $11.16B (2030)**, >22% CAGR. A separate listing gives $2.82B (2024) → $9.58B (2029), 27.7% CAGR. Not verified against the original. [secondary] — [Mynewsdesk](https://www.mynewsdesk.com/in/business-inside/pressreleases/ai-training-dataset-market-3132595); [GII Japan](https://www.gii.co.jp/report/go1479648-artificial-intelligence-ai-training-dataset.html?)
- Lucintel: **$5.8B by 2030**, 20.3% CAGR (2024–30). [primary listing] — [Lucintel](https://lucintel.com/ai-training-dataset-market.aspx)
- Fortune Business Insights: **$3.59B (2025)**. [secondary, via search summary] — no direct URL captured; treat as unverified.
- Dataset licensing segment (MarketIntelo): **$4.8B (2025) → $22.6B (2034)**. [secondary] — via search summary; related analyses: [Neudata](https://www.neudata.co/blog/ai-data-licensing-market-analysis); [Quartz 2026](https://qz.com/ai-training-data-pricing-licensing-deals-market-052126)
- Creative-works licensing for AI estimated as a **$67.5B** market (scope unclear). [secondary] — [CO/AI](https://getcoai.com/news/a-67-5b-market-emerges-for-licensing-creative-work-to-train-ai)
- Technavio covers a separate segment, AI datasets and licensing for academic research and publishing (2025–29) — [Technavio](https://www.technavio.com/report/ai-datasets-and-licensing-for-academic-research-and-publishing-market-industry-analysis)
- Price map of what AI labs pay for data — [Acquiry](https://www.acquiry.com/research/ai-data-licensing-deals-price-map/)

### Inferences
- Syndicated "dataset market" figures ($3–11B) are smaller than the observed vendor revenue (Scale + Surge + Mercor + Handshake ≈ $5B+ gross annualized in 2025–26). The real spend on training and eval data is larger than analyst forecasts, and most of it goes to expert human labor rather than static dataset licenses.

### Gaps
- No dedicated forecast for a *medical AI training data* market was retrieved.
- Fortune Business Insights and MarketIntelo figures lack verified URLs.

## 6. Lawsuits and copyright pressure pushing toward licensed data

### Takeaway
*Bartz v. Anthropic* produced the largest copyright settlement in history: $1.5B, ~$3,100 per work for ~480k+ pirated books, with final approval in July 2026. The cost of training on unlicensed or pirated data is now concrete. *NYT v. OpenAI/Microsoft* was at summary judgment in Sept 2026 with no trial date set.

### Cited Findings
- **Bartz v. Anthropic:** final approval of the **$1.5B** non-reversionary class settlement, with final judgment entered on **20 July 2026** (N.D. Cal.). Reports give a ~92.77% claims rate, ~$3,100 per work across >480,000 works, and $101M in attorneys' fees. Anthropic admitted no liability. Reports name Judge Araceli Martínez-Olguín (the case was originally before Judge Alsup; check whether it was reassigned). The 2025 ruling in the case held that training on lawfully acquired books was fair use, while the pirated-library copies drove the liability. [secondary + trade-association primary] — [Authors Guild](https://authorsguild.org/news/court-grants-final-approval-anthropic-copyright-settlement/); [Bloomberg Law](https://news.bloomberglaw.com/ip-law/anthropic-authors-1-5-billion-deal-receives-final-approval); [JURIST](https://www.jurist.org/news/2026/07/judge-approves-record-1-5-billion-settlement-involving-anthropic/); [Pearl Cohen](https://pearlcohen.com/federal-court-approves-1-5-billion-anthropic-copyright-settlement-largest-in-history); [AAP press release](https://publishers.org/?p=13761)
- **NYT v. OpenAI & Microsoft (SDNY, Judge Stein):** most motions to dismiss were denied in March/April 2025, and the case was consolidated with other news cases for discovery. In **Sept 2026** the parties argued summary judgment. OpenAI relies on *Kadrey v. Meta* and *Bartz* (training = fair use), and NYT argues that market substitution distinguishes its case. No trial date or ruling had been reported as of the search. [secondary, 2026] — [Axios Sept 2026](https://axios.com/2026/09/08/nyt-openai-microsoft-copyright-lawsuit); [Axios Apr 2025](https://www.axios.com/2025/04/01/nyt-openai-microsoft-lawsuit-advances); [OPB/NPR Mar 2025](https://www.opb.org/article/2025/03/27/judge-allows-new-york-times-copyright-case-against-openai-to-go-forward/)
- Dozens of similar suits are pending against OpenAI, Meta, Google and others. [secondary] — [Bloomberg Law](https://news.bloomberglaw.com/ip-law/anthropic-authors-1-5-billion-deal-receives-final-approval)

### Inferences
- The fair-use rulings (Bartz, Kadrey) protect training on *lawfully acquired* data but penalize acquisition through piracy. That makes **provenance and documented consent** the main legal risk control, which favors licensed and consented sources. For health data, HIPAA and consent add a second layer on top of copyright.
- At ~$3,100 per book, Bartz gives a rough reference price for the liability of unlicensed works.

### Gaps
- No ruling on NYT v. OpenAI summary judgment as of Oct 2026 was found.
- Other 2026 settlements (Getty v. Stability, music labels v. Suno/Udio, etc.) were not researched this session.
