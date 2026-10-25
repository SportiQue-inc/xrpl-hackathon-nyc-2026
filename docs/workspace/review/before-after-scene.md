# 전후 비교 장면: 지금의 SportiQue vs 에이전트가 붙은 SportiQue (10/25 01:40 EDT)

결론: 영상 첫 15초를 **분할 화면 전후 비교**로 바꾼다. 왼쪽은 지금의 UniQLab·UniQdata 흐름이다. 연구자가 단계를 하나씩 밟고 참여자를 기다리며, 참여자는 항목마다 직접 승인한다. 오른쪽은 이번 해커톤의 AgentRail이다. 기관 에이전트가 빈칸을 찾아 바로 요청하고, 개인 에이전트가 정해 둔 규칙 안에서 처리하며, 새 용도만 본인에게 묻는다. 원장이 동의와 지급을 집행한다.

"전" 흐름의 근거: [AgentRail × UniQLab·UniQdata 연결 흐름 점검](https://claude.ai/artifact/QuzHNXPz3at65ym1ZYq6LD) (UniQLab web @ 00de0ca1 기준).

## 1. 비교 내용 (화면에 그대로)

| | 전: 지금의 SportiQue (UniQLab·UniQdata) | 후: AgentRail이 붙은 SportiQue |
|---|---|---|
| 연구자 | 연구 설계 → IRB 준비 → 공개 모집 → 지원자 큐 검토 → 링킹코드 변환 → 동의 요청 → **참여자가 들어올 때까지 대기** → 정산 배치 승인 | 연구 에이전트가 커버리지 표에서 빈칸을 찾아 **바로 요청**. 예산은 2인 서명으로 한 번 승인 |
| 빈 주가 생기면 | **다시 요청하는 흐름이 없다**(현재 UniQLab). 재모집해야 한다 | 그 사람의 그 주만 다시 요청. 전달되면 Escrow가 열리며 지급 |
| 참여자 | 링킹코드 발급 → 연구자에게 전달 → 동의 레인마다(연구 참여, 민감 건강 수집) 승인. 연구마다, 항목마다 직접 승인 | 규칙을 한 번 정함("심박은 자동, 피로·진료는 물어봐, 유전체는 거절"). 에이전트가 규칙 안의 요청을 처리하고 **새 용도·민감 항목만** 본인에게 묻는다 |
| 지급 | 정산 배치 승인 후 지급, 영수증 | 주마다 전달과 동시에 지급(열쇠 공개 Escrow), 80% 즉시 + 20% 보류 |
| 철회 | UniQdata 등록 철회 | 원장에서 라이선스 회수, 미전달 회차 환불 |

## 2. 화면 카운터 (정직한 숫자)

| 카운터 | 전 | 후 | 숫자 성격 |
|---|---|---|---|
| 빈칸을 채우기까지 | **수 주~수 개월**(재모집). 데이터 계약 중앙값 80일 | **수 분**(요청 → 승인 → Escrow 해제) | 전: 외부 연구 인용 + **예시**. 후: **데모 실행에서 실측**한 값(통합 Testnet 실행의 요청~EscrowFinish 시각 차이)을 넣는다 |
| 참여자 직접 승인 수(예: 6주, 3항목) | **18회**(3항목 × 6주, 매번 직접) | **규칙 1개 + 예외 1회**(피로·진료 첫 요청) | **예시**라고 자막에 표기 |
| 참여자 한 명 대체 비용 | 약 $19.5k | 그 주의 기여 1건($20 수준) | 외부 연구 인용(market-deep-dive.md), 예시 |

SportiQue의 실제 소요 시간 기록이 없으므로 "전" 숫자에는 자막에 반드시 `illustrative`를 붙인다. "후"의 시간은 녹화 당일 실행 로그에서 가져온다. 추정치로 채우지 않는다.

## 3. 영상 장면 (0:00–0:15, 구간 1의 첫 줄을 교체)

| 시간 | 화면 | 내레이션(약 38단어) | 자막 |
|---|---|---|---|
| 0:00–0:08 | 왼쪽 절반만: UniQLab 단계 칸이 하나씩 켜지고 "Waiting for participants…" 시계가 돈다. 아래 참여자 폰에 승인 알림이 18번 쌓인다 | "This is how research runs on our platform today. Design, ethics review, recruit, then wait. Every participant approves every item, every week, by hand." | today: weeks of waiting · 18 manual approvals (illustrative) |
| 0:08–0:15 | 오른쪽 절반이 켜진다: 같은 빈칸에 에이전트 요청이 바로 가고, 폰에는 "규칙 1개 + 예외 1회", 시계가 분 단위에서 멈춘다 | "With agents, the study's agent asks for the exact gap, the person's agent answers inside their rules, and the ledger settles. Weeks become minutes." | with agents: minutes (measured) · 1 rule + 1 exception |

그다음 0:15–0:30 구조(3층) 장면으로 그대로 넘어간다. 영상 끝(2:25–2:30) 철회 장면 뒤에 같은 분할 화면을 2초 다시 보여 주며 실측값을 띄운다.

## 4. 라이브 피치용 문장 (30초)

"Today on SportiQue, a researcher designs a study, gets ethics review, recruits, and then waits. When a week goes missing, there is no way to ask for it again. And every participant approves every item by hand. In this hackathon we put agents on both sides. The study's agent finds the gap and asks for it at once. The person's agent answers inside rules the person set once, and only asks them about something new. The ledger makes sure consent and payment hold on both sides. Weeks of waiting become minutes, and eighteen taps become one rule."

한국어: "지금 SportiQue에서는 연구자가 연구를 설계하고, IRB를 받고, 모집한 뒤 기다립니다. 한 주가 빠지면 다시 요청할 방법이 없습니다. 참여자는 모든 항목을 직접 승인합니다. 이번 해커톤에서 양쪽에 에이전트를 붙였습니다. 연구 에이전트는 빈칸을 찾아 바로 요청하고, 개인 에이전트는 본인이 한 번 정한 규칙 안에서 답하며 새로운 것만 본인에게 묻습니다. 원장은 양쪽의 동의와 지급을 보장합니다. 몇 주의 대기가 몇 분이 되고, 열여덟 번의 승인이 규칙 하나가 됩니다."
