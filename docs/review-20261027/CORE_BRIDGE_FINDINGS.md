# Core 연동(UniQdata backend bridge) 점검 결과 — 2026-10-27

이 세션(`agent/` 에이전트 구현 점검)의 경계에 따라 Core 연동에서 본 결함은 고치지 않고 여기에 적는다.
리팩토링 세션이 `output/full-audit-20261027/BACKLOG.md`에 합친다. 모든 항목은 코드 읽기와 로컬 재현이며,
실제 UniQdata 서버·실계정에 대한 호출은 하지 않았다.

대상: `agentrail/research_contracts.py`(이 저장소, 송신측) ↔ `UniQdata/backend` origin/main `5c2b86d0`의
`app/api/v1/endpoints/agentrail_settlement.py`, `app/schemas/agentrail_settlement.py` (PR #1593, 2026-10-25 머지, 수신측).

## F1. AP4M 레일로 결제된 주문은 UniQdata에 영수증 없이 "settled"로만 보고된다

- 송신: `agentrail/research_contracts.py:675-685` `settlement_records()`가 보내는 필드는 `escrow_create_tx` /
  `escrow_finish_tx` / `escrow_cancel_tx`뿐이고, AP4M 레일이면 세 값을 모두 `None`으로 보낸다.
- 수신: Core 스키마 `app/schemas/agentrail_settlement.py`는 AP4M용 선택 필드 `receipt_url`, `voucher_tx`,
  `forward_tx`를 받도록 되어 있다(`EVM_TX` 패턴, `HTTPS_URL` 패턴). 송신측이 이 세 필드를 채우지 않는다.
- 결과: 앱의 연구 기여 탭은 AP4M 결제를 금액·상태만 보고 tx 링크를 하나도 볼 수 없다. Core의 `summarize()`는
  `latest_tx`를 escrow 해시에서만 만들므로 AP4M 행은 `latest_tx=None`이다.
- 재현(로컬, 가짜 레일): `tests/test_research_contracts.py::test_payments_reach_the_members_uniqdata_account_once_per_order`
  의 `FakeUniQdata`를 AP4M 계약(`AP4M_TERMS`)으로 바꿔 실행하면 전송 레코드에 `receipt_url`/`voucher_tx` 키가 없다.
  이 세션의 프로브 `P1`(`docs/review-20261027/STATUS.md` 참조)에서 `_order_view()["payment"]`에는
  `voucher_redeemed.tx`, `receipt_url`, `forward.tx`가 있으므로 송신측에서 채울 재료는 이미 있다.
- 수정 위치(제안): 송신측 `settlement_records()`에 `receipt_url`, `voucher_tx`, `forward_tx`를 추가
  (`o["payment"]` 값 사용, 패턴에 맞지 않으면 `None`). Core 변경은 필요 없다.

## F2. `network` 값이 AP4M일 때 "testnet"(XRPL L1 Testnet)으로 보고된다

- 송신: `research_contracts.py:679` `"network": "testnet" if ap4m else self.ledger.name`.
- 수신: 스키마 `network: Literal["testnet", "devnet"]`; 핸들러 `EXPLORERS["testnet"] = "https://testnet.xrpl.org/transactions/"`.
- 결과: AP4M 결제는 XRPL EVM Testnet(chain 1449000)인데 Core는 XRPL L1 Testnet 행으로 저장·표시한다. tx가 없어
  링크가 깨지지는 않지만(F1), 네트워크 표기가 사실과 다르다. 두 체인을 구분하려면 Core 스키마에 값 하나
  (예: `xrpl-evm-testnet`)와 EXPLORER 매핑이 필요하다 — 이것은 Core 쪽 변경이다.

## F3. 동기화 조건이 레일·네트워크에만 걸려 있고, 실패는 조용히 다음 라운드로 미뤄진다

- `research_contracts.py:686-704` `sync_uniqdata()`: `uniqdata:` 소스 멤버이고 (`ledger.name in (testnet, devnet)` 또는 AP4M)일 때만
  보고한다. 예외는 `uniqdata_sync_failed` 로그 한 줄로 삼키고 `None`을 돌려준다. 재시도 큐나 "마지막 성공 보고 시각"이 없어
  라운드가 더 없으면 영원히 미보고 상태가 남는다(철회·종료 후 마지막 상태 변화가 특히 그렇다: `withdraw()`가 한 번
  호출하고 끝).
- Core의 PUT은 `(person, contract, order_ref)` 유니크로 멱등이므로(`app/models/agentrail_settlement.py:25`) 재보고 자체는 안전하다.

## F4. 패스키/실계정 경로는 이 저장소에서 검증되지 않았다

- `agentrail/uniqdata_live.py:94-155` `SoftPasskey`는 소프트웨어 EC 키로 WebAuthn assertion을 만든다(샌드박스용).
  `DevLaneApproval`(157)은 QA 계정 비밀번호 재확인이다. 둘 다 실제 기기 패스키가 아니다.
- 이 세션은 UniQdata 서버를 호출하지 않았다. `UNIQDATA_ROSTER`가 없으면 `Lane.uniqdata`는 빈 dict이고
  `uniqdata_account`로 가입하면 422("that UniQdata account is not connected to this service")다 — `research_contracts.py:366-369`.
- 따라서 "실계정·실기관 미연결"은 이 점검에서도 그대로다. 해커톤 당시 샌드박스 계정 연결 기록은
  `docs/UNIQDATA_LIVE.md`와 `docs/runs/research-contracts/README.md`(daniel50 등 test account)에 있고, 그것은 당시 상태의 증거다.

## 확인한 일치 사항 (결함 아님)

- 송신 상태값 `held/settled/withheld/refunded`(`research_contracts.py:655-657 STATUS`)는 Core의 `CheckConstraint`와 일치한다.
- `contract_id`(`RC1-xxxxxx`), `order_ref`(`order-N`), `consent_hash`(64 hex), `period`(`week N`), `asset`(`USD`/`XRP`),
  `display_unit`(`RLUSD`)는 Core 스키마의 패턴 안에 있다.
- `contract_status`는 `active`/`withdrawn`만 보내며 Core는 `paused`/`closed`도 받는다. 계약 종료(`close()`)는 Core에 전달되지 않는다
  (`closed` 상태를 보내는 코드 경로가 없다). 표시상 차이일 뿐 금액 집계에는 영향이 없다.
