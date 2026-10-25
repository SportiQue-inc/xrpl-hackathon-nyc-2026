**한국어판**

```markdown
## 법적 근거 (요약)
> 법률 자문이 아닙니다. 데모는 합성 데이터와 XRPL Testnet만 사용합니다. 실서비스 전 당국·전문가 확인이 필요합니다.
- **동의**: 민감정보(건강), 제3자 제공, 국외 이전 동의를 각각 따로 받고, 회차·용도별로 범위를 정합니다(개인정보 보호법 제15·17·22·23·28조의8, 생명윤리법 제16조, 미국 45 CFR 46.116).
- **범위 검사**: 받는 자·목적·항목·기간 비교는 LLM이 아닌 결정적 코드가 하며, 접근할 때마다 현재 동의 상태를 확인합니다. 범위가 바뀌면 다시 동의를 받습니다.
- **가명처리**: 연구자에게는 참여번호와 동의한 항목만 제공됩니다. 사람과 참여번호를 잇는 정보는 연구자가 접근할 수 없는 곳에 따로 보관됩니다. 이 자료는 익명정보가 아니라 가명정보이며, 제공 계약에 재식별 금지 조항을 둡니다.
- **철회 3종**: 이번 회차 거절 / 향후 제공 중단 / 데이터 이용 동의 철회(개인정보 보호법 제37조). 철회하면 세션과 키 발급을 즉시 막고, 연구기관이 가진 개인 단위 자료의 파기와 결과 회신을 요청합니다. 이미 만든 익명 집계 통계는 남습니다.
- **국외 이전**: 해외에서 조회만 해도 이전에 해당하므로 나라·받는 자·목적·항목·기간을 알리고 따로 동의를 받습니다. 개인 기록은 그 사람의 나라 안에 보관합니다.
- **IRB**: 승인과 면제는 IRB가 판단합니다(생명윤리법 제15조, 45 CFR 46.112). XRPL Credential은 발급자의 진술을 표시할 뿐입니다.
- **참여 대가**: 회차별 Escrow로 연구기관이 직접 지급하고, 이미 지급된 대가는 철회해도 회수하지 않습니다. 플랫폼은 키와 자금을 보관하지 않습니다.
- **기록**: 접근·권한 변경 기록은 보존하고, 원장에는 개인정보·연구명·질환명을 기록하지 않습니다.
```

**English version**

```markdown
## Legal basis (summary)
> Not legal advice. The demo uses synthetic data and XRPL Testnet only. A live service needs review by regulators and counsel.
- **Consent**: separate consent for health (sensitive) data, third-party provision and international transfer, scoped per round and purpose (Korea PIPA Arts. 15, 17, 22, 23, 28-8; Bioethics Act Art. 16; US 45 CFR 46.116).
- **Scope check**: deterministic code, not the LLM, compares each request with the consented recipient, purpose, fields and period, and checks current consent on every access. Any change needs new consent.
- **Pseudonymization**: researchers receive only a participant number and the consented fields. The link between a person and their number is stored separately, where researchers cannot reach it. This is pseudonymized data, not anonymous data, and the data agreement prohibits re-identification.
- **Three withdrawal options**: decline this round / stop future contributions / withdraw data-use consent (PIPA Art. 37). Withdrawal immediately blocks sessions and key release, and asks the institution to destroy individual-level data and confirm. Aggregate statistics already produced remain.
- **International transfer**: access from abroad counts as transfer, so we disclose countries, recipients, purpose, fields and retention, and ask for separate consent. Each person's records stay in their own country.
- **IRB**: approval and exemption are decided by the IRB (Bioethics Act Art. 15; 45 CFR 46.112). An XRPL Credential only shows the issuer's attestation.
- **Participation compensation**: paid per round by the institution through Escrow and never taken back after withdrawal. The platform holds no keys or funds.
- **Records**: access and permission-change logs are retained; no personal data, study names or conditions go on the ledger.
```
