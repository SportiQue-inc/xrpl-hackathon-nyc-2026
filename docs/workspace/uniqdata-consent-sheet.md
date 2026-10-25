# UniQdata 동의·패스키 승인 시트 디자인 레퍼런스

서명·동의 화면을 UniQdata 앱의 동의 시트·패스키 사유 시트와 같은 모양으로 만들기 위한 참고 문서입니다.

- 근거: `UniQdata/app` 저장소(기본 브랜치 HEAD)에서 읽기 전용으로 가져온 소스
  - `lib/features/consent/presentation/widgets/institution_share_sheet.dart`
  - `lib/features/consent/presentation/widgets/transfer_consent_sheet.dart`
  - `lib/features/auth/presentation/widgets/passkey_reason_sheet.dart`
  - `lib/features/uniqdata/presentation/widgets/tier2_batch_consent_sheet.dart`
  - `lib/l10n/app_ko.arb`(한국어 문구), `lib/core/theme/app_theme.dart`, `app_colors.dart`, `figma_tokens.dart`
  - 문구·흐름 확인용: `lib/core/ai/transfer_consent_notice.dart`, `lib/core/services/passkey_prompt_gate.dart`, `lib/app/runtime_bindings.dart`, `lib/features/consent/services/cross_border_voice_consent_flow.dart`, `lib/core/services/institution_share_service.dart`, 설정 화면 2곳(`security_settings_page.dart`, `wallet_recovery_page.dart`)
- 문구 표기: `"문구"` (`l10n 키`). 키가 없는 문구는 **하드코딩**이라고 표시합니다. `{변수}`는 런타임 값입니다.
- 사용자 데이터는 포함하지 않았습니다. 런타임 값은 자리표시자로만 적었습니다.

---

## 0. 공통 테마·토큰 (모든 시트에 적용)

### 0.1 테마 기본값 (`AppTheme._buildTheme`)

| 항목 | 토큰/코드 | 라이트 | 다크 |
|---|---|---|---|
| 강조색(primary) | `colorScheme.primary` = `ext.accent` | `#005FFF` (Core Blue) | `#4AAAF4` (Air Blue) |
| secondary / tertiary | `_airBlue` | `#4AAAF4` | `#4AAAF4` |
| 시트·카드 배경 | `bottomSheetTheme.backgroundColor` = `ext.appCard` = `colorScheme.surface` | `#FFFFFF` | `#161A2A` |
| 앱 배경 | `ext.appBg` | `#FAFBFC` | `#0A0C14` |
| 본문 텍스트 | `ext.appText` | `#0F172A` | `#F0F2F6` |
| 보조 텍스트 | `ext.appSub` (bodySmall, labelMedium 기본색) | `#64748B` | `#8890A4` |
| 테두리·구분선 | `ext.appBorder` | `#E2E8F0` | `#262A3C` |
| 오류 | `colorScheme.error` | `#EF4444` | `#EF4444` |
| 글꼴 | `fontFamily` | `Pretendard` → 대체 `SF Pro Text`, `Apple SD Gothic Neo`, `Noto Sans KR`, `Roboto`, `sans-serif` | 동일 |

`ColorScheme.fromSeed(seedColor: #005FFF, …)`가 자동으로 만드는 역할 색은 정확한 hex 값을 소스에서 확인할 수 없습니다(Flutter 버전에 따라 계산 결과가 다름). 시트에서 쓰는 역할은 다음과 같습니다.

| 시트에서 쓰는 역할 | 쓰임 | 값 |
|---|---|---|
| `colorScheme.surfaceContainerLow` | 공시 카드와 패스키 안내 박스의 배경 | 시드에서 계산된 연한 블루그레이 톤. **미확인(unresolved)** |
| `colorScheme.outlineVariant` | 직접 그린 드래그 핸들 | **미확인(unresolved)** |
| `colorScheme.onSurfaceVariant` | 부제, 라벨, 보조 아이콘 | **미확인(unresolved)**. bodySmall/labelMedium의 기본색 `appSub` `#64748B`와는 별개 값 |
| `colorScheme.primaryContainer` / `onPrimaryContainer` | Tier-2 개수 칩 | **미확인(unresolved)** |

브랜드 팔레트 참고(`AppColors`): primaryLight `#4AAAF4`, primaryDark `#0047CC`, secondaryDark `#268FE7`, accent(앰버) `#F59E0B`, success `#22C55E`, warning `#F59E0B`, error `#EF4444`, info `#3B82F6`, surface `#F8FAFC`. 시트 코드에서는 이 상수를 직접 쓰지 않고 `Theme.of(context)`만 참조합니다.

`FigmaColors`/`FigmaSpacing`/`FigmaRadii`(`figma_tokens.dart`)는 신규 Figma 화면(홈/루틴/리포트) 전용입니다. 동의 시트 4종은 이 토큰을 쓰지 않습니다. 시트에서 쓰는 숫자를 대응시키면 spacing `xs 4 / sm 8 / md 12 / lg 16 / xl 20 / xxl 24`, radii `md 12 / lg 16 / sheet 24 / pill 999`입니다.

### 0.2 컴포넌트 테마

