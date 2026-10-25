# AgentRail 전체 점검과 보안 리뷰

대상: `claude/project-thread-vfr62v` @ 8981a8e (`claude/uniqdata-adapter` ffaf66d는 이미 병합됨). 점검일 2026-10-25.
마감: 코드 동결 08:00 EDT (12:00 UTC), 제출 12:30 EDT.

## 결론

- **작동하는 부분은 진짜다.** 테스트 71개가 모두 통과한다(README에는 61개로 적혀 있음). mock 데모(`scripts/run_health_demo.py`)는 처음부터 끝까지 한 번에 돈다. README에 링크한 Testnet tx(Escrow, MPT, Clawback, Credential, multisig, DepositAuth, x402)는 코드 경로와 맞다.
- **비밀값은 깨끗하다.** 히스토리 전체를 훑어봤다. 커밋된 .env, 시드, 개인키, API 키는 없다. `.gitignore`가 `.env`, `*seed*`, `wallet*.json`, `wallets.local.json`을 막는다. 로그와 대시보드에도 키를 출력하지 않는다.
- **비어 있는 것은 "앱 경계"다.** API에 인증이 전혀 없다. 서버 한 프로세스가 모든 당사자(연구기관, 서명자 2명, 참여자, 운영자)의 키를 갖고 있다. 그래서 원장이 강제하는 규칙(2-of-2 multisig, escrow 조건, MPT 권한)을 HTTP 호출 한 번으로 우회할 수 있다. 원장 계층은 탄탄하고, 그 위의 HTTP와 키 보관 계층이 비어 있는 구조다.
- **README가 과장한 곳이 세 군데 있다.**
  1. "운영자는 번들을 열 수 없다": `/api/study/bundle/{id}`가 서버에서 복호화한 건강 데이터를 누구에게나 돌려준다.
  2. "기관 간에 기록을 연결할 수 없다, 날짜 이동은 에이전트만 안다": 가명과 날짜 이동이 키 없는 sha256이라 다시 계산할 수 있다. 연구자 화면은 실제 ID와 가명을 나란히 보여준다.
  3. "키 공개 직전에 동의와 준법을 다시 확인한다": 공개 직전에는 철회와 라이선스만 본다. 검증 기관 Credential, 기간, 목적은 다시 보지 않는다.
- **데모 경로의 위험:** 문서에 나온 `/participant`와 `/console`은 `apps/` 폴더가 저장소에 없어서 404가 난다(팀이 만드는 UI). 그리고 Testnet에서 같은 계정이 xrpl-py autofill과 로컬 sequence 카운터를 섞어 쓴다. 그래서 라이선스 발급 뒤 같은 계정에서 다음 tx를 보내면 sequence가 충돌해 멈출 수 있다(아래 S8).

판정: **데모와 원장 증거는 제출할 만하다.** 08:00 전에 꼭 고칠 것은 M1~M8이다. 다 하면 약 3시간이고 M1을 빼면 약 2시간이다. 나머지는 README "보안 설계와 한계"에 적는다.

## 심각도별 표

재현 방법: `M2`, `M5`, `M6`, `M7`은 FastAPI TestClient로 실제 재현했다(/tmp 스크립트). 나머지는 코드를 읽고 확인했다.

### 꼭 고칠 것 (코드 동결 전)

