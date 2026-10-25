# US federal and state law for individual-directed health data contribution to research (as of 2026-10-25)

> Hackathon evidence summary, not legal advice. **Method note:** in this session, direct fetches of hhs.gov, ecfr.gov, app.leg.wa.gov and mofo.com failed (proxy 403/DNS). Findings marked **[search-verified]** were confirmed through web-search results that quote the primary source. Findings marked **[reg-text, not re-fetched]** come from the codified text at the linked official URL, recalled from the regulation itself. Re-check those before anything is quoted externally. Items marked **[UNCERTAIN]** need confirmation.
>
> Terms: use "research contribution", "participation compensation/settlement", "re-identification risk reduction" and "research missing-data inference". Statutory definitions of "sale/sell" are reported verbatim only where analysis requires them.

---

## Q0. Verification and correction of prior points 6-9 (from 00_design_and_prior_answers.md)

### Takeaway
Points 6-9 are directionally correct, but each needs a qualifier. (6) Broad consent covers only *storage, maintenance and secondary research use* of identifiable data. Few institutions have adopted it, and it requires limited IRB review. (7) The OHRP retention-after-withdrawal rule is right, but the guidance's "annual continuing review" condition predates the 2018 Rule. HIPAA's "reliance" exception and FDA retention duties also apply. (8) The NIH point is too vague, and NIH Certificates of Confidentiality are the more useful hook. (9) This point is correct, and HIPAA 164.512(i)(2) gives concrete documentation elements that a Credential could reference but cannot replace.

핵심 요약(한국어): 6~9번은 대체로 맞지만 보완이 필요하다. broad consent는 "식별가능 정보의 보관·2차 연구"에만 쓸 수 있고, 제한적 IRB 검토(limited IRB review)를 거쳐야 하며, 실제로 도입한 기관도 적다. 철회 후 기존 데이터 보관은 가능하지만, 2010년 지침의 "연 1회 지속심의" 조건은 2018 개정 Common Rule로 일부 바뀌었다. IRB 문서 요건(164.512(i)(2))은 체인 Credential로 대체할 수 없다.