| 컴포넌트 | 값 |
|---|---|
| Bottom sheet | 위쪽 모서리 radius **14** (`navRadius`), 배경 `appCard` |
| `FilledButton` (주 버튼) | 배경 primary, 글자 흰색, padding 가로 24 / 세로 16, radius **12**, 16px w700 |
| `OutlinedButton` | 글자·테두리 primary, padding 24/16, radius 12, 16px w700 |
| `TextButton` (보조) | 글자 primary, padding 가로 16 / 세로 12, 14px w700 |
| 비활성 버튼 | Material 3 기본 비활성 스타일(onSurface 12%/38%). 앱에서 따로 지정하지 않음 |
| Checkbox | 선택 시 채움 primary, 미선택 시 `appBorder`, 체크 표시 흰색 |
| TextField (`inputDecorationTheme`) | filled `appCard`, radius 12, 테두리 `appBorder`, 포커스 시 primary 2px, 오류 시 `#EF4444`, contentPadding 16/16 |
| Dialog | 배경 `appCard` |
| 페이지 전환 | 애니메이션 없음 |

### 0.3 타이포그래피

굵기와 색은 앱 테마에서 지정합니다. 크기와 행간은 Flutter Material 3 기본값을 따르며, 앱 소스에서 다시 정의하지 않습니다(**추정**: M3 2021 타입 스케일).

| 스타일 | 크기/행간 (M3 기본, 추정) | 앱 굵기 | 앱 색 |
|---|---|---|---|
| headlineSmall | 24 / 32 | w700 (시트에서 **w800**으로 덮어씀) | appText |
| titleLarge | 22 / 28 | w700 (시트에서 w800으로 덮어씀) | appText |
| titleMedium | 16 / 24 | w700 | appText |
| bodyLarge | 16 / 24 | w500 | appText |
| bodyMedium | 14 / 20 | w500 | appText |
| bodySmall | 12 / 16 | w500 | **appSub** |
| labelLarge | 14 / 20 | w700 | appText |
| labelMedium | 12 / 16 | w600 | appSub |

### 0.4 공용 시트 프레임

- 호출: `showModalBottomSheet(isScrollControlled: true, useSafeArea: true)`. 결과는 `Navigator.pop(true|false)`로 돌려주며, 시트를 그냥 닫으면 `false`(거부)로 처리합니다.
- 바깥 여백: 좌우 **20**, 위 **16**(직접 그린 핸들이 있을 때) 또는 **4**(`showDragHandle: true`일 때) 또는 **20**(기관 공유 시트), 아래 `키보드 높이 + 24~28`
- 직접 그린 드래그 핸들: 42×4, radius 999, 색 `outlineVariant`, 가운데 정렬, 아래 간격 18
- 프레임워크 드래그 핸들: `showDragHandle: true`(Tier-2 두 시트). Material 3 기본 핸들(32×4)로, 앱에서 크기·색을 지정하지 않음
- 정렬: `Column(mainAxisSize: min, crossAxisAlignment: start)`. 내용이 길어질 수 있으면 `SingleChildScrollView`로 감쌈
- 주 버튼과 보조 버튼은 모두 `SizedBox(width: double.infinity)` 전체 폭으로 세로로 쌓고, 버튼 사이 간격은 **8**

---

## 1. 패스키 사유 시트 — `passkey_reason_sheet.dart` (`confirmPasskeyReason`)

### 1.1 목적·노출 시점

OS 패스키(생체·PIN) 인증 창이 뜨기 **직전에** 인증이 필요한 이유를 보여 주고 확인을 받는 앱 공통 시트입니다. 이 시트는 디바이스 인증을 직접 호출하지 않습니다. `true`를 돌려주면 호출한 쪽이 이어서 OS 인증 창을 엽니다.

- 전역 게이트: `PasskeyPromptGate.run(purpose, ceremony)` → `runtime_bindings.dart`의 `_promptPasskeyReason`이 `confirmPasskeyReason(..., centered: true)`를 **가운데 다이얼로그**로 띄움 → 확인을 누르면 OS 패스키 인증 창이 열림
- 예외: 이미 설명·동의 버튼이 있는 화면(예: 해외 음성 AI 동의 시트의 "동의하고 패스키로 인증")은 `PasskeyPromptGate.afterConfirmation`으로 감쌉니다. 이 경우 사유 시트를 다시 띄우지 않고 OS 인증 1회만 허용합니다.
- 설정 화면은 하단 시트 형태로 직접 호출합니다. 보조 패스키 추가(`security_settings_page.dart`)와 패스키로 비밀번호 재설정(`wallet_recovery_page.dart`)이 여기에 해당합니다.
- 노출 조건: 화면이 현재 최상위 라우트이고 앱이 foreground(`resumed`)일 때만 띄웁니다(`isPasskeyPromptSurfaceCurrent`).

### 1.2 레이아웃 (위에서 아래로)

```
[하단 시트형]  Padding(L20 R20 T16 B=키보드+28)
[다이얼로그형] Dialog(insetPadding 가로28/세로24, radius 24) > Padding(20 사방)
 Column(min, start)
 ├─ (시트형만) 드래그 핸들 42×4 outlineVariant r999   ── 간격 18
 ├─ 제목            headlineSmall w800                ── 간격 8
 ├─ 설명            bodyLarge, onSurfaceVariant       ── 간격 18
 ├─ 안내 박스       Container(padding 14, surfaceContainerLow, r18)
 │   └─ Row: Icon(fingerprint_rounded, primary) · 12 · Expanded(infoNote, bodyMedium)
 │                                                     ── 간격 18
 ├─ 주 버튼         FilledButton.icon(lock_open_rounded) 전체 폭  ── 간격 8
 └─ 보조 버튼       TextButton 전체 폭 "취소"
```

체크박스, 항목 목록, 경고는 없습니다. 이 시트는 사유를 알리고 확인을 받는 용도만 맡습니다.

### 1.3 문구

기본값:

