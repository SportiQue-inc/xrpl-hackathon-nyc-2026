# Research contract runs, 2026-10-25

Two live runs of research contracts on https://agentrail-try-production.up.railway.app.

- Test accounts only. No real health data: readings are generated test data, labelled as such.
- Delivery records run on `LEDGER=mock`. Payments go through AP4M on XRPL EVM Testnet, one Voucher per member-week, at most 0.10 RLUSD each.
- Amounts in the JSON files are millionths of the unit (`10000` = 0.01 RLUSD).
- Times are UTC.
- Keys, tokens and invite codes are not in these files.

## RC1-ec4083: sleep and fatigue, 3 weeks

Build c4ae56b (#80). The service had no volume, so the contract was removed from the server at the next deploy. These files are the record.

| | |
|---|---|
| Terms | `sleep.daily` + `fatigue.survey`, weeks 1–3, 0.01 RLUSD per item (0.02 per member-week), budget 1.00 RLUSD, rounds every 60 s |
| Posted | 15:44:33 |
| Closed | about 16:03 (status `closed` seen at 16:03:22) |
| Members | 11 joined (10 test accounts + daniel, `auto_all`), 0 failed; 9 active at close |

| Week | Round recorded | Delivered | Needs approval |
|---|---|---|---|
| 1 | 15:52:52 | 10 | 1 |
| 2 | 15:57:17 | 8 | 1 |
| 3 | 16:01:37 | 8 | 1 |

"Needs approval" is the one test account that chose `confirm_each`. Nobody approved it in this run.

**Payments: 24 of 26 paid.** 0.48 RLUSD was paid and 0.04 RLUSD was not.

| Unpaid order | Slot | Reason |
|---|---|---|
| 12 | RC1-378feaba week 2 | `payment error: purchase outcome unavailable (HTTP 503); resume the same operation`. This happened while the AP4M rail service restarted, at about 15:54. |
| 26 | RC1-dd40fe54 week 3 | `not attempted yet`. The contract closed before this payment was tried. |

These two were not re-run: this build has no retry endpoint, and running a week again could create duplicate orders.

Order 2 first failed with "Merchant store belongs to another configuration" and was paid on a later retry.

Withdrawals happened after week 1 and before week 2:

- test 03 (RC1-75db28a3) at 15:52:57
- test 05 (RC1-4db4d4f8) at 15:53:15

Each has only its week 1 order and payment (orders 5 and 4). Neither has an order or a payment for weeks 2–3.

`receipt_url` was `null` on every paid order, including after close.

Sample AP4M Voucher redemptions:

- order 1: https://explorer.testnet.xrplevm.org/tx/0x451d3682fa655e0741a67518af6b4c883b4ea8f0421339699e89b1c45f11d044
- order 2: https://explorer.testnet.xrplevm.org/tx/0xb80a9377681a6319786198905e4bb0f3def4c846c1aad456be4022f015187d95
- order 3: https://explorer.testnet.xrplevm.org/tx/0x2e66a0f34f990d5193013cb4835b98c081cdd8442c228aeae6167794b7448209

Files:

- `rc1-ec4083_console.json`: the researcher console after close
- `rc1-ec4083_p05_before_withdraw.json`, `rc1-ec4083_p05_after_withdraw.json`: test 05's own view, before and after its withdrawal

## RC1-16b39a: sleep diary, 2 weeks, 50 test accounts

Build 9c18498 (dashboard thread, includes #86 and #91). The contracts database is on the `/data` volume.

| | |
|---|---|
| Terms | `sleep.daily`, weeks 1–2, 0.01 RLUSD per member-week, budget 1.50 RLUSD, rounds every 60 s |
| Posted | 16:12:38 |
| Members | 51 joined (50 test accounts + daniel50, `auto_all`), 0 failed |

Payments were made one after another. In week 1, the first 12 took about 31 s each (16:13:51 to 16:20:07).

Status at the time of this snapshot (`rc1-16b39a_console_partial.json`, contract still open):

| Week | Round recorded | Delivered | Needs approval |
|---|---|---|---|
| 1 | 16:35:51 | 46 | 5 |

- Payments: 71 paid (0.71 RLUSD), 3 unpaid (0.03 RLUSD):

| Unpaid order | Slot | Reason |
|---|---|---|
| 35 | RC1-8cc259f9 week 1 | `payment error: purchase outcome unavailable (HTTP 409); resume the same operation` |
| 70 | RC1-5a94f196 week 2 | `payment error: purchase outcome unavailable (HTTP 503); resume the same operation` |
| 74 | RC1-6c91191d week 2 | `not attempted yet` |

- `receipt_url` was filled on 2 paid orders so far.

Sample AP4M Voucher redemptions:

- https://explorer.testnet.xrplevm.org/tx/0x6af884c9daf6b28a51b8ead33774b99c519e8363a3557dc3337b3e4e17720300
- https://explorer.testnet.xrplevm.org/tx/0x230daa0fe16b5596ccf5875045a4ff3a0ee890593e4c44173e0de607842a1bcb
- https://explorer.testnet.xrplevm.org/tx/0xf50bf35268a8e571db56b5832947f0c3058f5d91acc07540ec5c8db10aeccaa7

Files:

- `rc1-16b39a_console_partial.json`: the researcher console while open
- `daniel50_view.json`: daniel50's own view (pid RC1-4dbb6c1d)
