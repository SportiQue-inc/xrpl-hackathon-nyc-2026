# National health-data regimes: from institution-held records to person-mediated access and secondary use (as of Oct 2026)

Method note: research date is 2026-10-25. Direct fetch failed: healthit.gov returned DNS ENOTFOUND, and no other direct fetch went through. **Every finding below comes from WebSearch result summaries.** Where the cited URL is itself the primary document (a government PDF, statistics page or the Nature paper), it is marked "primary URL, summary only". Where it is a press or law-firm piece, it is marked "secondary". Nothing was read in full. Re-verify any number before it goes on a slide.

## US: Cures Act information blocking, HIPAA right of access, TEFCA/IAS, CMS-0057-F, CMS Health Tech Ecosystem, app usage

### Takeaway
In the US, an individual's legal right to pull their records is strong. The HIPAA right of access, information-blocking penalties of up to $1M per violation, and TEFCA's Individual Access Services (IAS) together make it real. The tooling is now mainstream: 57% use app-based access, and officials say ~60% of Americans can now pull records into an app. However, IAS covers getting records *to* the individual. No federal rail lets the individual then consent or be paid when that data goes on to research.

### Cited Findings
**Information blocking (21st Century Cures Act)**
- OIG civil monetary penalties of up to $1M per violation took effect on 1 Sep 2023. They apply to health IT developers, HIEs and HINs. Provider "disincentives" took effect on 31 Jul 2024, and the ACO participant disincentives on 1 Jan 2025. — [Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/ehrs/from-law-to-enforcement-how-information-blocking-went-from-policy-to-compliance-risk/) (secondary, 2026)
- HHS publicly announced information-blocking enforcement as a priority in Sep 2025. By Jun 2026, ASTP head Thomas Keane said HHS was issuing notices of nonconformity and corrective action plans to provider organizations. Over 2,000 complaints had been filed, and OIG was hiring attorneys and running investigations. — [Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/ehrs/from-law-to-enforcement-how-information-blocking-went-from-policy-to-compliance-risk/) (secondary, Jun 2026); see also [HIPAA Journal](https://www.hipaajournal.com/hhs-crackdown-information-blocking-healthcare/) (secondary)
- A proposed rule would revise or remove information-blocking exceptions that could be misused. Its comment period closed on 27 Feb 2026, and no final rule had been issued as of 24 Jun 2026. — [Becker's](https://www.beckershospitalreview.com/healthcare-information-technology/ehrs/from-law-to-enforcement-how-information-blocking-went-from-policy-to-compliance-risk/) (secondary)
- None of the sources found named a first monetary penalty against a specific entity.

**HIPAA right of access**
- The current rule allows 30 days to respond, with one 30-day extension if the entity explains the delay in writing. A proposed Privacy Rule change would cut this to 15 calendar days plus one 15-day extension. It would also clarify access fees, advance notice of estimated fees, and when ePHI must be provided free. The rulemaking (RIN 0945-AA00) was listed at the Final Rule Stage, but as of 18 Aug 2026 no final rule had been published. — [HIPAA Journal, New HIPAA Regulations 2026](https://www.hipaajournal.com/new-hipaa-regulations/) and [HIPAA Updates 2026](https://www.hipaajournal.com/hipaa-updates-hipaa-changes/) (secondary, Aug 2026)
- OCR right-of-access enforcement was described as "ramping up" in Feb 2026. — [Healthcare Law Insights](https://www.healthcarelawinsights.com/2026/02/enforcement-ramps-up-on-patient-right-of-access-what-providers-need-to-know/) (secondary, Feb 2026)
- The fee standard is "reasonable, cost-based" (45 CFR 164.524). This comes from background knowledge and was not verified in this session. The exact fee caps found by search were not confirmed.

**TEFCA / QHINs / IAS**
- **11 designated QHINs**, by date of designation:
  - Dec 2023 (5): eHealth Exchange, Epic Nexus, Health Gorilla, KONZA, MedAllies
  - Feb 2024: CommonWell, Kno2
  - Jan 2025: eClinicalWorks
  - Apr 2025: Surescripts
  - Aug 2025: Netsmart
  - Nov 2025: Oracle Health Information Network
  — [ASTP "History & Growth of TEFCA"](https://healthit.gov/resources/data-liquidity-affordability-and-access-the-history-growth-of-tefca/) (primary URL, summary only). The [ASTP Feb 2026 deck](https://healthit.gov/wp-content/uploads/2026/02/2026-02-19_TEFCA_Updates_Presentation_508.pdf) says "3 new designated QHINs in 2025", which conflicts with the 4 above. No 2026 designations were found.
- **Volume:** over 70,000 sites and over **474 million documents** shared since go-live in Dec 2023. The deck does not break out an IAS-specific volume. — [ASTP TEFCA Update deck, 19 Feb 2026](https://healthit.gov/wp-content/uploads/2026/02/2026-02-19_TEFCA_Updates_Presentation_508.pdf) (primary URL, summary only). A vendor blog says "nearly 500M" as of early 2026: [Wireless Life Sciences](https://wirelesslifesciences.org/2026/01/tefca-in-2026-what-qhin-expansion-means-for-digital-health-vendors-and-providers/) (secondary)
- **IAS** is one of six TEFCA exchange purposes. The IAS Provider supports an Individual's ability to "access, inspect, obtain, or transmit a copy" of their own information. — [ASTP TEFCA page / search summary](https://healthit.gov/resources/data-liquidity-affordability-and-access-the-history-growth-of-tefca/) (summary only)
- **IAS timeline:**
  - IAS Provider Requirements SOP v2.1 was approved on 12 Jan 2026 and took effect on 17 Mar 2026.
  - IAS Exchange Purpose Implementation SOP v3.0 took effect on 3 Aug 2026.
  - From 1 Oct 2026, credential service providers working through IAS Providers must be able to use distinct production and non-production issuer URLs.
  — [RCE SOP IAS XP v3, Jun 2026](https://rce.sequoiaproject.org/wp-content/uploads/2026/07/SOP-IAS-XP-v3_June2026_Clean_-5081.pdf) (primary URL, summary only)

**CMS Interoperability & Prior Authorization rule (CMS-0057-F)**
- The Patient Access API has been required since 1 Jan 2021 for claims, encounter and clinical data. Under 0057-F, prior-authorization information must be added by **1 Jan 2027**. That date applies to Medicare Advantage and state Medicaid/CHIP fee-for-service. Medicaid/CHIP managed care and Federally-facilitated Exchange QHP issuers have dates tied to their rating or plan years.
- Operational prior-authorization timeframes took effect on 1 Jan 2026: 72 hours for urgent requests, 7 days for standard ones, and specific reasons required for denials.
- CMS's ePA page, updated 14 Sep 2026, still shows the 1 Jan 2027 date.
— [Saga IT checklist](https://saga-it.com/blog/cms-0057-f-compliance-checklist), [Firely](https://fire.ly/blog/cms-0057-f-decoded-must-have-apis-vs-nice-to-have-igs-for-2026-2027/), [c9group](https://c9group.dev/en/articles/cms-0057-f-payer-api-prior-authorization-2027) (secondary, 2026)

**CMS Health Tech Ecosystem / "Kill the Clipboard"** (launched July 2025)
- The ecosystem grew from 60 organizations at launch to **over 800** at the 1-year anniversary (late Jul 2026). Secretary Kennedy said ~**60% of Americans** can now bring their records into an app of their choice, up from **5%** a year earlier. This is a self-reported government figure that has not been independently verified. CMS also announced a new CMS product office and an EHR-by-EHR guide for accepting QR-code health links. — [CitizenPortal](https://citizenportal.ai/articles/8661642/Federal/Executive/Department-of-Health-and-Human-Services-HHS/Centers-for-Medicare-and-Medicaid-Services-CMS/HHS-CMS-leaders-mark-1-year-of-health-tech-kill-the-clipboard-push-as-patient-access-climbs-to-60) (secondary, Jul 2026)
- Eight new pledge categories were announced at the same event. — [STAT, 28 Jul 2026](https://www.statnews.com/2026/07/28/medicare-medicaid-evaluates-health-tech-progress-unveils-eight-pledge-categories/) (secondary)
- First-wave tools launched in Apr 2026. At that point there were over 700 organizations, and over 120 said they were ready for production or soon would be. Named participants include eClinicalWorks (production support) and athenahealth + b.well (a point-of-care sharing workflow). — [AHA, 28 Apr 2026](https://www.aha.org/aha-center-health-innovation-market-scan/2026-04-28-cms-announces-first-healthtech-ecosystem-tools); [Healthcare Dive](https://www.healthcaredive.com/news/cms-update-health-tech-ecosystem-data-sharing-interoperability/817205/); [HIPAA Journal](https://www.hipaajournal.com/cms-first-wave-health-tech-ecosystem-health-information-sharing-access-tools/) (secondary)

**Patient app usage**
- In 2024, **65%** of individuals were offered *and* accessed an online record or portal (75% among people managing recent cancer). App-based access rose from **38% (2020) to 57% (2024)**. 59% had multiple portals, but only **7%** used an app that aggregates them. — [ASTP Data Brief No. 77, Jul 2025 (HINTS 2024)](https://www.healthit.gov/wp-content/uploads/2025/07/2024-HINTS-Patient-Access-DB77_508.pdf) (primary URL, summary only)

### Inferences
- The legal plumbing for "pull my own longitudinal record" is complete: a right of access, penalties for blocking, IAS through 11 QHINs, payer FHIR APIs, and CMS-aligned apps. The weak link is aggregation. Only 7% use an aggregator, and that gap is where a personal agent fits.
- None of these regimes includes a mechanism for the individual to consent per study or be compensated when their record goes on to research. IAS stops at delivering data to the person. So the "missing consent/compensation rail" claim holds for the US.

### Gaps
- No primary-source count of IAS-specific transactions or IAS providers was found.
- The exact current HIPAA fee caps (for example, the $6.50 flat-fee option from 2016 guidance) were not verified in this session.
- No first named information-blocking CMP amount was found.
- The 60% figure is a political claim with no published methodology found.

## EU: EHDS Regulation (EU) 2025/327 and GDPR Art. 20

### Takeaway
The EHDS creates a free, cross-border right of access for individuals to their electronic health data (primary use). Secondary use runs on **permits issued by Health Data Access Bodies (HDABs), not consent**, with an individual opt-out. Fees go to HDABs and data holders, not to the individuals. The design leaves no compensation or per-study consent channel for the data subject.

### Cited Findings
- The regulation was published in the Official Journal on 5 Mar 2025. Sources differ on entry into force: 25 or 26 Mar 2025. It applies generally from **26 Mar 2027**, and Member States must name their national contact points for secondary use by that date. — [Arnold & Porter](https://www.arnoldporter.com/en/perspectives/advisories/2025/03/european-health-data-space-regulation-published); [noze.it](https://www.noze.it/en/insights/ehds-regulation-2025-327/) (secondary)
- Most secondary-use provisions apply from **26 Mar 2029**. The rest, including clinical-trial data and human genetic data, apply from **26 Mar 2031**. — [Sidley, Sep 2025](https://goodlifesci.sidley.com/2025/09/23/navigating-the-european-health-data-space-regulation-what-life-sciences-companies-need-to-know-about-secondary-use-implementation-now-a-tracking-tool-september-2025/); [Datacapt](https://www.datacapt.com/blog/ehds-clinical-trials-timeline) (secondary)
- Secondary use is **permit-based, not consent-based**. HDABs issue scope-limited permits, and analysis happens inside secure processing environments. Designating HDABs and connecting HealthData@EU happens mostly between now and 2029. — [Mithras Health](https://mithrashealth.com/journal/ehds-explained/) (secondary)
- Individuals may **opt out** of secondary use at any time without giving a reason (Art. 71). Member-state latitude here was contested in negotiations. — [Arnold & Porter](https://www.arnoldporter.com/en/perspectives/advisories/2025/03/european-health-data-space-regulation-published); [Wikipedia](https://en.wikipedia.org/wiki/European_Health_Data_Space) (secondary)
- **Fees (Art. 62):**
  - HDABs and trusted data holders may charge fees "in proportion to the cost" that do not restrict competition. Fees can cover application assessment, permits, and data preparation including pseudonymisation and anonymisation.
  - Fees include compensation to the *data holder* for compiling and preparing the data.
  - Member States may set reduced fees for public bodies, academics and microenterprises.
  — [streamlex Art. 62](https://streamlex.eu/articles/ehds-en-art-62/) (summary of legal text)
- TEHDAS2 published a fee and penalty guideline for HDABs (dated 27 Feb 2026). — [TEHDAS](https://tehdas.eu/results/tehdas2-guidance-clarifies-ehds-fees-and-penalties/); [D4.1 PDF](https://tehdas.eu/wp-content/uploads/2026/05/d4.1-guideline-for-health-data-access-bodies-on-fees-and-penalties-for-non-compliance-related-to-the-ehds-regulation.pdf) (primary URL, summary only)
- Physicians' body CPME warned that data-holder preparation could amount to "working for free". — [CPME submission, Nov 2025](https://www.cpme.eu/api/documents/adopted/2025/11/cpme.2025-192.final.cpme.submission.m4.1.1.fees.tehdas2.pdf) (primary URL, summary only)

### Inferences
- EHDS fees flow only to HDABs and data holders. That is a structural contrast with a person-mediated, compensated model, and it is pitch material.
- GDPR Art. 20 (portability) applies only to data processed on consent or contract by automated means. Much hospital data rests on other legal bases, which is why the EHDS primary-use access right matters. This comes from background knowledge and was not sourced in this session.

### Gaps
- No primary-text confirmation was found of the primary-use phase-in dates (patient summary and ePrescription by ~2029; images, lab and discharge reports by ~2031) or of the "free of charge" wording for individual access. Verify on EUR-Lex (32025R0327).
- No EHDS implementation budget figures (for example, EU4Health allocations) were found.

## UK: NHS App, UK Biobank, Our Future Health, FDP, Health Data Research Service

### Takeaway
The UK has the largest consumer-facing state health app (39.3M registered users) and two mega-cohorts: UK Biobank (~500k, fee-based access) and Our Future Health (>2.5M enrolled). Research access is centralizing through a £600M Health Data Research Service. Participants volunteer and are not paid per use.

### Cited Findings
- **NHS App, Sep 2026:** **39,311,635 registered users** (+7% year on year), **16,669,924** distinct users logging in during the month, and **91,585,102** login sessions. The 2026 target was ≥100M logins a month. — [NHS England Digital, NHS App MI Sep 2026](https://digital.nhs.uk/data-and-information/publications/statistical/nhs-app-statistics/september-2026) (primary URL, summary only); [Healthcare Leader](https://healthcareleadernews.com/news/nhs-app-aiming-for-100-million-logins-by-next-year/) (secondary)
- NHS England reported over 39M registered users in Dec 2025. — [NHS England, Dec 2025](https://www.england.nhs.uk/2025/12/record-numbers-using-nhs-app-to-manage-health/) (primary URL, summary only)
- A £160M NHS App contract was awarded to IBM in Apr 2026. — [HTN, 13 Apr 2026](https://htn.co.uk/2026/04/13/nhs-app-160-million-contract-awarded-to-ibm/) (secondary)
- **UK Biobank fees:**
  - Standard: about £9,000 + VAT for 3-year access for UK researchers. This is a 2024 figure and the current fee is unverified.
  - Students: £500 + VAT for data-only requests.
  - The Global Researcher Access Fund covers lower-income-country researchers.
  - UK Biobank says it charges only to cover the cost of handling applications.
  — [UK Biobank fees/financial support](https://www.ukbiobank.ac.uk/use-our-data/fees/financial-support/) (primary URL, summary only); [Research Professional, 2024](https://www.researchprofessionalnews.com/rr-news-africa-partnerships-2024-4-uk-biobank-gives-poor-country-researchers-free-access-to-data/) (secondary)
- UK Biobank cohort size: ~500,000 participants. This is background knowledge and was not re-verified in this session.
- **Our Future Health:**
  - Enrollment: over **2.5M enrolled** with baseline data for over 1.9M (Nature Medicine, published 10 Sep 2026). The target is 5M.
  - Release 14 (May 2026) counts 2,021,810 participants with baseline questionnaires. Of those, 755,000 have genotype data and 1,518,202 have clinic measurements.
  - The most deprived communities are under-represented: 13% of participants versus 20% nationally.
  — [Nature Medicine](https://www.nature.com/articles/s41591-026-04602-4) (primary URL, summary only); [OFH data release](https://ourfuturehealth.gitbook.io/our-future-health/data-releases/current-data-release) (primary URL, summary only); [Oxford MSD](https://www.medsci.ox.ac.uk/news/new-study-charts-the-health-of-nearly-2-million-uk-adults-in-our-future-health) (secondary)
- **Health Data Research Service (HDRS):**
  - Funding is up to **£600M**: £500M from government and £100M from Wellcome. It was announced in Apr 2025 and will be housed at the Wellcome Genome Campus.
  - It will give approved researchers a single secure route to de-identified NHS data.
  - It was established, and a governance blueprint was published by Jan 2026.
  — [Research Professional, Apr 2025](https://www.researchprofessionalnews.com/rr-news-uk-innovation-2025-4-pm-announces-600m-health-data-research-service/); [Wellcome](https://wellcome.org/news/national-data-service-will-simplify-access-health-data-research); [Univ. Liverpool, Jan 2026](https://news.liverpool.ac.uk/2026/01/14/uks-600-million-health-data-research-service-could-unlock-great-benefits-for-patients-communities-and-economies/amp/) (secondary)

### Inferences
- The UK's model is institution-to-researcher: HDRS, trusted research environments, and cohort fees paid to the custodian. The NHS App gives citizens access and control over opt-out, but not data contribution or compensation.

### Gaps
- No details were found on the NHS Federated Data Platform in this session. Its background is the Palantir-led contract of ~£330M awarded in Nov 2023, which is unverified here.
- The current UK Biobank standard fee is unconfirmed.
- No figures were found on NHS App record-view usage specifically.

## Korea: 건강정보 고속도로, 의료 마이데이터, 국가통합바이오빅데이터, 데이터3법, 디지털헬스케어법

### Takeaway
Korea already has a state-run personal record-pull rail (건강정보 고속도로 / 나의건강기록 앱) and a national cohort of 1M people (₩600B+ in phase 1). Coverage of clinics is very low, at 3%. The law that would formalize a patient's right to transmit their medical data (전송요구권) to third parties, the 디지털헬스케어법, was **still not passed as of Sep 2026**.

### Cited Findings
- **건강정보 고속도로, Oct 2026 국정감사 (Rep. 최혁진, using KHIS data):**
  - 1,363 institutions are EMR-linked.
  - All **47** tertiary hospitals are linked.
  - General hospitals: 115 of 337 linked (34.12%).
  - Hospitals and clinics: 1,201 of 39,160 linked (**3.07%**).
  - Cumulative 나의건강기록 앱 users: **611,033**.
  — [머니투데이, 20 Oct 2026](https://www.mt.co.kr/thebio/2026/10/20/2026102011104860722) (secondary)
- Full operation started in 2024 with 860 institutions. After the second expansion, 1,263 data-providing institutions were planned. — [보건복지부 보도자료](https://www.mohw.go.kr/board.es?mid=a10503010100&bid=0027&tag=&act=view&list_no=378308&cg_code=) (primary URL, summary only); [이투데이](https://www.etoday.co.kr/news/view/2409773) (secondary)
- The ministry plans to merge the 진료정보교류 system and 건강정보 고속도로 into a "디지털의료정보교류시스템" by 2029. — [전자신문, 20 Oct 2025](https://www.etnews.com/20251020000130) (secondary)
- **국가통합바이오빅데이터구축사업:**
  - Timeline: 2024–2032. Phase 1 targets **772,000** people by 2028, and phase 2 brings the total to **1,000,000** by 2032.
  - Mix: 585,000 general participants, 140,000 with severe disease, 47,000 with rare disease.
  - Participants: ~220,000 in Sep 2026 and ~238,000 by 14 Oct 2026, with 600–700 new sign-ups a day. Recruitment runs through 48 institutions, up from 38 at launch.
  - Phase-1 budget is reported as **₩606.6B** in one source and **₩660B** in another. The discrepancy is unresolved.
  - First research dataset: ~120,000 people, opening Nov 2026. Another count gives 131,471 pseudonymized clinical records as of Apr 2026.
  - Participation has been opened to people outside the health-screening population.
  — [전자신문, 15 Oct 2026](https://www.etnews.com/20261015000307); [데일리안](https://www.dailian.co.kr/news/view/1701579/%EB%B0%94%EC%9D%B4%EC%98%A4-%EB%8D%B0%EC%9D%B4%ED%84%B0-%EA%B8%B0%EC%A6%9D-%EB%8C%80%EC%83%81-%ED%99%95%EB%8C%802028-2026); [서울경제](https://m.sedaily.com/article/20102034); [데이터경제신문](https://www.dataeconomy.co.kr/news/articleView.html?idxno=43093); [의학신문](https://www.bosa.co.kr/news/articleView.html?idxno=3014024) (all secondary, 2026)
- **데이터3법 / 가명정보 특례:**
  - The amended 개인정보 보호법 took effect on **5 Aug 2020**. Its Art. 28-2 to 28-6 (가명정보 특례) allow pseudonymized data to be used without consent for statistics, scientific research and public-interest archiving.
  - The 보건의료 데이터 활용 가이드라인 (PIPC and MOHW, Sep 2020) takes precedence for health data.
  — [보건의료 데이터 활용 가이드라인 PDF](https://www.smallake.kr/wp-content/uploads/2020/12/보건의료_데이터_활용_가이드라인최종.pdf) (primary document mirror, summary only); [신김 newsletter](https://shinkim.com/kor/media/newsletter/1305) (secondary)
- **디지털헬스케어법 (디지털 헬스케어 및 보건의료데이터 활용에 관한 법률):**
  - It has stalled for about 4 years and had not passed as of late Sep 2026.
  - The bill would put the following into statute: pseudonymization review procedures, the patient 전송요구권 (my-data), designation of 의료 마이데이터 business operators, and the legal basis of 한국보건의료정보원.
  - The bill introduced by Rep. 서영석 (Nov 2025) had a public hearing on 22 Jun 2026. Rep. 전진숙 introduced another bill in Aug 2026.
  - Civil-society groups oppose it over re-identification and leakage risk.
  — [MTN, 28 Sep 2026](https://news.mtn.co.kr/news-detail/2026092815573380395); [전자신문, 1 Apr 2026](https://www.etnews.com/20260401000353); [전자신문, 22 Jun 2026](https://www.etnews.com/20260622000225) (secondary)

### Inferences
- In Korea, people can already pull their records (via 고속도로) and donate them (via the bio-bigdata project, unpaid and recruited through institutions). The legal right to send records onward to a chosen third party is still pending. A consent/compensation rail could be positioned as the private-sector complement once the 디지털헬스케어법 passes.

### Gaps
- No official current 건강정보 고속도로 user count was found beyond the 611,033 app figure.
- The status of the 의료 마이데이터 pilots and the 전송요구권 under the PIPA general my-data provisions (Art. 35-2, in force from Mar 2025 for designated sectors) was not verified in this session.

## Japan: 次世代医療基盤法 and its 2024 amendment

### Takeaway
Japan's route is opt-out collection by state-certified intermediaries. Patients are notified, and their data flows unless they refuse. Since 1 Apr 2024 the law also allows pseudonymized data for certified users. Volumes run to a few million patients per operator. The individual is not paid and does not choose per use.

### Cited Findings
- The amendment was promulgated on 26 May 2023 and took effect on **1 Apr 2024**. It created the 仮名加工医療情報 (pseudonymized medical information) scheme and allows linkage with public databases such as NDB. Pseudonymized data may go only to state-certified users. — [内閣府 改正法 医療機関編, Apr 2024](https://www8.cao.go.jp/iryou/kouhou/pdf/kaisei_jisedaiiryou_iryoukikan.pdf); [官邸 資料](https://www.kantei.go.jp/jp/singi/kenkouiryou/genome/genome_dai13/siryou1.pdf) (primary URLs, summary only)
- Certified so far: **3** pseudonymized-data creators (認定日 13 Dec 2024) and **2** users. RIKEN became the first certified user on 28 Feb 2025. — [内閣府 進捗状況, 3 Sep 2025](https://www8.cao.go.jp/iryou/studygloup/20250903/pdf/s-4.pdf) (primary URL, summary only); [RIKEN](https://www.riken.jp/pr/news/2025/20250228_1/index.html) (primary URL, summary only)
- **Volumes:** at end-Jul 2025, the two leading anonymized-data operators had collected data on ~**2.85M** and ~**2.16M** patients, up from ~2.73M and ~2.10M at end-Apr 2025. A pseudonymized creator figure of ~1.84M patients appears in one deck, but which operator it belongs to is unclear. — [内閣府 s-4, Sep 2025](https://www8.cao.go.jp/iryou/studygloup/20250903/pdf/s-4.pdf) (primary URL, summary only; the table layout was garbled in the summary)
- Certification requires the capacity to collect data on ~1M people a year within 3 years of starting. — [BUSINESS LAWYERS](https://www.businesslawyers.jp/articles/1300) (secondary)

### Inferences
- In Japan, the institution decides and the patient can only refuse. No path exists for a patient to choose to contribute data or to be paid for it. That makes Japan a clear contrast case for the pitch.

### Gaps
- No 2026 volume update was found.
- The names of the certified operators were not confirmed in this session. Background knowledge: LDI, J-MIMO and ICI as 匿名 operators, which is unverified.
- No figures were found on the size of Japan's medical-data market.

## Market size / public budgets tied to these programs

### Takeaway
Public budgets found: UK HDRS £600M; Korea bio-bigdata phase 1 ₩606.6–660B; NHS App IBM contract £160M. No reliable market-size figure for "personal health data contribution" was found.

### Cited Findings
- UK HDRS: £500M from government plus £100M from Wellcome. — [Research Professional](https://www.researchprofessionalnews.com/rr-news-uk-innovation-2025-4-pm-announces-600m-health-data-research-service/) (secondary)
- Korea 국가통합바이오빅데이터 phase 1 (to 2028): ₩606.6B or ₩660B, depending on the source. — [전자신문](https://www.etnews.com/20261015000307); [서울경제](https://m.sedaily.com/article/20102034) (secondary, conflicting)
- NHS App: £160M contract to IBM (Apr 2026). — [HTN](https://htn.co.uk/2026/04/13/nhs-app-160-million-contract-awarded-to-ibm/) (secondary)
- UK Biobank access: ~£9,000 per 3-year project (2024), which gives a reference price for research access. — [Research Professional, 2024](https://www.researchprofessionalnews.com/rr-news-africa-partnerships-2024-4-uk-biobank-gives-poor-country-researchers-free-access-to-data/) (secondary)

### Inferences
- In every regime, money flows to custodians: HDABs, data holders, cohort operators and certified intermediaries. The individual is unpaid. That supports the "no compensation rail" thesis.

### Gaps
- No credible, sourced market size was found in this session for real-world data, health data monetization, or EHDS implementation spend. Another research thread should cover it, or the pitch should leave it out.
