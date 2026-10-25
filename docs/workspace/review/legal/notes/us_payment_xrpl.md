# US Payments/Crypto Law and XRPL Technical Facts for Research-Participant Compensation (as of Oct 2026)

> Hackathon evidence summary, not legal advice. Framing: "participant compensation / settlement for research contribution" (not "rewards", not "data sale").
> Method caveat: direct fetches of xrpl.org, fincen.gov, fda.gov were blocked by this session's egress proxy (403 / DNS failure). All findings below come from web-search retrieval of those primary pages (URLs cited) plus law-firm/university secondary sources. Exact quotes marked "per search snippet" should be re-checked against the primary page before being quoted in a deck. Items from model background knowledge that I could not re-verify are labeled [UNVERIFIED].

## Q1. FinCEN: is a non-custodial platform that only constructs transactions (signed by the institution) a money transmitter?

### Takeaway
Under FinCEN's 2019 CVC guidance (FIN-2019-G001), the test is whether a person "accepts and transmits" value or has independent control over it; a software provider that never holds keys and whose user signs every transaction is generally not a money transmitter, but adding hosted-wallet features (holding keys, internal ledger balances, independent control) flips it. A platform that only builds unsigned EscrowCreate/EscrowFinish for the institution to sign fits the non-custodial pattern, but the conclusion is fact-specific.
(요약: 플랫폼이 키를 보관하지 않고 기관이 직접 서명하는 트랜잭션만 구성하면 FinCEN 2019 지침상 송금업자(MSB) 아닐 가능성이 높음. 단, 키 보관·내부 잔액·독립 통제가 생기면 송금업자 판단으로 바뀜.)