### Cited Findings
- **(6) Broad consent [reg-text, not re-fetched].** 45 CFR 46.116(d) permits broad consent only "for the storage, maintenance, and secondary research use of identifiable private information or identifiable biospecimens". Its elements are listed in 46.116(d)(1)-(8). They include the types of research that may be conducted, the identifiable private information that might be used, whether information will be shared and the types of institutions or researchers that might receive it, and the storage/use period, which may be indefinite. Subjects must also be told that they will not be informed of the specific studies "unless" told otherwise, whether clinically relevant results will be returned, and whom to contact. — [eCFR 45 CFR 46.116](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.116)
- Broad consent works together with exemptions 46.104(d)(7) (storage and maintenance, with limited IRB review) and 46.104(d)(8) (secondary research under broad consent). Under (d)(8), the IRB must determine that the specific study is within the scope of the broad consent. If a person was asked for broad consent and **refused**, the IRB **cannot waive** consent for that person's information (46.116(f)(1)). — [eCFR 45 CFR 46.104](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.104); [eCFR 46.116](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.116) [reg-text, not re-fetched]
- **(7) Withdrawal [search-verified].** OHRP's "Guidance on Withdrawal of Subjects from Research: Data Retention and Other Related Issues" (Sept 2010) says investigators may retain and analyze data already collected from a withdrawn subject, including identifiable private information. The analysis must stay within the IRB-approved scope, and OHRP recommends explaining the retention policy during consent. The guidance is described as recommendations unless it cites a specific regulatory requirement. It also states that revoking a HIPAA authorization does not prevent continued retention and analysis because of the Privacy Rule's reliance provision. — [OHRP Withdrawal Guidance (2010)](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/guidance-on-withdrawal-of-subject/index.html); [PDF](https://www.hhs.gov/ohrp/sites/default/files/ohrp/policy/subjectwithdrawal.pdf); [Federal Register notice, Sept 21, 2010](https://www.govinfo.gov/content/pkg/FR-2010-09-21/pdf/2010-23517.pdf)
- That guidance also states that "IRB continuing review of the data analysis must occur at least annually". Under the 2018 Common Rule, 46.109(f)(1) removes continuing review for many minimal-risk studies, including expedited studies, studies under limited IRB review, and studies at the data-analysis-only stage. That condition is therefore **outdated** for most 2018-Rule studies. — [OHRP guidance](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/guidance-on-withdrawal-of-subject/index.html); [eCFR 46.109](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.109) [reg-text, not re-fetched]
- NIH's intramural IRB office applies the same subject-withdrawal approach: data collected before withdrawal may be kept as described in consent. — [NIH OHSRP Subject Withdrawal](https://irbo.nih.gov/conducting-your-study/subject-withdrawal-from-research/)
- **(8) NIH [UNCERTAIN as phrased].** I found no single NIH document that states the "existing protocol vs new purpose follow-on study" distinction as framed in the prior answer. The Common Rule mechanism for this distinction is the IRB's within-scope determination under 46.104(d)(8)(iii) and the 46.116(b)(9) statement about future research use of de-identified data. For NIH-funded work, the stronger legal hook is the **Certificate of Confidentiality**. NIH-funded research that collects identifiable sensitive information is automatically issued one under 42 U.S.C. 241(d), as amended by the 21st Century Cures Act §2012. It bars compelled disclosure (e.g., subpoena) and disclosure without consent. — [42 U.S.C. 241 (LII)](https://www.law.cornell.edu/uscode/text/42/241) [reg-text, not re-fetched]
- **(9) IRB status [reg-text, not re-fetched].** Documentation of a HIPAA waiver of authorization under 164.512(i)(2) must include the IRB or privacy board's identity, the approval date, a statement that the waiver criteria are met, a brief description of the PHI needed, the review procedure used, and the signature of the chair or designee. A hash or Credential on XRPL can *point to* this document but cannot *be* it. Under 46.112, an institution's officials may not approve research that the IRB has disapproved. — [eCFR 45 CFR 164.512](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.512); [eCFR 46.112](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.112)

### Inferences
- Rewrite point 6 as: "Under 46.116(d), broad consent can cover storage and secondary research use of identifiable data within described research types. A specific study still needs the institution or IRB to decide that it falls within that scope. Our per-round, per-purpose consent is *narrower* than broad consent. That is a safer default, and it means we do not depend on whether the institution has adopted broad consent."
- Rewrite point 7 to add that in FDA-regulated trials, data collected before withdrawal **must** be kept (FDA 2008 guidance; 21 CFR 312.62) [UNCERTAIN: not re-fetched]. Our withdrawal type (3), "withdraw data access consent", should be described as stopping new access and key release. It does not delete copies already delivered and analyzed.
- Point 9 stands as written. In addition, the agent should require a human-verified document (approval letter, or exemption determination by the institution, not the investigator) before an IRB Credential is treated as valid.

### Gaps
- I could not re-fetch the exact 46.116(d) and 46.109(f) text this session.
- I did not find a specific NIH policy for "new purpose follow-on" studies. The NIH Genomic Data Sharing Policy and the 2023 Data Management & Sharing Policy may be relevant but were not checked.

---

## Q1. HIPAA Privacy Rule: when the personal agent is not a covered entity or business associate; research provisions; 2024 reproductive health rule

### Takeaway
A consumer-chosen personal agent that is **not provided by or on behalf of** a covered entity (CE) is outside HIPAA. Once a CE sends a person's PHI to an app that person chose, the CE is not liable for what the app does with it. HIPAA research rules (164.508, 164.512(i), 164.514) therefore bind the *recipient* only if the recipient is itself a CE or BA. They are still the best **design template** for consent content, de-identification and minimum-necessary filtering. The 2024 reproductive health amendments were **vacated nationwide** (June 18, 2025), and the vacatur stands after the appeal was dismissed (Sept 2025).

핵심 요약: 개인이 직접 고른 앱/에이전트는 HIPAA 적용 대상(CE/BA)이 아니다. 병원이 환자 요청에 따라 그 앱으로 PHI를 보낸 뒤에는 병원 책임이 없다. 대신 FTC법과 주법이 적용된다. HIPAA 연구 조항은 수신 기관이 CE일 때만 직접 적용되지만, 동의서 요소·비식별·최소필요 설계의 기준으로 쓴다. 2024 생식건강 규칙은 2025년 6월 전국적으로 무효화되었다.

### Cited Findings
- **Not liable after app transfer [search-verified].** If the individual's chosen app "was not provided by or on behalf of the covered entity", the CE "would not be liable under the HIPAA Rules for any subsequent use or disclosure" by the app. If the app was developed for or provided on behalf of the CE, a business-associate relationship exists and the CE can be liable. — [HHS FAQ 3009](https://www.hhs.gov/hipaa/for-professionals/faq/3009/does-a-hipaa-covered-entity-bear-liability.html); [HHS FAQ 3010](https://www.hhs.gov/hipaa/for-professionals/faq/3010/what-liability-does-a-covered-entity-face.html); [HHS Access Right, Health Apps & APIs](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access-right-health-apps-apis/index.html)
- **Unsecure transmission [search-verified].** At the individual's request, a CE may send ePHI to the app over an unsecure channel. The CE is not responsible for unauthorized access in transit, though it may warn the patient about the risk. — [HHS FAQ 3010](https://www.hhs.gov/hipaa/for-professionals/faq/3010/what-liability-does-a-covered-entity-face.html)
- **Ciox caveat [search-verified].** The app guidance remains effective only to the extent it is consistent with *Ciox Health, LLC v. Azar* (D.D.C. 2020). That decision limited the third-party-directive right in 164.524(c)(3)(ii) to electronic copies of PHI in an EHR, and limited the patient-rate fee cap to an individual's own access. — [HHS Access Right, Health Apps & APIs](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access-right-health-apps-apis/index.html)
- **Right of access [reg-text, not re-fetched].** Under 45 CFR 164.524, the individual has a right to inspect and obtain a copy of PHI in a designated record set, in the form and format requested if it is readily producible. The CE must act within 30 days, with one 30-day extension. — [eCFR 164.524](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.524)
- **Research definition [reg-text, not re-fetched].** 164.501 defines "Research" as "a systematic investigation, including research development, testing, and evaluation, designed to develop or contribute to generalizable knowledge". — [eCFR 164.501](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.501)
- **Authorization 164.508 [reg-text, not re-fetched].**
  - Core elements, 164.508(c)(1): a specific description of the information; who may disclose; recipients; each purpose; an expiration date or event ("end of the research study" or "none" is allowed for a research database or repository); signature and date.
  - Required statements, 164.508(c)(2): the right to revoke and how; whether treatment is conditioned on signing; that information may be redisclosed and lose protection.
  - Compound authorizations, 164.508(b)(3)(i): a research authorization may be combined with another research authorization or consent. Since the 2013 Omnibus Rule, conditioned and unconditioned research authorizations may be combined if they are clearly differentiated and the unconditioned part is opt-in.
  - Revocation, 164.508(b)(5): revocation must be in writing and is effective except to the extent the CE has acted in reliance on the authorization. For research, this lets data already obtained be used to protect the study's integrity.
  - Since 2013, HHS also permits authorizations for *future* research if the uses are described so that disclosure would reasonably be expected. — [eCFR 164.508](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.508); [HHS Research guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/research/index.html)
- **Waiver 164.512(i) [reg-text, not re-fetched].** An IRB or privacy board may waive or alter authorization if three conditions are met. The use or disclosure must involve no more than minimal risk to privacy, which requires an adequate plan to protect identifiers, an adequate plan to destroy identifiers at the earliest opportunity, and written assurances against reuse. The research must also be impracticable without the waiver, and impracticable without the PHI. Separate provisions cover reviews preparatory to research (164.512(i)(1)(ii)) and decedents' information (164.512(i)(1)(iii)). — [eCFR 164.512](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.512)
- **De-identification [reg-text, not re-fetched].** 164.514(b) offers two routes.
  - Expert Determination, (b)(1): a qualified expert determines that the risk of identification is "very small".
  - Safe Harbor, (b)(2): remove 18 identifiers, and the CE must have no actual knowledge that the remaining information could identify the person. The identifiers include names, geographic units smaller than a state (the first 3 ZIP digits are allowed if the area has more than 20,000 people), and **all elements of dates except year** (ages over 89 aggregated). They also include phone, fax, email, SSN, medical record number, health plan number, account number, certificate or license number, vehicle IDs, **device identifiers and serial numbers**, URLs, IP addresses, biometric identifiers, full-face photos, and "any other unique identifying number, characteristic, or code".
  - Re-identification code, 164.514(c): a code is allowed only if it is **not derived from** information about the individual and the CE does not disclose the mechanism.
  - HHS guidance says hashes of identifiers such as an SSN are not acceptable codes. — [eCFR 164.514](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514); [HHS De-identification Guidance](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html)
- **Limited data set 164.514(e) [reg-text, not re-fetched].** A limited data set excludes 16 direct identifiers but may keep dates, city, state, 5-digit ZIP and ages. It may be used only for research, public health or health care operations, under a **data use agreement** that bars re-identification and contact. — [eCFR 164.514](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514)
- **Minimum necessary 164.502(b) [reg-text, not re-fetched].** The standard does **not** apply to disclosures to the individual or to disclosures made under an authorization (164.502(b)(2)(i), (iii)). Under 164.514(d)(3)(iii)(D), a CE may rely on a researcher's documentation or representations (164.512(i)) as meeting the minimum-necessary standard. — [eCFR 164.502](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.502)
- **2024 reproductive health rule [search-verified].** In *Purl v. HHS* (N.D. Tex.), Judge Kacsmaryk vacated most of the 2024 amendments nationwide on June 18, 2025. The Fifth Circuit dismissed the appeal on Sept 10, 2025, so the vacatur remains. The 42 CFR Part 2-related changes to the Notice of Privacy Practices were not vacated (compliance date Feb 16, 2026). — [Haynes Boone (appeals closed)](https://www.haynesboone.com/news/publications/hipaa-reproductive-healthcare-privacy-rule-remains-vacated-after-appeals-closed); [Husch Blackwell](https://huschblackwell.com/newsandinsights/federal-court-vacates-2024-hipaa-reproductive-health-privacy-rule-key-impacts-for-covered-entities-and-npp-compliance); [Quarles](https://www.quarles.com/newsroom/publications/hipaa-reproductive-health-rule-vacated-nationally)

### Inferences (mapping to design)
- **Records obtained by the individual:** the hospital's release through 164.524 needs no HIPAA authorization, and once released HIPAA no longer follows the data. Our agent is regulated by the **FTC Act, the HBNR and state law**, not by HIPAA. This holds only if the platform is not offered "by or on behalf of" a partner hospital. A Mongolian or Korean hospital partner would not be a HIPAA CE anyway, but a *US* hospital partner that white-labels the agent could create a business-associate relationship.
- **Recipient side:** if the research institution is a hybrid CE, such as an academic medical center, data it receives could become PHI if its research unit sits inside the covered component. Many universities place research outside that component. [UNCERTAIN, institution-specific]
- **Study-specific pseudonymous IDs:** random per-study IDs that are not derived from identifiers fit the 164.514(c) model. Wearable **timestamped time series** keep full dates, so they **fail Safe Harbor** unless dates are shifted or reduced to year. Device serial numbers must be removed. In practice, our "blocking risky quasi-identifier combinations" fits **Expert Determination** (statistical, "very small risk") or a **limited data set plus DUA**, not Safe Harbor. Describe this as "re-identification risk reduction".
- **Minimum necessary:** this is not legally required for an individual-directed disclosure. Using it as a voluntary design control matches 164.514(d) best practice and the "data minimization" expectations in the FTC and state laws below.
- **Consent screen:** mirror 164.508(c) elements per round: data description, recipient, purpose, expiration event, revocation method, redisclosure warning, and no conditioning of services on signing.

### Gaps
- I could not re-fetch the 2019 HHS app FAQ text. The quotes come from search excerpts of FAQs 3009 and 3010.
- The status of the Jan 2025 HIPAA Security Rule NPRM was not checked.

---

## Q2. Common Rule 45 CFR 46, payment to participants

### Takeaway
The individual's agent is not an "investigator", but the receiving institution conducts human-subjects research if it obtains identifiable private information **or** obtains data through **interaction** with the person. Our per-round request to the person through the agent is probably an interaction. The safest framing is that each contributing study has its own IRB approval or institutional exemption determination, with consent elements from 46.116(a)-(c). Payment is **not a benefit**, must avoid undue influence, should accrue across rounds, and must not be forfeited when a participant withdraws.

핵심 요약: 기관이 개인 에이전트를 통해 참여자에게 회차별로 요청하면 "상호작용(interaction)"으로 볼 가능성이 높다. 그러면 가명 ID를 써도 인간대상연구로서 IRB 심의/면제 판단이 필요하다. 참여 대가는 연구의 "이익"이 아니며, 회차별로 누적 지급해야 하고, 철회 시 이미 발생한 대가를 회수하면 안 된다(Escrow/clawback 설계 주의).

### Cited Findings
- **Definitions, 46.102(e) [reg-text, not re-fetched].** A "human subject" is a living individual about whom an investigator "(i) obtains information … through intervention or interaction with the individual, and uses, studies, or analyzes the information; or (ii) obtains, uses, studies, analyzes, or generates identifiable private information". "Interaction includes communication or interpersonal contact between investigator and subject". "Identifiable private information" means information for which "the identity of the subject is or may readily be ascertained by the investigator or associated with the information". — [eCFR 46.102](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.102)
- **Coded data [reg-text, not re-fetched].** OHRP's 2008 Coded Private Information guidance says coded data is not identifiable to the investigator if the investigator cannot readily ascertain identity. One example is when the key holder agrees in writing never to release the key. — [OHRP Coded Private Information (2008)](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/research-involving-coded-private-information/index.html)
- **Consent, 46.116 [reg-text, not re-fetched].**
  - 46.116(a)(5)(i): consent must begin with a "concise and focused presentation of the key information".
  - 46.116(b)(8): basic element that participation is voluntary, refusal involves no penalty or loss of benefits, and the subject "may discontinue participation at any time without penalty or loss of benefits to which the subject is otherwise entitled".
  - 46.116(b)(9): for identifiable private information, a statement on whether identifiers might be removed and the de-identified data used in future research without additional consent.
  - 46.116(c)(4): additional element covering the consequences of withdrawing and the procedures for orderly termination.
  - 46.116(c)(7): additional element covering commercial profit and whether the subject will share in it. — [eCFR 46.116](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.116)
- **Exemptions, 46.104(d) [reg-text, not re-fetched].**
  - (d)(4): secondary research uses of identifiable information when (i) the information is publicly available, (ii) it is recorded so subjects cannot readily be identified and with no contact or re-identification, (iii) the use is regulated by HIPAA as "health care operations/research/public health", or (iv) the research is conducted by or for a federal agency.
  - (d)(7) and (d)(8): storage and secondary research under broad consent.
  - Exemption (d)(4) covers **secondary** use of existing data and does not cover prospective, per-round collection through interaction. — [eCFR 46.104](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.104)
- **IRB approval criteria, 46.111(a)(7) [reg-text, not re-fetched].** The IRB must find "adequate provisions to protect the privacy of subjects and to maintain the confidentiality of data". Under 46.111(b), additional safeguards are required for subjects vulnerable to coercion or undue influence. — [eCFR 46.111](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-A/part-46/section-46.111)
- **Payment [reg-text/guidance, not re-fetched].** FDA's "Payment and Reimbursement to Research Subjects" information sheet (Jan 2018) makes four points. Payment is **not** a benefit. It should accrue as the study progresses and not be contingent on completion. A small completion bonus is acceptable if it is not coercive. The IRB reviews the amount and schedule to avoid undue influence. OHRP's Informed Consent FAQs likewise say payment should not be considered a benefit. — [FDA Payment guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/payment-and-reimbursement-research-subjects); [OHRP Informed Consent FAQs](https://www.hhs.gov/ohrp/regulations-and-policy/guidance/faq/informed-consent/index.html)

### Inferences (mapping to design)
- **Interaction:** a per-round request delivered to the person's agent, which asks the person, is "communication … between investigator and subject". That likely makes the person a human subject even if the institution sees only a pseudonymous ID. Do not claim "not human subjects research because pseudonymous". [UNCERTAIN: depends on whether an agent's automated reply counts as interaction. The conservative answer is yes.]
- **Three withdrawal types mapped to 46.116(b)(8) and (c)(4):**
  - (1) Decline this round: refusal without penalty. Other rounds are unaffected.
  - (2) Stop future supply: discontinuation. Data already given is kept per the protocol.
  - (3) Withdraw data access consent: request to end further use or access. The institution may still keep already analyzed data if the consent form said so, per OHRP 2010 guidance.
  The consent text must state all three outcomes explicitly.
- **Payment through XRPL Escrow:** escrow per completed round (prorated) is consistent with FDA guidance. A single escrow released only at "study completion" is not. MPT clawback may revoke a *data license token*, but **completed-round compensation must not be clawed back** on withdrawal, because the participant may not lose benefits "otherwise entitled".
- **Commercial-profit element (46.116(c)(7)):** disclose whether the participant shares in commercial profits.
- **The agent must not self-issue exempt status.** Exemption determinations are made under institutional policy, usually by the IRB office (OHRP recommends against investigator self-determination). [UNCERTAIN: OHRP guidance not re-fetched]

### Gaps
- Not checked: a SACHRP-specific payment recommendation (2019?).
- Not checked: whether an LLM agent's automated response is an "interaction" under OHRP interpretations. No guidance found.

---

## Q3. FTC Act §5 and Health Breach Notification Rule (16 CFR Part 318, amended 2024)

### Takeaway
Our personal agent aggregates wearable, hospital and survey data for the individual, so it is very likely a **vendor of personal health records** under the amended HBNR. Any disclosure beyond what the person authorized is a **"breach of security"** that requires notice. Under FTC Act §5 and the GoodRx, BetterHelp, Premom and Flo orders, sharing health data beyond what users understood is deceptive or unfair. Those orders require **affirmative express consent** before sharing health data.

핵심 요약: 우리 개인 에이전트는 개정 HBNR상 "개인건강기록(PHR) 벤더"에 해당할 가능성이 높다. 동의 범위를 벗어난 제공은 해킹이 없어도 "침해(breach)"로 통지 의무가 생긴다. FTC는 건강 앱의 제3자 공유에 대해 명시적 사전 동의를 요구하는 명령을 반복해 내렸다.

### Cited Findings
- **Effective date [search-verified].** The FTC finalized HBNR amendments on April 26, 2024. They were published May 30, 2024 and took effect **July 29, 2024**. The rule covers PHR vendors and PHR-related entities not covered by HIPAA, and the amendments clarify that it reaches health apps and similar technologies. — [FTC](https://www.ftc.gov/node/78112); [Venable](https://www.venable.com/insights/publications/2024/07/final-changes-to-health-breach-notification); [Quarles](https://www.quarles.com/newsroom/publications/ftc-publishes-final-rule-amending-health-breach-notification-rule)
- **Definitions, 16 CFR 318.2 [search-verified].**
  - "Personal health record (PHR) means an electronic record of PHR identifiable health information on an individual that has the technical capacity to draw information from multiple sources and that is managed, shared, and controlled by or primarily for the individual."
  - "Breach of security … acquisition of [unsecured PHR identifiable health information] without the authorization of the individual … A breach of security includes an unauthorized acquisition … that occurs as a result of a data breach or an unauthorized disclosure."
  - "PHR identifiable health information" refers to information created or received by a "covered health care provider". — [eCFR 16 CFR 318.2](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-318/section-318.2); [LII 318.2](https://www.law.cornell.edu/cfr/text/16/318.2)
- **Provider definitions, 318.2 [reg-text, not re-fetched].** The 2024 rule defines "covered health care provider" by cross-reference to 42 U.S.C. 1395x(u) and (s) and to any entity furnishing "health care services or supplies". That term includes any online service, such as a website, mobile application or IoT device, that provides mechanisms to track diseases, health conditions, diagnoses, treatments, medications, vital signs, symptoms, bodily functions, fitness, fertility, sexual health, sleep, mental health, genetic information or diet. — [eCFR 318.2](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-318/section-318.2)
- **Notice and enforcement [reg-text, not re-fetched].** Notice is due to individuals without unreasonable delay and within 60 calendar days. For 500 or more affected people, the FTC must be notified at the same time as individuals, and media must be notified in some cases. The statutory basis is ARRA §13407 (42 U.S.C. 17937). Violations are treated as violations of a trade regulation rule, so civil penalties are available. — [eCFR Part 318](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-318)
- **GoodRx (2023) [search-verified].** This was the first HBNR enforcement action: a $1.5M civil penalty and a ban on sharing health information for advertising. It followed the FTC's Sept 2021 policy statement that health apps and connected devices must comply with the HBNR. — [Davis Polk](https://www.davispolk.com/insights/client-update/ftc-brings-first-enforcement-action-under-health-breach-notification-rule); [Akerman](https://www.akerman.com/en/perspectives/hrx-ftcs-enforcement-action-against-goodrx-breathes-new-life-into-decade-old-regulation.html)
- **BetterHelp (2023) [search-verified].** The settlement was $7.8M under §5 only, not the HBNR. The order bans sharing health information for advertising, requires affirmative express consent for other sharing, and requires third parties to delete the data. — [Frier Levitt](https://www.frierlevitt.com/articles/ftc-orders-virtual-mental-health-platform-to-pay-7-8-million-to-resolve-data-disclosure-allegations/); [CLA Privacy Law](https://calawyers.org/privacy-law/ftc-enforcement-action-against-goodrx-and-betterhelp/)
- **Premom (2023) [search-verified].** The FTC alleged that the app shared reproductive health and precise geolocation data through SDKs (Google, Umeng). The case was brought under §5 and the HBNR, with a $100,000 civil penalty and a consent-before-sharing requirement. — [Axios](https://www.axios.com/2023/05/18/ftc-cracks-down-fertility-app-premom-after-goodrx-action)
- **Flo (2021) [search-verified].** The complaint did not allege an HBNR violation, and two commissioners dissented on that point. This gap motivated the 2024 "health care provider" clarification. — [Davis Polk PDF](https://www.davispolk.com/index%2Ephp/print/pdf/node/110107)
- **§5 penalties [search-verified].** §5 (15 U.S.C. 45) generally does not allow civil penalties against first-time offenders. That is why the HBNR's civil-penalty route matters. — [Akerman](https://www.akerman.com/en/perspectives/hrx-ftcs-enforcement-action-against-goodrx-breathes-new-life-into-decade-old-regulation.html); [15 U.S.C. 45 (LII)](https://www.law.cornell.edu/uscode/text/15/45)

### Inferences (mapping to design)
- **The agent is likely a PHR vendor.** It draws data from multiple sources and is controlled by and for the individual. Any field sent outside the round's consented scope, such as an extra field an LLM "inferred" as useful, could be an **unauthorized disclosure, which is a reportable breach**. Deterministic, code-enforced scope checks are therefore a legal control, not just a UX preference.
- The research institution receiving data with authorization is not a breach. Third-party SDKs or analytics inside the agent that receive health data without consent would be the GoodRx/Premom pattern.
- **Claims:** under §5, statements like "cannot be re-identified" or "fully anonymous" are deceptive if not true. Use "re-identification risk reduction".

### Gaps
- Exact current civil-penalty amount per violation (inflation-adjusted 2025/2026) was not verified.
- I did not verify any 2025-2026 FTC HBNR enforcement actions after the amendments.
- *Frasco v. Flo Health* (private CIPA litigation; reported Aug 2025 jury verdict against Meta) was not verified in this session. [UNCERTAIN]

---

## Q4. State law: CCPA/CPRA, CMIA, Washington MHMDA, New York HIPA, Connecticut and Colorado

### Takeaway
- **Washington MHMDA** is the highest-risk state law. It has no revenue threshold, requires separate consent for collection and sharing, requires a strict "valid authorization" for any sale, and is enforced through the WA Consumer Protection Act with a private right of action.
- **CCPA** treats a disclosure the consumer intentionally directs as not a "sale". It classifies health data as sensitive personal information, and its new regulations (effective Jan 1, 2026) add risk-assessment and ADMT duties.
- **CMIA §56.06** can treat a personal health record app as a "provider of health care".
- **NY HIPA S929 was vetoed** on Dec 19, 2025. A revised bill (A.10357/S.9269) was introduced in 2026, and its status is unconfirmed.

핵심 요약: 가장 위험한 주법은 워싱턴 MHMDA다. 매출 기준 없이 적용되고, 수집·공유 동의를 각각 받아야 하며, "판매"에는 엄격한 서면 승인이 필요하고, 개인 소송이 가능하다. 참여자에게 대가가 지급되는 기여 구조가 MHMDA상 "sell"로 해석될 위험은 배제할 수 없으므로 보수적으로 설계해야 한다. 뉴욕 HIPA(S929)는 2025.12.19 거부권으로 폐기되었고, 2026년 수정안의 통과 여부는 확인하지 못했다.

### Cited Findings: Washington MHMDA (RCW 19.373)
- **Sale authorization and enforcement [search-verified].** RCW 19.373.070(1): "it is unlawful for any person to sell or offer to sell consumer health data concerning a consumer without first obtaining valid authorization". An authorization is invalid if it has expired, lacks required content, has been revoked, or is combined with other documents. Required content includes a revocation statement and notice that sold data may be redisclosed and lose protection. Under RCW 19.373.090, a violation is a per se violation of the WA Consumer Protection Act (ch. 19.86 RCW), which carries a private right of action. — [RCW 19.373.070](https://app.leg.wa.gov/RCW/default.aspx?cite=19.373.070); [RCW 19.373 full](https://app.leg.wa.gov/RCW/default.aspx?cite=19.373&full=true)
- **Definition of "sell" [search-verified, secondary].** "Sell" means exchanging consumer health data for monetary or other valuable consideration. Exclusions include transfers to processors and as assets in a merger. Orrick notes the definition mirrors the CCPA's broad definition of sale. — [Orrick](https://www.orrick.com/en/Insights/2023/05/6-Things-to-Know-About-Washingtons-My-Health-My-Data-Law); [Sidley](https://datamatters.sidley.com/?p=4971)
- **Valid-authorization content [reg-text, not re-fetched; UNCERTAIN on details].** 19.373.070(2) requires:
  - the specific data concerned
  - the names and contact information of seller and purchaser
  - the purpose of the sale
  - how the purchaser will use the data
  - a statement that goods or services may not be conditioned on signing
  - the right to revoke
  - a notice about redisclosure
  - **expiration one year** after signature
  - signature and date
  Seller and purchaser must keep the authorization for 6 years. — [RCW 19.373.070](https://app.leg.wa.gov/RCW/default.aspx?cite=19.373.070)
- **Other core provisions [reg-text, not re-fetched].**
  - "Consumer health data" (19.373.010) is personal information linked or reasonably linkable to a consumer that identifies past, present or future physical or mental health status. It includes bodily functions, vital signs, symptoms, biometric and genetic data, precise location related to health services, and health data **derived or extrapolated** from non-health data (inferences).
  - 19.373.030(1): collection requires consent for a specified purpose unless necessary to provide a requested product or service. Sharing requires **separate consent** distinct from the collection consent. "Consent" must be a clear affirmative act and cannot be obtained through general terms of use or dark patterns.
  - 19.373.040 gives rights to confirm, access (including the list of third parties and affiliates), withdraw consent and delete (with propagation to processors and third parties).
  - 19.373.100 exempts, among other things, information used **only for public or peer-reviewed scientific, historical, or statistical research in the public interest** that follows applicable ethics and privacy laws and is approved, monitored and governed by an IRB or similar independent oversight body. It also exempts data covered by Common Rule, ICH or FDA research regulations, and deidentified data. — [RCW 19.373 full](https://app.leg.wa.gov/RCW/default.aspx?cite=19.373&full=true)
- **Litigation [search-verified, sources conflict].** *Maxwell v. Amazon.com* (W.D. Wash. No. 2:25-cv-00261, filed Feb 10, 2025) was the first MHMDA class action. A 2026 guide says it was voluntarily dismissed in 2025, while an older source describes early motion practice. — [Womble Bond Dickinson](https://www.womblebonddickinson.com/us/insights/alerts/first-class-action-filed-under-washingtons-my-health-my-data-act-draws-parallels); [Proskauer](https://www.proskauer.com/blog/my-health-my-dollar-amazons-health-data-troubles-in-washington); [Enzuzo 2026 guide](https://www.enzuzo.com/blog/washington-mhmda)

### Cited Findings: California
- **CCPA definitions and rights [reg-text, not re-fetched].**
  - Cal. Civ. Code 1798.140(ae)(2)(B): sensitive personal information includes "personal information collected and analyzed concerning a consumer's health".
  - 1798.121: right to limit use and disclosure of sensitive personal information to what is necessary for the requested service.
  - 1798.140(m), "deidentified": the information cannot reasonably be used to infer information about, or be linked to, a consumer, *and* the business takes reasonable measures, publicly commits not to re-identify, and contractually binds recipients.
  - 1798.140(ad), "sell": selling, renting, releasing, disclosing… "for monetary or other valuable consideration". Under (ad)(2)(A), it is not a sale when "the consumer uses or directs the business to intentionally disclose personal information".
  - 1798.140(ab) defines "research" with conditions.
  - 1798.146 exempts medical information governed by CMIA, PHI under HIPAA, HIPAA-deidentified information, and information collected in research under the Common Rule, ICH GCP or FDA rules.
  - 1798.148 prohibits re-identifying HIPAA-deidentified data. — [Cal. Civ. Code 1798.140 (leginfo)](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1798.140); [1798.146](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=1798.146)
- **CPPA regulations [search-verified].** The CPPA Board adopted the ADMT, risk-assessment and cybersecurity-audit regulations on July 24, 2025. OAL approved them on Sept 22-23, 2025, and they took effect **Jan 1, 2026**. ADMT duties for significant decisions apply from **Jan 1, 2027**. The risk-assessment compliance deadline is reported as Dec 31, 2027. — [CPPA notice of approval](https://www.cppa.ca.gov/regulations/pdf/ccpa_updates_cyber_risk_admt_noa.pdf); [Greenberg Traurig](https://www.gtlaw.com/en/insights/2025/9/revised-and-new-ccpa-regulations-set-to-take-effect-on-jan-1-2026-summary-of-near-term-action-items); [Thompson Coburn](https://www.thompsoncoburn.com/insights/californias-2026-ccpa-regulations-summary-and-preparation-guide/); [Hunton](https://www.hunton.com/privacy-and-information-security-law/cppa-finalizes-ccpa-regulations-on-automated-decision-making-technology-risk-assessments-and-cybersecurity-audits)
- **ADMT scope [search-verified, secondary].** "Significant decision" is a closed list: financial or lending services, housing, education, employment, and **healthcare services** (diagnosis, prevention, treatment, assessment or care). Advertising is excluded. Duties are a pre-use notice (§7220), an opt-out with exceptions (§7221), access (§7222), and a risk assessment before processing. — [Thompson Coburn ADMT](https://www.thompsoncoburn.com/insights/californias-admt-rules-under-the-ccpa-what-they-mean-for-significant-decisions-and-how-to-get-ahead-of-implementation/); [CASRAI guide](https://casrai.org/guides/california-cppa-admt-regulations-explained)
- **CMIA [reg-text, not re-fetched].**
  - Civ. Code 56.06(b): a business that offers software or hardware "designed to maintain medical information … in order to make the information available to an individual or a provider of health care … for the purposes of allowing the individual to manage his or her information" is deemed a provider of health care subject to CMIA. Later amendments extend this to mental-health digital services (AB 2089, 2022) and reproductive or sexual health digital services (AB 254, 2023).
  - 56.10: no disclosure without authorization, with listed exceptions, including 56.10(c)(7) for bona fide research.
  - 56.11: authorization formalities, including a specific expiration date.
  - 56.36: nominal damages of $1,000 without proof of actual damages, plus actual damages. — [Civ. Code 56.06](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=56.06); [56.10](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CIV&sectionNum=56.10)

### Cited Findings: New York, Colorado, Connecticut
- **NY HIPA [search-verified].** S929/A2141 passed both houses (Jan 22, 2025) and was **vetoed by Gov. Hochul on Dec 19, 2025**. A revised NYHIPA (A.10357/S.9269) was introduced in 2026. — [Epstein Becker Green (update)](https://www.ebglaw.com/health-law-advisor/new-yorks-health-information-privacy-act-poised-to-become-the-latest-in-a-growing-trend-of-state-data-privacy-laws); [MoFo, Mar 2026](https://www.mofo.com/pdf/resources/insights/260316-nyhipa-returns-in-2026-revised-bill); [NYC Bar](https://www.nycbar.org/reports/support-for-new-york-health-information-privacy-act/); [FPF letter](https://fpf.org/resource/fpf-submits-letter-to-new-york-governor-hochul-on-s929-the-new-york-health-information-privacy-act/)
- **Colorado AI Act [search-verified].** SB 24-205 was delayed to June 30, 2026 by SB25B-004 and then **repealed and replaced by SB 26-189**, signed May 14, 2026 and **effective Jan 1, 2027**. The new law is a narrower notice and transparency framework. It removes the duty of care, risk-management programs and impact assessments. AG enforcement awaits rulemaking. — [Ropes & Gray, May 2026](https://www.ropesgray.com/en/insights/alerts/2026/05/colorado-scales-back-ai-law-with-targeted-implications-for-health-care); [Illinois Lawyer Now, Jun 2026](https://www.illinoislawyernow.com/2026/06/the-colorado-ai-act-everyone-was-preparing-for-no-longer-exists-here-is-what-actually-takes-effect-and-why-illinois-businesses-should-still-pay-attention/); [GovTech](https://www.govtech.com/artificial-intelligence/colorado-passes-bill-amending-current-ai-legislation); [GT Law (2025 delay)](https://www.gtlaw.com/en/insights/2025/9/colorado-delays-comprehensive-ai-law-with-further-changes-anticipated)
- **Connecticut and Colorado privacy acts [reg-text, not re-fetched; UNCERTAIN on 2025-26 amendments].** The Connecticut Data Privacy Act (Conn. Gen. Stat. 42-515 et seq., amended by SB 3, 2023) requires consent to process or sell consumer health data, and some of its health-data provisions apply regardless of the general thresholds. The Colorado Privacy Act (C.R.S. 6-1-1301 et seq.) treats health data as "sensitive data" that requires opt-in consent. — [CGA CTDPA](https://www.cga.ct.gov/current/pub/chap_743jj.htm); [Colorado AG CPA](https://coag.gov/resources/colorado-privacy-act/)

### Inferences (mapping to design)
- **Is a paid research contribution a "sale" under MHMDA?** The statute covers any exchange of consumer health data for "monetary or other valuable consideration", and 19.373.070 applies to "any person".
  - If the platform receives fees from institutions tied to data delivery, treating the flow as a sale is a **substantial risk**.
  - If only the participant is compensated and the participant directs the disclosure, the argument against "sale" is stronger. That argument is untested, and MHMDA has no explicit CCPA-style "consumer-directed disclosure" exclusion [UNCERTAIN].
  - Conservative options:
    - (a) rely on the 19.373.100 IRB-governed research exemption, which requires each study to have real IRB oversight
    - (b) also collect separate *sharing* consent per round under 19.373.030
    - (c) for WA residents, also obtain a 19.373.070-style signed authorization (one-year expiry, revocable)
  - Do not rename flows to avoid the definition. Report the definition accurately and design to satisfy it.
- **CCPA:** the per-round, person-directed disclosure fits the 1798.140(ad)(2)(A) exclusion from "sell". Health data is sensitive personal information, so collection beyond what the consumer requested triggers the right to limit. Data collected *by the institution* under Common Rule or FDA research is exempt under 1798.146. Applicability thresholds (annual revenue over about $26.6M as adjusted, or 100k+ consumers, or 50%+ of revenue from selling or sharing) may not reach a hackathon startup [UNCERTAIN: adjusted figure].
- **CMIA:** a California-facing personal agent that keeps hospital records for the individual's own management likely falls under **56.06(b)**. Each disclosure then needs a 56.11-compliant authorization or a 56.10 exception.
- **Withdrawal type (3) under MHMDA:** withdrawing consent plus a deletion request obliges the *regulated entity* (our platform) to delete and notify processors and third parties. Copies already held by an IRB-governed research recipient may be covered by the research exemption. State this split clearly.

### Gaps
- The full text of RCW 19.373.010 (sale exclusions) and 19.373.100 (research exemption) was not re-fetched. The wording above is recalled and should be verified.
- The current 2026 status of NY A.10357/S.9269 (passed, vetoed or pending) was not confirmed.
- Connecticut SB 1295 (2025) consumer-health-data amendments and their effective dates were not verified. Nevada SB 370 and other consumer health data laws were not checked.

---

## Q5. 21st Century Cures Act information blocking (45 CFR Part 171): individual access to own EHI

### Takeaway
The information-blocking rules support the individual's right to get their own records electronically, including through apps. Providers, health IT developers and HIEs/HINs are "actors" who may not unreasonably interfere with access, subject to eight exceptions. This supports the "hospital records obtained by the individual" input, but only for **US** actors. Mongolian and Korean partner hospitals are outside its scope.

핵심 요약: 미국 의료기관·EHR 개발사는 환자 본인의 전자건강정보(EHI) 접근을 부당하게 방해하면 안 된다(정보차단 금지). 이는 개인이 진료기록을 직접 받는 경로를 뒷받침한다. 다만 미국 기관에만 적용된다.

### Cited Findings
- **Definitions and exceptions [reg-text, not re-fetched].**
  - 45 CFR 171.102 defines "electronic health information" as ePHI in a designated record set. The full EHI scope has applied since Oct 6, 2022.
  - 171.103 defines information blocking as a practice likely to interfere with access, exchange or use of EHI, with knowledge standards that differ for providers and for developers or HINs.
  - Exceptions: 171.201-205 (preventing harm, privacy, security, infeasibility, health IT performance) and 171.301-303 (manner, fees, licensing). Later HTI rules added further exceptions [UNCERTAIN on numbering]. — [eCFR 45 CFR Part 171](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-171)
- **Penalties [reg-text, not re-fetched].** Developers and HINs/HIEs face civil money penalties of up to $1M per violation (OIG final rule, 42 CFR Part 1003, effective Sept 1, 2023). Providers face "appropriate disincentives" through CMS programs (final rule, July 1, 2024, 89 FR 54662). — [HHS OIG Information Blocking](https://oig.hhs.gov/reports-and-publications/featured-topics/information-blocking/); [HealthIT.gov Information Blocking](https://www.healthit.gov/topic/information-blocking)

### Inferences
- The agent can show "patient-directed retrieval" from US providers through FHIR patient-access APIs and SMART on FHIR. A provider refusing to release records to a patient's chosen app without an exception risks information blocking. Combined with HIPAA 164.524, this makes the individual-obtained-records path the cleanest legal input route in the US.

### Gaps
- 2025-2026 HHS information-blocking enforcement announcements and the HTI-4/HTI-5 rule changes were not verified in this session.

---

## Q6. LLM agents making automated decisions about what to request and contribute

### Takeaway
No US law specifically prohibits an individual's own agent from automating contribution choices. The binding constraints are indirect:
- the FTC/HBNR "unauthorized disclosure equals breach" rule
- MHMDA and CCPA consent that must be a clear affirmative act by the consumer, which LLM inference cannot supply
- CCPA ADMT rules (Jan 1, 2027) if ADMT is used for a "significant decision" about healthcare
- risk assessments for processing sensitive personal information
- Colorado SB 26-189 transparency (from Jan 1, 2027)

Consent-scope checking should be deterministic code. The LLM may only *propose*, and the person must *confirm* any change in scope.

핵심 요약: 개인 에이전트의 자동 결정 자체를 금지하는 미국 법은 없다. 하지만 동의는 "소비자의 명확한 적극적 행위"여야 하므로, LLM이 동의 범위를 추정·확장하면 무단 공개(HBNR 침해, MHMDA 위반)가 된다. 캘리포니아 ADMT 규정(2027.1.1)은 "의료" 관련 중대한 결정에 적용되는데, 연구 기여 여부 결정은 여기에 해당하지 않을 가능성이 크다. 다만 민감정보 처리에 대한 위험평가 의무는 별도로 검토해야 한다.

### Cited Findings
- **CCPA ADMT [search-verified].** ADMT duties (pre-use notice, opt-out, access, risk assessment) apply to "significant decisions", a closed list that includes healthcare services, from Jan 1, 2027. The regulations as a whole took effect Jan 1, 2026. — [Thompson Coburn ADMT](https://www.thompsoncoburn.com/insights/californias-admt-rules-under-the-ccpa-what-they-mean-for-significant-decisions-and-how-to-get-ahead-of-implementation/); [GT Law](https://www.gtlaw.com/en/insights/2025/9/revised-and-new-ccpa-regulations-set-to-take-effect-on-jan-1-2026-summary-of-near-term-action-items)
- **Colorado [search-verified].** SB 26-189 replaces the 2024 Act with a notice and transparency framework effective Jan 1, 2027. A federal court stayed enforcement of the 2024 Act in April 2026, and DOJ joined a constitutional challenge. — [Ropes & Gray](https://www.ropesgray.com/en/insights/alerts/2026/05/colorado-scales-back-ai-law-with-targeted-implications-for-health-care); [Illinois Lawyer Now](https://www.illinoislawyernow.com/2026/06/the-colorado-ai-act-everyone-was-preparing-for-no-longer-exists-here-is-what-actually-takes-effect-and-why-illinois-businesses-should-still-pay-attention/)
- **Consent and HBNR [reg-text, not re-fetched].** MHMDA "consent" must be a clear affirmative act and is invalid when obtained through general terms or deceptive design. — [RCW 19.373](https://app.leg.wa.gov/RCW/default.aspx?cite=19.373&full=true). The HBNR treats acquisition "without the authorization of the individual" as a breach. — [eCFR 318.2](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-318/section-318.2)

### Inferences (mapping to design)
- **Institution-side agent:** an LLM inferring "missing research fields" and generating requests is not a significant decision *about the consumer* under CCPA ADMT. It does not grant or deny healthcare, credit, housing, education or employment. If outputs were used to select participants for clinical care or treatment, that could change [UNCERTAIN].
- **Personal agent:** an auto-accept policy is lawful only within a scope the person affirmatively consented to in advance, with per-round notice. This matches the prior AP2 point 11. Every field leaving the device should pass a code-level check against that round's consent record (purpose, fields, recipient, expiry). LLM suggestions that would widen scope must go back to the human.
- **Risk assessment:** processing sensitive personal information (health) is a CCPA risk-assessment trigger under the new regulations, so a California-scale deployment should prepare one [UNCERTAIN on exact §7150 trigger list].
- **FTC:** statements about AI capability ("predicts disease", "guarantees anonymity") are subject to §5 deception standards. Use "research missing-data inference".

### Gaps
- The exact §7150 risk-assessment triggers and the §7221 opt-out exceptions were not re-fetched.
- Federal AI preemption developments (for example, the late-2025 executive order on state AI laws, and DOJ litigation beyond Colorado) were not verified. [UNCERTAIN]