| 위치 | 문구 | 키 |
|---|---|---|
| 안내 박스(기본) | "계속하면 이 기기의 패스키(생체·PIN) 인증 창이 열립니다." | `passkeyReasonDefaultInfoNote` |
| 주 버튼(기본) | "패스키로 계속" | `passkeyReasonDefaultConfirm` |
| 보조 버튼 | "취소" | `passkeyReasonCancel` |

호출부별 사유 문구(OS 패스키 창 직전에 표시):

| 용도 (`PasskeyPromptPurpose`) | 제목 | 설명 |
|---|---|---|
| registration | "보안 설정" (`signupSecurityTitle`) | "패스키와 보안 자격을 준비합니다" (`signupSecuritySubtitle`) |
| vaultUnlock | "보관함 잠금 해제" (`passkeyVaultReasonTitle`) | "기기에 암호화해 보관한 내 기록을 열기 위해 패스키로 본인을 확인합니다. 확인을 누르면 패스키 인증창이 열립니다." (`passkeyVaultReasonBody`) |
| accountAction | "요청한 작업 본인 확인" (`passkeyActionReasonTitle`) | "요청하신 작업을 본인 계정에서 진행하는지 확인합니다. 확인을 누르면 패스키 인증창이 열립니다. 취소하면 인증을 진행하지 않습니다." (`passkeyActionReasonBody`) |
| dataRead | "내 정보 열람 확인" (`passkeyReadReasonTitle`) | "요청하신 개인 정보를 본인만 열람할 수 있도록 패스키로 확인합니다. 확인을 누르면 인증창이 열립니다." (`passkeyReadReasonBody`) |
| dataWrite | "기록 저장·수정 확인" (`passkeyWriteReasonTitle`) | "요청하신 기록 저장 또는 수정을 본인이 승인하는지 패스키로 확인합니다. 확인을 누르면 인증창이 열립니다." (`passkeyWriteReasonBody`) |

위 다섯 경우는 안내 박스와 버튼에 기본 문구("계속하면 이 기기의…", "패스키로 계속", "취소")를 그대로 씁니다. 형태는 가운데 다이얼로그입니다.

| 설정 화면 호출 | 제목 | 설명 | 안내 박스 | 주 버튼 |
|---|---|---|---|---|
| 보조 패스키 추가 | "보조 패스키 추가" (`securitySettingsBackupPasskeyReasonTitle`) | "이 기기에 보조 패스키를 추가하고, 기존 Health Vault와 지갑의 키 연결을 확인합니다." (`…Description`) | "iCloud 계정이 다르면 기존 패스키 확인 때 다른 기기의 패스키를 선택하세요. 기존 패스키 확인·새 패스키 생성·새 패스키 확인으로 인증 창이 여러 번 열릴 수 있어요." (`…InfoNote`) | "패스키 추가 계속" (`…Confirm`) |
| 비밀번호 재설정 | "패스키로 비밀번호 재설정 승인" (`walletRecoveryPasskeyReasonTitle`) | "기존 패스키로 본인 확인을 하면 비밀번호 재설정이 승인됩니다." (`walletRecoveryPasskeyReasonDescription`) | 기본값 | "패스키로 승인" (`walletRecoveryPasskeyReasonConfirm`) |

### 1.4 항목별 내역

없음.

### 1.5 버튼·상태

- 주 버튼: 항상 활성. 누르면 `pop(true)` → 호출부가 OS 패스키 창을 엽니다.
- "취소" 또는 시트 닫기: `false`. 게이트에서는 `PasskeyAuthCancelledException`으로 처리되어 인증을 진행하지 않습니다.
- 로딩·오류 문구는 이 시트에 없고 호출부가 표시합니다.

### 1.6 토큰

핸들 `outlineVariant`, 제목 `headlineSmall`+w800, 설명 `bodyLarge`+`onSurfaceVariant`, 안내 박스 `surfaceContainerLow`·padding 14·radius 18, 지문 아이콘 `primary`(기본 24), 안내 글자 `bodyMedium`, 다이얼로그 radius 24.

---

## 2. 해외 음성 AI 처리 동의 시트 — `transfer_consent_sheet.dart` (`showTransferConsentSheet`)

### 2.1 목적·노출 시점

음성·건강 메모를 해외(기본 대한민국, `destinationCountryLabel`)의 AI로 보내기 전에 받는 세분화된 국외이전 동의입니다(코드 주석의 표현은 "동의 창"). MindQ 음성 버튼(`mindq_speak_button.dart`)에서 라우터가 클라우드 처리를 열어야 할 때(`AiConsentOpportunity.shouldAsk`) `CrossBorderVoiceConsentFlow`를 통해 띄웁니다.

이 시트는 동의 여부만 돌려줍니다. `true`를 받은 뒤의 순서는 다음과 같습니다.

1. 서버에 대기 상태의 동의를 생성
2. 동의에 묶인 패스키 서명(`_attester`) — OS 패스키 창
3. Core가 승인하고 `consent.granted`를 기록한 뒤 XRPL 앵커링

사유 시트를 따로 띄우지 않습니다. 이 시트의 안내 박스와 버튼 문구가 사유 안내 역할을 합니다.

### 2.2 레이아웃

