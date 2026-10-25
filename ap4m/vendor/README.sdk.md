# AP4M Hackathon SDK

> **For hackathon use only.** This SDK is provided exclusively for the Mastercard XRPL Hackathon and must not be used outside of that context.

---

## Prerequisites

- Node.js 22.13 or later
- `ethers` v6 and the AP4M SDK package (see Installation)
- Your team onboarded on the participant portal: Agent wallet added and budget funded (`/docs/quickstart.md`)
- XRP for gas, from the [XRPL EVM Testnet faucet](https://faucet.testevm.ripple.com)

---

## What you need from the hackathon

| Item | Description |
|---|---|
| `AP4M_API_URL` | Service base URL; `https://hackathon.ap4m.build/llms.txt` lists every guide, the network and the contract addresses |
| `TEAM_NAME` | Your registered team name — used to sign in with your agent or funding wallet |
| `CHANNEL_ID` | Optional: an open Channel from the participant portal; otherwise your agent opens one with `requestChannel` |
| `PAYMENT_LEDGER` | PaymentLedger contract address (portal SDK tab or `/public/config`) |
| Agent wallet | You generate this EOA and add its address on the portal's My setup tab; it signs once to prove it is yours |
| Merchant payout wallet | Optional. You generate this EOA and add it on My setup; it receives RLUSD when agents pay your team's Merchant |

> **Tip:** Download the pre-filled `example-agent.js` from your participant portal (`/sdk/example-agent.js` is the unfilled template) — it has your API URL and team name already filled in and opens its own Channel. You only need to add your `AGENT_PRIVATE_KEY`.

---

## Network

| Property | Value |
|---|---|
| Network | XRPL EVM Testnet |
| Chain ID | `1449000` |
| RPC URL | `https://rpc.testnet.xrplevm.org` |
| Gas token | XRP |

---

## E2E flow

```
Your agent                               AP4M Service
─────────────────────────────────────    ─────────────────────────────────
0. requestChannel() ─── vault request ──→  service binds the payout and opens the Channel
1. signVoucher()           ← sign with your agent private key (local)
2. redeemVoucher()  ─── direct RPC ──→  PaymentLedger contract on-chain
3. POST /public/participant/record-redemption ← optional: report tx hash so the service sees it at once
                                         service pays the Merchant from the vault, then
                                         records the settlement on-chain (automatic)
4. POST /public/participant/close-channel ──→  optional early close; after the event end the
                                         service closes every Channel and returns
                                         unused deposits automatically
```

---

## Installation

```bash
npm install ethers@6.17.0 https://hackathon.ap4m.build/sdk/ap4m-sdk.tgz
curl -O https://hackathon.ap4m.build/sdk/ap4m-hackathon-sdk.js
curl -O https://hackathon.ap4m.build/sdk/ap4m-x402.mjs
```

`ap4m-hackathon-sdk.js` needs only `ethers`; `ap4m-x402.mjs` and `verify-receipt.mjs` also need the AP4M SDK package,
which is served by the hackathon service rather than the public npm registry.

In a project with `"type": "module"` in `package.json`, download the helpers as `ap4m-hackathon-sdk.cjs` instead:

```bash
curl -O https://hackathon.ap4m.build/sdk/ap4m-hackathon-sdk.cjs
```

```js
import sdk from './ap4m-hackathon-sdk.cjs';
const { signIn, requestChannel } = sdk;
```

### Coding agents

If you build with an AI coding tool, save `https://hackathon.ap4m.build/sdk/AGENTS.md` in your project root and point the tool at
`https://hackathon.ap4m.build/llms.txt` (guide index with this deployment) or `https://hackathon.ap4m.build/llms-full.txt` (all guides in one
file). The guides are plain Markdown under `https://hackathon.ap4m.build/docs/`.

---

## x402 payments (Agent and Merchant)

`ap4m-x402.mjs` lets your agent pay over HTTP and lets your team sell a resource:

- `loadX402Context(apiUrl)` reads the chain, contracts and event window from the AP4M service.
- `buyResource({ context, provider, wallet, stateDirectory, resourceUrl, channelId, maximumAmount, operation })`
  answers a Merchant's 402 challenge with a signed Voucher and returns the resource. The signed payment is
  saved first, so a rerun with the same `operation` resumes it instead of paying twice.
- `createX402Merchant({ context, provider, submitter, stateDirectory, resourceUrl, merchantParticipantId, payout, amount, content })`
  serves `GET /resource`, redeems each Voucher on-chain from `submitter` (a wallet with XRP for gas) and returns `content`.
  `merchantParticipantId` and `payout` are your team's Merchant ID and payout wallet from the participant portal.

```bash
npm install ethers@6.17.0 https://hackathon.ap4m.build/sdk/ap4m-sdk.tgz
MERCHANT_ID=0x... MERCHANT_PAYOUT=0x... MERCHANT_SUBMITTER_KEY=0x... node example-x402-merchant.mjs
AGENT_PRIVATE_KEY=0x... TEAM_NAME="Your Team" RESOURCE_URL=http://127.0.0.1:4308/resource node example-x402-agent.mjs
```

After a purchase, the service pays the Merchant and records the settlement automatically, usually within a few
blocks. `example-x402-agent.mjs` reports the redemption and calls `settle` to wait for that result. Use a public HTTPS URL for a Merchant that is called from other machines.

---

## Code examples

These snippets are steps of one flow. CommonJS has no top-level `await`, so run them inside
`async function main() { ... }` (as `example-agent.js` does), or in an `.mjs` file with
`import sdk from './ap4m-hackathon-sdk.cjs'`.

### Get a session token

Your agent wallet (or funding wallet) signs a one-time sign-in message; nothing is sent on-chain.

```js
const { ethers } = require('ethers');
const { signIn } = require('./ap4m-hackathon-sdk');

const agentWallet = new ethers.Wallet(process.env.AGENT_PRIVATE_KEY);
const { token } = await signIn(AP4M_API_URL, 'Your Team', agentWallet);
```

### Sign and redeem a voucher

```js
const { ethers } = require('ethers');
const { signVoucher, redeemVoucher, getChannelState } = require('./ap4m-hackathon-sdk');

const agentWallet = new ethers.Wallet(process.env.AGENT_PRIVATE_KEY);
const provider = new ethers.JsonRpcProvider('https://rpc.testnet.xrplevm.org');

// Read current redeemed amount, then add your payment on top
const state = await getChannelState(provider, PAYMENT_LEDGER, CHANNEL_ID);
const cumulativeAmount = state.redeemed + ethers.parseUnits('1', 18); // +1 RLUSD

const { claimId, txHash } = await redeemVoucher(
  agentWallet, PAYMENT_LEDGER, 'https://rpc.testnet.xrplevm.org', CHANNEL_ID, cumulativeAmount
);
```

### Report redemption to the service

```js
await fetch(`${AP4M_API_URL}/public/participant/record-redemption`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ tx_hash: txHash }),
});
```

### Open a Channel

```js
const { requestChannel, listChannels } = require('./ap4m-hackathon-sdk');

const provider = new ethers.JsonRpcProvider('https://rpc.testnet.xrplevm.org');
const channel = await requestChannel(AP4M_API_URL, token, agentWallet.connect(provider), { capRlusd: '5' });
const CHANNEL_ID = channel.channel_id;
console.log(await listChannels(AP4M_API_URL, token)); // every Channel and its status
```

Your team adds its Agent wallet and funds its budget on the portal's My Setup tab first. A Channel pays your team's
own Merchant. If the organizers turn on cross-team payments, `listMerchants` lists other teams' Merchants (it is
empty otherwise), and you can buy from another team by passing its Merchant ID:

