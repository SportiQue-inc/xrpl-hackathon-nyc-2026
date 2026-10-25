# Research contribution pages

Two pages built from the Figma file "연구 기여 - English" and the designer brief, on one engine.
All data is synthetic; payments run on XRPL Testnet or the practice (mock) ledger.

| Page | Served at | Screens |
|---|---|---|
| Researcher console | `/console` | Participants overview, directory and detail (Figma 56:12480, 56:12554, 56:12628, study selector 59:12377-12379), Rounds: goal, proposal checked by code, budget approval by 2 signers, send (R1), Study details with IRB number (R2) |
| Participant app | `/participant?pid=P-017` | Participation request (P1), consent by purpose (P2), preview and weekly status (P3), payment timeline with the 20% review part (P4), stop or withdraw (P5), review notice (P6) |

Both open the same ledger receipt panel (R3) from every `Tx … · View ↗` link. The console polls
`GET /api/events` once a second and the participant app polls its own view, so an action on one shows on
the other.

Every call carries a bearer token for one role (researcher, each approver, reviewer, the participant,
the operator for reset). On a dev engine the pages get them from `/api/dev/login/{sub}`; a host app
passes `token: async (sub) => ...` to the mount function instead. The budget step opens an approval and
each signer signs on their own device; the page shows "1 of 2 signed, waiting" until both have.

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
which drops our own sidebar and top bar so UniQLab's layout stays. List UniQLab's origin in
`AGENTRAIL_CORS_ORIGINS` on the engine. The UniQLab change (a route `/research/participants`, a sidebar item
and the wrapper page) is kept as a patch outside this repo until the UniQLab owner applies it.

For the UniQdata participant app, the participant page can open in the app's existing in-app WebView
(`flutter_inappwebview`) as a mini app entry, with `?pid=` set to the signed-in participant's study
number. That change is described, not made.

## Wording

`tests/test_apps.py` fails if any page text uses a word the project does not show (for example
reward, RLU, sell, anonymous, fraud, penalty, 리워드, 데이터 판매, 토큰 보상, 재식별 불가, 질병 예측,
의료 AI 진단). Engine field names the client reads are not page text and are skipped.

## Before/after demo (`/demo`)

A clickable stage for the before/after video: UniQLab (researcher, desktop) next to UniQdata (participant,
phone), linked live. A click on one side shows up on the other (same browser, via `BroadcastChannel`, so it
also works with the two pages in separate windows). Static pages with synthetic data in `apps/demo/`, no
engine calls, so a recording never depends on ledger timing. Amounts are RLUSD.

| Mode | UniQLab | UniQdata |
|---|---|---|
| `?mode=before` (today) | Three projects at one lab, each with its own contract, IRB and recruiting · lifecycle stuck on "Waiting for participants" with a day counter · applicant queue · linking code sent by text · data table with a missing week and no way to ask for it · monthly settlement batch | Browse all 41 studies · type the linking code · two full-screen consent forms per project · 18 approvals (every item, every week) |
| `?mode=after` (with agents) | One institution relationship per person with several sub-projects under it, and what that saves · study agent finds the exact gaps across sub-projects and asks only those people's agents · weekly delivery paid per delivered week · add a sub-project with no new contract | My agent: rules set once, only matched studies · one bottom sheet (top of the screen stays visible) with the amount pinned and one passkey for the batch · late week and new purpose asked in a small sheet · weekly sends and RLUSD paid |

Open `/demo?mode=before` or `/demo?mode=after`; `&show=lab` or `&show=phone` shows one side only.
"Start over" resets both pages. Each page also opens alone: `/apps/demo/lab.html?mode=after&view=agent`,
`/apps/demo/phone.html?mode=after`.

## Try it on the real engine (`/try`, `/live`)

`/try` lets a visitor pick a role. **Researcher** opens `/apps/live/`: the person → institution → sub-projects
structure, the 50-person cohort week by week, buttons that run the study (agent finds gaps, budget co-signed
by 2 with demo keys, send requests, close the week, create a sub-project under the scope, run a round), and a
live transaction log with tx hashes. **Participant** opens `/apps/live/me.html?pid=…` (one of the 50, assigned
per browser): one relationship with the institution, each sub-project's payouts under it, and only
outside-scope or T3 items asked. The page seeds four sub-projects on first load.

Access: on localhost everything works. On a public deploy, set `AGENTRAIL_SANDBOX_CODE` (8+ characters).
Visitors who enter it (or open `/try?code=…`) act through the demo devices; everyone else gets the read-only
`/api/public/live` view. The operator (reset, scene runner) stays localhost-only either way.

Sandbox limit: the code is one shared demo key. Anyone holding it can sign in as any participant or
institution role except the operator, including both budget co-signers, so one visitor can play both
signers of the 2-of-2 approval. So the engine accepts the code only on the mock ledger (on
Testnet only with `AGENTRAIL_SANDBOX_ALLOW_TESTNET=1`, since a code holder could co-sign repeated top-ups) and
never with `AGENTRAIL_ENV=prod`. Use 16+ random characters, rotate it after the event, and never set
`FORWARDED_ALLOW_IPS=*` (it would let anyone pose as localhost). Never set `AGENTRAIL_SANDBOX_CODE` on a deployment that holds real people, real keys or real money.

Deploy as a second Railway service from this repo: config file `railway.engine.json`
(builds `docker/engine.Dockerfile`), variables `AGENTRAIL_SANDBOX_CODE`, `LEDGER` (`mock` or `testnet`) and,
for the token unit, the build thread's settlement variables.