```
Padding(L20 R20 T16 B=키보드+28) > SingleChildScrollView > Column(min, start)
 ├─ 드래그 핸들 42×4 outlineVariant r999         ── 18
 ├─ 제목  headlineSmall w800                     ── 8
 ├─ 부제  bodyMedium, onSurfaceVariant            ── 18
 ├─ 공시 카드 _DisclosureCard                     ── 16
 │   Container(padding 가로14/세로6, surfaceContainerLow, r18)
 │   └─ _DisclosureRow ×7 (각 행 위아래 padding 10)
 │       Row(start): Icon(20, primary) · 12 · Column(
 │           라벨 labelMedium w700 onSurfaceVariant · 2 · 값 bodyMedium)
 ├─ 패스키 안내 박스 Container(padding 14, surfaceContainerLow, r18)  ── 18
 │   └─ Row: Icon(fingerprint_rounded, primary) · 12 · Expanded(bodySmall)
 ├─ 주 버튼 FilledButton.icon(lock_open_rounded) 전체 폭   ── 8
 └─ 보조 버튼 TextButton 전체 폭
```

체크박스는 없습니다. 주 버튼을 누르는 것이 곧 동의입니다.

### 2.3 문구

이 시트의 문구는 모두 **하드코딩된 한국어**이며 l10n 키가 없습니다. 값은 `transfer_consent_notice.dart`에서 만듭니다.

| 위치 | 문구 |
|---|---|
| 제목 | "해외({destinationCountryLabel}) 음성 AI 처리 동의" — 기본값이면 "해외(대한민국) 음성 AI 처리 동의" |
| 부제 | "이 기능은 귀하의 음성·건강 메모를 {destinationCountryLabel}에서 처리합니다. 민감한 건강정보가 포함될 수 있어, 아래 내용을 확인하고 동의해 주세요." |
| 패스키 안내 | "동의하면 패스키(생체·PIN)로 본인 확인 후, 동의 기록이 안전하게 봉인·기록됩니다." |
| 주 버튼 | "동의하고 패스키로 인증" |
| 보조 버튼 | "{fallbackLabel}(으)로 계속" (예: "기기 내 처리(온디바이스)(으)로 계속") |

### 2.4 항목별 공시 (`_DisclosureRow`, 순서 고정)

| # | 아이콘 | 라벨 | 값(음성 레인 `buildTransferConsentNotice`) |
|---|---|---|---|
| 1 | `auto_awesome_rounded` | "처리 목적" | 목적별: "음성을 텍스트로 변환(받아쓰기)합니다." / "텍스트를 음성으로 합성(음성 안내)합니다." / "건강 메모를 요약·정리합니다." / "건강 메모를 번역합니다." / "품질 확인을 위해 사람이 내용을 검토합니다." / "AI 모델 개선에 데이터를 사용합니다." |
| 2 | `public_rounded` | "전송 대상 국가" | "{국가명} ({ISO 코드})" (예: "대한민국 (KR)") |
| 3 | `dns_rounded` | "수신자" | "Google Cloud Speech-to-Text (한국 리전)" / "NC AI VARCO 음성합성 (한국)" / "한국 내 AI 처리 서버" / "한국 내 AI 처리 서버 ({backendId})" |
| 4 | `gavel_rounded` | "이전 근거" | 정책별: 적정성 결정 — "대한민국은 EU 적정성 결정 대상국이며 영국–한국 데이터 브리지가 적용됩니다. 이 국제이전은 해당 적정성 결정·데이터 브리지에 근거합니다(별도 표준계약 불필요)." / 계약+동의 — "이전 계약과 동등수준 보호조치, 그리고 귀하의 명시적 동의에 근거하여 데이터를 대한민국으로 이전합니다." / 국내 처리 — "대한민국 내에서 처리되어 국외이전이 발생하지 않습니다." / 이전 불가 — "현재 국가 정책상 대한민국으로의 이전이 허용되지 않습니다." |
| 5 | `timer_outlined` | "보관·삭제" | "음성 오디오는 변환 직후 삭제되며, 광고나 AI 모델 학습에 사용하지 않습니다. 생성된 텍스트·요약은 귀하의 기록 보관 설정을 따르고, 사람이 열람·검토하지 않습니다." |
| 6 | `verified_user_outlined` | "내 권리" | "설정에서 언제든지 이 동의를 철회할 수 있습니다. 철회는 이미 완료된 처리에는 영향을 주지 않으며, 이후의 클라우드 처리는 중단됩니다." |
| 7 | `block_rounded` | "동의하지 않으면" | "동의하지 않아도 앱은 계속 사용할 수 있습니다. 이 기능은 {fallback}(으)로 처리됩니다." (fallback: "기기 내 처리(온디바이스)" / "직접 텍스트 입력" / "기기 내 처리") |

같은 시트를 쓰는 건강 수치 외부 AI 분석 레인(`buildExternalHealthReadConsentNotice`)의 값은 다음과 같습니다.

- 목적: "기록된 건강 수치(측정값·기간·추이)를 외부 AI 모델이 분석하여 요약 리포트를 생성합니다."
- 보관·삭제: "전송되는 내용에는 이름·연락처·식별번호가 포함되지 않으며, 요청마다 가명 처리되어 되돌릴 수 있는 연결 정보를 남기지 않습니다. 전송 사실은 식별정보 없는 이전 기록으로 보관되며, 전송한 내용은 AI 모델 학습에 사용하지 않습니다."
- 내 권리: "설정에서 언제든지 이 동의를 철회할 수 있습니다. 철회하면 이후 외부 AI 분석은 중단되며, 철회 전에 이미 생성된 리포트에는 소급되지 않습니다."
- 동의하지 않으면: "동의하지 않아도 앱은 계속 사용할 수 있습니다. 외부 AI 분석 리포트만 생성되지 않고, 직접 기록한 수치와 기간별 추이는 그대로 열람할 수 있습니다."
- fallback 버튼: "외부 AI 분석 없이 내 기록 직접 열람(으)로 계속"
- 단, 제목과 부제는 시트에 하드코딩된 "음성 AI" 문구가 그대로 표시됩니다. 이 레인에서 제목·부제를 어떻게 다루는지는 **미확인(unresolved)**입니다.