| # | 심각도 | 위험 | 위치 | 공격 시나리오 | 수정안 | 시간 |
|---|---|---|---|---|---|---|
| M1 | High | 인증 없음, CSRF | `agentrail/web.py` 전체. bodyless POST: `/api/reset`, `/api/p/{pid}/revoke`·`pause`·`resume`, `/api/study/send`·`sweep`·`close-round` | 같은 네트워크의 누구든, 또는 브라우저에 열린 아무 웹사이트가 `fetch('http://127.0.0.1:8000/api/p/P-017/revoke',{method:'POST',mode:'no-cors'})`를 보낸다. 그러면 참여자 철회, 데이터 송부, 세계 초기화가 일어난다. `?ledger=testnet`을 붙이면 faucet 경로도 돈다 | 역할별 데모 토큰을 둔다(`AGENTRAIL_TOKENS`, 없으면 시작할 때 생성해 콘솔에 출력): participant:{pid}, researcher, signer:owner, signer:compliance. FastAPI dependency로 `Authorization: Bearer` 헤더를 검사한다. 커스텀 헤더가 있으면 CORS preflight가 강제되므로 CSRF도 같이 막힌다. `/api/reset`의 `ledger` 파라미터는 `AGENTRAIL_ALLOW_RESET=1`일 때만 받는다. 대시보드 JS는 `?token=`을 sessionStorage에 넣고 헤더로 보낸다 | 45분 |
| M2 | High | 서버가 복호화한 건강 데이터를 누구에게나 반환 | `web.py:185` → `study.py:350` → `engine.py:528`. `study.py:488` `"operator_can_open": False` | `for i in 1..N: curl /api/study/bundle/$i`로 모든 참여자의 행 데이터를 받는다. order id가 순차라서 추측이 쉽다 | researcher 토큰을 요구한다. 철회한 참여자의 주문은 410을 돌려준다. preview 응답의 `operator_can_open`을 지우거나 사실대로 바꾼다 | 10분 |
| M3 | High | 가명과 날짜 이동을 되돌릴 수 있음 | `agentrail/connectors.py:135-141`. `study.py:633-634`(person과 pseudonym을 같이 반환). `study.py:238`(slot에 실제 pid) | 다른 연구도 `sha256("org_x\|P-017")`로 가명을 계산해 기관 간 기록을 연결할 수 있다. 날짜 이동도 같은 방식으로 계산되므로 실제 날짜가 복원된다 | `PersonalVaultConnector.__init__`에서 `self._secret = os.urandom(32)`를 만들고, pseudonym과 day_shift를 `hmac.new(secret, f"{study}\|...")`로 계산한다. 연구자용 `study_view.contributions`에서 `person`을 빼고 pseudonym만 남긴다(heatmap 행 이름은 study 등록 번호라서 그대로 둬도 된다. README에 "등록 번호는 연구가 아는 값, 가명은 기관 간 연결 방지"라고 구분해 적는다). 테스트: 두 Vault 인스턴스의 가명이 서로 다르고, 키 없이 재계산하면 맞지 않음 | 25분 |
| M4 | Medium | 키 공개 직전 재검사 누락 | `agentrail/policy.py:160-170`(`for_delivery=True` 분기) | 120~600초 escrow 창 안에 검증 기관 Credential이 회수되거나 윤리 Credential이 만료돼도 `_escrow_finish`(engine.py:467)가 K를 공개한다. 데이터와 보상이 그대로 넘어간다. README와 DEMO_SCOPE는 공개 직전에 다시 확인한다고 적었다 | delivery 분기에서도 `compliance.check`(prohibited, verified, quasi)와 기간 검사를 실행한다. 거부되면 withheld로 처리하고 cancel을 예약한다. pause는 지금처럼 확정된 건을 통과시킨다. 테스트: escrow 후 verified_check를 False로 바꾸면 process 결과가 withheld | 15분 |
| M5 | Medium | 철회를 되돌릴 수 있음 | `agentrail/agents.py:357` `resume` → `_update(status="active")` | `POST /api/p/P-0xx/resume` 한 번으로 revoked가 active로 바뀐다(CSRF로도 된다). 라이선스가 없는 참여자는 licence_check가 None이라 다음 send에서 다시 송부와 키 공개가 일어난다 | `_update`/`resume`에서 status가 revoked면 거부한다(새 동의 서명, 즉 `set_consent`로만 재개). 테스트 추가 | 5분 |
| M6 | High | 남의 요청을 조작(IDOR) | `study.py:477`(preview), `:491`(approve), `:514`(decline) | `POST /api/p/P-001/requests/<P-017의 rid>/decline`이 P-017의 요청을 declined로 바꾼다(재현함). approve는 P-001의 open 승인(범위 확장 포함)을 처리한 뒤 P-017의 요청에 `_answer`를 돌린다 | 세 함수의 맨 앞에서 `if req["person"] != pid: raise KeyError(rid)` → 404. 테스트 추가 | 5분 |
| M7 | High | multisig를 API로 우회, 예산 반복 인출, 서명 상한 자동 상승 | `study.py:160`(모르는 이름은 LAB 주소로 대체), `study.py:146`(set_goal이 status를 draft로 되돌림), `mandate.py:83`(`max(ceiling, total)`), `web.py:165` | 누구든 `goal` → `approve {"signers":["owner","compliance"]}`를 반복하면 매번 40 XRP 공동서명 top-up이 일어나 treasury가 바닥난다(1회 재현함). owner가 서명한 100 XRP 상한도 total을 따라 자동으로 다시 서명된다 | (a) 서명자마다 `signer:{name}` 토큰을 요구한다(M1). 요청 하나에 서명자 둘이 모두 들어 있으면 거부하고, 서명자가 각자 `POST /api/study/approve/sign`을 보내 2명이 모이면 제출한다. 시간이 없으면 최소 (b)~(d)만 한다. (b) 모르는 서명자 이름은 거부한다(fallback 삭제). (c) spec hash 하나에 승인은 한 번만 받는다. (d) `issue_from`이 L1 ceiling을 올리지 않게 한다(`self.ceiling_drops` 고정, total이 ceiling을 넘으면 거부). README에는 "데모는 두 서명자 키를 한 서버가 들고 있음"이라고 명시한다 | (b)~(d) 15분, (a) 30분 |
| M8 | Medium | Testnet sequence 충돌로 정지 | `ledger/xrpl_ledger.py:76`(로컬 카운터)와 `ledger/licence.py`, `xrpl_extras.py`의 `submit_and_wait`(autofill)를 같은 계정에 섞어 씀. `engine.py:396` `_send`에 만료 처리 없음 | P-017 승인 → LAB의 `MPTokenAuthorize`가 autofill로 sequence N을 쓴다 → LAB의 로컬 카운터는 여전히 N이다 → 다음 EscrowCreate가 tefPAST_SEQ를 받는다 → `_send`가 같은 blob을 계속 재제출하고 주문이 reserved에 영원히 머문다. 라이선스 발급 뒤 `send`나 `close_round`를 한 번 더 누르는 라이브 시연에서 발생할 수 있다 | autofill로 제출한 직후 해당 계정을 `self._seq.pop(account, None)` 한다(licence, credential, deposit, multisig 헬퍼 4곳. 또는 `_next_sequence`를 `max(local, account_info current)`로). `_send`에서 not found이고 `is_expired`이면 hash와 blob을 비우고 다시 서명한다 | 25분 |
| M9 | Medium(신뢰도) | README 과장과 불일치 | README §2, §5, §9, §10. `boundaries.py:42` | 심사위원이 코드를 열면 "operator cannot open bundles", "re-check before key"(M4 전), "61 tests", `/participant`·`/console` 404가 바로 보인다 | 아래 README 초안으로 교체한다. 테스트 개수를 실제 값으로. `/participant`·`/console`은 팀 UI가 들어올 때만 문서에 남기고, 아니면 "UI는 팀 작업, API 계약은 docs/API.md"로 쓴다 | 15분 |

