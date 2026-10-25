# UniQdata app — real screens (research consent sheet)

Captured on 2026-10-25 from the UniQdata Flutter app (iPhone 17 Pro simulator, demo build
`UNIQDATA_RESEARCH_CONSENT_DEMO=true`). All studies, institutions and participants are synthetic.
App code: UniQdata/app branch `feat/research-consent-sheet-rlusd` (draft PR #927).

**01–09: static synthetic studies (no server)**

| File | Step |
| --- | --- |
| 01_list.png | Research tab: recruiting studies with the participation payment in RLUSD |
| 02_list_selected.png | Two studies selected; one button opens one sheet for both (21.50 RLUSD) |
| 03_sheet_over_page_locked_checkbox.png | Consent sheet over the page: pinned institution, sub-project, RLUSD amount, period, purpose, IRB; agree box locked |
| 04_clause_scrolling_locked.png | Reading the clauses; the agree box stays locked until the end |
| 05_clause_read_checked.png | Read to the end, agree checked, Next enabled |
| 06_sign_page.png | Sign page: the institution with each sub-project's amount, period and consents |
| 07_sign_page_passkey_notice.png | Sign page notice: one passkey signature covers the relationship with the institution; each consent recorded separately |
| 08_demo_passkey_prompt.png | Demo passkey prompt (labelled demo) |
| 09_after_sign.png | After signing: "6 consents recorded separately" |

**10–15: local hackathon engine (AgentRail, mock ledger), batch approval with one signature**

| File | Step |
| --- | --- |
| 10_engine_list.png | The tab loads participant P-017's pending requests from the engine |
| 11_engine_two_selected.png | Both requests selected (1.20 RLUSD) |
| 12_engine_sheet.png | Sheet for the engine's institution (Northside Sleep Lab), request #17 |
| 13_engine_sign_page.png | Sign page: requests #17 and #66 under one institution |
| 14_engine_passkey_prompt.png | One signature (demo software key) for 6 consents |
| 15_engine_after_batch_approve.png | Engine approved both requests; nothing left pending |
| batch_approval_flow_small.mp4 | Screen recording of the whole engine flow (select → 6 consent pages → one signature → approved) |
