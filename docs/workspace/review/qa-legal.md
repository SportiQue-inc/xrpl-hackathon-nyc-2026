# Judge Q&A: legal and regulatory (30-second answers)

> These are answers for the pitch Q&A. They are design evidence, not legal advice. The demo uses only synthetic data and XRPL Testnet.
> Never say: "compliant", "exempt", "anonymous", "can't be re-identified", "data sale", "reward", "disease prediction".

## 1. Is this HIPAA compliant?
We don't claim that. HIPAA covers providers, health plans and the businesses that work for them. Participants share their own records with a study under a signed authorization (45 CFR 164.508), so the authorization is the gate. Each authorization in our app has a scope, an expiry date and a way to revoke it. When data comes from a hospital, a HIPAA authorization or an IRB waiver still applies, and we'd sign a BAA where one is needed.

## 2. Are you a HIPAA business associate?
It depends on who we work for. When we serve a covered entity, we expect to be one even though we only store ciphertext. HHS's cloud guidance treats a provider that holds encrypted PHI without the key as a business associate, so we plan to sign a BAA. When participants send data directly to a research institution, we act as the participant's tool. In that case the FTC Health Breach Notification Rule is the closer fit.

## 3. Doesn't end-to-end encryption take you out of privacy law?
No. Encryption is a safeguard, not an exemption. It means the platform can't read the data, and a leak of encrypted data isn't a "breach of unsecured" health data under the FTC rule (16 CFR 318.2). But the institution holding the key is fully bound by consent, IRB approval and deletion duties. In Korea, a transfer still counts as cross-border even when the data is encrypted, so we disclose it and get separate consent.

## 4. What happens when someone withdraws? Can you really delete the data?
Withdrawal takes effect at once:
- The agent stops issuing keys.
- The data license (MPT) is clawed back.
- Future rounds stop.
- The institution must delete the participant's individual-level data and send a confirmation, which we log.

What withdrawal can't do:
- Undo analysis that was already done lawfully (HIPAA 164.508(b)(5), Mongolia PDPL 8.7).
- Erase the ledger. The ledger holds only hashes and payment status, never health data.
- Physically reach into the institution's servers. Deletion is enforced by contract and audit, not cryptography.

Participants keep what they were already paid.

## 5. Why separate consents? Isn't one checkbox enough?
Korea's PIPA requires it. Sensitive information, third-party sharing and overseas transfer each need their own consent (Art. 22(1), 23(1)1, 28-8). The US Common Rule and Washington's My Health My Data Act also separate collection consent from sharing consent. So each one is its own signed receipt, and code checks the receipts before anything is shared.

## 6. Can the AI agent consent on the user's behalf?
No. The agent carries out a consent the person already signed. Code checks every request against the signed recipient, purpose, fields and period. The LLM explains requests but can't widen the scope. Anything outside the scope, and any penalty, goes to a human.

## 7. What about genomic data?
We handle genomes more strictly than any other data:
- Consent is per study, signed with the participant's own passkey, and is never delegated to the agent.
- Raw genomes are never shared through the agent.
- Only computed or aggregate results the participant approved in advance can leave.

This follows Korea's Bioethics Act consent rules (Art. 15, 16) and the Common Rule's disclosure on whole-genome sequencing (45 CFR 46.116(c)(9)). The demo includes no Mongolian genomes.

## 8. Mongolia requires data localization. How do you deal with that?
We know about it and haven't solved it yet. PDPL Art. 14.1 allows cross-border transfer with consent. Separately, Ministerial Order A/90 requires servers that process sensitive data to sit in Mongolia and be accessed only from there. The UN privacy rapporteur raised the same tension in 2026. Before launch we'll get written opinions from Mongolian counsel on consent, foreign storage, remote access and outbound results. The demo uses synthetic data only, and no researcher logs in remotely to Mongolian servers.

## 9. Isn't paying people in crypto money transmission?
We designed around the control-of-funds test used by FinCEN (FIN-2019-G001) and Korea's FIU (2026 manual):
- The institution signs every payment from its own wallet.
- The platform only drafts transactions and never holds keys or funds.
- Escrow terms are locked on-ledger when created.

We don't claim an exemption.

## 10. Doesn't payment create undue influence?
Payment builds up round by round and never depends on finishing the study. That is what the FDA's 2018 guidance on paying research subjects recommends. 20% is held back for a short quality check and paid by default. Participants keep what they earned if they withdraw, and withdrawal never affects their score or future offers.

## 11. Who approves the research?
The IRB does, not us. Payment unlocks only when the ethics board's Credential is on the ledger. The agent can check for the Credential but can't create one.

## 12. Any precedent?
- Busan's blockchain regulatory free zone paid people with vouchers for sharing medical data (2021–).
- Korea's national bioethics consent template pays per visit and destroys data on withdrawal.
- FDA guidance pays as the study progresses.

These show the same direction. None of them approves our service.
