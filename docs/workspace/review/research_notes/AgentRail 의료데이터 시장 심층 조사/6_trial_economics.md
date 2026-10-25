# Clinical Trial and Cohort Study Economics: What Missing Participants and Missing Data Cost (as of Oct 2026)

Method note: Direct fetches failed in this environment. These hosts did not resolve: csdd.tufts.edu, appliedclinicaltrialsonline.com, contractpharma.com and the HubSpot mirror of the Tufts PDF. The proxy also blocked clinicaltrials.gov, including its API. Unless marked otherwise, every finding below comes from WebSearch result summaries and should be treated as **secondary**. Where I give a primary source URL, it is the URL of the primary document, but its content was read through a search summary rather than opened directly. Tags: [P-via-S] = primary document read through a search summary. [S] = secondary report, aggregator or vendor.

## 1. Market size and trial volume

### Takeaway
Estimates of the 2025 global clinical trials market range from about $65B to $89B, depending on the firm and how it defines the market. Since about 2021, ClinicalTrials.gov has recorded roughly 35,000–37,000 new trials starting each year.

### Cited Findings
- Precedence Research: USD 87.42B in 2025 (2024 base USD 83.75B), CAGR 5.97% for 2025–2034, reaching USD 149.58B by 2034 (2025 press release) [S] — [BioSpace / Precedence press release](https://www.biospace.com/press-releases/clinical-trials-market-size-is-estimated-to-be-us-149-58-billion-by-2034)
- Fortune Business Insights: USD 64.94B in 2025, USD 69.27B in 2026, USD 120.75B by 2034, CAGR 7.2% [S] — [Fortune Business Insights](https://www.fortunebusinessinsights.com/markt-f-r-klinische-studien-106930)
- Grand View Research, as reproduced on a Research and Markets listing: USD 89.0B in 2025, USD 158.4B by 2033. I could not confirm this on Grand View's own site [S] — [Research and Markets](https://www.researchandmarkets.com/reports/4396385/clinical-trials-market-size-share-and-trends)
- ClinicalTrials.gov trial starts per year: 37,061 started in 2021 (a COVID-era peak) and 35,338 in 2022. These come from a Sept 2024 preprint analysis of registry data extracted in July 2024 [S] — [Preprints.org 202409.0559](https://www.preprints.org/manuscript/202409.0559)
- Registry size: 492,685 registered studies as of 25 Apr 2024 [P-via-S] — [ClinicalTrials.gov Trends, Charts, and Maps](https://classic.clinicaltrials.gov/ct2/resources/trends). About 501,515 by 15 Jul 2024 [S] (same search result set). An AACT snapshot on 1 May 2024 counted 493,116 studies [S] — [Duke DCRI slides, Jul 2025](https://dcricollab.dcri.duke.edu/sites/NIHKR/KR/GR-Slides-07-18-25.pdf)

### Inferences
- In a pitch, a defensible range is "a ~$65–90B global market (2025)", or a single firm's figure with its name attached. The firms define the market differently, which explains the ~$25B spread.
- About 35k trials start each year, so even a small share with retention problems is thousands of trials a year.

### Gaps
- I could not get an exact count of trials started in 2024 or 2025: the ClinicalTrials.gov API returned 403 through the proxy. Rerun from an unrestricted network: `https://clinicaltrials.gov/api/v2/studies?query.term=AREA[StartDate]RANGE[2025-01-01,2025-12-31]&countTotal=true`.
- I found no IQVIA, Evaluate or other primary market report in 2026 dollars.

## 2. Recruitment cost, budget share, enrollment timelines, non-enrolling sites

### Takeaway
Most trials miss their enrollment timelines; the widely quoted share is 80–86%. About 11% of sites enroll nobody, and 37% under-enroll. A typical cost is about $6.5k to recruit a patient, but a site that enrolls only one patient costs about $130k for that patient. Recruitment is commonly said to be the largest cost driver, at around 32% of trial cost, but that figure has no traceable primary source.

### Cited Findings
- Tufts CSDD (2018 study as cited): 11% of sites fail to enroll a single patient, and 37% under-enroll [S] — [Lab News coverage of Phesi analysis](https://labnews.co.uk/a-fifth-of-cancer-trial-sites-enrol-only-one-patient/)
- Phesi (vendor, 173 trials): single-patient sites cost about **$130,000 per enrolled patient**, versus **$14,167** at better-performing sites (about 10x). Activating a site costs at least **$40,000**, plus about **$3,000/month** in investigator management. A fifth of cancer trial sites enroll only one patient [S] — [Lab News](https://labnews.co.uk/a-fifth-of-cancer-trial-sites-enrol-only-one-patient/)
- Opening a single research site costs about $34,000 (older figure) [S] — [FierceHealthcare / Sheridan Healthcare](https://www.fiercehealthcare.com/healthcare/sheridan-healthcare-inc-calls-medical-profession-to-eliminate-zero-enrollment-boost)
- About 30% of sites enroll zero patients (vendor blog, repeated in a 2026 ACT feature). This conflicts with Tufts' 11% [S] — [Omni Online Strategies](https://omnionlinestrategies.com/blog/why-30-percent-clinical-trial-sites-enroll-zero-patients); [Applied Clinical Trials, Sep 2026](https://www.appliedclinicaltrialsonline.com/view/ai-patient-recruitment-trial-bottleneck-competitive-edge-2026-perspective)
- Citeline e-book (Apr 2026): an estimated **86%** of clinical trials fail to meet their original enrollment targets and timelines [S] — [Clinical Leader / Citeline, 2026](https://www.clinicalleader.com/doc/a-guide-to-patient-engagement-and-recruitment-solutions-0001). Others cite 80–85%, attributed to a 2020 review I could not locate [S] — [DataAlly](https://www.dataally.ai/blog/clinical-trial-enrollment-statistics)
- Recruitment is said to account for **32%** of trial costs, making it the largest cost driver. Multiple secondary pages repeat this with no primary source, and the figure is usually dated to 2015–16 [S] — [Clinical Leader 2023](https://www.clinicalleader.com/doc/patient-centered-clinical-trials-improve-recruitment-and-retention-0001); [OpenClinica](https://www.openclinica.com/blog/patient-centered-clinical-trials-improve-recruitment-and-retention/)
- Average cost to recruit one patient: **~$6,500 ($6,533)** (2015–16 benchmark) [S] — [Scout Clinical](https://www.scoutclinical.com/insights/resources/patient-attrition-infographic); [Clinical Leader / Medable white paper](https://www.clinicalleader.com/doc/clinical-trial-recruitment-0001)
- GlobalData: Phase II accounts for 50% of terminated trials. In oncology, 65% of Phase II trials were terminated, and "low accrual" was the top stated reason, at 35% of terminations [S] — [Pharmaceutical Technology](https://www.pharmaceutical-technology.com/comment/therapy-trials-oncology/)

### Inferences
- The site economics favor the pitch. Each extra site costs at least $40k fixed plus about $3k/month, and 11–30% of sites yield nothing. Over-recruiting by opening more sites is therefore costly and slow. Filling specific gaps at sites that already perform avoids these fixed costs.
- Treat "32% of budget" and "80–86% miss timelines" as industry folklore. Cite them as "widely reported".

### Gaps
- I found no primary Tufts source for cost per randomized patient by phase.
- I could not retrieve Sertkaya et al. (2016, *Clinical Trials*) per-study cost tables by phase and therapeutic area.
- The Tufts finding that "89% meet enrollment, but timelines nearly double" (2013 Impact Report) did not surface.

## 3. Daily cost of delay (Tufts CSDD 2024)

### Takeaway
Tufts CSDD (2024) puts the mean direct cost of running a Phase II or III trial at about **$40,000 per day**: $7,829 for Phase I, $23,737 for Phase II and $55,716 for Phase III. It values lost sales from delayed market entry at about **$800,000 per day** in the white paper and trade press. Later coverage, attributed to the same work, cites **about $500,000 per day**.

### Cited Findings
- Primary sources: Smith Z., DiMasi J., Getz K. "New Estimates on the Cost of a Delay Day in Drug Development," *Therapeutic Innovation & Regulatory Science* 2024, doi 10.1007/s43441-024-0667-w (as reported; the DOI is malformed and could not be verified) [P-via-S]. Also the Tufts CSDD white paper, August 2024: [Tufts CSDD Day of Delay White Paper PDF](https://csdd.tufts.edu/sites/default/files/2025-02/Aug2024%20Day%20of%20Delay%20White%20Paper%20Final.pdf) [P-via-S]
- Direct trial cost per day: Phase II and III combined mean about **$40,000**. By phase: **Phase I $7,829**, **Phase II $23,737**, **Phase III $55,716** [P-via-S] — [Tufts white paper](https://csdd.tufts.edu/sites/default/files/2025-02/Aug2024%20Day%20of%20Delay%20White%20Paper%20Final.pdf); [Applied Clinical Trials](https://www.appliedclinicaltrialsonline.com/view/how-much-does-a-day-of-delay-in-a-clinical-trial-really-cost-)
- Methodology: proprietary budget data from Tufts protocol design benchmark studies conducted 2016–2021, excluding COVID-19 protocols [P-via-S] — [Tufts white paper](https://csdd.tufts.edu/sites/default/files/2025-02/Aug2024%20Day%20of%20Delay%20White%20Paper%20Final.pdf)
- Lost sales: about **$800,000/day** in lost prescription drug or biologic sales (Contract Pharma, Sep 2024) [S] — [Contract Pharma](https://www.contractpharma.com/updates-on-the-value-of-a-day-of-delay-in-drug-development/). About **$500,000/day** in unrealized sales on average (later ACT commentary, Aug 2026) [S] — [Applied Clinical Trials, Aug 2026](https://www.appliedclinicaltrialsonline.com/view/economics-clinical-trial-execution-pharma)
- A secondary source says the peer-reviewed paper reports about $500k while the white paper and trade press round to $800k. This is unverified [S] — search summary of [Applied Clinical Trials](https://appliedclinicaltrialsonline.com/how-much-does-a-day-of-delay-in-a-clinical-trial-really-cost-)
- Critique: a Substack argues that the $500k/day headline overstates the losses [S] — [First Patient In](https://firstpatientin.substack.com/p/saturday-archive-a-day-late-and-half)
- For context, the old, widely quoted figure was $600k to $8M/day in lost sales. I did not verify it here.

### Inferences
- Rule of thumb for the pitch: each day a Phase III trial is extended costs about $56k in direct spend, plus $0.5–0.8M/day in deferred revenue for a successful drug.
- Medidata's dropout model (Section 4) adds a 45-day replacement delay for every 10% dropout. At Phase III, 45 days is about $2.5M in direct cost alone (45 × $55,716 ≈ $2.51M, my arithmetic).

### Gaps
- I could not resolve whether the peer-reviewed number is $500k or $800k; the full paper was not reachable. Cite both, or say "$0.5–0.8M/day".
- I found no therapeutic-area breakdown of daily cost.

## 4. Dropout and attrition, replacement cost, non-adherence, missing data handling

### Takeaway
Typical trial dropout is reported at 15–40%, with about 30% as the common baseline. Replacing a dropout costs about **$19,500**, roughly 3x the cost of recruiting the patient. In top-journal RCTs, 95% of trials have some missing outcome data, with a median of 9% of participants missing. Non-adherence dilutes the effect size, so the required sample size grows roughly by 1/(1−p)²; at 20–30% non-adherence that means about 50% or more extra participants. ICH E9(R1) and the NRC 2010 report make preventing missing data the primary goal.

### Cited Findings
- Dropout range is 15–40%. Initial recruitment costs about $6,500/patient and replacement about **$19,500/dropout** (2015–16 benchmark) [S] — [Scout Clinical](https://www.scoutclinical.com/insights/resources/patient-attrition-infographic); [Scout Clinical PDF 2024](https://scoutclinical.com/hubfs/Web-Insights%202024/Scout%20-%20Understanding%20Clinical%20Trial%20Patient%20Attrition.pdf?hsLang=en)
- Medable / Clinical Leader: up to 30% of recruited patients drop out; recruitment costs $6,533 and replacement $19,533 [S] — [Clinical Leader](https://www.clinicalleader.com/doc/clinical-trial-recruitment-0001)
- Medidata Patient Dropout Calculator (an illustrative model, not observed data): 30% baseline dropout, $19,500 per replacement, and **45 days of added delay per 10% dropout**. It applies the Tufts daily costs by phase ($7,829, $23,737, $55,716) [S] — [Medidata](https://www.medidata.com/en/patient-dropout-calculator/)
- Phase I dropout by therapeutic area (Cutting Edge Information, 2013): oncology 8%, CNS/neurology 7%, women's health 16%. Dropout rises with the number of required visits [S] — [Fierce Biotech](https://www.fiercebiotech.com/cro/dropout-rates-for-oncology-phase-i-trials-remain-under-10)
- Dropout in palliative cancer trials is reported at about 26–44%; I could not find the original source [S] — [IntuitionLabs](https://intuitionlabs.ai/pdfs/patient-retention-in-clinical-trials-strategies-impact.pdf)
- Missing data in top journals (BMJ, JAMA, Lancet, NEJM; Jul–Dec 2013): 73 of 77 RCTs (**95%**) had missing outcome data. The median share of participants missing was **9%** (range 0–70%). Primary analyses used complete-case analysis in 45%, simple imputation in 27%, model-based methods in 19% and multiple imputation in 8%. Only 35% reported a sensitivity analysis [P-via-S] — [Bell et al. 2014, BMC Med Res Methodol (PMC4247714)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4247714/)
- Non-adherence: 20–30% non-adherence to the investigational product requires a **50% increase** in sample size to keep the same power [S] — [Designit](https://designit.com/stories/point-of-view/how-to-improve-clinical-trial-adherence-through-patient-centricity). The standard ITT dilution adjustment is N/(1−p)². For example, an alteplase stroke trial protocol inflated its sample size by 1/0.95² = 1.108 for 5% non-adherence, citing Friedman et al. 1998 [P-via-S] — [NCT02072226 protocol](https://cdn.clinicaltrials.gov/large-docs/26/NCT02072226/Prot_001.pdf); [Penn State STAT 509 §6a.10](https://online.stat.psu.edu/stat509/book/export/html/670)
- A pharmacometric simulation found that the required sample size could **double** depending on adherence level and effect size [S] — [UNTHSC repository](https://unthsc-ir.tdl.org/handle/20.500.12503/27563)
- Standard sample-size methods assume non-compliance is non-informative. Data from OPTIMAAL, LIFE, RENAAL and SOLVD show this assumption often does not hold [P-via-S] — [PMC6310871](https://pmc.ncbi.nlm.nih.gov/articles/PMC6310871)
- NRC (2010), *The Prevention and Treatment of Missing Data in Clinical Trials*, National Academies Press. It prioritizes preventing missing data through design and conduct, specifying the estimand, and sensitivity analyses [P-via-S] — [NAP 12955 / OpenBook](https://nap.nationalacademies.org/read/12056/chapter/16) (note: the search returned a related NAP OpenBook chapter; the report is NAP record 12955). Secondary sources credit it with putting estimand specification at the center of trial design [S] — [Olarte Parra et al., PMC10228513](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10228513/)
- ICH E9(R1) addendum (adopted by ICH in 2019; FDA final guidance 2021):
  - It defines **intercurrent events** (e.g. treatment discontinuation, rescue medication, death) and five strategies for handling them: treatment-policy, hypothetical, composite, while-on-treatment and principal stratum.
  - It distinguishes treatment discontinuation, which is an intercurrent event handled through the estimand, from **study withdrawal**, which produces missing data handled in the analysis.
  - The analysis must align with the estimand and be subject to sensitivity analysis.
  
  [P-via-S] — [FDA E9(R1) guidance](https://fda.gov/media/108698/download); [PMDA copy](https://www.pmda.go.jp/files/000269157.pdf)

### Inferences
- Replacing a dropout costs about $19.5k, versus $6.5k to recruit initially. Each replacement also adds time: about 45 days per 10% dropout in Medidata's model. Recovering data from the dropout instead attacks both the cost and the delay.
- Under the treatment-policy estimand, the one regulators generally favor, outcome data collected *after* treatment discontinuation still count. So recovering missing visits from participants who discontinued has direct regulatory value. This is the strongest argument that targeted backfill beats over-recruitment, because extra recruits do not fix the bias from informative missingness in the existing cohort.
- Arithmetic check (mine): 1/(1−0.2)² = 1.56 and 1/(1−0.3)² = 2.04. So "20–30% non-adherence needs 50% or more extra sample" is consistent with the squared formula, and at 30% the required sample roughly doubles.

### Gaps
- I found no recent (2023–26) peer-reviewed meta-analysis of dropout rates by phase and therapeutic area. The by-phase figures are old (2013) or come from vendor models.
- The $19.5k replacement cost traces to one 2015–16 benchmark that vendors repeat. I could not identify its primary source.

## 5. Observational cohorts: attrition and per-participant cost; protocol amendments

### Takeaway
Retention in long-term cohorts varies widely. One systematic review of preterm birth cohorts reports a median of 87%, and attrition is systematic rather than random. Large cohorts cost hundreds of dollars or pounds per participant per year. All of Us has been squeezed from more than $500M (FY2023) to about $150M (FY2025/26) for roughly 870k participants. Protocol amendments now affect 76% of protocols and cost $141k (Phase II) to $535k (Phase III) in direct cost per amendment (2016 figures).

### Cited Findings
- Retention in cohorts of very preterm and very low birth weight infants: median **87%** retention across 39 cohorts and 83 follow-ups (individual follow-ups ranged ~15–100%) [P-via-S] — [Frontiers in Pediatrics 2021](https://www.frontiersin.org/journals/pediatrics/articles/10.3389/fped.2021.529733/pdf)
- A meta-analysis of 143 longitudinal cohort studies found that barrier-reduction strategies retained about **10% more** of the sample; it identified 95 distinct retention strategies [P-via-S] — [Teague et al. 2018, BMC Med Res Methodol](https://link.springer.com/article/10.1186/s12874-018-0586-7)
- Attrition is systematic. It is most common among older, non-white, male, less educated participants and those with multiple health problems. It reduces both generalizability and power [P-via-S] — [PMC6258319](https://pmc.ncbi.nlm.nih.gov/articles/PMC6258319)
- All of Us budget history:
  - 2017: $230M, against $1.455B authorized over 10 years under the 21st Century Cures Act (2018 reporting) [S] — [WRAL / NYT](https://www.wral.com/the-struggle-to-build-a-massive-biobank-of-patient-data/17428049/)
  - FY2024: $357M, a $184M cut from FY2023 [S] — [Healthcare Innovation](https://www.hcinnovationgroup.com/clinical-it/learning-health-systems-research/news/55250877/with-funding-uncertain-all-of-us-program-eyes-revisions-new-income-sources)
  - FY2025: about $150M, per CEO Josh Denny, down from more than $500M in 2023 [S] — [GenomeWeb](https://genomeweb.com/sequencing/all-us-research-program-unfazed-funding-cuts-lays-out-plans-through-2026)
  - FY2026: about $153M, roughly 72% below FY2023 (July 2026 aggregator) [S] — [CASRAI](https://casrai.org/news/nih-all-of-us-pediatric-enrollment-funding-2026)
  - Enrollment: more than **873,000** consented participants. Adult enrollment sites were sharply reduced and adult biosample collection paused [S] — [GenomeWeb](https://www.genomeweb.com/sequencing/nih-all-us-program-plans-2026-data-release-boost-pediatric-enrollment-new-studies)
- All of Us researcher biospecimen fee: $14.00 per tube for pulling and aliquoting [P-via-S] — [All of Us biospecimen cost estimates 2026](https://www.researchallofus.org/wp-content/themes/research-hub-wordpress-theme/media/2026/biosp_cost_estimates.pdf)
- UK Biobank funding (about 500k participants):
  - Cumulative funding of **£303.2M** (July 2024 summary, including £120M of added infrastructure funding). The 2022 version gave £174.6M.
  - Line items include £23.1M for MRI of 100,000 participants and £10.0M for repeat imaging of up to 60,000.
  - Wellcome core funding: £26.8M (2004–10) and £53.2M (2010–29).
  
  [P-via-S] — [UK Biobank funding summary, Jul 2024](https://www.ukbiobank.ac.uk/media/jq2lj0wi/uk-biobank-funding-details-summary_july-2024.pdf); [2022 version](https://www.ukbiobank.ac.uk/media/zyxa35t2/funding-uk-biobank-summary-19-10-22-for-publication.pdf)
- UK Biobank repeat-imaging project: £30M from MRC, CZI and Calico, £10M each [P-via-S] — [UK Biobank news](https://www.ukbiobank.ac.uk/news/ambitious-project-announced-to-create-the-worlds-largest-longitudinal-imaging-dataset/)
- Protocol amendments, 2024 Tufts study (Getz, Smith, Botto, Murphy, Dauchy, TIRS 2024; 16 companies, 950 protocols, 2,188 amendments):
  - Protocols with at least one amendment rose from 57% to **76%** since 2015.
  - The mean number of amendments per protocol rose 60%, from 2.1 to **3.3**.
  - **77%** of amendments were judged unavoidable.
  - From identifying the need to amend to final approval took about **260 days** (secondary report only).
  
  [P-via-S] — [TIRS 2024 record](https://katalog.hcu-hamburg.de/vufind/Search2Record/SPR055638252); [IntuitionLabs summary](https://intuitionlabs.ai/articles/clinical-trial-protocol-amendments-cost-data)
- Amendment cost (Tufts 2016, TIRS; 836 protocols from 2010–13, with cost data on 52 protocols):
  - Median direct cost per substantial amendment: **$141,000 (Phase II)** and **$535,000 (Phase III)**.
  - Indirect costs could make the total 3–4x larger.
  - At about 2.3 amendments per Phase III protocol, direct amendment cost exceeds $1M per study (derived figure).
  
  [P-via-S] — [Getz et al. 2016, TIRS](https://journals.sagepub.com/doi/abs/10.1177/2168479016632271); [Applied Clinical Trials](https://www.appliedclinicaltrialsonline.com/view/protocol-amendments-costly-solution)

### Inferences
- All of Us per participant, my arithmetic: about $150M/yr ÷ 873k ≈ **$170 per participant per year** in current funding. The historical average is much higher: cumulative appropriations of more than $2B over about 873k participants. This is a rough figure, not a published one.
- UK Biobank, my arithmetic: £303M ÷ 500k ≈ **£600 per participant** cumulative over about 20 years, or roughly £30 per participant per year in core funding. Imaging costs about £231 per baseline scan and £167 per repeat scan.
- Because cohort attrition is systematic, extra recruitment cannot replace the specific person-weeks lost from older, multimorbid participants. Targeted backfill can.
- Protocol amendments, often made to rescue enrollment, each cost $141k–$535k in direct cost plus months of cycle time.

### Gaps
- I found no general benchmark for retention in adult observational cohorts.
- I found no official per-participant-per-year costs for UK Biobank or All of Us; the figures above are derived.
- I found no 2024-wave cost figures for amendments.

## 6. Total cost to bring a drug to market and the clinical share

### Takeaway
DiMasi, Grabowski and Hansen (2016) estimate **$2.558B** in capitalized pre-approval cost per approved new drug, or $2.87B including post-approval R&D (2013 dollars). Of the pre-approval cost, **$1.46B (about 57%) is the clinical phase**.

### Cited Findings
- DiMasi JA, Grabowski HG, Hansen RW. "Innovation in the pharmaceutical industry: New estimates of R&D costs," *J Health Econ* 2016;47:20–33:
  - Pre-approval capitalized cost **$2,558M** (2013 $, 10.5% real discount rate).
  - Including post-approval R&D: **$2,870M**.
  - Based on 106 randomly selected new drugs from 10 firms.
  - Costs grew 8.5% per year above inflation compared with the previous study.
  
  [P-via-S] — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jhecon/v47y2016icp20-33.html); [Tufts CSDD cost study page](https://csdd.tufts.edu/cost-study)
- Split of the capitalized cost: **pre-human $1,098M**, **clinical $1,460M**. Clinical out-of-pocket cost was $965M before the cost of capital. Preclinical cost was imputed using a 0.308 ratio of pre-human to total spending, giving $430M out of pocket [P-via-S] — [Tufts CSDD briefing, 18 Nov 2014 (KEI copy)](https://www.keionline.org/wp-content/uploads/2017/10/Tufts_CSDD_briefing_on_RD_cost_study_-_Nov_18,_2014..pdf)
- Critiques: the estimate relies on industry-provided data, applies only to self-originated new chemical entities, and the preclinical figure is essentially an assumption [S] — [KEI](https://www.keionline.org/23054); [Fierce Biotech](https://www.fiercebiotech.com/r-d/harvard-tufts-med-students-stage-protest-at-biased-2-9b-drug-development-figure)

### Inferences
- The clinical share is 57% of capitalized cost (1,460/2,558) and about 69% of out-of-pocket cost (965/(965+430)), my arithmetic. Most of R&D cost sits in trials, where recruitment and retention problems hit.
- The DiMasi figure is in 2013 dollars and has not been updated by Tufts. Inflated to today it would be noticeably higher, but I found no sourced update.

### Gaps
- I did not retrieve alternative estimates, such as Wouters et al. 2020 (JAMA; from memory, a median of about $985M; not verified here) or Sertkaya et al. 2024 (JAMA Netw Open). I did not search for them within the tool budget.
