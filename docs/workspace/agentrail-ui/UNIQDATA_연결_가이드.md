# AgentRail 연구 기여 화면을 UniQLab·UniQdata에 붙이는 방법

아직 아무 저장소에도 적용하지 않았습니다. 적용하려면 daniel의 승인이 필요합니다.

## 1. UniQLab 웹 (연구자 화면) — 패치 준비됨

파일: `uniqlab-agentrail-participants.patch` (UniQLab `web` @ 00de0ca1 기준)

바뀌는 것
- `src/research-studio-ui/pages/ResearchParticipantsPage.tsx` 새 파일: 엔진 주소에서 `apps/shared/researcher.js`를 불러와 `embedded` 모드로 띄움. UniQLab 사이드바와 헤더는 그대로.
- `src/App.tsx`: `/research/participants` 경로 추가 (`ResearchStudioRoute` 안).
- `Sidebar.tsx`: "연구 생애주기" 아래에 "참여자 · 연구 기여" 메뉴 추가.

적용 순서
1. UniQLab `web`에서 새 브랜치를 만들고 `git apply uniqlab-agentrail-participants.patch` (작업 폴더 `web` 기준, `-p1`).
2. `.env.local`에 `VITE_AGENTRAIL_API_URL=http://localhost:8000` 추가.
3. 엔진 실행: 해커톤 저장소에서 `uvicorn agentrail.web:app --port 8000`. 다른 주소에서 띄우면 `AGENTRAIL_CORS_ORIGINS`에 그 주소를 넣음.
4. `npm run dev` 후 `/research/participants`.

연구 생애주기 화면에 잠겨 있는 단계(참여자 모집, 동의·온보딩, 데이터 수집, 누락 모니터링)가 이 화면이 채우는 자리입니다.

## 2. UniQdata 앱 (참여자 화면) — 설계만

UniQdata 앱에는 이미 `flutter_inappwebview`와 미니앱 등록부(`lib/core/mini_app/mini_app_registry.dart`)가 있습니다. 권장 방식:
- `partnerInnovationDemo`처럼 빌드 플래그로 켜는 미니앱 하나를 추가하고, 연구 참여 화면(`AppRoutes.research`)에서 진입.
- WebView 주소: `{엔진}/participant?pid={연구 참여 번호}`. 실명이나 계정 ID는 넘기지 않음.
- 동의 기록은 엔진 `GET /api/p/{pid}/uniqdata`가 UniQdata 동의 레인(`research_participation`, `sensitive_health_collection`) 모양으로 돌려줌. 국외 이전 동의처럼 UniQdata에 레인이 없는 동의는 막힘.

Dart 코드는 빌드해 보지 못해 아직 쓰지 않았습니다.