```js
const { listMerchants } = require('./ap4m-hackathon-sdk');

const merchants = await listMerchants(AP4M_API_URL); // [{ team_name, merchant_id, payout }]
const other = merchants.find((entry) => entry.team_name === 'Other Team');
await requestChannel(AP4M_API_URL, token, agentWallet.connect(provider), { capRlusd: '2', merchantId: other.merchant_id });
```

### Settle and close

Settlement is automatic: the service pays each redeemed Claim to the Merchant payout wallet, then records the
settlement on the ledger. `settle` is optional; it settles the Channel's pending Claims now, waits while a payout
is confirming, and returns the latest settled one with its `receipt_url` (a path on the service), plus `receipts`:
every settled Claim on the Channel with its absolute receipt URL. `GET /public/evidence/claims/<claimId>` also
lists a Claim's receipt URLs. `closeChannel` is also optional: after the event ends, the service closes every open Channel.

```js
const { closeChannel, settle } = require('./ap4m-hackathon-sdk');

const settled = await settle(AP4M_API_URL, token, CHANNEL_ID);
console.log('Paid out:', settled.payout_tx);
console.log('Receipt:', AP4M_API_URL + settled.receipt_url);
for (const receipt of settled.receipts) console.log(receipt.claim_id, receipt.amount_rlusd, receipt.receipt_url);

const closed = await closeChannel(AP4M_API_URL, token, agentWallet, CHANNEL_ID);
console.log('Closed:', closed.tx_hash);
```

### Verify a payment receipt

Every settled payment gets an `ap4m.claim-receipt.v1` receipt that anyone can check against the chain: the vault
payout and its RLUSD transfer, the payout wallet balance, the redeemed Voucher and the settlement digest on the
ledger. Your receipts are listed on the My Setup tab. `verify-receipt.mjs` checks one through the RPC the service
publishes, or through your own node with `RPC_URL`:

```bash
npm install ethers@6.17.0 https://hackathon.ap4m.build/sdk/ap4m-sdk.tgz
node verify-receipt.mjs https://hackathon.ap4m.build/public/evidence/claims/<claimId>/<settlementDigest>.json
```

It prints the ledger, vault and token addresses it checked against; compare them with the event deployment.

---

## Notes

- `cumulativeAmount` is the **total** amount redeemed across all vouchers, not the increment. Always read the current `redeemed` value from chain first.
- RLUSD uses 18 decimal places. Use `ethers.parseUnits('1', 18)` for 1 RLUSD.
- Your agent private key is never sent to the service. Keep it secret.
- Pass the Channel ID to `settle` and `closeChannel` when your team has more than one Channel. Before a Channel's cutoff, `closeChannel` uses your agent's signature; after it, the service closes without one.
- Gas is paid in XRP. Fund your Agent wallet from the [XRPL EVM Testnet faucet](https://faucet.testevm.ripple.com) before running.