### Cited Findings
- FIN-2019-G001, issued May 9, 2019, "Application of FinCEN's Regulations to Certain Business Models Involving Convertible Virtual Currencies" — [FinCEN PDF](https://www.fincen.gov/system/files/2019-05/FinCEN%20Guidance%20CVC%20FINAL%20508.pdf)
- Unhosted wallets: software a user has on their own device that lets them interact directly with the payment system; using one does not make a person a money transmitter if a third party is not necessary for the transaction — [Covington summary](https://www.cov.com/-/media/files/corporate/publications/2019/11/fincen-issues-guidance-to-synthesize-regulatory-framework-for-virtual-currency.pdf); [FinCEN PDF](https://www.fincen.gov/system/files/2019-05/FinCEN%20Guidance%20CVC%20FINAL%20508.pdf)
- Multiple-signature wallet providers (section 4.2.2 of the guidance, per search): providers that create wallets needing more than one private key, typically keeping one key "for additional validation" while the owner holds the other; such a provider "is not a money transmitter because it does not accept and transmit value" — [FinCEN PDF](https://www.fincen.gov/system/files/2019-05/FinCEN%20Guidance%20CVC%20FINAL%20508.pdf); [O'Melveny](https://www.omm.com/insights/alerts-publications/fincen-speaks-crypto-extensive-new-guidance-for-icos-digital-wallets-dapps-trading-platforms-decentralized-exchanges-and-others-in-the-blockchain-and-crypto-space/)
- But a multi-sig provider becomes a money transmitter where value is represented as an entry in the provider's accounts, the owner does not interact with the payment system directly, or the provider has total independent control of the value; and anyone who "combines the services of a [multi-sig] provider and a hosted wallet provider" qualifies as a money transmitter — [Jones Day](https://www.jonesday.com/en/insights/2019/06/fincen-consolidates-guidance); [Covington](https://www.cov.com/-/media/files/corporate/publications/2019/11/fincen-issues-guidance-to-synthesize-regulatory-framework-for-virtual-currency.pdf)
- FinCEN's long-standing position is that the analysis turns on control; a person who only publishes software or offers a non-custodial interface generally is not a money transmitter (secondary commentary) — [Equilex](https://www.equilex.co/insights/us-crypto-license-2026-fincen-msb-and-state-licensing); [UChicago Business Law Review](https://businesslawreview.uchicago.edu/print-archive/regulating-cryptocurrency-non-custodial-service-providers-through-bank-secrecy-act)
- Reported Oct 2026: FinCEN withdrew its long-pending NPRMs (Dec 2020 unhosted-wallet reporting; CVC mixing) around Oct 5–6, 2026; existing AML obligations unchanged. Date not verified against Federal Register — [didit.me](https://didit.me/blog/privacy-coins-no-kyc-swaps-rules-2026/); [OneSafe](https://www.onesafe.io/blog/crypto-treasury-management-fincen-surveillance-rules)
- [UNVERIFIED from background knowledge] Money transmitter definition is 31 CFR 1010.100(ff)(5)(i)(A): "a person that provides money transmission services" = acceptance of currency, funds, or other value that substitutes for currency from one person and transmission to another location or person by any means. The payment-processor exemption is 31 CFR 1010.100(ff)(5)(ii)(B); the 2019 guidance (section 4.4, CVC payment processors) says it applies only if the processor (a) facilitates purchase of goods/services or bill payment, (b) operates through clearance and settlement systems that admit only BSA-regulated financial institutions, (c) under formal agreement, (d) with the seller/creditor — and that CVC payment processors usually do not meet (b). The guidance also covers DApps (section 5.2): a DApp operator that accepts and transmits value is a money transmitter, the code itself is not determinative. Source to check: [FinCEN PDF](https://www.fincen.gov/system/files/2019-05/FinCEN%20Guidance%20CVC%20FINAL%20508.pdf)

### Inferences
- Design that keeps the project outside MSB status: (1) the institution holds its own keys and signs EscrowCreate; (2) the participant's wallet (or the participant agent on the participant's device) holds its own key; (3) the platform never holds keys, never pools funds, and never keeps an internal balance ledger. EscrowFinish can be submitted by any account (see Q5), so the platform submitting a Finish does not by itself mean control of funds — but this is an inference, not a FinCEN ruling.
- Payment-processor exemption is likely not the right route (requires BSA-regulated clearing systems); rely on the "no acceptance/transmission/control" analysis instead.
- If a future production version holds institution keys, custodies participant wallets, or converts fiat to RLUSD for institutions, FinCEN MSB registration and state licensing analysis become necessary.
- 해커톤 설명 문구: "플랫폼은 키를 보관하지 않으며 기관·참여자가 직접 서명" — 이것이 핵심 방어 논리.

### Gaps
- Could not open the FinCEN PDF directly; section numbers 4.2.2 (multi-sig) is supported by search, 4.4 and 5.2 are from memory. Whether the guidance explicitly discusses "escrow" for CVC (beyond multi-sig) not confirmed.
- NY BitLicense (23 NYCRR Part 200; "virtual currency business activity" incl. receiving VC for transmission, storing/holding/custody on behalf of others) — text of 200.2(q) not retrieved; [UNVERIFIED] there is an exemption in 200.3(c) for merchants/consumers using VC solely to purchase goods/services/investment. Check [NYDFS](https://www.dfs.ny.gov/) directly. Other state money transmitter laws vary.

## Q2. GENIUS Act and RLUSD vs XRP

### Takeaway
GENIUS Act (Pub. L. 119-27) was signed July 18, 2025; it governs who may issue "payment stablecoins" and, from July 18, 2028, bars digital asset service providers from offering non-permitted-issuer stablecoins to US persons. It regulates issuers/intermediaries, not an institution simply paying a participant. RLUSD is issued by a NYDFS-chartered trust (SCTC); Ripple received OCC conditional approval for a national trust bank in Dec 2025.
(요약: GENIUS Act는 발행자·중개자 규제. 기관→참여자 지급 자체를 규제하진 않음. RLUSD는 NYDFS 감독 신탁회사 발행, OCC 국가 신탁은행은 조건부 승인 상태.)

### Cited Findings
- Signed July 18, 2025 (Senate 68–30, House 308–122); effective on earlier of 18 months after enactment (~Jan 18, 2027) or 120 days after final regulations — [Gibson Dunn](https://www.gibsondunn.com/the-genius-act-a-new-era-of-stablecoin-regulation/); [congress.gov S.1582 text](https://www.congress.gov/bill/119th-congress/senate-bill/1582/text)
- Section 3(b): three years after enactment (July 18, 2028), a digital asset service provider may not offer or sell a payment stablecoin to a US person unless issued by a permitted payment stablecoin issuer (or qualifying foreign issuer) — [Morgan Lewis](https://www.morganlewis.com/pubs/2025/07/genius-act-passes-in-us-congress-a-breakdown-of-the-landmark-stablecoin-law); [congress.gov](https://www.congress.gov/bill/119th-congress/senate-bill/1582/text)
- Rulemaking: Treasury ANPRM "GENIUS Act Implementation" Sept 19, 2025 — [Federal Register](https://www.federalregister.gov/documents/2025/09/19/2025-18226/genius-act-implementation); proposed rules on issuance/offer/sale published Aug 18, 2026 — [Federal Register](https://www.federalregister.gov/documents/2026/08/18/2026-16796/genius-act-regulations-on-payment-stablecoin-issuance-offer-and-sale). Reported that regulators missed the July 18, 2026 final-rule deadline (secondary) — [governancedocs](https://governancedocs.com/genius-act-effective-date/)
- The Act prohibits issuers paying interest/yield to holders; a March 2, 2026 proposal would presume affiliate/third-party yield pass-throughs violate it (per search summary) — [Brookings](https://www.brookings.edu/articles/next-steps-for-genius-payment-stablecoins/)
- RLUSD issuer: Standard Custody & Trust Company, LLC, NY limited purpose trust company supervised by NYDFS — [Ripple](https://ripple.com/insights/what-actually-makes-a-stablecoin-regulated-a-guide-for-institutions-evaluating-rlusd/)
- OCC conditional (preliminary) approval for Ripple National Trust Bank on Dec 12, 2025; intended role includes RLUSD reserve trustee — [OCC application](https://www.occ.gov/news-issuances/news-releases/2025/nr-occ-2025-125b.pdf); [Ripple press](https://ripple.com/ripple-press/ripple-secures-federal-approval-to-establish-national-trust-bank/); [Axios](https://www.axios.com/2025/12/12/banks-crypto-occ-charters)
- OCC Corporate Decision #1385 (Aug 2026) treats payment stablecoin issuance as permissible for a national trust bank under 12 USC 27(a) — [OCC CD1385](https://www.occ.gov/topics/charters-and-licensing/interpretations-and-decisions/2026/cd1385.pdf)

### Inferences
- RLUSD (USD-denominated, redeemable) suits per-round compensation because participant amounts are stable in USD and tax FMV is simple; XRP introduces price volatility between escrow creation and release, and the participant's income/basis computation is harder.
- For the hackathon: Testnet only; there is no Testnet "real" RLUSD — use a test-issued IOU/MPT labeled as mock USD. Do not claim the demo token is RLUSD.
- Whether RLUSD becomes a GENIUS "permitted" issuer depends on final OCC/NYDFS pathways — mark as pending.

### Gaps
- Whether RLUSD's XRPL issuer account has enabled Allow Trust Line Locking (needed to escrow trust-line tokens, see Q5) — not found. [UNVERIFIED] RLUSD on XRPL is a trust-line (IOU) token with clawback enabled by the issuer.
- Final status of RNTB charter as of Oct 2026 not confirmed.

## Q3. OFAC sanctions screening (brief)

### Takeaway
OFAC's Oct 15, 2021 "Sanctions Compliance Guidance for the Virtual Currency Industry" expects a risk-based program: screening counterparties/addresses against the SDN list, geolocation/IP controls for embargoed jurisdictions, and risk assessment by geography. OFAC obligations apply to all US persons, including institutions paying participants, regardless of MSB status.
(요약: OFAC 의무는 MSB 여부와 무관하게 미국인 전체 적용. 지급 전 SDN 주소·인물 스크리닝, 제재국 IP 차단 권장.)

### Cited Findings
- Guidance issued Oct 15, 2021 with FAQs 559 and 646 updated; addressed to tech companies, exchanges, administrators, miners, wallet providers and users — [Skadden](https://www.skadden.com/insights/publications/2021/11/recent-developments-in-the-regulation-of-virtual-assets/us-treasury-provides-detailed-guidance); [Cooley](https://www.cooley.com/news/insight/2021/2021-10-29-ofac-sanctions-compliance-guidance-virtual-currency-industry)
- Risk assessment should consider customer base, products, counterparties, transactions and geographic locations — [Weil](https://weil.com/-/media/files/pdfs/2021/ofac-issues-sanctions-compliance-guidelines-for-virtual-currency-industry.pdf)
- Dec 2020 and Feb 2021 OFAC settlements with VC companies for failing to block IP addresses from embargoed jurisdictions — [Cooley](https://www.cooley.com/news/insight/2021/2021-10-29-ofac-sanctions-compliance-guidance-virtual-currency-industry)
- Primary brochure: home.treasury.gov virtual_currency_guidance_brochure.pdf (not fetched).

### Inferences
- Demo: show an OFAC-screen step (mock SDN address list check) before EscrowCreate; note that participants in Mongolia/Korea are not embargoed jurisdictions but individual screening still applies.

### Gaps
- Exact brochure wording not retrieved.

## Q4. Tax: participant compensation, 1099-MISC threshold, 1099-DA

### Takeaway
Research-participant payments are generally taxable income; payment in crypto is income at USD fair market value on receipt (Notice 2014-21). The 1099-MISC/NEC reporting threshold rose from $600 to $2,000 for payments made in 2026 (OBBBA, July 2025), inflation-indexed from 2027. Form 1099-DA applies to custodial brokers; non-custodial platforms are excluded (DeFi broker rule repealed via CRA, April 2025).
(요약: 참여 대가는 과세소득. 암호자산 지급은 수령일 USD 공정가치. 2026년분부터 1099-MISC 기준 $2,000. 1099-DA는 수탁형 브로커만 해당.)

### Cited Findings
- OBBBA raised 1099-MISC/1099-NEC threshold from $600 to $2,000 for payments made in 2026, indexed for inflation after 2026; aggregate per payee per year — [Patriot Software](https://www.patriotsoftware.com/blog/accounting/1099-reporting-threshold/); [Avalara](https://www.avalara.com/us/en/blog/one-big-beautiful-bill-act-1099-reporting-threshold.html); [Verrill (prizes/1099-MISC)](https://www.verrill-law.com/blog/the-new-2000-threshold-for-sending-irs-form-1099-misc-to-prize-winners/)
- 1099-K threshold reverted to $20,000 and >200 transactions — [OnPay](https://onpay.com/insights/1099-reporting-threshold-updates/)
- University policies treat research incentives/compensation as taxable income and issue 1099-MISC over the IRS threshold (Northeastern cites $600, pre-2026); UW says subjects expected to earn ≥$1,500/yr are told SSNs will be collected — [Northeastern](https://dhr.research.northeastern.edu/wp-content/uploads/2023/05/Compensating-human-subjects-for-research-activities-03.02.2023.pdf); [UW](https://www.washington.edu/research/hsd/guidance/subject-payment/); [UNCA policy 418](https://www.unca.edu/policies/policy-418/)
- Tax burden of participant payments affects inclusive research (PLOS One 2024) — [PLOS One](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0303112)
- Notice 2014-21: virtual currency is property; recipient includes FMV in USD on date received; payments in VC reported on 1099-MISC at FMV on payment date, same as other property payments (modified by Notice 2023-34) — [Journal of Accountancy](https://www.journalofaccountancy.com/news/20149850.html); [Tax Notes](https://taxnotes.com/lr/resolve/-notice-2014-21/1fx2x)
- Form 1099-DA: custodial brokers file; 2025 first year (gross proceeds); basis from 2026 acquisitions; final regs exclude non-custodial brokers that do not take possession; DeFi broker rule repealed via CRA April 2025 — [IRS newsroom](https://www.irs.gov/newsroom/final-regulations-and-related-irs-guidance-for-reporting-by-brokers-on-sales-and-exchanges-of-digital-assets); [The Tax Adviser, Mar 2026](https://www.thetaxadviser.com/issues/2026/mar/navigating-the-form-1099-da-reporting-maze/)

### Inferences
- The paying institution (not the non-custodial platform) is the likely 1099-MISC payer; amounts in RLUSD/XRP valued at USD FMV at EscrowFinish (when participant receives). Platform can export a per-participant annual USD-FMV report to help the institution.
- Non-US participants (Korea/Mongolia): US institutions paying non-resident aliens face Form 1042-S/withholding questions instead — [UNVERIFIED], flag for tax counsel.
- 1099-DA is not triggered by the non-custodial platform; participant later selling RLUSD/XRP on an exchange may receive 1099-DA from that exchange.

### Gaps
- Box designation (Box 3 "Other income" is common practice) not confirmed from IRS instructions.
- No IRS guidance specific to research-subject payments in crypto found.

## Q5. Research-payment ethics (FDA / OHRP / SACHRP) → per-round escrow mapping

### Takeaway
FDA (Jan 2018 guidance) says payment is a recruitment incentive, not a benefit; payment should accrue as the study progresses and not be contingent on completion, with only a small, non-coercive completion bonus. SACHRP (2019) asks IRBs to assess undue influence contextually. This maps directly to one escrow per contribution round, each independently finishable, with no "all-or-nothing" escrow.
(요약: 대가는 '혜택'이 아니라 모집 유인. 완료 조건부 일괄 지급 금지, 회차별 누적 지급 → 회차별 Escrow 설계와 일치. 완료 보너스는 소액만.)

### Cited Findings
- FDA "Payment and Reimbursement to Research Subjects" (Guidance for IRBs and Clinical Investigators, Jan 2018): payment "is not considered a benefit" in risk–benefit weighing; it is a recruitment incentive — [FDA](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/payment-and-reimbursement-research-subjects)
- FDA: entire payment should not be contingent on completion; a small proportion as a completion incentive is acceptable if not coercive; IRB should determine the bonus is reasonable; payment amount and schedule belong in the consent document — [FDA](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/payment-and-reimbursement-research-subjects); [Clinical Leader commentary](https://www.clinicalleader.com/doc/commentary-fda-guidance-on-payment-and-reimbursement-to-research-subjects-0001)
- "Credit for payment should accrue as the study progresses and not be contingent upon the subject completing the entire study" — wording found in IRB policies implementing FDA guidance (search could not confirm it verbatim on the FDA page) — [Pitt HRPO](https://www.hrpo.pitt.edu/node/645); [UAMS 14.2](https://research.uams.edu/irb/wp-content/uploads/sites/9/2022/10/14.2-10.10.02.pdf); [UMass HRP-403](https://www.umassmed.edu:443/globalassets/ccts/ccts-media/irb/updated-worksheets-2015/hrp-403-worksheet---payments.pdf)
- SACHRP "Attachment A: Addressing Ethical Concerns Regarding Offers of Payment to Research Participants" (finalized 2019): undue influence is contextual and hard to bright-line; prorating recommended — [NIH IRB Tip Sheet June 2023](https://irbo.nih.gov/documents/150/Payment_of_Research_Subjects_June-2023.pdf); [clinician.com](https://www.clinician.com/articles/145104-sachrp-approves-participant-payment-guidelines)
- Some IRBs (Duke) discourage completion bonuses — [Duke 2024](https://irb.duhs.duke.edu/sites/default/files/2024-02/compensation_payments_to_research_participants_1-29-2024.pdf)

### Inferences
- Design mapping: one EscrowCreate per round (amount fixed in IRB-approved schedule). On delivery of round N, the institution's EscrowFinish (or condition fulfillment) releases round N. Withdrawal type (1) "decline this round" → that round's escrow simply cancels after CancelAfter; earlier rounds already paid stay paid. Type (2)/(3) withdrawal must never claw back already-earned compensation (claw back the data-use license MPT, not the money).
- Avoid "reward" wording; describe as "compensation for time and contribution per IRB-approved schedule".
- Escrow amounts and timing must match the consent document; the chain cannot verify that, so the consent document hash is just a reference.

### Gaps
- Could not re-read FDA page verbatim (blocked).

## Q6. XRPL technical facts (Escrow, MPT, Credentials, Permissioned Domains, transparency, finality)

### Takeaway
All needed features are enabled on Mainnet as of Oct 2026 per xrpl.org Known Amendments: Credentials (2025-09-04), MPTokensV1 (2025-10-01), PermissionedDomains (2026-02-04), TokenEscrow (2026-02-12). Escrow for MPT requires the issuer's Can Escrow (+ normally Can Transfer) flag; token escrows require CancelAfter. MPT clawback requires tfMPTCanClawback set at creation.
(요약: 필요 기능 모두 메인넷 활성. 토큰 에스크로는 CancelAfter 필수, MPT는 CanEscrow 플래그 필요. 클로백은 발행 시 플래그 설정.)

### Cited Findings — amendment status
- Known Amendments: Credentials enabled 2025-09-04 (v2.3.0); MPTokensV1 2025-10-01 (v2.3.0); PermissionedDomains 2026-02-04 (v2.4.0, requires Credentials); TokenEscrow 2026-02-12 (v2.5.0); fixTokenEscrowV1 (v3.0.0) listed 2026-01-27 — [xrpl.org Known Amendments](https://xrpl.org/resources/known-amendments)
- News: TokenEscrow (XLS-85) live Feb 12, 2026 with 88% (30/34 validators) — [MEXC news](https://www.mexc.com/news/705502); release context [CoinDesk Jun 2025](https://coindesk.com/tech/2025/06/25/xrp-ledger-brings-token-escrow-other-upgrades-for-dexs-in-new-release). Conflict: one secondary article described TokenEscrow as not yet enabled; and fixTokenEscrowV1 enabled date (Jan 27) preceding TokenEscrow (Feb 12) is odd — treat ordering as UNCERTAIN, verify on Known Amendments page.
- Third-party analysis (Oct 2, 2026) reports DepositAuth, DepositPreauth, Credentials, PermissionedDomains, PermissionedDEX, Clawback, DeepFreeze, TokenEscrow, MPTokensV1 enabled on Testnet and Mainnet — [GitHub IllestAlive/xrpl-input-credit](https://github.com/IllestAlive/xrpl-input-credit)

### Cited Findings — Escrow
- EscrowCreate: FinishAfter / CancelAfter in seconds since Ripple Epoch, immutable once set; Condition = PREIMAGE-SHA-256 crypto-condition; valid combinations: time-based, time-based+expiration, timed conditional, timed conditional+expiration, conditional+expiration — [EscrowCreate](https://xrpl.org/docs/references/protocol/transactions/types/escrowcreate)
- Expiration (CancelAfter) optional for timed XRP escrows but required for token escrows — [EscrowCreate](https://xrpl.org/docs/references/protocol/transactions/types/escrowcreate)
- EscrowFinish: fails before FinishAfter, without matching fulfillment, or after CancelAfter; any account may submit EscrowFinish — [EscrowFinish](https://xrpl.org/docs/references/protocol/transactions/types/escrowfinish)
- EscrowCancel succeeds only after expiration (relative to previous ledger close); returns funds to sender — [EscrowFinish/Escrow docs](https://xrpl.org/docs/references/protocol/ledger-data/ledger-entry-types/escrow)
- TokenEscrow: escrow of trust-line tokens and MPTs; trust-line issuer must enable Allow Trust Line Locking — [XLS-85](https://xls.xrpl.org/xls/XLS-0085-token-escrow.html); [Send Fungible Token Escrows](https://xrpl.org/es-es/docs/tutorials/payments/send-fungible-token-escrows)
- MPT escrow: issuance must have lsfMPTCanEscrow (0x08) else tecNO_PERMISSION; needs Can Transfer too unless destination is issuer; issuer-as-sender is handled (LockedAmount reduced at finish) — [XLS-85](https://xls.xrpl.org/xls/XLS-0085-token-escrow.html); [MPTokenIssuanceCreate](https://xrpl.org/docs/references/protocol/transactions/types/mptokenissuancecreate)
- Smart Escrows (XLS-100) is a separate proposal — [XLS-100](https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html) (status not verified; do not depend on it)

### Cited Findings — MPT (XLS-33)
- Flags: tfMPTCanLock?; tfMPTRequireAuth 0x04 (holders must be individually authorized); tfMPTCanEscrow 0x08; tfMPTCanTransfer 0x20 (transfers to non-issuer accounts; nonzero TransferFee requires it); tfMPTCanClawback 0x40 (issuer may Clawback from individual holders) — [MPTokenIssuanceCreate](https://xrpl.org/docs/references/protocol/transactions/types/mptokenissuancecreate); [XLS-33](https://xls.xrpl.org/xls/XLS-0033-multi-purpose-tokens.html)
- Clawback flag must be set at creation per XLS-33 and clawback guide; migration guide suggests some flags can be enabled later (via MPTokenIssuanceSet / mutable flags) — conflicting; treat as "set at creation" — [Migrating to MPTs](https://xrpl.org/docs/use-cases/tokenization/migrating-from-trust-lines-to-mpts); [MPTokenIssuanceSet](https://xrpl.org/docs/references/protocol/transactions/types/mptokenissuanceset)
- MPT ledger entry: [MPTokenIssuance](https://xrpl.org/docs/references/protocol/ledger-data/ledger-entry-types/mptokenissuance); concept: [MPTs](https://xrpl.org/docs/concepts/tokens/fungible-tokens/multi-purpose-tokens)

### Cited Findings — Credentials (XLS-70) and Permissioned Domains (XLS-80)
- CredentialCreate: issuer provisionally creates for a subject; not valid until the subject submits CredentialAccept; optional Expiration (Ripple Epoch seconds) — [CredentialCreate](https://xrpl.org/docs/references/protocol/transactions/types/credentialcreate); [CredentialAccept](https://xrpl.org/docs/references/protocol/transactions/types/credentialaccept)
- Accepting an expired credential fails with tecEXPIRED and deletes it; reserve borne by subject after acceptance, issuer before — [Credential entry](https://xrpl.org/docs/references/protocol/ledger-data/ledger-entry-types/credential)
- DepositPreauth extended to authorize by credential; CredentialIDs field added to Payment, EscrowFinish, PaymentChannelClaim, AccountDelete; each credential must exist, be accepted, unexpired, and have the sender as subject — [Payment](https://xrpl.org/docs/references/protocol/transactions/types/payment); [Manage Credentials](https://xrpl.org/docs/tutorials/compliance-features/manage-credentials)
- CredentialDelete exists (issuer or subject can delete; anyone after expiry) — [UNVERIFIED detail], see [Transaction Types](https://xrpl.org/docs/references/protocol/transactions/types)
- Permissioned Domains: domain defined by accepted credentials; used for permissioned DEX (DomainID) — [PermissionedDomainSet](https://xrpl.org/es-es/docs/references/protocol/transactions/types/permissioneddomainset); [Permissioned Domains concept](https://xrpl.org/es-es/docs/concepts/tokens/decentralized-exchange/permissioned-domains)

### Cited Findings — transparency and finality
- Results are final only in a validated ledger; check via look-up of transaction results — [Look Up Transaction Results](https://xrpl.org/es-es/docs/concepts/transactions/finality-of-results/look-up-transaction-results)
- [UNVERIFIED wording] All ledger data including Memos is public; do not put PII/PHI in memos.

### Inferences (design mapping)
- Recommended demo pattern: Institution account = escrow sender; participant account = destination with DepositAuth enabled + DepositPreauth by credential (e.g. CredentialType "IRB_APPROVED_STUDY_X" issued by an IRB/ethics-office account to the institution). EscrowFinish carries CredentialIDs, so release requires an accepted, unexpired IRB credential. Note: this binds the *institution's* credential status at release time, not ethics validity itself.
- Condition-based escrow: the participant agent can hold the fulfillment preimage and reveal it on delivery acknowledgment, or the institution holds it and finishes on receipt — the chain cannot verify that data was actually delivered or decrypted correctly; that is off-chain.
- Data-use license MPT: issue with RequireAuth + CanClawback, without CanTransfer (non-transferable license held only by authorized institution). On withdrawal type (3), the participant's agent asks the issuer to Clawback.
- If CancelAfter is required for token escrow (RLUSD/MPT), every per-round escrow has a deadline after which the institution can reclaim — fits "decline this round".

## Q7. What XRPL can and cannot enforce

### Takeaway
XRPL enforces value movement, timing, signatures, and token/credential state; it cannot enforce data deletion, prove IRB approval is genuine, or verify that delivered data matched consent. Clawback of a license MPT revokes the on-chain license record, not copies of data already decrypted.
(요약: 체인은 지급·시간·서명·토큰 상태만 강제. 데이터 삭제, IRB 진위, 동의 범위 준수는 강제 불가. MPT 회수 ≠ 복호화된 데이터 삭제.)

### Cited Findings
- Credentials are issuer-created attestations accepted by the subject; ledger checks existence/acceptance/expiry only — [CredentialCreate](https://xrpl.org/docs/references/protocol/transactions/types/credentialcreate); [Credential entry](https://xrpl.org/docs/references/protocol/ledger-data/ledger-entry-types/credential)
- Clawback moves MPT balance back to issuer — [MPTokenIssuanceCreate](https://xrpl.org/docs/references/protocol/transactions/types/mptokenissuancecreate)
- Escrow terms (FinishAfter/CancelAfter) are immutable once created — [EscrowCreate](https://xrpl.org/docs/references/protocol/transactions/types/escrowcreate)
- OHRP: data collected before withdrawal may be retained/analyzed within approved protocol (prior answer item 7 in 00_design file; not re-verified here).

### Inferences
- Can enforce: payment released only after time/condition and only to credential-preauthorized flows; license token non-transferable; issuer can revoke license token; full audit trail.
- Cannot enforce: deletion of decrypted data; whether the IRB credential issuer is a real IRB (trust in issuer account identity off-chain); whether the institution honors clawback; consent scope; re-identification risk. Withdrawal recorded on-chain does not alter an existing escrow's terms.
- Privacy: payment address ↔ study link may reveal participation (health-study membership is sensitive) — use per-study fresh addresses, no memos with PHI, pseudonymous IDs off-chain.

### Gaps
- Exact MPT Clawback field requirements (Holder field) not retrieved. Whether DynamicMPT (mutable flags) amendment is enabled is unknown.
- RLUSD escrowability on mainnet (issuer lsfAllowTrustLineLocking) unknown; irrelevant for Testnet demo using a self-issued mock token.
