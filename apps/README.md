# Research contribution pages

Two pages built from the Figma file "연구 기여 - English" and the designer brief, on one engine.
All data is synthetic; payments run on XRPL Testnet or the practice (mock) ledger.

| Page | Served at | Screens |
|---|---|---|
| Researcher console | `/console` | Participants overview, directory and detail (Figma 56:12480, 56:12554, 56:12628, study selector 59:12377-12379), Rounds: goal, proposal checked by code, budget approval by 2 signers, send (R1), Study details with IRB number (R2) |
| Participant app | `/participant?pid=P-017` | Participation request (P1), consent by purpose (P2), preview and weekly status (P3), payment timeline with the 20% review part (P4), stop or withdraw (P5), review notice (P6) |

Both open the same ledger receipt panel (R3) from every `Tx … · View ↗` link, and both poll
`GET /api/events` once a second, so an action on one shows on the other.

## One source, two targets

There is no build step. `apps/shared/` holds plain ES modules and one stylesheet scoped under `.ar`:

- `api.js`: engine client and the event poller
- `ui.js`: DOM helpers, shared wording (week states, payment states), the receipt panel
- `researcher.js`: `mountResearcher(el, { base, embedded })`
- `participant.js`: `mountParticipant(el, { base, pid, embedded })`
- `ui.css`: tokens from the Figma file

Target A (this repo): `apps/researcher/index.html` and `apps/participant/index.html` mount the modules.
Run `uvicorn agentrail.web:app` and open `/console` and `/participant` side by side.

Target B (UniQLab researcher workspace): a page in UniQLab imports
`${VITE_AGENTRAIL_API_URL}/apps/shared/researcher.js` at runtime and mounts it with `embedded: true`,
which drops our own sidebar and top bar so UniQLab's layout stays. The engine allows that origin
through `AGENTRAIL_CORS_ORIGINS`. The UniQLab change (a route `/research/participants`, a sidebar item
and the wrapper page) is kept as a patch outside this repo until the UniQLab owner applies it.

For the UniQdata participant app, the participant page can open in the app's existing in-app WebView
(`flutter_inappwebview`) as a mini app entry, with `?pid=` set to the signed-in participant's study
number. That change is described, not made.

## Wording

`tests/test_apps.py` fails if any page text uses a word the project does not show (for example
reward, RLU, sell, anonymous, fraud, penalty, 리워드, 데이터 판매, 토큰 보상, 재식별 불가, 질병 예측,
의료 AI 진단). Engine field names the client reads are not page text and are skipped.
