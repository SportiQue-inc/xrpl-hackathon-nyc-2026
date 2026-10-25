# PT용 "법적 요구사항을 설계에 반영" 슬라이드 문구

> 쓰는 원칙: "법을 준수한다", "HIPAA compliant", "합법 확인"처럼 단정하지 않는다(법률 검토·당국 답변이 끝나지 않았고 데모는 Testnet이다). 대신 "법이 요구하는 것을 기능으로 만들었다"고 말한다.

## 슬라이드 제목 후보
- **한국어:** 법이 요구하는 것을 코드로 만들었습니다
- **English:** We turned legal requirements into product rules

## 본문 (요구사항 → 우리가 만든 장치)
| 법이 요구하는 것 | 우리가 만든 장치 | 근거 |
|---|---|---|
| 건강정보는 따로 동의, 동의 사항은 구분해서 | 민감정보·제3자 제공·국외 이전 동의를 각각 따로 받고 서명과 연결 | 개인정보 보호법 제22·23조, 45 CFR 46.116 |
| 동의 범위 밖으로 제공하면 안 됨 | 받는 자·목적·항목·기간을 코드가 매번 검사. LLM은 범위를 넓히지 못함 | 개인정보 보호법 제17조, FTC Health Breach Notification Rule |
| 연구자는 개인을 알아보면 안 됨 | 연구별 참여번호와 최소 항목만 전달. 사람과 번호를 잇는 정보는 따로 보관하고, 위험한 항목 조합은 차단 | 개인정보 보호법 제28조의2~5, HIPAA 164.514 참고 |
| 언제든 불이익 없이 철회 | 철회 3종. 철회하면 즉시 키 발급을 차단하고, 기관 사본은 파기를 요청해 회신을 기록. 철회 이력은 점수와 대가에 영향 없음 | 개인정보 보호법 제37조, 생명윤리법 제16조, 45 CFR 46.116(b)(8) |
| 해외에서 조회해도 국외 이전 | 나라·받는 자·목적·기간을 알리고 따로 동의. 개인 기록은 본인 나라에 보관 | 개인정보 보호법 제28조의8, 몽골 개인정보보호법 |
| IRB 승인은 IRB가 판단 | 에이전트는 승인을 만들지 않음. 발급 기관의 Credential이 있어야 대가가 풀림 | 생명윤리법 제15조, 45 CFR 46.112 |
| 대가는 진행에 따라, 부당한 유인 없이 | 회차별 Escrow. 80%는 즉시, 20%는 검수 뒤 지급. 철회해도 받은 돈은 회수하지 않음 | FDA 2018 지급 지침 |
| 플랫폼이 남의 돈을 맡으면 인허가 | 기관이 직접 서명해 지급하고, 플랫폼은 키와 자금을 갖지 않음 | 특금법, FinCEN FIN-2019-G001 |
| 공개 원장에 개인정보 금지 | 원장에는 지급·라이선스 상태와 해시만 기록. 건강정보·연구명은 기록하지 않음 | PIPC 블록체인 가이드라인(2026) |

## 발표 멘트 (30초)
**한국어:** "개인 건강데이터를 연구에 쓰려면 동의, 철회, 국외 이전, 대가 지급마다 법이 요구하는 조건이 있습니다. 저희는 이 조건을 안내문이 아니라 코드로 만들었습니다. 에이전트는 요청을 이해하고 설명하지만, 무엇을 줄 수 있는지는 코드가 판정합니다. 철회는 바로 반영되고, 대가는 회차마다 정산되며, 플랫폼은 키도 돈도 맡지 않습니다. 실서비스 전에는 각국 전문가 검토를 거칠 예정이고, 오늘 데모는 합성 데이터와 Testnet입니다."

**English:** "Using personal health data for research comes with legal conditions on consent, withdrawal, cross-border transfer and payment. We built those conditions into code, not just into a notice. The agent understands and explains requests, but code decides what can be shared. Withdrawal takes effect immediately, compensation settles each round, and the platform never holds keys or funds. Before launch we will get country-by-country legal review; today's demo runs on synthetic data and Testnet."

## 쓰지 말 것
"법을 완벽히 준수", "HIPAA compliant", "합법 인증", "재식별 불가", "익명", "데이터 판매", "리워드", "질병 예측", 기관 상담 답변 인용(K-DATA 답변은 제3자 공유 금지)