### README에 한계로 적을 것

| # | 심각도 | 위험 | 위치 | 내용 / 장기 수정안 |
|---|---|---|---|---|
| L1 | High(설계) | 모든 키가 한 프로세스에 있음 | `engine.py:96` box_keys, `engine.py:188` escrow_keys 평문, `xrpl_ledger.py` wallets | 데모는 연구기관, 참여자, 서명자, 운영자를 한 서버에서 시뮬레이션한다. DB를 읽을 수 있는 사람은 EscrowFinish 없이 번들을 연다. 운영에서는 K가 참여자 기기에만 있고, 연구기관 box 키는 기관 HSM/KMS에, 서명은 각 서명자 기기에서 한다(XRPL multisign blob 결합) |
| L2 | Medium | 파기가 부분적임 | `study.py:568-590` | 철회 시 inbox만 비운다. `bundles`, `escrow_keys` 행과 원장에 공개된 K는 남는다. 꼭 고칠 것 범위에서는 5분 안에 `DELETE FROM bundles/escrow_keys WHERE order_id IN (...)`를 추가할 수 있다(가능하면 M7과 함께). 원장의 K는 지울 수 없다고 고지해야 한다(번들 사본이 파기되면 K만으로는 의미 없음) |
| L3 | Medium | 감사 로그 무결성 | `db.py:139` events, `consent_history` | 해시 체인이 없다(proposals와 consent는 문서별 해시만 있음). 시간이 남으면 20분: events에 `prev_hash`, `hash = sha256(prev_hash + canonical(row))`를 넣고, 대시보드에 "체인 검증 OK"를 표시한다 |
| L4 | Medium | 온체인 연결성 | escrow 수취 주소 | 원장은 "연구기관 X가 주소 Y에 반복 지급"을 공개한다. 건강 데이터 값은 없지만 참여 사실 자체가 드러날 수 있다. 운영에서는 연구별 새 주소나 destination tag, 수탁형 지급을 쓴다 |
| L5 | Medium | LLM 요약이 동의 화면에 그대로 나감 | `cohort.py:238` summary(300자 자르기만 함), `study.py:397` | 연구자가 입력한 goal 문장이 LLM을 거쳐 참여자 카드의 "왜" 설명이 된다. 과장된 요약("완전 익명" 같은)이 동의를 왜곡할 수 있다. 수정: 카드에 "AI 요약, 구속력 있는 조건은 아래 DUO·항목·기간"이라는 라벨을 붙이고, 숫자와 약속어("anonymous", "never") 필터 또는 템플릿 요약을 쓴다(라벨은 5분) |
| L6 | Low-Med | 판매자 간 프롬프트 인젝션 | `reasoning.py:301` batch_proposer | 모든 판매자의 라이선스 텍스트와 샘플을 한 프롬프트에 넣는다. 악성 판매자가 "C1은 commercial false로"라고 적어 경쟁자를 배제할 수 있다. 돈과 권한은 AND 규칙 때문에 좁아지기만 하지만 선택의 공정성은 흔들린다. 수정: 판매자별로 따로 호출하거나 텍스트를 구분자로 감싸고, 결과를 seller terms와 비교한다. product id 충돌도 막는다(seller+product 키) |
| L7 | Low | drops와 XRP 사이의 float 왕복 | `scenario.py:175,183`, `study.py:161` | `int(x/1e6*1e6)`은 249 drops를 248로 만든다. 지금 금액은 0.2 XRP 단위라 문제가 없다. 수정: top_up이 drops를 받게 한다(5분) |
| L8 | Low | L3 검증의 빈칸 | `mandate.py:139-142` | `aud`, `orderId`, 서명된 `purpose`를 비교하지 않는다. issuer 공개키도 메모리에서 신뢰한다. 3줄이면 추가된다(5분, 여유가 있으면) |
| L9 | Low | 실패한 EscrowFinish | `engine.py:487` | tec로 실패한 finish도 원장에 Fulfillment(K)를 남긴다. 그런데 엔진은 cancel을 예약해 환불한다. 그러면 연구기관이 무료로 데이터를 얻을 수 있다. 데모 경로에서는 발생하지 않는다 |
| L10 | Info | 레이트 리밋, CORS 미설정 | `web.py` | localhost 데모. 운영에서는 UniQdata/UniQLab 인증과 게이트웨이 뒤에 둔다 |

