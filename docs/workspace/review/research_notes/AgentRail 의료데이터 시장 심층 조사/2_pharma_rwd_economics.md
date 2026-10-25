# Pharma / CRO Real-World Data (RWD/RWE) Supply Chain: Intermediaries, Deal Sizes, Prices (as of Oct 2026)

Source-type legend: **[P]** = primary (company filing/press release/regulator/study authors); **[S]** = secondary (trade press, aggregator, or WebSearch summary). Direct fetch failed for many hosts (e.g., fda.gov ENOTFOUND), so most figures come from WebSearch summaries of the linked pages and are marked [S] unless the link is the company's own release. The report writer should treat [S] numbers as needing spot-checks.

## 1. Revenue, valuation and business models of the major intermediaries

### Takeaway
Patient-level health data is a multi-billion-dollar business run by intermediaries (data aggregators, tokenization/linkage companies, EHR vendors, health-system consortia, and pharma-owned data companies). Patients are not counterparties to any of these deals. The biggest valuations go to companies that hold or link longitudinal, person-level records: Flatiron ($1.9B, 2018), Datavant ($7B, 2021), Optum/Change ($13B, 2021).

### Cited Findings
**IQVIA (largest RWD/analytics intermediary)**
- FY2025 total revenue $16,310M (2024: $15,405M). Technology & Analytics Solutions (TAS, the data/analytics segment) revenue was $6,626M, up 7.6%, with segment profit of $1,595M. Q4 2025 TAS revenue was $1,821M (+9.8% reported) — [IQVIA FY2025 results, Feb 2026](https://www.iqvia.com/newsroom/2026/02/iqvia-reports-fourth-quarter-and-full-year-2025-results-issues-full-year-2026-guidance) [P]; [IQVIA FY2025 ARS (SEC)](https://www.sec.gov/Archives/edgar/data/1478242/000162828026012899/ars_2025.pdf) [P]
- 2026 resegmentation: "Real-World Late Phase and certain other Real-World offerings" (2025 revenue **$674M**) move from TAS to R&DS (the CRO segment). CSMS ($788M) folds into TAS, which is renamed "Commercial Solutions". The new structure applies from the Q1 2026 10-Q — [IQVIA FY2025 results release (BusinessWire)](https://www.businesswire.com/news/home/20260205999087/en/IQVIA-Reports-Fourth-Quarter-and-Full-Year-2025-Results-Issues-Full-Year-2026-Guidance) [P, via search summary]

**Datavant (tokenization/linkage and record-release intermediary)**
- June 2021: Datavant merged with Ciox Health in a deal valued at **$7.0B**. The combined company projected ~**$700M** in annual revenue and a network of 2,000+ hospitals, 15,000 clinics, 30+ life-science companies and 70 academic institutions. Backers included New Mountain Capital, Roivant, Sixth Street and Goldman Sachs AM — [Datavant/Ciox release (BusinessWire, 2021)](https://www.businesswire.com/news/home/20210609005224/en) [P]; [Fierce Biotech, 2021](https://www.fiercebiotech.com/medtech/datavant-to-absorb-ciox-health-7b-medical-data-deal) [S]
- How it works: identifiers (name, address, DOB) are replaced by an encrypted one-way-hash "token", so the same person's records can be matched across datasets without naming them. This is the core way claims, EHR, lab and genomic records get linked at the person level — [Fierce Biotech, 2021](https://www.fiercebiotech.com/medtech/datavant-to-absorb-ciox-health-7b-medical-data-deal) [S]; [Wikipedia: Datavant](https://en.wikipedia.org/wiki/Datavant) [S]
- An aggregator lists Datavant's valuation at $7.0B as of Dec 2025 (unverified) — [PremierAlts](https://www.premieralts.com/companies/datavant/valuation) [S]
- **Aetion acquisition (2025):** Datavant agreed to buy Aetion, an RWE analytics platform with 220 staff, 40+ biopharma clients and 80+ data partners, in May 2025. Terms were undisclosed. Axios reported "nearly **$400M**", citing two anonymous sources — [Fierce Healthcare, May 2025](https://www.fiercehealthcare.com/health-tech/datavant-acquires-real-world-evidence-company-aetion-boost-its-life-sciences-business) [S]; [Axios Pro, May 20 2025](https://www.axios.com/pro/health-tech-deals/2025/05/20/datavant-aetion-400-million) [S]. Closing dates conflict (May vs. July 13, 2025) — [Pulse2](https://pulse2.com/datavant-acquisition-of-aetion-completed/) [S]

**HealthVerity / Symphony Health (2026)**
- HealthVerity agreed to buy Symphony Health (commercial claims/Rx data) from ICON in early May 2026, terms undisclosed. HealthVerity announced the close on May 8, 2026. The stated rationale is to combine HealthVerity's clinical data and patient-identity (linkage) layer with Symphony's commercial datasets into one "AI-ready" platform, so buyers need fewer vendor contracts — [HealthVerity completion release, May 2026](https://healthverity.com/?p=18989) [P]; [MobiHealthNews, May 2026](https://mobihealthnews.com/news/healthverity-acquire-data-platform-symphony-health) [S]; [HLTH, May 6 2026](https://hlth.com/insights/news/healthverity-to-acquire-symphony-health-from-icon-to-expand-real-world-data-ecosystem) [S]
- Earlier prices for the same asset: PRA Health Sciences bought Symphony for **$530M** (2017), and ICON then acquired PRA (2021). So a single dataset business was resold between CROs and data firms at least three times — [Signalbase](https://www.trysignalbase.com/news/acquisitions/symphony-health-acquired-by-healthverity-acquisition) [S]

**Komodo Health**
- The last confirmed valuation is **$3.3B** (Series E, March 2021). ARR was ~$150M in 2022 (Axios, via search). The company cut 9% of staff (~78 people) in 2022. Reported 2024 revenue conflicts ($200M vs. $284M, Latka), and the 2026 valuation estimates (Dealroom $1–2.5B) are unreliable — [TechCrunch, 2022](https://techcrunch.com/?p=2457744) [S]; [MobiHealthNews, 2022](https://www.mobihealthnews.com/news/komodo-health-lays-9-its-workforce) [S]; [Latka](https://getlatka.com/companies/komodo-health) [S, low reliability]; [Dealroom](https://dealroom.co/companies/komodo-health/) [S, estimate]

**Truveta (health-system-owned EHR data consortium)**
- Series C (Jan 2025): **$320M** raised at a reported valuation above $1B. Regeneron invested **$119.5M** upfront, Illumina $20M, alongside 17 health systems (e.g., Northwell, Trinity) — [Fierce Biotech, JPM25](https://www.fiercebiotech.com/medtech/jpm25-regeneron-illumina-and-more-back-truveta-10m-genome-sequencing-project) [S]; [Truveta blog](https://www.truveta.com/blog/news/truveta-genome-project/) [P]; [Pulse2](https://pulse2.com/truveta-ehr-data-company-raises-320-million-at-over-1-billion-valuation/amp/) [S]
- Truveta Genome Project: the plan is to sequence exomes of up to **10M** consenting participants from leftover routine lab biospecimens and link them to de-identified EHRs. The Regeneron Genetics Center does the sequencing and gets **exclusive rights** to access the de-identified EHR data. Microsoft Azure is the exclusive cloud — [Providence (member system) release, 2025](https://blog.providence.org/news/leading-us-health-systems-launch-the-truveta-genome-project-creating-the-world-s-largest-and-most-diverse-database-to-discover-the-science) [P]; [BiopharmaTrend](https://www.biopharmatrend.com/news/truveta-raises-320m-to-sequence-10m-exomes-and-build-largest-genetic-database-1109/) [S]
- Truveta data covers 120M+ patients (Jan 2025, company-linked figure); an aggregator cites 70M (older). Member counts differ between sources (13 vs. 17+ systems) — [Pulse2](https://pulse2.com/truveta-ehr-data-company-raises-320-million-at-over-1-billion-valuation/amp/) [S]. No 2026 round was found.

**Flatiron Health (Roche)**
- Roche paid **$1.9B** (2018) for the rest of Flatiron, on top of its existing 12.6% stake, for a total implied value of about $2.1B. Flatiron held 2M+ oncology patient records from 2,500+ oncology clinicians and sells "regulatory-grade" RWE — [MedCity News, 2018](https://medcitynews.com/?p=76255) [S]; [Healthcare IT News, 2018](https://healthcareitnews.com/node/540417) [S]; [TechCrunch, 2018](https://techcrunch.com/?p=1599214) [S]

**Tempus AI (genomic + clinical data licensing)**
- FY2025: Data & Applications revenue **$316.4M** (+30.9% YoY), with Insights (data licensing) growing 38.0%. Remaining total contract value (TCV) was **>$1.1B** and net revenue retention 126%. FY2026 revenue guidance is **$1.59B** (total company) — [Tempus FY2025 results](https://www.tempus.com/news/pr/tempus-reports-fourth-quarter-and-full-year-2025-results/) [P]; [Tempus TCV release, Jan 2026](https://www.tempus.com/news/pr/tempus-achieves-record-total-contract-value-exceeding-1-1-billion/) [P]
- AstraZeneca + Pathos AI signed a **$200M** data-licensing and modeling deal (2025) to build an oncology foundation model. It lifted AstraZeneca's remaining contract value with Tempus above **$1B** (as of Apr 30, 2025) — [Tempus/Nasdaq coverage](https://www.nasdaq.com/articles/tempus-ais-data-business-keeps-scaling-can-growth-pace-last) [S]

**Optum / Change Healthcare**
- Optum paid about $8B cash plus about $5B of assumed debt, a total of **$13B** (announced Jan 2021). Change's claims-transaction network was folded into OptumInsight, which provides data analytics, research and advisory services — [Healthcare IT News, 2021](https://www.healthcareitnews.com/news/optum-acquire-change-healthcare-13b-deal) [S]; [Becker's, 2021](https://beckershospitalreview.com/digital-health/optum-to-buy-change-healthcare-in-13b-deal-5-details.html) [S]

**Veeva**
- FY2026 (ended Jan 31, 2026): total revenue about $3.2B (+16%) and subscription revenue $2,684.2M. Compass and Data Cloud revenue is not broken out. The earnings call highlighted Compass (patient/claims data), OpenData, Link and Pulse. Crossix (patient-level ad-measurement data) showed slight deceleration — [Veeva FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1393052/000139305226000014/veev-20260131.htm) [P]; [Veeva Q4 FY26 8-K](https://www.sec.gov/Archives/edgar/data/1393052/000139305226000007/veev-20260131q426xex991.htm) [P]; [TipRanks call summary](https://www.tipranks.com/news/company-announcements/veeva-systems-earnings-call-highlights-strong-growth-and-strategic-wins) [S]

**Oracle Health (Cerner) Learning Health Network**
- As of Sep 2026: **122M+** de-identified patient records from **255+** health systems, sold to life sciences for trials, HEOR, synthetic control arms, safety and regulatory submissions. Early 2024 figures were ~117 systems and 108M records — [Oracle press release, Sep 22 2026](https://www.oracle.com/news/announcement/oracle-named-a-leader-in-idc-marketscape-worldwide-life-sciences-vendor-assessment-2026-09-22/) [P]; [IntuitionLabs](https://intuitionlabs.ai/articles/oracle-life-sciences-products) [S]
- Business model: Oracle says member health systems "can generate revenue by participating in funded clinical trials and research collaborations with pharmaceutical and device companies". The revenue goes to the health system, not the patient — [Oracle LHN page](https://www.oracle.com/life-sciences/learning-health-network/) [P]

**Epic Cosmos**
- More than 300M patient records and 18.3B encounters (Feb 2026) — [Wake Forest CTSI, Feb 2026](https://ctsi.wakehealth.edu/announcements/2026/02/advocate-transitions-to-epic-cosmos) [S]. A secondhand summary of Epic UGM 2026 cites **320M** unique patients, 23B encounters and 99B lab results (not verified against Epic) — [Healthcare IT Today](https://www.healthcareittoday.com/?p=2536340) [S]. July 2025: 300M records, 16B+ encounters — [UTMB, 2025](https://www.utmb.edu/facultyaffairs/news-events/news/newsletter/newsletter/2025/07/30/epic-cosmos-makes-big-data-research-possible---sidekick-ai-makes-it-practical) [S]. (Cosmos is used for research by Epic customers. I found no evidence of direct sales to pharma.)

**Genetic data as an asset (consumer genomics)**
- Regeneron agreed to buy bankrupt 23andMe for **$256M** (May 2025), covering data from 15M+ customers. That works out to about **$17/person** (Daily Dot's own calculation). GSK's earlier deal is described as a $300M, 4-year deal (2018); its later renewal was a $20M one-year license — [Pharmaphorum, 2025](https://pharmaphorum.com/news/regeneron-swoops-genetic-testing-firm-23andme) [S]; [HealthExec, 2018](https://healthexec.com/node/107506) [S]; [Daily Dot](https://lede-v2.dailydot.com/23andme-genetic-data-sale) [S]. (Note: Regeneron was later outbid in court by TTAM Research Institute. That comes from prior knowledge and was not verified in this session.)

### Inferences
- Implied value per patient in M&A: Flatiron is about $2.1B / ~2M oncology patients ≈ **~$1,000 per patient record** (2018). 23andMe is about $17 per genotyped customer (2025, distressed sale). This gap of roughly 60x fits the idea that deep, longitudinal, clinically curated (and outcome-linked) records are worth far more than shallow, single-source data. These are my calculations, not disclosed per-patient prices.
- The value chain has layers: data generators (providers, payers, pharmacies, labs) → aggregators (IQVIA, Symphony/HealthVerity, Komodo, Optum) → linkage/tokenization (Datavant, HealthVerity) → analytics/RWE platforms (Aetion, Flatiron) → pharma/CRO buyers. Consolidation is merging the linkage and analytics layers (Datavant+Aetion 2025, HealthVerity+Symphony 2026).
- Health systems are capturing more value themselves (Truveta equity, Oracle LHN member revenue, Epic Cosmos). Patients are still not paid in any of these models.

### Gaps
- No primary 2025–2026 revenue figure for Datavant, Komodo or HealthVerity. No current Komodo valuation.
- No disclosed price for HealthVerity–Symphony (2026).
- Optum's RWD-specific revenue is not broken out. Veeva Compass revenue is not broken out.
- Epic's 320M figure was not verified against Epic's own materials.

## 2. Per-patient / per-record prices, contract sizes and durations, linkage pricing

### Takeaway
Real-world data is almost never priced publicly per record. Pharma buys annual, non-exclusive licenses or subscriptions: roughly $0.5–5M+ per dataset per year, $1–10M+ for enterprise deals, and $0.25–5M per study. Multi-year strategic deals for linked genomic plus clinical data reach $200M+. Disclosed per-record prices exist only at the low end, from the broker market (cents per record for aggregate or marketing-grade data).

### Cited Findings
- RWD subscription feeds cost roughly **$0.5–5M/year**, enterprise agreements **$1–10M+/year**, and vendors often raise prices **10–30% a year**. A single study costs $0.25–2M, and a regulatory-grade study $1–5M — [IntuitionLabs 2026 vendor comparison](https://intuitionlabs.ai/articles/pharma-real-world-data-platforms-comparison) [S, vendor-blog estimate]
- Major claims databases (IQVIA, Optum) charge about **$1–5M/year** for big-pharma access. A modeled non-exclusive per-licensee value is about $128K–160K/year (model, not market price) — [arXiv 2606.22760 (2026)](https://arxiv.org/pdf/2606.22760) [S, preprint]
- Duke Sanford Tech Policy (Joanne Kim, Feb 2023; one listing says 2022) contacted 37 brokers, and 11 were willing to sell mental-health data. One broker charged **$275 for 5,000 aggregated records (~$0.055/record)**. Another offered 435,780 records at **$0.06/record**, with prices "starting at $0.20" and bulk discounts. Subscriptions ran **$75,000–$100,000+/year** — [Duke Sanford report page](https://techpolicy.sanford.duke.edu/data-brokers-and-the-sale-of-americans-mental-health-data/) [P]; [Daily Dot](https://dailydot.com/?p=1295896) [S]
- Strategic multi-year licenses: Tempus–AstraZeneca/Pathos is **$200M** (2025) for data plus modeling, and AstraZeneca's remaining TCV with Tempus is above $1B — [Nasdaq](https://www.nasdaq.com/articles/tempus-ais-data-business-keeps-scaling-can-growth-pace-last) [S]. GSK–23andMe was **$300M over 4 years** (2018), renewed as **$20M for 1 year** — [HealthExec](https://healthexec.com/node/107506) [S]. Regeneron–Truveta is a $119.5M investment for exclusive access to EHR data linked to 10M exomes (2025) — [Fierce Biotech](https://www.fiercebiotech.com/medtech/jpm25-regeneron-illumina-and-more-back-truveta-10m-genome-sequencing-project) [S]
- Tempus's backlog structure (remaining TCV >$1.1B, NRR 126%) shows that data-licensing contracts run over multiple years and expand over time — [Tempus, Jan 2026](https://www.tempus.com/news/pr/tempus-achieves-record-total-contract-value-exceeding-1-1-billion/) [P]
- Context, not a data price: generating genomic data costs about US$716–4,817 per patient for an exome and $2,094–9,706 for a genome (systematic review). A TSO500 oncology panel is about $2,944 per sample. This is the replacement-cost floor for genomic records — [Genetics in Medicine review](https://www.gimjournal.org/article/S1098-3600(23)00842-0/fulltext) [P]; [J Mol Diagn (Norway)](https://www.sciencedirect.com/science/article/pii/S1525157825001710) [P]
- Illicit market reference (not a licensing benchmark): an EHR database reportedly sold for up to $500,000 — [Medical Economics](https://www.medicaleconomics.com/view/what-price-medical-record) [S]

### Inferences
- Where per-record prices are visible, a gradient appears: aggregated or broker data sells for about $0.05–0.20/record. Distressed consumer-genomic data was implied at about $17/person. Curated longitudinal oncology EHR data was implied at about $1,000/patient in M&A (Flatiron). That is roughly a 4-order-of-magnitude range by data depth and linkage.

### Gaps
- No public per-record price for claims, EHR, linked or oncology licenses. Vendors keep it under NDA.
- No public pricing for tokenization or linkage fees (Datavant/HealthVerity per-token or per-match fees). I searched and found nothing.
- Contract durations are rarely disclosed beyond the examples above (4-year GSK; multi-year Tempus TCV).

## 3. RWE market size, pharma RWD spend, FDA use of RWE

### Takeaway
Market-research estimates for "RWE solutions" in 2025 range from $2B to $20B depending on definition. A more grounded floor is the disclosed revenue of the intermediaries: IQVIA TAS alone was $6.6B in FY2025. FDA does use RWE in approvals, but the share that relies on it as pivotal evidence is small.

### Cited Findings
- RWE solutions market size, 2025: IMARC **$2.0B** (→$3.8B by 2034); GMI **$2.6B** (→$11.9B by 2035); Spherical Insights $2.97B; Fortune Business Insights **$20.03B** (→$65.42B by 2034), with North America at $8.44B (42%) — [IMARC](https://www.imarcgroup.com/real-world-evidence-solutions-market) [S]; [GMI](https://www.gminsights.com/industry-analysis/real-world-evidence-solutions-market) [S]; [Fortune BI](https://www.fortunebusinessinsights.com/markt-f-r-reale-evidenzl-sungen-107676) [S]. Pharma/biotech buyers make up ~41% of the North America market (2025) — [Towards Healthcare](https://www.towardshealthcare.com/insights/north-america-real-world-evidence-solutions-market-sizing) [S]
- FDA approvals using RWE: about **31% of FDA approvals in 2019–2021** incorporated data from routine clinical use (Purpura et al., cited secondhand) — [PMC12593103](https://pmc.ncbi.nlm.nih.gov/articles/PMC12593103) [S]. In oncology 2015–2020, **11 of 133** original and **2 of 573** supplemental approvals included RWE, none before 2017 — [PMC9299054](https://pmc.ncbi.nlm.nih.gov/articles/PMC9299054/) [P]
- FDA published a catalog of RWE regulatory-decision examples since 2011 (first posted Sep 2025, later updated with CDRH device examples). I could not retrieve the counts because fda.gov was unreachable. FDA's final RWE guidance for devices came out Dec 18, 2025 — [FDA RWE page](https://www.fda.gov/science-research/real-world-evidence/fda-use-real-world-evidence-regulatory-decision-making) [P, not fetched]; [Becaris blog](https://becarispublishing.com/digital-content/blog-post/fda-expands-real-world-evidence-examples-used-regulatory-decision-making) [S]; [Duane Morris](https://www.duanemorris.com/alerts/fda_releases_guidance_use_real_world_evidence_medical_devices_1225.html) [S]

### Inferences
- Revenue at IQVIA TAS ($6.6B) plus Tempus data ($316M), Veeva data products, Optum and others exceeds the low-end market estimates. The narrow "RWE solutions" figures undercount total trade in patient-level data.

### Gaps
- No credible direct figure for total pharma spend on RWD.
- The exact count of FDA RWE examples in the 2025–2026 catalog was not retrieved.

## 4. Value reaching patients; patient-compensation models

### Takeaway
Under HIPAA de-identification, providers and intermediaries can license patient data without consent or payment. Patients get essentially nothing. Revenue-sharing goes to health systems (equity or revenue), not individuals. Proposals to pay patients exist but are rare and hard to implement.

### Cited Findings
- De-identified data (18 identifiers removed) can be sold by providers "without compensation" to patients — [Medical Economics](https://www.medicaleconomics.com/view/who-profits-from-medical-records-) [S]
- Brookings describes a "multi-billion dollar industry" collecting, merging and selling patient data to the highest bidder. Only New Hampshire explicitly grants patients ownership of their data — [Brookings](https://www.brookings.edu/articles/who-should-profit-from-the-sale-of-patient-data) [S]
- Proposed models: royalty payments to patients who opt in, or health-system equity in partner companies (a BMJ-based viewpoint) — [Becker's viewpoint](https://www.beckershospitalreview.com/?p=202269) [S]. Hank Greely (Stanford) doubts royalties are workable because it is hard to attribute value to one person's data, and expects flat payments to be small — [Stanford Law](https://law.stanford.edu/?p=272655) [S]
- A 2019 Oregon bill would have required patient authorization for data sales and given patients a right to compensation. I found no evidence it passed — [BenefitsPRO, 2019](https://benefitspro.com/2019/02/05/oregon-bill-would-allow-consumers-to-monetize-health-data) [S]
- Health systems capture value instead: Truveta is owned by health systems (17 invested in the Series C), and Oracle LHN members earn research revenue. In the Truveta Genome Project, patients consent to research use of leftover specimens, but no payment is described — [Fierce Biotech](https://www.fiercebiotech.com/medtech/jpm25-regeneron-illumina-and-more-back-truveta-10m-genome-sequencing-project) [S]; [Oracle LHN](https://www.oracle.com/life-sciences/learning-health-network/) [P]
- In the 23andMe bankruptcy sale (2025), customers' genetic data was sold as an asset, with no payment to customers — [Pharmaphorum](https://pharmaphorum.com/news/regeneron-swoops-genetic-testing-firm-23andme) [S]

### Inferences
- In every deal found ($1.9B Flatiron, $7B Datavant, $13B Change, $200M Tempus–AZ, $119.5M Regeneron–Truveta, $256M 23andMe), the share paid to the people whose records were traded was effectively 0%.

### Gaps
- I found no quantified study of what share of RWD revenue reaches patients, and no Health Affairs or JAMA article quantifying it in this session.
- I did not research consented patient data-cooperative examples (e.g., LunaDNA, Hu-manity.co) for payout amounts.

## 5. Evidence that longitudinal, multi-source linked data is priced higher

### Takeaway
No source publishes a side-by-side price list. But the evidence points the same way. Industry calls linked claims plus EHR data the "gold standard", and it is scarce. The largest valuations and deals go to linked, longitudinal, clinically deep data. Recent consolidation is explicitly about adding identity and linkage layers.

### Cited Findings
- Linked EHR plus claims data has "long been considered the gold standard for HEOR", yet "very few integrated EHR and claims systems are generally available" — [ISPOR 2024, TriNetX](https://www.ispor.org/heor-resources/presentations-database/presentation/intl2024-3896/138131) [S]
- Linking closed claims to EHR improved longitudinal capture and continuity while keeping data granularity (ISPOR Europe 2025) — [ISPOR EU 2025 poster](https://www.ispor.org/heor-resources/presentations-database/presentation-cti/ispor-europe-2025/poster-session-1-2/characterization-of-a-large-scale-real-world-data-source-impact-of-linking-closed-claims-with-electronic-health-record-data) [S]. About 1 in 5 Americans change health plans each year, which breaks claims-only longitudinality — [Truveta](https://www.truveta.com/?p=268697) [P]
- Vendors sell linked products as premium offerings: Veradigm + MarketScan (8M+ linked lives), Flatiron claims-linked EHR, Truveta Live Link — [Merative/Veradigm](https://www.merative.com/real-world-evidence/veradigm-ehr-claims-data) [P]; [Flatiron](https://flatiron.com/real-world-evidence/claims-linked-ehr-data?hsLang=en) [P]
- The HealthVerity–Symphony rationale (2026) is to join identity resolution and clinical data with commercial claims so buyers can avoid multiple vendor contracts and integrations — [MobiHealthNews](https://mobihealthnews.com/news/healthverity-acquire-data-platform-symphony-health) [S]
- Genomic data linked to EHRs commanded exclusive-access strategic money: Regeneron paid $119.5M for exclusive access to EHRs linked to exomes. AstraZeneca paid $200M for Tempus multimodal (genomic plus clinical) data — [Fierce Biotech](https://www.fiercebiotech.com/medtech/jpm25-regeneron-illumina-and-more-back-truveta-10m-genome-sequencing-project) [S]; [Nasdaq](https://www.nasdaq.com/articles/tempus-ais-data-business-keeps-scaling-can-growth-pace-last) [S]

### Inferences
- Implied unit values form a gradient: aggregated or broker records at about $0.05–0.20, single-source genotype at about $17/person (distressed), and curated longitudinal oncology EHR at about $1,000/patient (Flatiron M&A). This supports the claim that depth, longitudinality and linkage drive price, but the numbers come from different contexts and are not like-for-like.
- Tokenization is the technology that turns single-source data into linked data. It is valued accordingly: Datavant was valued at $7B and kept buying analytics layers (Aetion, ~$400M).

### Gaps
- No direct quoted price premium (e.g., "linked data costs X% more") was found in public sources. That would need vendor rate cards or analyst (e.g., Axios Pro, Chilmark) reports behind paywalls.
