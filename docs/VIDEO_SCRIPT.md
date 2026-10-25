# 3분 영상 대본 (문제와 해법 40초 · 데모 2분 · 기술과 확장 20초)

기준 코드: `main` (PR #11 이후). 내레이션은 영어(뉴욕 심사위원 대상), 화면 자막은 짧게. 말하는 속도는 분당 약 150단어로 잡았다. 각 구간의 단어 수는 시간에 맞췄다. 숫자 출처는 [MARKET.md](MARKET.md).
**[10/25 갱신] 402 장면(1:25)은 Mastercard AP4M 바우처 결제로 바꿨다. AP4M 심사가 VoucherRedeemed 이벤트, payout 주소의 RLUSD 잔액 변화, 녹화 아닌 라이브를 요구하기 때문이다. T54 x402는 AP4M이 실패할 때의 예비 장면이다.**
주인공은 A등급 기술 셋이다: **열쇠 공개형 Escrow, MPT 라이선스 회수, 다중서명.** 요청하신 "402 자동 결제" 장면은 개인 에이전트가 병원 내보내기 API의 HTTP 402에 위임 한도 안에서 자동으로 결제하는 장면(x402 + 서명 위임)으로 해석해 넣었다.

## 구간 1. 문제와 해법 (0:00–0:40, 약 100단어)

첫 문장은 "데이터가 있다"가 아니라 "연구가 멈춘다"로 시작한다. 한 줄 해법: **연구가 빠진 데이터 때문에 멈추면, 그 사람의 에이전트가 본인이 정한 한도 안에서 자기 기록으로 그 빈칸을 채우고, 원장이 양쪽 조건을 보장한다.**

| 시간 | 화면 | 내레이션 | 자막 |
|---|---|---|---|
| 0:00–0:15 | 멈춘 히트맵: 피로 설문 3–5주 차가 회색, 검정력 0.65, 달력이 넘어간다 | "A sleep study is stuck. Half its cohort skipped three weeks of fatigue surveys. The answer today is to recruit again: months of agreements, and close to twenty thousand dollars for every dropout replaced." | study stalled · weeks 3–5 missing · months to re-collect · ≈ $19.5k per dropout |
| 0:15–0:28 | 한 문장이 화면 가운데에 뜬다 | "AgentRail fixes that. When a study stalls on missing data, each person's own agent fills the gap from their own records, within the limits they set. The ledger guarantees the terms on both sides." | gap → person's agent → their own records → within their limits → ledger guarantees both sides |
| 0:28–0:40 | 양쪽 보장 두 칸: 연구 쪽 / 참여자 쪽 | "The study pays only when the exact weeks arrive. The person shares only what they agreed to, is paid directly, and can withdraw at any time. Now watch one gap get filled." | study: pays on delivery · person: consents, is paid, can withdraw |

시장 숫자(Flatiron $1,000, 23andMe ≈$20, 네 가지 변화)는 영상에서 빼고 README의 잠재력 절과 Q&A로 옮긴다. 영상 첫 40초는 문제와 해법만 말한다.

## 구간 2. 데모 (0:40–2:40, 약 300단어)

| 시간 | 화면 | 내레이션 | 원장 증거 (자막·링크) | 기술 |
|---|---|---|---|---|
| 0:40–0:55 | 연구자 콘솔: 목표 입력 → LLM 빈칸 제안 옆에 코드 판정 | "Our sleep study's research agent reads the coverage table. The LLM proposes what's missing; code recomputes every gap. P-017 is missing fatigue weeks three to five and two clinic visits." | LLM 제안 / 코드 판정 (근거 없는 항목 삭제 표시) | GPT, 안전 레이어 |
| 0:55–1:10 | 콘솔: 한 명 서명 → 거절, 두 명 서명 → 승인 | "The agent can't give itself a budget. The study treasury is multi-signed. One signer: the ledger refuses. Investigator and compliance co-sign, and only then does the owner sign the agent's spending mandate, as a Mastercard Verifiable Intent credential." | `tefBAD_QUORUM`(서버 응답 원문) → 공동서명 40 XRP tx → 소유자의 Mastercard Verifiable Intent 위임 서명 | **다중서명**, Mastercard VI |
| 1:10–1:25 | 폰: P-017의 연구 요청 카드 | "P-017's own agent gets the request. The lab's ethics and verified-organization credentials are read from XRPL. Heart rate is inside consent, so it goes automatically. Fatigue and clinic records need P-017." | Credential 배지, DUO 칩, 자동/승인 필요 | Credential |
| 1:25–1:40 | 폰: 미리보기 → 승인 → **402 자동 결제(AP4M, 라이브 터미널 분할 화면)** | "P-017 approves. The clinic's export API answers 402, payment required. The agent checks price, payee and purpose against its mandate, decides to pay, and signs a Mastercard AP4M voucher. No human click. The voucher is redeemed on-chain and RLUSD settles to the clinic." | HTTP 402 → 결정 로그(within cap) → `VoucherRedeemed` tx (XRPL EVM 1449000) → payout RLUSD 잔액 전/후 → 내보내기 200 | **Mastercard AP4M**, RLUSD, VI |
| 1:40–2:00 | 콘솔: Escrow 생성 → 폰: 열쇠 공개 → 콘솔: 묶음 열림, 히트맵 채워짐 | "Each week is sealed. The lab escrows the payment, locked to the hash of a key. To get paid, P-017's agent must publish that key on the ledger, and the lab opens the data with the same key. Payment and delivery are one transaction." | EscrowCreate → EscrowFinish의 `Fulfillment` 필드 → 그 키로 복호화 → 검정력 0.65 → 0.75 | **열쇠 공개 Escrow** |
| 2:00–2:10 | 콘솔: 라이선스 MPT | "The lab also receives a licence token from P-017's agent. It can't be transferred, and the lab's every later access re-reads it on the ledger." | MPTokenIssuanceCreate, 양도 시 `tecNO_AUTH` | **MPT** |
| 2:10–2:25 | 경계 탭: 새 용도 → 보류, 준식별자 조합 → 거절, 미검증 기관 직접 결제 → 거절 | "Boundaries are enforced, not promised. A new purpose waits for P-017. Birth date plus postal code plus rare diagnosis is refused. An unverified lab can't even send P-017 money." | `tecNO_PERMISSION` tx | DepositPreauth |
| 2:25–2:40 | 폰: 철회 → 콘솔: 행이 회색 | "P-017 withdraws. The licence is clawed back, so the lab's next access is refused. The unreleased week's key is never published, and its escrow refunds the lab. Money already paid stays with P-017." | Clawback tx → 연구실 재열람 `410 Gone`(사본 파기 확인) → EscrowCancel tx | **MPT 회수, Escrow 환불** |

## 구간 3. 기술과 확장 (2:40–3:00, 약 50단어)

| 시간 | 화면 | 내레이션 | 자막 |
|---|---|---|---|
| 2:40–2:50 | XRPL 기능 다섯 개 타일 + 테스트 수 | "Escrow, MPT clawback, multi-signing and credentials on XRPL, and Mastercard Agent Pay settling RLUSD on the XRPL EVM sidechain, all live on Testnet with tests. Settling a twenty-dollar week costs a fraction of a cent." | Escrow · MPT · Multisig · Credentials · Mastercard AP4M · RLUSD · tests · $0.0002 vs $0.88 |
| 2:50–3:00 | 로봇 데이터 장면(장면 A) → 로고 | "We solved the hardest data first. With a lighter consent layer, the same engine runs AI training and robot data. The LLM proposes, code verifies, the ledger enforces." | AgentRail · LLM proposes · code verifies · ledger enforces |

## 녹화 메모

- 녹화 전에 `LEDGER=testnet python scripts/run_health_demo.py`를 한 번 돌려 LLM 응답을 기록해 둔다. 녹화 때는 같은 실행 결과의 tx 링크를 쓴다.
- XRPL 본체의 병원 내보내기는 실제 HTTP 402 엔드포인트다(`GET /clinic/export`, `agentrail/clinic.py`). 예비 장면으로 쓸 때는 브라우저 네트워크 탭에 402 → 200과 `PAYMENT-REQUIRED`·`PAYMENT-RESPONSE` 헤더를 띄운다.
- 화면과 내레이션 금지 표현: data sale, reward token, "cannot be re-identified", diagnosis, HIPAA compliant, 제품명.
- 시간 확인: 구간 1 약 100단어, 구간 2 약 300단어, 구간 3 약 50단어. 녹음 후 3:00을 넘으면 1:10–1:25의 배지 설명을 자막으로 넘기고 내레이션을 줄인다.

## 부록. Mastercard AP4M 라이브 장면 (바우처 심사용, 녹화 영상 대체 불가)

AP4M 심사는 "녹화 출력 없이 3분 안에 라이브"를 요구한다. 그래서 본 영상과 별도로, 피치 때 터미널 두 개로 라이브로 돌린다. 코드는 `ap4m/`(XRPL EVM Testnet chain 1449000). 기존 T54 장면(1:25–1:40, XRPL 본체)은 그대로 둔다.

| 시간 | 화면 | 내레이션 | 증거 |
|---|---|---|---|
| 0:00–0:20 | 왼쪽 터미널: `merchant.mjs` 시작(합성 병원 내보내기 API) | "This is a clinic's record export API. It charges per call, and it answers 402 until it is paid." | `GET /export/S-xxxx/3 → 402` |
| 0:20–1:10 | 오른쪽 터미널: `agent.mjs` | "P-017's agent has a delegated budget and a per-call cap. It reads the 402, checks price, payee and purpose against its mandate, and decides to pay. No human click. It signs an AP4M voucher, the merchant redeems it on-chain, and the package unlocks." | 결정 로그 3줄(within cap), VoucherRedeemed tx |
| 1:10–1:30 | 네 번째 요청 | "This one is priced above the cap. The agent refuses on its own. Nothing is paid." | `refused: over per-call cap` |
| 1:30–2:20 | XRPL EVM 익스플로러 + payout 잔액 | "Here is the VoucherRedeemed event at the PaymentLedger contract, and the settlement reaching the clinic's payout address." | VoucherRedeemed 이벤트, payout 잔액 전/후 |
| 2:20–3:00 | 요약 | "Payment is load-bearing: no payment, no package. The agent decides inside limits its owner set, and every package is synthetic, pseudonymous and only what was consented." | run-<timestamp>.json |

메모: 토큰 이름은 SDK와 체인이 부르는 그대로 쓴다. 이 장면은 XRPL EVM Testnet이며, 본 제품의 XRPL 본체 흐름과 다르다고 한 번 말한다.
