# 예상 질문: "개인 에이전트를 사람마다 계속 띄워 두면 비용이 얼마나 드나?" (10/25)

## 한 줄 답 (영어, 발표용)

"The personal agent isn't an always-on chatbot. It's a small rule-checker that wakes up only when a request arrives, checks what the person signed, and sends. The LLM is called only for something new, and the study pays for all of it, a fraction of a cent per participant per week."

## 근거 (코드 기준, origin/main)

| 항목 | 실제 구조 | 비용 성격 |
|---|---|---|
| 개인 에이전트 상주 | 상주 프로세스가 아니라 **요청이 올 때만 깨어나는 이벤트 방식**. 서명된 규칙과 비교하는 일은 코드(`contract/terms.py` negotiate, 동의 확인)가 한다. 참여자 수만큼 서버를 띄우지 않고, 워커 하나가 여러 사람의 요청을 차례로 처리한다 | 서버리스 호출 수준. 1인당 주 몇 건 |
| LLM 호출 | 연구 쪽 빈칸 추론(`reasoning.infer_spec`), 스키마 맞추기, 라이선스 읽기에서만 쓴다. 기본 모델은 `gpt-4.1-mini`(`agentrail/llm.py`). 참여자 쪽은 **새 항목이 생길 때만** 호출한다 | 호출 1번(입력 약 2천, 출력 약 300토큰)이 약 $0.001 수준(추정, 공시 단가 기준. 확인 필요) |
| 원장 거래 수수료 | Escrow, 지급, 라이선스 tx | 건당 약 $0.0002 |
| 원장 예치금(reserve) | 계정, Escrow, MPT 같은 원장 객체마다 XRP 예치금이 묶인다. 객체를 지우면 돌려받는다 | 비용이 아니라 **묶이는 돈**. 연구 예산에서 낸다 |
| 누가 내나 | 참여자는 내지 않는다. 연구 기관이 수수료(take rate) 안에서 낸다 | 참여자 부담 0 |

## 예상 반문과 답

- **"폰이 꺼져 있으면 어떻게 보내나?"** 데이터 묶음과 서명된 범위는 UniQdata 백엔드의 참여자 금고에 있고, 에이전트 워커가 거기서 보낸다. 새 항목만 폰으로 Touch ID를 묻는다.
- **"에이전트가 서명된 범위를 넘으면?"** 코드가 거절한다. LLM은 범위를 좁힐 수만 있고 넓힐 수 없다(적대적 LLM 테스트 있음). 원장의 라이선스와 Escrow 조건이 마지막 방어선이다.
- **"사람이 10만 명이면?"** 비용은 사람 수가 아니라 요청 수에 비례한다. 요청이 없는 사람은 비용이 0이다.

## 확인 필요 (지금은 추정)

- 실제 1인·1주당 LLM 호출 수와 토큰 수는 통합 실행 로그에서 세어 README에 넣는 것이 좋다. 구현 스레드에 요청할 항목이다.
- 모델 단가는 공시 가격 기준 추정이다.