## 확인 결과 문제 없음

- SQL: 모든 쿼리가 파라미터 바인딩이다(`_send`의 f-string 컬럼명은 상수).
- XSS: `static/index.html`은 사용자나 LLM에서 온 문자열을 모두 `esc()`로 처리한다.
- 이중 지급: order_key 멱등성, 제출 전 서명 blob 저장, 같은 blob 재제출, `finish_tx` 가드가 있다. 검증된 원장에서 destination, amount, InvoiceID, Condition을 대조한다.
- drops 단위: 원장에 보내는 금액은 모두 정수 drops 문자열이다.
- 에이전트 지갑 한도: place_order 단계의 per-order와 total 예약, 지급 직전의 L1→L2→L3 서명 체인 검증(위 L8 빈칸 제외).
- Escrow condition과 fulfillment: PREIMAGE-SHA-256, 32바이트 K. 길이와 접두사를 검증한다.
- LLM 출력: 스키마를 검증하고, 알 수 없는 값은 제거하고, 예산·목적·민감 필드는 owner 한도로 clamp한다. 원시 기록 값은 LLM에 보내지 않는다(커버리지 표만 보냄).

## 참고

- 보안 리뷰는 security-review 절차(탐지 서브태스크 1회 + 직접 재현과 코드 대조)로 했다. 정확성 리뷰(원장 sequence, 만료, 단위)는 직접 코드를 읽어서 했다. code-review 스킬은 따로 돌리지 않았다.
- `LLM_RECORD`의 기본값이 1이라 데모를 실행하면 `fixtures/llm_cache.json`이 바뀔 수 있다. 커밋 전에 diff를 확인해야 한다(비밀값은 들어가지 않음).
