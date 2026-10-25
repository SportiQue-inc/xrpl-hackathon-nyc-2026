# Reuse log

Hackathon rules allow building on existing projects; only work done during the event
is judged. This file lists everything brought in from earlier SportiQue work.

| Date | Source | Version / commit | What was reused | Why |
|------|--------|------------------|-----------------|-----|
| 2026-10-25 | SportiQue UniQdata backend, UniQLab backend | UniQdata `main` @ f9a54fcd5 (local checkout) | Interface shapes only, no code copied: UniQdata consent lane names (`research_participation`, `sensitive_health_collection`), the rule that paid and pending research rewards stay after revoke, `privacy_epoch` with `supersede_for_privacy_boundary`, `withdraw_enrollment` audit fields (`deletion_type`, `records_deleted`, `tables_affected`); UniQLab `payout_receipt` fields (`receipt_ref_hash`, `amount_minor`, `currency`, `status`). New code written here: `agentrail/uniqdata_port.py`, `tests/test_uniqdata_port.py` | Show where the engine plugs into the production participant app and researcher workspace without importing their code |
| 2026-10-25 | AP4M hackathon SDK and examples (Mastercard Agent Pay for Machines) | as distributed to hackathon participants, vendored in `ap4m/vendor/` | The SDK (`ap4m-hackathon-sdk.*`, `ap4m-sdk.tgz`, `ap4m-x402.mjs`), its README and example agent/merchant, unchanged | Third-party SDK the AP4M bounty requires; our own code is `ap4m/agent.mjs`, `ap4m/merchant.mjs`, `ap4m/lib/`, `ap4m/test/` |

Rules:
- 2026-10-25 UniQdata presentation: reused the unchanged brand SVG from `UniQdata/landing` commit `7528f272ed3239af2c7370322911a6fc09814d79` (`public/brand/uniqdata-logo.svg`). The interface follows the existing five navigation labels and color values in `UniQdata/app` commit `fc224c9c13bc572d5f43aaea9d21ae270f4a980a` (`figma_tokens.dart`); no Flutter application code, production configuration, or personal data was copied. The web screen and presenter controls are new hackathon work.
- Add a row in the same commit that imports the code.
- Imported code goes in its own commit, separate from new hackathon work.
- No secrets, real user data or production configuration may be imported.
