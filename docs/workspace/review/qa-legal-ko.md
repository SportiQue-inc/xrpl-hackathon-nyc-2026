# 심사위원 법률 Q&A: 한국어 해설 + 짧은 영어 답변

> 사용법
> - 영어 답은 1~2문장이라 그대로 읽으면 됩니다.
> - 질문을 못 알아들으면 이렇게 말합니다: **"Good question. Our design rule is simple: the agent explains, code decides, and the user can stop anytime."**
> - 더 깊이 들어오면 이렇게 말합니다: **"Our full legal memo is in the appendix. Happy to share it."**
> - 쓰지 말 말: compliant, exempt, anonymous, data sale, reward

---

### Q1. HIPAA 지키나요? (Is this HIPAA compliant?)
**말할 것:** "Users share their own records with a signed authorization. We don't claim compliance; we built the authorization rules into code."
**해설:** 본인이 서명한 승인서(HIPAA 164.508)로 자기 기록을 넘기는 구조입니다. "준수한다"고 말하지 않습니다.

### Q2. 암호화하면 규제에서 빠지나요? (Does encryption exempt you?)
**말할 것:** "No. Encryption means we can't read the data. The research institution with the key still follows every rule."
**해설:** 암호화는 면제가 아니라 안전장치입니다. 플랫폼은 데이터를 못 보고, 키를 가진 기관이 동의·IRB·파기 의무를 집니다.

### Q3. 철회하면 데이터가 정말 지워지나요? (Can you really delete data?)
**말할 것:** "Access stops at once and the institution must delete and confirm. Past analysis stays, and the ledger never holds health data."
**해설:** 즉시 키 발급을 막고, 기관에 파기를 요청해 회신을 받습니다. 이미 끝난 분석은 되돌릴 수 없습니다. 원장에는 해시만 있습니다.

### Q4. AI가 대신 동의하나요? (Does the AI consent for the user?)
**말할 것:** "No. The user signs. The agent only executes that consent, and code blocks anything outside it."
**해설:** 에이전트는 서명된 동의를 실행만 합니다. 범위 밖 요청은 코드가 막고, 사람이 확인합니다.

### Q5. 유전체 데이터는요? (What about genomic data?)
**말할 것:** "Genome consent is per study, signed by the user. Raw genomes never leave through the agent."
**해설:** 유전체는 연구마다 본인이 직접 동의합니다. 원본은 넘기지 않고, 미리 동의한 계산 결과만 나갑니다.

### Q6. 크립토로 돈 주면 송금업 아닌가요? (Isn't this money transmission?)
**말할 것:** "The institution pays from its own wallet. We never hold keys or funds."
**해설:** 기관이 직접 서명해서 지급하고, 플랫폼은 거래 초안만 만듭니다. "면제"라는 말은 하지 않습니다.

### Q7. 돈으로 참여를 유도하는 것 아닌가요? (Is payment undue influence?)
**말할 것:** "Pay builds up each round, like FDA guidance says. Users keep what they earned if they quit."
**해설:** 회차마다 지급하고 완료를 조건으로 하지 않습니다. 철회해도 받은 돈은 그대로입니다.

### Q8. 몽골 데이터 현지화는요? (Mongolia data localization?)
**말할 것:** "Mongolian law allows transfer with consent. Server location rules will get local legal review before launch. Today's demo is synthetic data only."
**해설:** 동의 기반 국외이전은 가능합니다(PDPL 14.1). 서버 요건(A/90)과의 관계는 출시 전에 현지 변호사 의견으로 확정합니다.

### Q9. 누가 연구를 승인하나요? (Who approves the research?)
**말할 것:** "The ethics board, not us. Payment unlocks only with their credential on the ledger."
**해설:** IRB 승인 Credential이 원장에 있어야 정산이 풀립니다. 에이전트는 승인을 만들 수 없습니다.

### Q10. 비슷한 사례가 있나요? (Any precedent?)
**말할 것:** "Yes. Korea's Busan blockchain zone paid people for sharing medical data, and FDA guidance supports paying per round."
**해설:** 부산 특구 의료 마이데이터 보상 실증, FDA 2018 지침을 듭니다. 우리 서비스를 승인한 사례는 아닙니다.
