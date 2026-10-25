# AgentRail × AP4M: the participant's agent pays per export call

This folder is the Mastercard AP4M bounty integration for AgentRail. A participant's agent gets the task
"contribute P-017 weeks 3-5 to study SLEEP-01". For each week it requests a synthetic clinic record export.
The merchant answers HTTP 402 with an offer, and the agent decides by itself whether to pay: no human prompt.
A paid call settles as participation compensation in RLUSD to the merchant payout wallet, using the AP4M
x402 toolkit.

**This runs on XRPL EVM Testnet (chain ID 1449000), not on the XRPL ledger used by the rest of AgentRail.**
All data is synthetic.

## What happens in one run

1. `merchant.mjs` serves `GET /export/:pseudonym/:week`. Without payment it answers **402** with an offer: price
   per call (0.05 RLUSD), `pay_to` = the merchant payout address, purpose (`SLEEP-01`, DUO `HMB`), the items
   (resting heart rate, fatigue score) and the x402 resource URL to pay.
2. `agent.mjs` applies a deterministic policy to each offer and logs one decision line with the reason:
   - payee is in the allowlist (default: `MERCHANT_PAYOUT`)
   - price <= per-call cap (`PER_CALL_CAP_RLUSD`, default 0.10)
   - running total <= delegated budget (`BUDGET_RLUSD`, default 0.20)
   - purpose and items match the participant's consent (study SLEEP-01, DUO HMB, P-017, consented items only)
3. To pay, the agent uses the SDK: `signIn` → `requestChannel` (cap = budget, or reuse `CHANNEL_ID`) →
   `buyResource` (signs the EIP-712 Voucher; the merchant redeems it on-chain, which emits `VoucherRedeemed`) →
   `POST /public/participant/record-redemption` → `settle` (payout tx, settlement tx, receipt URL).
   The SDK gets the approved offer price as `maximumAmount`, so a separate 402 challenge cannot charge more
   than the policy approved. The agent also checks the on-chain channel payout against the allowlist and offer.
4. The package is a study-only pseudonym, study-relative days in place of calendar dates, and only the
   requested items, plus its sha256. The agent recomputes the hash and rejects a package that does not match.
5. Scripted refusal: a fourth request (week 6, 0.50 RLUSD) is above the cap. The agent refuses it and pays nothing.
6. The agent writes `out/run-<timestamp>.json`: every decision and reason, `VoucherRedeemed` tx hashes,
   claim IDs, the record-redemption response, the settlement result and receipt URL, the payout wallet's RLUSD
   balance before and after (read on chain with `balanceOf` on the x402 token), and explorer links.

### Why each package has its own port

The SDK's `createX402Merchant` sells exactly one fixed-price `GET /resource`. `merchant.mjs` therefore keeps
`/export/:pseudonym/:week` as the offer endpoint and starts one x402 instance per package on
`MERCHANT_PORT + 1 + n` (4401 to 4404 by default). The offer's `resource_url` points at that instance.

## How this differs from the T54 path

| | T54 path (`agentrail/ledger/x402_rail.py`) | AP4M path (this folder) |
|---|---|---|
| Ledger | XRPL L1 | XRPL EVM Testnet, chain 1449000 |
| Payment | XRP `Payment`, presigned, submitted by the T54 facilitator | Channel opened from a funded budget; EIP-712 Voucher per call, cumulative per Channel |
| On-chain step | the XRP Payment itself | merchant redeems the Voucher on the PaymentLedger contract (`VoucherRedeemed`) |
| Settlement | the Payment | the AP4M service pays RLUSD from the vault to the merchant payout address (`settle` returns the payout tx and receipt) |

The two paths share no code. Nothing here touches `agentrail/`, `xrpl_checks/` or the XRPL wallets.

## Commands

```bash
cd ap4m
npm test                  # node:test, no network, no packages needed
DRY_RUN=1 ./run-live.sh   # no network: fake signer, fake redeem, same decision logs
npm install               # live only: ethers 6.17.0 and the vendored AP4M SDK (vendor/ap4m-sdk.tgz)
./run-live.sh             # live run on XRPL EVM Testnet
```

If Node reports `fetch failed` with connection timeouts while curl can reach the AP4M service, this Mac's
IPv4 transport was verified with the following per-run setting (also applies to the child Agent/Merchant):