민감도 표시는 행별 배지 없이 부제 문장("민감한 건강정보가 포함될 수 있어")으로만 합니다.

### 2.5 버튼·상태

- "동의하고 패스키로 인증": 항상 활성 → `pop(true)` → 흐름이 패스키 서명을 실행합니다(OS 창). 사유 시트는 다시 띄우지 않습니다.
- "{fallback}(으)로 계속" 또는 시트 닫기: `false`. 기기 내 처리나 텍스트 대체 경로를 유지합니다.
- 로딩·오류 문구는 시트에 없습니다. 패스키나 기록 단계가 실패하면 흐름이 `denialReason: 'passkey_failed' | 'record_failed'`로 거부 처리합니다. 사용자에게 보이는 실패 문구는 **미확인(unresolved)**입니다.

### 2.6 토큰

핸들 `outlineVariant`, 제목 `headlineSmall` w800, 부제 `bodyMedium`+`onSurfaceVariant`, 카드 `surfaceContainerLow`·radius 18·padding 14/6, 행 아이콘 20 `primary`, 라벨 `labelMedium` w700 `onSurfaceVariant`, 값 `bodyMedium`, 패스키 안내 `bodySmall`.

---

## 3. 기관 공유 신청 시트 — `institution_share_sheet.dart` (`showInstitutionShareSheet`)

### 3.1 목적·노출 시점

의료·연구 기관에서 받은 12자리 코드로 공유 조건을 미리 조회하고, 개인 건강 기록 열람 권한의 동의를 신청하는 시트입니다. 진입점은 내 동의 화면(`my_consent_page.dart`)입니다. 신청하면 상태가 `pending`이 되며, 기관이 확인해야 활성화됩니다.

- API: `/access-grants/preview-cohort-code` → `/access-grants/redeem-cohort-code`
- 이 시트의 코드에는 패스키 사유 시트나 `PasskeyPromptGate` 호출이 없습니다. 서버 step-up 핸들러를 거쳐 패스키가 요구되는지는 **미확인(unresolved)**입니다.

### 3.2 레이아웃 (상태에 따라 바뀜)

드래그 핸들이 없고 `SafeArea > SingleChildScrollView(padding L20 T20 R20 B=키보드+24) > Column(stretch, min)` 구조입니다. 이 시트만 기본 Material 위젯을 그대로 써서 카드·아이콘이 없는 평문 목록입니다.

```
 ├─ 제목 titleLarge (덮어쓰기 없음 → w700)            ── 16
 ├─ [완료 상태] 신청 완료 안내(liveRegion)
 └─ [그 외]
    ├─ TextField 코드 입력 (OutlineInputBorder, 대문자 자동, 자동완성 끔)
    │   미리보기 전에만 활성
    ├─ [미리보기 없음] 12 · FilledButton "공유 조건 확인"
    └─ [미리보기 있음] 16
        ├─ 기관명 titleMedium
        ├─ 목적 문장
        ├─ 12 · 공유 항목(scope)별 Text 한 줄씩
        ├─ 이용 기간 / 처리 국가 / 신청 가능 기한
        ├─ [처리 정보 있음] 12 · 처리 기관 / 처리 시스템 / 보관 조건 / (보관 기한)
        ├─ [승인 불가] 승인 불가 안내
        ├─ CheckboxListTile(contentPadding 0) 동의 문장
        ├─ FilledButton "확인한 조건으로 동의 신청"
        └─ TextButton "다른 코드 확인"
 ├─ [처리 중] Padding(12) > CircularProgressIndicator(가운데)
 ├─ [실패] 실패 안내(liveRegion)
 └─ TextButton 닫기 (Material 기본 문구, 한국어 "닫기")
```

### 3.3 문구

| 위치 | 문구 | 키 |
|---|---|---|
| 제목 | "기관 공유 신청" | `institutionShareTitle` |
| 입력 라벨 | "기관에서 받은 코드" | `institutionShareCode` |
| 조회 버튼 | "공유 조건 확인" | `institutionShareReview` |
| 기관명 | {institution} (서버 값) | — |
| 목적 | "아래 기관에 개인 건강 기록을 공유하기 위한 신청입니다." | `institutionSharePurpose` |
| 공유 항목(알려진 scope) | "기관의 건강 기록 열람" (`provider:records:read`) | `institutionShareRecords` |
| 공유 항목(알 수 없는 scope) | "확인되지 않은 동의 범위 (앱에서 이름을 확인할 수 없음): {scope}" | `myConsentCardUnresolvedScope` |
| 이용 기간 | "이용 기간: 기관 확인으로 활성화 후 {days}일" | `institutionShareDuration` |
| 처리 국가 | "처리 국가: {country}" | `institutionShareCountry` |
| 신청 가능 기한 | "신청 가능 기한: {date}" | `institutionShareOfferExpires` |
| 처리 기관 | "처리 기관: {name}" | `institutionShareProcessor` |
| 처리 시스템 | "처리 시스템: {name}" | `institutionShareSoftware` |
| 보관 조건 | "보관 조건: {policy}" | `institutionShareRetention` |
| 보관 기한 | "보관 기한: {date}" | `institutionShareRetainUntil` |
| 승인 불가 경고 | "처리 조건이나 공유 항목을 확인할 수 없어 동의할 수 없습니다. 기관에 현재 코드를 확인해 주세요." | `institutionShareUnavailable` |
| 체크박스 | "기관, 공유 항목, 이용 기간, 처리·보관 조건을 확인하고 동의합니다." | `institutionShareConsent` |
| 주 버튼 | "확인한 조건으로 동의 신청" | `institutionShareApprove` |
| 다시 하기 | "다른 코드 확인" | `institutionShareAgain` |
| 완료 | "동의 신청을 보냈습니다. 기관의 확인을 기다리고 있습니다. 아직 데이터 전달이 완료된 상태는 아닙니다." | `institutionSharePending` |
| 실패 | "조건 조회 또는 신청 결과를 확인하지 못했습니다. 신청을 보냈다면 동의 목록을 먼저 확인해 주세요." | `institutionShareFailed` |
| 닫기 | "닫기" (`MaterialLocalizations.closeButtonLabel`, Flutter 기본 한국어) | — |

