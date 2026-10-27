# sportique 에이전트 구현 점검 — 상태 보고 (2026-10-27)

점검자: 이 세션(Claude, `SportiQue/agent` 폴더 한정). 브리프: 대표가 전달한 Codex 인계 문서(2026-10-27).
질문: "지금 만든 에이전트가 충분히 작동하는 에이전트인가." 답은 §2의 판정표와 §6의 결함 목록이다.

## 0. 기준과 방법

- **기준 커밋.** 브랜치 `claude/project-thread-g0xdy9`는 인계 시점의 `65be74c`에서 시작했으나, `origin/main` `2063d5b`가 140커밋 앞서 있고
  그 안에 AP4M 레일, 연구 계약의 AP4M 결제, 볼트 마켓, 실행 기록(#98)이 들어 있어 **`2063d5b`로 fast-forward한 뒤 점검했다**
  (65be74c는 main의 조상이므로 이력 손실 없음). 인계 문서의 미커밋 변경 2건은 main에 이미 같은 내용으로 들어 있음을 바이트 단위로 확인했다
  (`ap4m/run-live.sh` 1줄, `ap4m/receipts/run-2026-10-25T14-59-45-563Z.json`). `ap4m/package-lock.json`은 untracked로 그대로 둔다.
- **환경.** Python 3.11 venv(`.venv/`, gitignored), Node 23.11, `npm install`(ethers 6.17.0 + vendored SDK). `.env` 없음 → LLM off, XRPL 키 없음, AP4M 키 없음.
  외부 호출을 하지 않았다: 체인 재조회, AP4M 서비스, UniQdata 서버, Railway 상태 모두 미조회. GitHub는 PR #1593 상태 조회 1회.
- **방법.** (1) 진입점에서 호출 관계를 코드로 추적, (2) 기존 테스트 실행, (3) 고정 fixture를 바꾼 행동 프로브
  (`/private/tmp/.../scratchpad/probes/` — 세션 임시, 결과는 이 문서에 전사), (4) 합성 목표 1개의 전 과정 데모(`demo/run_demo.py`, 결과 `demo/demo_run.json`·`demo/demo_log.md`),
  (5) 브라우저(앱 내장 브라우저)로 실제 페이지 경로 확인.

## 1. 실제 진입점과 호출 관계 (판정 A)

| 사용자가 여는 것 | 배포 단위 | 코드 | 호출되는 에이전트 구현 |
|---|---|---|---|
| `/try`, `/console`, `/participant`, `/apps/decide`, `/apps/contracts/*`, `/institutions` | `agentrail.web:app` (Railway `agentrail-try`, `railway.engine.json`, `docker/engine.Dockerfile`) | `agentrail/web.py` | ① 연구 데모 레인 `/api/study/*`(`study.py`, `scenario.py`: fixture 참여자 50명, `agents.PersonalAgent`·`InstitutionAgent`) ② 연구 계약 레인 `/api/contracts/*`(`research_contracts.Lane`: 멤버마다 `PersonalAgent`, 기관 측은 `run_round`) ③ 시장 시뮬레이션 `/api/market/run`(`market/acts.py` → `market/exchange.Exchange`) ④ 결정 설명기 `/api/agent/explain`(`catalog/explain.py`, 상태 없는 합성 owner) ⑤ AP4M 영수증 뷰 `/api/public/ap4m`(`ap4m_receipts.py`, `ap4m/receipts/*.json` 읽기) |
| Data Vault Market | `prototypes/data-vault-market/server` (Railway, `railway.json`) | `vaultmarket/app.py`, `market.py`, `agents.py`, `llm.py`, `rail.py` | 구매자/판매자 에이전트: LLM이 문장·verdict·가격을 제안, 코드가 경계 집행. 한 게시당 판매자 1명과 1:1 협상 |
| AP4M 레일 | `ap4m/rail-server.mjs` (Railway, `ap4m/railway.json`) | `rail-server.mjs` | 결정 없음. `ref`별 멱등 결제, 건당 상한·풀 예산 |
| AP4M 단독 실행기 | 로컬 `ap4m/run-live.sh` | `ap4m/agent.mjs`, `merchant.mjs`, `lib/policy.mjs` | 결정형 정책, 과제·상대·가격 고정 |

연결: 연구 계약 레인 → AP4M 레일(HTTP, `agentrail/ap4m_rail.py`, `AGENTRAIL_CONTRACTS_PAY=ap4m`일 때); 볼트 마켓 → AP4M 레일(`config.AP4M`);
연구 계약 레인 → UniQdata(`PUT /research/agentrail/settlements`, `UNIQDATA_ROSTER`가 있을 때만); 기관 대시보드(`institution_view.py`)는 레인 DB·`ap4m/receipts/`·볼트 마켓 URL을 읽어 모은다.
연구 데모 레인(①), 시장 시뮬레이션(③), 연구 계약 레인(②)은 서로 호출하지 않는 **독립 데모**다. 인계 문서가 언급한 `agents.SellerAgent/BuyerAgent`는 ①의 scene A/B에서만 쓰이고, 시장 경로(③)는 `Exchange`가 별도 구현이다.

## 2. 판정표 (B–F)

| 질문 | 연구 계약 레인 (②, 사용자가 실제로 여는 경로) | 시장 시뮬레이션 (③) | 볼트 마켓 | AP4M 실행기 |
|---|---|---|---|---|
| B 목표·관찰에 따라 행동이 바뀌나 | **예.** 조건은 게시에서 온다(코드에 없음). 동의 항목·자동화·예산을 바꾸면 결과가 바뀐다(프로브 P1·P3·P5). 실행 출처: 규칙(LLM은 `talk()` 문장에만, 기본 off) | 부분. fixture 50계정(`fixtures/market_profiles.json`), 예산을 1/100로 줄이면 체결 6→3건(프로브). 소유자 응답은 난수(`policies.py:187-188`) | 부분. LLM 제안 + 코드 경계. 소유자 최저가·금지 목적이 실제로 가격·verdict를 바꾼다(프로브 vault) | **아니오.** 과제·주차·가격·상대 고정(`agent.mjs:24-30`, `lib/catalog.mjs:13-18`) |
| C 후보 선택·협상·중단이 실제로 달라지나 | 후보 비교·협상 **없음**(고정가, 전원에게 요청). 중단은 있음(동의 밖·예산·서명) | 예. 책 앵커·샘플검사·점수·협상(`exchange.py:362-454`), 상한 아래 floor면 walk away(프로브: "ceiling 8333 below the seller's floor 13507") | 1:1만. 후보 비교 없음(`market.py:467` `cands[:1]`) | 없음(거절만) |
| D 양쪽 권한을 같은 흐름에서 집행하나 | **예.** 기관: `BuyerMandate`(예산·건당·목적, `engine.py:217-224`) + 윤리 credential(`policy.py:133-149`). 개인: 동의 상태·기간·목적·최저가·항목·자동화(`policy.py:171-231`). 사람이 승인해도 예산 밖이면 `budget`(데모 6단계) | 예(정책 plug-in + mandate) | 예(소유자 규칙 + 구매자 한도 `auto_limit`) | 한쪽만: 참여자 정책(상한·예산·allowlist·동의). 기관 권한은 없음 |
| E 실행·회복(이중지급·허용밖 전달·재시작) | **예.** 주문 키 멱등(`engine.py:158-200`), 레일 ref 멱등, 미지급 재시도 1회만(프로브 P4·P8), 철회 시 키 미공개(`research_contracts.py:625-647`), 재시작 복구 테스트 있음 | 지급 후 부적합은 **환불 청구 기록**(`exchange.py:554-586`, 원장 환불 아님) | 레일 ref 멱등, 재시작 복구(`market.py:785`) | 결제 후 해시검증(x402 구조). **수정 전 결함**: 변조 뒤에도 계속 지급(§6 D2) |
| F 유효한 완료(전달물·검증·수신측 열람·잔여예산) | 부분. 콘솔에 주문·결제·잔여예산, 멤버 뷰에 paid/held. **연구자가 전달 번들을 내려받는 API/페이지 없음**(데모 7단계는 엔진 내부 호출로 열람) | 예(열람·fitness·refund claim 기록) | 예(번들 열람·해시 대조, `market.py:640-644`) | 예(패키지 해시, 영수증 URL, 잔액 전후) |

**한 줄 답:** 사용자가 실제로 여는 연구 계약 레인은 "동의·권한·예산·서명을 집행하고 멈출 줄 아는 실행기"로는 작동한다(§3). "목표를 이해하고 상대를 찾아 비교·협상하는 에이전트"는
시장 시뮬레이션과 볼트 마켓 프로토타입에만 있고, 둘 다 합성 계정·난수/LLM 응답 위의 데모다(§4). IR 대본의 네 문장 중 둘은 수정이 필요하다(`IR_CLAIM_BOUNDARY.md`).

## 3. 지금 작동하는 것 (이 세션에서 실행해 확인)

재현은 모두 mock 원장·LLM off. `PYTHONPATH=. .venv/bin/python docs/review-20261027/demo/run_demo.py`가 §3.1–3.7을 한 번에 다시 만든다.

1. **게시 조건이 곧 계약이다.** `POST /api/contracts`의 terms가 기관·IRB·목적·항목·기간·가격·예산·정원을 정하고(`research_contracts.py:245-307`), T3(유전체·CT·MRI)는 게시 자체가 거절된다(`:283-286`, `tests/test_research_contracts.py:58`).
2. **동의 밖은 값이 있어도 보내지 않는다.** 프로브 P1: 멤버가 `sleep.daily`만 동의, 기관은 두 항목에 0.01씩 제시 → `granted=['sleep.daily']`, 0.01만 결제, `fatigue.survey`는 scope 질문으로 사람에게(`policy.py:203-208`, `agents.py:400-419`).
3. **'매번 확인'은 멈춘다.** P2·데모 5단계: `needs_approval`, 주문 없음, 결제 없음. 틀린 서명 403, 다른 멤버 키 403, 본인 키 새 서명 200 → `delivered`(`research_contracts.py:603-623`, 서명 메시지는 요청 id·항목·계약·동의 해시에 바인딩 `:591-595`).
4. **기관 예산은 사람의 승인으로 넘지 못한다.** P3: 예산 0.02에 멤버 2명 → 1명 `delivered`, 1명 `budget "needs 20000 drops, 0 available"`. 데모 6단계: 예산 소진 뒤 유효한 서명으로 승인해도 `budget`.
5. **이중 지급 없음.** P4: 같은 주차 두 번 → 주문 수 2→2, 레일 호출 2→2. P8: 레일 다운 → `unpaid`/`held 20000`, 복구 후 retry 1건, 두 번째 retry 0건, 같은 ref 호출 1회.
6. **철회.** P6·데모 8단계: `withdrawn` 뒤 다음 라운드에서 제외, 기수령 지급 유지.
7. **기관이 산 것을 열 수 있다.** 데모 7단계: 전달 주문 5건 모두 `engine.open_payload(iid, oid)`로 열림, 해시 일치, 행 7개/주, 항목은 멤버가 동의한 것만.
8. **AP4M 레일 자체.** `ap4m/test/rail.test.mjs`(가짜 pay): 상한·풀 예산 거절, 같은 ref 1회, 실패 건 pending 재개, 영수증 후속 채움, 재시도 시 동일 resource URL — 17/17 통과(수정 후 `npm test`).
9. **LLM 제안은 좁히기만 한다.** 프로브(market, 적대적 proposer: 모든 gap 항목·8주·상한 10^12 요구): 계획 27건 전부 검사 기록, 상한은 항목별 예산으로 깎임("price ceiling 1000000000000 above the budget per item 666666: kept 12000"), 체결가 전부 항목별 예산 이하(`discovery.py:66-83`). 볼트 마켓: LLM이 최저가 7 아래 5에 agree → 코드가 counter 7(`vaultmarket/agents.py:108-115`); 금지 목적은 LLM을 부르지 않고 decline(`:88-99`).
10. **브라우저 경로.** 로컬 엔진(`uvicorn`, mock)에서 `/apps/contracts/post.html`로 계약 게시(브라우저 WebCrypto Ed25519 키 생성·로그인·콘솔 표시 확인, RC1-a1f8a5), `/apps/contracts/join.html` 초대 링크로 가입(혈압 항목 제외, `confirm_each`, 가입 RC1-a647a40b, 서명 동의 `e59823e6…`). 연구자 페이지 'Run week'(1주차) → 멤버 상태 `needs_approval`(주문·결제 없음) → 참여자 페이지에 'Week 1: Activity, Fatigue, Sleep' 대기 표시 → 'Approve this week'(브라우저 키로 서명) → 참여자 페이지 `paid 0.03 RLUSD`, 결제 행 `1 · 0.03 · paid · F2D86A4C37…`(mock 에스크로) → 연구자 콘솔 `Order 1 · week 1 · 0.03 · delivered · paid`. 즉 브라우저 경로(키 생성·동의 서명·로그인·승인 서명)는 스크립트 경로와 같은 결과를 낸다. 관찰한 UX 결함: 혈압 항목의 scope 질문이 'Week -: … / Approve this week'로 표시된다(§6 D6).

## 4. scripted · mock · simulation인 것

| 항목 | 파일:행 | 무엇이 고정/가정인가 |
|---|---|---|
| AP4M 실행기 과제 | `ap4m/agent.mjs:24-30`, `ap4m/lib/catalog.mjs:13-18` | P-017 / SLEEP-01 / 3–5주, 6주차 0.50은 scripted. 상대는 자기 merchant 한 곳. 새 목표·상대 탐색 없음 |
| 2026-10-25 AP4M 영수증 | `ap4m/receipts/run-2026-10-25T14-59-45-563Z.json` | 당시 live 기록(testnet, 0.05×3 지급, 0.50 거절). 이번 점검은 체인을 재조회하지 않았다 |
| 시장 시뮬레이션 수치(109/80/6/4, 239) | `market/acts.py:194-256`, `fixtures/market_profiles.json` | seed 11, mock 원장, 소유자 응답 `rng.random() < accept`(`policies.py:187-188`, `:230-240`), 판매자 floor는 run마다 난수(`acts.py:244-246`), P-001만 수동 승인 |
| 11,600 → 233 | `catalog/simulate.py:17-109` | 50 합성 owner·6 study, 응답시간 18h 지수분포 **가정**(`:31`), 수락률 0.8/0.5 난수(`:68-69`), TouchID는 소프트웨어 서명키(`scope.py:77`). 재계산: manual 11,600 / touch_id 233 / auto 1,792 / declined 83 / refused 275 |
| 결정 설명기 `/apps/decide` | `catalog/explain.py:19-20, 67-69` | 상태 없는 합성 owner, 기본 grant 고정. 실제 사람의 동의 상태를 읽지 않는다 |
| 연구 데모 레인 `/console`, `/participant` | `scenario.py`, `study.py`, `cohort.py` | fixture 참여자 50명, dev 로그인 harness(`web.py:1086-1120`, dev에서만) |
| 볼트 마켓 배경 거래 | `vaultmarket/market.py:931-989` `tick()/run_forever()` | 시뮬레이션 계정끼리 자동 게시·협상; 멤버/demo-vault 거래만 항상 AP4M(`:711-722`) |
| 연구 계약 테스트 계정 | `research_contracts.py:415-441`, `scripts/contract_join.py` | 생성 데이터 `generated_test` 라벨; 2026-10-25 실행도 테스트 계정(`docs/runs/research-contracts/README.md`) |
| 영수증 검증 `?verify=1` | `ap4m_receipts.py` | 공개 RPC 재조회 코드. 이번 점검에서 실행 안 함 |

## 5. 구현은 있으나 이 점검에서 검증하지 않은 것

- XRPL Testnet 실행(README Run C/D, `LEDGER=testnet`): 키·네트워크 사용 안 함. 코드 경로만 읽음(`ledger/xrpl_ledger.py`, `engine.py:495-700`).
- AP4M live(`rail-server.mjs` `connect()/payOnce()`, `agent.mjs` live 분기): `.env` 없음, live 결제 금지. 10-25 영수증의 tx·receipt URL 재검증 안 함.
- UniQdata 연동(`uniqdata_live.py`, `sync_uniqdata`): 서버 미호출. 결함 후보는 `CORE_BRIDGE_FINDINGS.md`.
- LLM live 경로(`llm.py` propose/say, `vaultmarket/llm.py`): 스텁으로만 검사. 429/fallback 로직은 `tests/test_llm.py`가 가짜 클라이언트로 덮는다.
- 패스키(`security/passkey.py`, `uniqdata_live.SoftPasskey`): 이 세션의 모든 승인은 Ed25519 소프트웨어 키.
- Railway 배포 상태·`apps/try`의 production 링크: 미조회.
- 볼트 마켓 전체 흐름(`_negotiate` 실행): `tests/test_vault_market.py` 65건이 mock에서 통과하는 것으로 갈음(§7).

## 6. 실제 결함

| # | 결함 | 위치 | 재현 | 처리 |
|---|---|---|---|---|
| D1 | **AP4M 실행기의 동의 범위가 과제보다 넓다.** 과제는 3–5주인데 동의는 3–6주 → 상한 안(0.05)의 6주차 제안이 **지급된다**. IR 문장 2를 이 실행기에 대해 거짓으로 만든다 | `ap4m/agent.mjs` 구 30–32행 `weeks: [3,4,5,6]` | `decide(offer({week:6}), policy, taskConsent(), 0n)` → `pay:true`(수정 전 프로브) | **수정**: `weeks: TASK.weeks`(`agent.mjs:34-37`). 테스트 `agent.test.mjs:64` |
| D2 | **변조 패키지 뒤에도 계속 지급.** 3주차 패키지 해시 불일치를 봐도 4·5주차를 지급, 환불 청구 기록 없음 | `ap4m/agent.mjs` 구 196–204행 | 3주차만 변조하는 fetch로 dry run → `paid 3, total 0.15, refund_claim null`(수정 전 프로브) | **수정**: 불일치 시 `refund_claim` 기록, `record.halted`, 이후 호출 `refuse "halted after week 3"`(`agent.mjs:130, 151-154, 217-225, 230`). 수정 후: paid 1, total 0.05, refund 0.05. 테스트 `agent.test.mjs:87`. 결제 자체는 되돌리지 않는다(x402 구조) |
| D3 | **거절 사유가 첫 번째 규칙만 남는다.** scripted 6주차(0.50)는 상한·예산·동의 주차 세 규칙을 다 어기는데 기록엔 "exceeds per-call cap"만 남아 "한 가지 제한만 검증"으로 읽힌다 | `ap4m/lib/policy.mjs` 구 24–48행 | `run-live.sh` dry run의 w6 decision line | **수정**: 모든 규칙을 검사해 `reasons[]`로 열거(`policy.mjs:26-57`). dry run: "exceeds per-call cap…; over the delegated budget…; week 6 is outside consented weeks 3,4,5" |
| D4 | **README대로 설치하면 테스트 30건 실패.** `requirements.txt`에 `python-multipart`가 없어 `tests/test_vault_market.py` 30건이 `RuntimeError: Form data requires "python-multipart"` | `requirements.txt`; 볼트 서버는 자기 `requirements.txt`에만 추가 | `python -m pytest -q` 전체: 432 passed / 30 failed / 2 skipped | **수정**: 루트 `requirements.txt`에 1줄 추가. 재실행 65/65 통과 |
| D5 | 연구 계약 레인의 추출에 study 인자가 없어 **연구별 가명·날짜 이동이 적용되지 않는다**(행에 `person=pid`, 원래 study day). 연구 데모 레인은 `study=LAB`를 넘긴다 | `research_contracts.py:485` vs `study.py:323`, `connectors.py:165-181` | 데모 7단계 열람 행의 `person` 값이 pid | **수정(61ddb5b)**: `_send_week()`가 `pa.vault.extract(d.granted, week, study=t["institution_id"])`로 호출 → 행의 `person`은 기관별 가명 `S-…`, `day`는 기관별 이동값. `settlement_records`·`console`·`member_view` 출력 형태 불변. 테스트 `test_research_contracts.py::test_delivered_rows_carry_the_institutions_pseudonym_and_shifted_days` |
| D6 | scope 질문을 **거절할 수단이 없다**(승인 API만 있고 `approve(items=[])`를 보내는 UI 없음) → 열린 질문이 남는다. 참여자 페이지는 scope 질문(동의 범위 확장)을 'Week -: … / Approve this week'로 표시해 주차 확인처럼 보인다 | `web.py:1051-1053`, `apps/contracts/join.js:48-53` | P1의 `A_scope_ask_open`; 브라우저 확인(§3.10) | **수정(61ddb5b)**: `join.js`가 scope 질문(kind `scope`, week 없음)을 "New items asked, outside what you agreed to: …"로 구분 표시하고 Allow / Decline 버튼을 둔다. Decline은 `approve:{rid}:` 서명(`action_message` 형식과 일치) + `items: []`를 기존 approve route로 보내고, 서버는 질문을 닫되 동의를 넓히지 않는다. 정책이 다음 라운드에 같은 항목을 다시 물을 수 있는 것은 기존 동작이며 바꾸지 않았다. 테스트 `test_research_contracts.py::test_a_member_declines_a_scope_question_with_a_signature_and_consent_stays_as_signed` |
| D7 | `approve()`가 레인 락 안에서 AP4M 결제를 한다(#97이 `run_round`만 락 밖으로 옮김) | `research_contracts.py:608-623` `_send_week(... )` 기본 `pay=True` | 코드 읽기 | 미수정. 성능 |
| D8 | 볼트 마켓 프롬프트는 "다른 판매자와 경쟁, 가장 싼 쪽을 산다"고 하지만 코드는 **게시당 판매자 1명**만 묻는다. 문서·프롬프트와 동작 불일치 | `vaultmarket/agents.py:101` vs `market.py:467, 519-526` | 코드 읽기 | 미수정. 설명 수정 대상 |
| D9 | 연구 계약 레인에 **연구자가 전달물을 받는 API/페이지가 없다**(엔진 내부 `open_payload`만) | `web.py:977-1056`에 해당 route 없음 | 데모 7단계 | **수정(61ddb5b)**: `GET /api/contracts/{cid}/orders/{oid}/bundle`(rbac `Rule((R,), "contract")` — 그 계약의 연구자만, operator 제외) → `Lane.open_bundle()`이 `engine.open_payload(iid, oid)`로 열어 `{order_id, slot, granted, rows, bundle_hash}`를 돌려준다. 미전달·인박스 부재·해시 불일치 409, 타 계약 주문 404. `post.js` 주문 표에 "Open" 링크. 테스트 `test_research_contracts.py::test_the_researcher_receives_a_delivered_week_and_nobody_else_does`(연구자 200, 멤버·타 연구자 403, 변조 409) |
| D10 | Core 연동 4건 | `CORE_BRIDGE_FINDINGS.md` | 〃 | 경계상 미수정 |

## 7. 수정 파일과 영향 테스트

| 파일 | 변경 |
|---|---|
| `ap4m/lib/policy.mjs` | `decide()`가 모든 규칙을 검사하고 `reasons[]`를 돌려준다(`reason`은 `; `로 합친 문자열, 기존 정규식 호환) |
| `ap4m/agent.mjs` | 동의 = 과제 주차; 변조 뒤 `refund_claim`·`halted`·`refund_claims`·`total_refund_claimed_rlusd`; 이후 호출 거절; 요약 로그 |
| `ap4m/test/agent.test.mjs` | 6주차 거절이 세 규칙을 모두 명시하는지, 상한 안 6주차가 동의로 거절되는지(신규), 변조 뒤 중단·환불청구(수정) |
| `ap4m/README.md` | 위 동작 설명 4곳 |
| `requirements.txt` | `python-multipart` 1줄 |

실행 결과:
- `cd ap4m && npm test`: 수정 전 16/16 → 수정 후 **17/17** 통과.
- `DRY_RUN=1 ./run-live.sh`: 3 PAY / 1 REFUSE, 거절 사유 세 개 열거, 합계 0.15(기록 `ap4m/out/`, gitignored).
- `python -m pytest -q`(전체, mock): 수정 전 432 passed / 30 failed / 2 skipped(6분 24초) → `python-multipart` 설치 후 `tests/test_vault_market.py` 65/65. 수정 후 전체 재실행: **462 passed / 2 skipped**(6분 18초, 실패 0).
- 프로브 `probe_contracts.py`(P1–P8), `probe_market2.py`, `probe_vault.py`, `probe_ap4m.mjs`: 결과는 §3·§6에 전사. 스크립트는 세션 scratchpad에만 있다.

### 후속 수정 2026-10-27 — D5·D6·D9 (커밋 61ddb5b)

| 파일 | 변경 |
|---|---|
| `agentrail/research_contracts.py` | `_send_week()`에 `study=t["institution_id"]`; `Lane.open_bundle(cid, oid)` 추가 |
| `agentrail/web.py`, `agentrail/security/rbac.py` | `GET /api/contracts/{cid}/orders/{oid}/bundle` route와 접근 규칙(그 계약의 researcher만) |
| `apps/contracts/join.js` | scope 질문 라벨 구분, Allow / Decline 버튼(Decline = `items: []` 서명 전송) |
| `apps/contracts/post.js` | 주문 표 "Bundle" 열의 Open 링크(연구자 토큰으로 열어 행을 표시) |
| `tests/test_research_contracts.py` | D5·D6·D9 회귀 테스트 3건; helper `post(key_name=)`·`join(items=)` |

`PYTHONPATH=. .venv/bin/python -m pytest -q`(전체, mock): 수정 전 462 passed / 2 skipped → 수정 후 **465 passed / 2 skipped**. 브라우저 확인은 하지 않았다(페이지 변경은 서빙 테스트와 금지어 검사만 통과).

## 8. 남은 제한

- 이 점검은 mock 원장·LLM off·레일 미연결에서의 동작 증거다. 테스트넷·AP4M live·UniQdata 연동·패스키는 코드 존재만 확인했고 운영 증거가 아니다.
- "에이전트다움"(목표 해석·상대 탐색·협상)은 시장 시뮬레이션/볼트 마켓에만 있으며, 사용자가 실제로 여는 연구 계약 레인에는 없다. 이것은 결함이 아니라 설계 범위이지만 IR에서 섞어 말하면 안 된다.
- D5·D6·D9는 61ddb5b에서 수정했다(§6·§7). D7·D8·D10은 백로그로 넘긴다(리팩토링 세션 `output/full-audit-20261027/BACKLOG.md`).
- 2026-10-25 영수증·실행 기록은 당시 상태의 증거이며, 현재 레일/서비스가 같은 동작을 한다는 증거로 바꾸지 않았다.