```bash
NODE_OPTIONS='--no-network-family-autoselection --dns-result-order=ipv4first' ./run-live.sh
```

`npm test` covers: pays within cap, refuses over cap, refuses unknown payee, refuses after budget exhausted,
rejects a tampered package hash, refuses an off-consent purpose or item.

## Setup daniel must do before a live run

1. Prepare three separate wallets: the Agent, the merchant payout recipient, and the merchant submitter
   (which pays gas to redeem vouchers). The payout address receives test RLUSD settlement; it is not a
   hackathon prize-payment setting. Keep private keys on the Mac, outside chat and Git.
2. Fund the Agent wallet and the merchant submitter wallet with XRP for gas from the XRPL EVM Testnet faucet
   (`https://faucet.testevm.ripple.com` per the SDK files; the developer guide links `https://faucet.xrplevm.org/`).
   The Agent pays gas for `requestChannel`; the submitter pays gas for redemptions. The payout wallet must be
   a different wallet from the Agent and funding wallets (the agent refuses to start otherwise).
3. On the participant portal (`https://hackathon.ap4m.build/participant`, My setup tab): register and sign
   for the Agent, set up the team Merchant and its payout address, and fund the RLUSD budget. Use the exact
   registered team name and a registered funding or Agent wallet to sign in.
4. If `.env` does not exist, copy `.env.example` to `.env`. Fill in `TEAM_NAME`, `AGENT_PRIVATE_KEY`,
   `MERCHANT_ID`, `MERCHANT_PAYOUT`, and `MERCHANT_SUBMITTER_KEY`. The portal's Quick Start `ap4m-agent.js`
   (Demo 1) also contains `TEAM_NAME`, `AP4M_API_URL`, and an open `CHANNEL_ID`: copy those values to reuse
   that channel instead of opening another. Without a channel to reuse, leave `CHANNEL_ID` unset.
   Keep `.env` git-ignored and readable only by its owner (`chmod 600 .env`).
5. On the Mac: `cd ~/Developer/xrpl-ap4m/ap4m && npm install`. This installs the vendored external AP4M SDK
   and ethers; installation alone does not establish portal registration, funding, or a successful payment.

Setup is complete only after the wallet roles, gas, portal registration, funded budget, `.env`, and installed
dependencies have been checked. A live run is a separate check: collect `VoucherRedeemed`, settlement and payout
transaction hashes, and the on-chain payout balance change before claiming AP4M live success.

If `state/agent/purchase.json` contains an unresolved purchase, the agent stops before signing in or opening
another channel. Resume that purchase with its original SDK intent (same operation, channel, URL and maximum
amount), keeping the merchant state intact. Do not delete the state to restart. Automatic task recovery is not implemented.

## 3-minute live demo

1. (0:00) Show the task and policy: `agent.mjs` top, cap 0.10, budget 0.20, allowlist = our payout wallet,
   consent = SLEEP-01 / HMB.
2. (0:30) `./run-live.sh`. Point at the four decision lines as they print: three PAY with the reason, one REFUSE
   ("price 0.5 RLUSD exceeds per-call cap 0.1 RLUSD"), no payment for it.
3. (1:30) Open the `VoucherRedeemed` tx link from the summary in the XRPL EVM Testnet explorer.
4. (2:00) Show the settlement payout tx and the payout balance line, `before -> after` (+0.15 RLUSD).
5. (2:30) Open `out/run-<timestamp>.json`: package sha256 per week, receipt URL, explorer links. Optionally
   `node vendor/verify-receipt.mjs <receipt URL>` to check the receipt against the chain.

## Files

- `merchant.mjs`: offer endpoint and per-package x402 instances (live) or a fake redeem (DRY_RUN)
- `agent.mjs`: the participant's agent and run record
- `lib/policy.mjs`: the payment policy; `lib/catalog.mjs`: synthetic study and packages; `lib/pkg.mjs`: package hash
- `vendor/`: files downloaded unchanged from `https://hackathon.ap4m.build/sdk/` (`ap4m-hackathon-sdk.cjs` is a
  copy of `ap4m-hackathon-sdk.js` so it loads in this ESM package, as the SDK README says)
- `AGENTS.md`: the SDK's instructions for coding agents