날짜 형식은 `DateFormat.yMd(locale).add_Hm()`이며 현지 시간으로 표시합니다(예: `2026. 10. 25. 14:30`).

### 3.4 항목별 내역

- 공유 항목은 scope마다 `Text` 한 줄로 표시하고, 아이콘·민감도 배지·구분선은 없습니다. 앱이 이름을 모르는 scope는 원문 scope 문자열을 그대로 보여 줘서 숨기지 않습니다.
- 기간·국가·기한·처리 기관·시스템·보관은 "라벨: 값" 형식으로 한 줄씩 표시합니다.
- `processing`이 없으면 처리·보관 블록 전체를 숨깁니다. `retainUntil`이 없으면 보관 기한 줄만 숨깁니다.

### 3.5 버튼·상태

| 상태 | 조회 버튼 | 체크박스 | 동의 신청 | 다른 코드 확인 |
|---|---|---|---|---|
| 코드 입력 | 처리 중이 아니면 활성 | — | — | — |
| 미리보기, 미체크 | 숨김 | 활성 | **비활성** | 활성 |
| 미리보기, 체크 | 숨김 | 활성 | **활성** | 활성 |
| `canApprove == false` | 숨김 | **비활성** | **비활성** + 승인 불가 경고 | 활성 |
| 처리 중(`_busy`) | 비활성 | 비활성 | 비활성 | 비활성 + 스피너 |
| 신청 실패 | — | 체크 해제, 미리보기 초기화 | — | — + 실패 문구 |
| 완료 | 입력 영역 전체가 완료 문구로 바뀜 | | | |

- 로딩은 문구 없이 `CircularProgressIndicator`로만 표시합니다.
- 계정·세션이 바뀌면(`sessionChanges`) 입력값과 미리보기를 모두 초기화합니다.
- 같은 미리보기로는 두 번 제출할 수 없습니다(`_submitted`).

### 3.6 토큰

제목 `titleLarge`, 기관명 `titleMedium`, 나머지 기본 `bodyMedium`. TextField는 `OutlineInputBorder()`로 테두리를 지정했지만 radius 값을 넘기지 않아 Flutter 기본 radius 4가 적용됩니다. 테마의 radius 12는 이 테두리에 덮여 적용되지 않는 것으로 **추정**합니다. 버튼과 체크박스는 0.2 테마를 따릅니다.

---

## 4. Tier-2 일괄 동의 / 건강 문서 AI 처리 동의 — `tier2_batch_consent_sheet.dart`

파일 하나에 시트 2개가 있습니다.

### 4A. 국내 서버 분석 일괄 동의 (`showTier2BatchConsentSheet`)

#### 목적·노출 시점

네트워크가 다시 연결되었을 때 오프라인 큐에 기기 OCR로 읽지 못한 사진(식사, 신뢰도가 낮은 판독 등)이 남아 있으면 한 번에 묶어 동의를 받습니다. 동의해야만 암호화된 원본을 복호화해 업로드합니다. 업로드할 항목이 없으면(`hasUploadable == false`) 시트를 띄우지 않고 `false`를 돌려줍니다. 호출부는 `tier2_sync_coordinator.dart`와 `data_collect_sheet.dart`입니다.

#### 레이아웃

```
showModalBottomSheet(showDragHandle: true)
Padding(L20 R20 T4 B=키보드+24) > Column(min, start)
 ├─ 제목 titleLarge w800                                   ── 10
 ├─ 본문 bodyMedium, onSurfaceVariant, height 1.5           ── 16
 ├─ Wrap(spacing 8, runSpacing 8) 유형별 개수 칩 _CountChip
 ├─ [지역 정책으로 기기에만 보관되는 항목 있음] 14 ·
 │   Row(start): Icon(phonelink_lock_outlined, 16, onSurfaceVariant) · 8 ·
 │               Expanded(bodySmall, onSurfaceVariant, height 1.4)
 │                                                          ── 22
 ├─ 주 버튼 FilledButton.icon(cloud_upload_outlined, 18) 전체 폭
 │   (padding 세로 14, 글자 15px w700 — 테마 16px을 덮어씀)  ── 8
 └─ 보조 버튼 TextButton 전체 폭
```

#### 문구

