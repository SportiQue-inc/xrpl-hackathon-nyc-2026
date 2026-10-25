# Background: prior regulatory consultations

> Not legal advice. Summary in our words; the design's legal basis is the statutes and public
> guidance listed in [README.md](README.md).

## KISA personal information protection support center (answer received 2026-10-23)

| Topic | What the answer said (summary) | Where it shows in the design |
|---|---|---|
| Sensitive data | Health data is sensitive information; get consent for it separately from other information | Separate consents for sensitive data, third-party provision and international transfer (PIPA Arts. 22, 23) |
| Identity separation | Keep identifying information apart from study participation identifiers; keep the mapping separately with separate access; give researchers only the participant number and consented items | Per-study participant number; the link stays with the person's agent (PIPA Arts. 28-2 to 28-5) |
| Withdrawal | Manage consent status in one place, check it on every access, and invalidate sessions and tokens on withdrawal or expiry. On withdrawal, destroy the personal information held without delay; for data already provided to an institution, the provision contract should require destruction and a confirmation. Aggregate statistics are not subject to destruction; person-level outputs are | Consent checked on every round and again before key release; licence clawback; deletion request and the institution's confirmation recorded; only aggregate statistics remain (PIPA Art. 37) |
| Records | Keep access logs for at least 2 years and records of granting, changing or removing permissions for 3 years; these operating records are not subject to destruction | Retention shown on the request card and in the consent document |
| Provision contract | Prohibit re-identification; require destruction and confirmation on withdrawal | Provision terms in the consent document |
| AI training | Using the data to train models needs separate notice and consent | Participants' data is not used to train models; the LLM never sees record values |

## Not covered by any consultation

No consultation addressed settlement in virtual assets on XRPL. The demo runs on Testnet, the
platform is non-custodial (the institution signs its own payments), and confirming the payment
model with financial regulators is listed as work before a live service.

## Precedents (public sources only)

No public approval covers the whole structure: a person giving their own combined health record
to a research institution round by round and being paid for each round. Each mechanism has a close
public precedent. Sources were checked through reports that quote the originals; no case or
decision numbers are given because none were confirmed.

| Mechanism | Closest public precedent | What the design takes from it |
|---|---|---|
| Passing one's own medical record to a third party | Korea ICT regulatory sandbox, medical MyData for telemedicine (positive interpretation; service launched 2025-05). US HHS OCR FAQ on the access right, health apps and APIs (2019) | The person's consent is the route. In the US, once data reaches an app the person chose, the FTC and state law apply rather than HIPAA |
| Per-round payment and a small completion bonus | FDA guidance on payment to research subjects (2018); SACHRP recommendations (2019) | Every completed round is paid; the bonus and the held share stay small (20%) |
| Fixed payment, not equity or appreciating tokens | LunaDNA (2018) paid participants in shares and had to register a securities offering with the SEC | A fixed amount per round in XRP; no revenue share, no token whose value is meant to rise |
| Withdrawal stops new use | NIH All of Us (no new use; data already used cannot be recalled); HHS FAQ 316 | The withdrawal screen says what stops, what comes back and what cannot be recalled |
| Consent and international transfer notice | FTC orders on Flo (2021), GoodRx, BetterHelp, Premom (2023); PIPC improvement recommendation to DeepSeek (2025-04-23) and penalty on AliExpress (2024-07-24) | Separate, affirmative consent apart from the terms; each round names the institution, country, purpose and items; international transfer is a separate consent, off by default; the institution is told to delete on withdrawal |
| Records on a blockchain | PIPC guideline on personal information and blockchain (2026-06) | Personal data stays off the ledger. Each round's ledger hash uses its own salt kept inside the sealed bundle, and destroying the bundle on withdrawal destroys the salt |
| Research oversight | Apple Heart and Movement Study (in-app consent and withdrawal under IRB oversight) | A study cannot get a budget approved or send a request without an IRB approval number |