| 위치 | 문구 | 키 |
|---|---|---|
| 제목 | "선택한 자료를 국내 서버에서 분석할까요?" | `tier2BatchTitle` |
| 본문 | "동의하면 선택한 사진·문서 원본을 대한민국 내 UniQdata 서버의 한국어 OCR에 한 번 전달해 값을 읽어요. 처리가 끝나면 서버의 원본은 삭제하고, EXIF를 제거한 압축본만 비공개 개인 보관함에 저장합니다. 결과는 확인 전까지 기록으로 확정되지 않아요." | `tier2BatchBody` |
| 칩 라벨 | "식사" / "문서" / "약" / "기타" + 공백 + 개수 (예: "식사 3") | `tier2TypeMeal` / `tier2TypeDocument` / `tier2TypeMedication` / `tier2TypeOther` |
| 지역 정책 안내 | "일부 사진은 이 지역 정책상 기기에만 보관되고 서버로 보내지 않아요." | `tier2BatchResidencyNote` |
| 주 버튼 | "국내 서버에서 분석" | `tier2BatchAgree` |
| 보조 버튼 | "나중에" | `tier2BatchLater` |

#### 항목별 내역

캡처 유형별 개수를 알약 모양 칩으로 보여 줍니다(`_CountChip`).

- 모양: padding 가로 12 / 세로 7, radius 999, 배경 `primaryContainer` 40% 불투명도, 글자 `labelLarge` w700 `onPrimaryContainer`
- 유형 매핑: `meal`→식사, `doc`/`document`→문서, `pill`/`med`/`medication`→약, 그 외→기타
- 지역 정책 때문에 업로드할 수 없는 항목은 칩에 넣지 않고, 아래 자물쇠 아이콘 안내 한 줄로만 알립니다.

#### 버튼·상태

두 버튼 모두 항상 활성이며 체크박스는 없습니다. 주 버튼은 `true`, "나중에"와 시트 닫기는 `false`를 돌려줍니다. 로딩·오류 문구는 시트에 없습니다. 이 시트는 패스키를 호출하지 않습니다.

### 4B. 건강 문서 AI 처리 동의 — Upstage OCR (`showDataQFileKrProcessingConsentSheet`)

#### 목적·노출 시점

유효한 v2 동의가 없을 때 한 번 받는 상시 동의입니다. 브라우저 파일 선택이 끝난 뒤, 선택한 원본을 KR Core로 올리기 전에 띄웁니다. 처리 기업(Upstage)을 명시합니다.

#### 레이아웃

```
showModalBottomSheet(showDragHandle: true)
SingleChildScrollView(padding L20 T4 R20 B=키보드+24) > Column(min, start)
 ├─ Row(start): Icon(document_scanner_outlined, primary) · 10 ·
 │              Expanded(제목 titleLarge w800)                ── 14
 ├─ 본문 bodyMedium height 1.5                                 ── 12
 ├─ _ConsentDetail(lock_outline)        전송 데이터            ── 8
 ├─ _ConsentDetail(fact_check_outlined) 결과 검토              ── 8
 ├─ _ConsentDetail(policy_outlined)     약관·거부 시           ── 22
 ├─ 주 버튼 FilledButton 전체 폭                               ── 8
 └─ 보조 버튼 OutlinedButton 전체 폭
```

`_ConsentDetail`은 `Row(start)` 안에 Icon(18, onSurfaceVariant), 간격 8, Expanded(bodySmall, onSurfaceVariant, height 1.45)를 배치합니다.

#### 문구

| 위치 | 문구 | 키 |
|---|---|---|
| 제목 | "건강 문서 AI 처리를 허용할까요?" | `dataqUpstageOcrConsentTitle` |
| 본문 | "한 번 동의하면 앞으로 직접 분석을 요청한 건강 문서를 대한민국 AI 기업 Upstage의 문서 OCR로 읽어요. 동의 관리에서 언제든 철회할 수 있습니다." | `dataqUpstageOcrConsentBody` |
| 전송 데이터 | "원본에서 EXIF를 제거하고 최대 3000px JPEG로 압축한 파생본만 전송합니다. 계정 정보·연락처·인증 정보는 보내지 않아요." | `dataqUpstageOcrConsentData` |
| 결과 검토 | "약 이름과 가능한 처방 목적·증상은 확인 전 후보이며 진단이 아닙니다. 직접 확인한 내용만 건강 기록에 반영할 수 있어요." | `dataqUpstageOcrConsentReview` |
| 약관·거부 시 | "처리 목적과 공급자는 이용약관·개인정보 처리방침에서도 확인할 수 있습니다. 동의하지 않아도 파일 저장과 직접 기록을 계속 이용할 수 있어요." | `dataqUpstageOcrConsentTerms` |
| 주 버튼 | "AI 처리에 동의하고 계속" | `dataqUpstageOcrConsentAgree` |
| 보조 버튼 | "AI 없이 파일만 저장" | `dataqUpstageOcrConsentStorageOnly` |

#### 버튼·상태

두 버튼 모두 항상 활성이며 체크박스는 없습니다. 보조 버튼은 이 시트에서만 TextButton이 아닌 **OutlinedButton**을 써서, 거부 선택지인 "AI 없이 파일만 저장"을 동등한 무게로 보여 줍니다. 패스키는 호출하지 않습니다.

---

## 5. 시트별 요약 비교

| | 패스키 사유 | 해외 음성 AI | 기관 공유 | Tier-2 일괄 | Upstage OCR |
|---|---|---|---|---|---|
| 핸들 | 직접 그림 42×4 (다이얼로그형은 없음) | 직접 그림 42×4 | 없음 | 프레임워크 기본 | 프레임워크 기본 |
| 제목 스타일 | headlineSmall w800 | headlineSmall w800 | titleLarge | titleLarge w800 | titleLarge w800 + 아이콘 |
| 항목 표현 | 없음 | 아이콘+라벨+값 카드 7행 | 평문 줄 목록 | 개수 칩 | 아이콘+설명 3줄 |
| 체크박스 | 없음 | 없음 | 있음(필수) | 없음 | 없음 |
| 주 버튼 아이콘 | lock_open_rounded | lock_open_rounded | 없음 | cloud_upload_outlined | 없음 |
| 거부 버튼 | TextButton "취소" | TextButton "{대체}(으)로 계속" | TextButton "다른 코드 확인" + "닫기" | TextButton "나중에" | OutlinedButton "AI 없이 파일만 저장" |
| 패스키 | 호출 직전 사유 안내 | 동의 후 서명(사유 시트 생략) | 코드에 없음(미확인) | 없음 | 없음 |
| 로딩·오류 | 없음 | 없음(흐름이 처리) | 스피너 + 실패 문구 | 없음 | 없음 |

---

## 6. 재사용할 공통 패턴

**구조 (하단 시트, 위에서 아래로)**

1. **드래그 핸들**: 42×4, 알약형, `outlineVariant`, 아래 18
2. **제목**: 질문형이거나 "~ 동의/확인"으로 끝나는 짧은 문장. `headlineSmall`(패스키·서명 계열) 또는 `titleLarge`(데이터 처리 계열), 굵기 **w800**
3. **부제·본문**: 무엇을 어디서 처리하는지 한두 문장. `bodyMedium`/`bodyLarge`, 색 `onSurfaceVariant`, 행간 1.5
4. **공시 카드**: `surfaceContainerLow` 배경, radius 18, 행마다 primary 아이콘(20) + 회색 라벨(labelMedium w700) + 값(bodyMedium). 항목 순서는 **처리 목적 → 대상 국가 → 수신자 → 이전 근거 → 보관·삭제 → 내 권리 → 동의하지 않으면**
5. **보조 안내**: 지역 정책이나 예외는 회색 작은 아이콘(16~18)과 `bodySmall` 회색 한 줄
6. **패스키 안내 박스**: `surfaceContainerLow`, radius 18, padding 14, 지문 아이콘(primary) + "동의하면/계속하면 패스키(생체·PIN)…" 문장
7. **주 버튼**: 전체 폭 `FilledButton`, radius 12, 16px w700. 패스키가 이어지면 `lock_open_rounded` 아이콘을 붙이고 문구에 "패스키로"를 넣음
8. **거부 버튼**: 주 버튼 아래 8, 전체 폭 `TextButton`(또는 대등한 선택지면 `OutlinedButton`). 문구는 거부했을 때의 결과를 직접 말함("나중에", "취소", "AI 없이 파일만 저장", "{대체}(으)로 계속")
9. **간격 리듬**: 좌우 20 · 블록 사이 16~18 · 제목과 부제 8~10 · 버튼 위 18~22 · 버튼 사이 8 · 아래 키보드+24~28

**문구 규칙**

- 존댓말을 쓰되, 설명은 "~해요/~않아요"(부드러운 해요체), 법적 고지는 "~합니다/~됩니다"(합쇼체)를 섞어 씀
- 거부해도 앱을 계속 쓸 수 있다는 점을 반드시 밝힘("동의하지 않아도 … 계속 이용할 수 있어요/있습니다")
- 철회 경로를 알림("설정에서/동의 관리에서 언제든 철회할 수 있습니다")
- 학습·광고 미사용, 원본 삭제, EXIF 제거처럼 **하지 않는 일**을 구체적으로 적음
- AI 결과는 "확인 전 후보이며 진단이 아닙니다"처럼 확정이 아님을 밝힘
- 체크박스가 있다면 확인한 항목을 문장에 나열함("기관, 공유 항목, 이용 기간, 처리·보관 조건을 확인하고 동의합니다.")
- 완료 문구는 실제 상태만 말함("신청을 보냈습니다 … 아직 데이터 전달이 완료된 상태는 아닙니다.")
- 실패 문구는 중복 제출을 막는 다음 행동을 안내함("신청을 보냈다면 동의 목록을 먼저 확인해 주세요.")
- 패스키는 항상 "패스키(생체·PIN)"로 표기하고, 인증 창이 열린다는 사실을 미리 알림

**동작 규칙**

- 시트를 그냥 닫으면 거부로 처리함(`false`)
- 체크박스가 있는 화면은 체크 전까지 주 버튼을 비활성으로 둠. 조건을 확인할 수 없으면(`canApprove == false`) 체크박스와 주 버튼을 모두 비활성으로 하고 이유를 표시함
- 패스키 사유 안내는 OS 창 직전에 한 번만 띄움. 이미 동의 화면에서 패스키를 안내했다면 사유 시트를 다시 띄우지 않음
- 화면 낭독기 사용자를 위해 상태 문구(완료·실패)는 `Semantics(liveRegion: true)`로 알림

**미확인 항목(unresolved)**

- 시드에서 계산되는 `surfaceContainerLow`, `outlineVariant`, `onSurfaceVariant`, `primaryContainer`, `onPrimaryContainer`의 정확한 hex 값
- 타이포 크기·행간(앱이 지정하지 않아 Flutter M3 기본값으로 추정)
- 기관 공유 신청 승인 시 서버 step-up 패스키가 요구되는지 여부
- 해외 동의 흐름이 실패했을 때 사용자에게 보이는 문구
- 건강 수치 외부 AI 레인에서 시트 제목·부제("음성 AI" 하드코딩)를 어떻게 다루는지
