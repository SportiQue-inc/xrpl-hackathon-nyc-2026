// The participant's agent. Task: contribute P-017 weeks 3-5 to study SLEEP-01.
//
// For each export it reads the merchant's 402 offer and decides by itself, with a deterministic policy,
// whether to pay. A paid call goes through the AP4M x402 toolkit (signed EIP-712 Voucher on an open Channel,
// redeemed on-chain by the merchant), then the agent reports the redemption, settles, and writes a run record.
// A fourth, scripted request (week 6: outside the consented weeks and priced above the per-call cap) must be
// refused with no payment; the record lists every rule it broke. A package that fails its hash check after
// payment is recorded as a refund claim and stops every later payment in the run.
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { STUDY } from './lib/catalog.mjs';
import { DRY_AGENT, DRY_PAYOUT, dryChannelId, fakeSignVoucher, fakeTxHash } from './lib/dry.mjs';
import { payoutAddress, resolveEnv, setting } from './lib/env.mjs';
import { voucherRedeemedEvents } from './lib/ledger-events.mjs';
import { verifySealed } from './lib/pkg.mjs';
import { buildConsent, buildPolicy, decide } from './lib/policy.mjs';
import { fromWei, toWei } from './lib/units.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ERC20_ABI = ['function balanceOf(address) view returns (uint256)'];

export const TASK = Object.freeze({
  description: 'contribute P-017 weeks 3-5 to study SLEEP-01',
  pseudonym: 'P-017',
  weeks: [3, 4, 5],
  // Scripted fourth request: an add-on export priced above the per-call cap.
  scriptedExtra: { week: 6, note: 'scripted over-cap request' },
});

// The participant's consent covers exactly the task: the same weeks, items and study. An offer for another
// week is refused even when it is inside the cap and the budget.
export function taskConsent() {
  return buildConsent({ pseudonym: TASK.pseudonym, study: STUDY.id, duo: STUDY.duo, items: STUDY.items, weeks: TASK.weeks });
}

async function readJson(response) {
  const text = await response.text();
  try { return JSON.parse(text); } catch { return { error: 'non_json_response', body: text.slice(0, 200) }; }
}

// Live chain and service access; every import is lazy so DRY_RUN needs no packages and no network.
async function connectLive(env) {
  for (const name of ['AGENT_PRIVATE_KEY', 'TEAM_NAME']) if (!env[name]) throw new Error(`${name} is not set`);
  const { ethers } = await import('ethers');
  const { default: sdk } = await import(pathToFileURL(join(HERE, 'vendor/ap4m-hackathon-sdk.cjs')).href);
  const { buyResource, loadX402Context } = await import(pathToFileURL(join(HERE, 'vendor/ap4m-x402.mjs')).href);
  const apiUrl = setting(env, 'AP4M_API_URL');
  const config = await (await fetch(`${apiUrl}/public/config`)).json();
  const provider = new ethers.JsonRpcProvider(env.AP4M_RPC_URL || config.network.rpcUrl);
  const wallet = new ethers.Wallet(env.AGENT_PRIVATE_KEY, provider);
  const context = await loadX402Context(apiUrl);
  const { token } = await sdk.signIn(apiUrl, env.TEAM_NAME, wallet);
  const rlusd = new ethers.Contract(context.x402.token, ERC20_ABI, provider);
  return { ethers, sdk, buyResource, apiUrl, config, provider, wallet, context, token, rlusd };
}

/**
 * @param {{ dryRun: boolean, env: Record<string,string>, merchantUrl: string, outDir?: string,
 *           fetchImpl?: typeof fetch, log?: (line: string) => void, runId?: string }} options
 */
export async function runAgent({ dryRun, env, merchantUrl, outDir = join(HERE, 'out'), fetchImpl = fetch, log = console.log, runId }) {
  const startedAt = new Date();
  runId ??= startedAt.toISOString().replace(/[:.]/g, '-');
  const operationRun = runId.toLowerCase().replace(/[^a-z0-9]/g, '').slice(-14);
  const allowlist = (env.PAYEE_ALLOWLIST || (dryRun ? DRY_PAYOUT : payoutAddress(env))).split(',').map((s) => s.trim()).filter(Boolean);
  const policy = buildPolicy({
    perCallCapRlusd: setting(env, 'PER_CALL_CAP_RLUSD'),
    budgetRlusd: setting(env, 'BUDGET_RLUSD'),
    payeeAllowlist: allowlist,
  });
  const consent = taskConsent();
  const live = dryRun ? null : await connectLive(env);
  const explorer = live?.config.network.explorerUrl ?? 'https://explorer.testnet.xrplevm.org';
  const txLink = (hash) => (hash ? `${explorer}/tx/${hash}` : null);
  const record = {
    schema: 'agentrail.ap4m-run.v1',
    run_id: runId,
    mode: dryRun ? 'DRY_RUN (no network; fake signer and fake redeem)' : 'live',
    network: { name: 'XRPL EVM Testnet', chain_id: 1449000, note: 'AP4M runs on XRPL EVM Testnet, not the XRPL ledger used by the rest of AgentRail' },
    task: TASK.description,
    synthetic_data: true,
    policy: {
      per_call_cap_rlusd: fromWei(policy.perCallCapWei),
      budget_rlusd: fromWei(policy.budgetWei),
      payee_allowlist: policy.payeeAllowlist,
    },
    consent,
    agent: dryRun ? DRY_AGENT : live.wallet.address,
    channel: null,
    calls: [],
    halted: null,
    refund_claims: [],
    settlement: null,
    payout_balance: null,
    explorer_links: [],
  };

  const payout = dryRun ? DRY_PAYOUT : payoutAddress(env);
  // The developer guide requires the payout wallet to differ from the Agent (and funding) wallet.
  if (!dryRun && payout.toLowerCase() === live.wallet.address.toLowerCase()) {
    throw new Error('MERCHANT_PAYOUT must be a different wallet from the Agent wallet');
  }
  const balanceOf = async () => (dryRun ? null : await live.rlusd.balanceOf(payout));
  const balanceBefore = await balanceOf();

  // Open (or reuse) one Channel for the whole task; its cap is the delegated budget.
  let channelId = dryRun ? dryChannelId() : env.CHANNEL_ID;
  if (!dryRun) {
    if (!channelId) {
      const capRlusd = env.CHANNEL_CAP || fromWei(policy.budgetWei);
      log(`[channel] requestChannel cap ${capRlusd} RLUSD to merchant ${env.MERCHANT_ID || '(team default)'}`);
      const channel = await live.sdk.requestChannel(live.apiUrl, live.token, live.wallet, { capRlusd, merchantId: env.MERCHANT_ID || undefined });
      channelId = channel.channel_id;
      record.channel = { ...channel, opened_by_this_run: true };
    } else {
      record.channel = { channel_id: channelId, opened_by_this_run: false };
    }
    const state = await live.sdk.getChannelState(live.provider, live.context.participantRequest.ledger, channelId);
    record.channel.cap_rlusd = fromWei(state.cap);
    record.channel.redeemed_before_rlusd = fromWei(state.redeemed);
  } else {
    record.channel = { channel_id: channelId, opened_by_this_run: true, cap_rlusd: fromWei(policy.budgetWei) };
  }
  log(`[channel] ${channelId}`);

  let spentWei = 0n;
  let dryCumulative = 0n;
  let halted = null;   // set after a package fails verification: no further payment in this run
  const requests = [
    ...TASK.weeks.map((week) => ({ week, scripted: false })),
    { week: TASK.scriptedExtra.week, scripted: true },
  ];

  for (const { week, scripted } of requests) {
    const exportUrl = `${merchantUrl}/export/${TASK.pseudonym}/${week}`;
    const call = { request: exportUrl, scripted, paid: false };
    record.calls.push(call);
    const first = await fetchImpl(exportUrl);
    const body = await readJson(first);
    if (first.status !== 402 || !body.offer) {
      call.decision = 'error';
      call.reason = `expected HTTP 402 with an offer, got ${first.status}`;
      log(`[decision] ${TASK.pseudonym} w${week} ERROR ${call.reason}`);
      continue;
    }
    const { offer } = body;
    call.offer = offer;
    let verdict = decide(offer, policy, consent, spentWei);
    if (verdict.pay && halted) {
      const reason = `halted after week ${halted.week}: ${halted.reason}`;
      verdict = { pay: false, reason, reasons: [reason], priceWei: verdict.priceWei };
    }
    call.decision = verdict.pay ? 'pay' : 'refuse';
    call.reason = verdict.reason;
    call.reasons = verdict.reasons;
    log(`[decision] ${TASK.pseudonym} w${week} price=${offer.price_rlusd} RLUSD payee=${offer.pay_to} -> ${verdict.pay ? 'PAY' : 'REFUSE'}: ${verdict.reason}`);
    if (!verdict.pay) continue;

    let sealed;
    let redeemTx;
    if (dryRun) {
      dryCumulative += verdict.priceWei;
      const voucher = { channelId, cumulativeAmount: dryCumulative.toString() };
      const signature = fakeSignVoucher(voucher);
      const paid = await fetchImpl(offer.resource_url, { headers: { 'x-dry-payment': JSON.stringify({ voucher, signature }) } });
      const result = await readJson(paid);
      if (paid.status !== 200) throw new Error(`dry redeem failed: ${result.error}`);
      sealed = result.resource;
      redeemTx = result.transaction;
      call.voucher = { cumulative_amount_rlusd: fromWei(dryCumulative), signature: 'fake (DRY_RUN)' };
      call.record_redemption = { status: 'skipped (DRY_RUN)' };
    } else {
      // The per-call cap is the hard ceiling handed to the SDK; buyResource refuses a challenge above it.
      const remaining = policy.budgetWei - spentWei;
      const maximumAmount = (policy.perCallCapWei < remaining ? policy.perCallCapWei : remaining).toString();
      const purchase = await live.buyResource({
        context: live.context, provider: live.provider, wallet: live.wallet,
        stateDirectory: join(HERE, 'state', 'agent'),
        resourceUrl: offer.resource_url, channelId, maximumAmount,
        operation: `${offer.package_id}-${operationRun}`.slice(0, 64),
      });
      sealed = purchase.resource;
      redeemTx = purchase.transactionHash;
      call.claim_id = purchase.claimId;
      const receipt = await live.provider.getTransactionReceipt(redeemTx);
      const [event] = voucherRedeemedEvents(receipt, live.context.participantRequest.ledger)
        .filter((entry) => entry.claimId === purchase.claimId.toLowerCase());
      call.voucher_redeemed_event = event
        ? { ...event, amount_rlusd: fromWei(event.amount), cumulative_rlusd: fromWei(event.cumulativeAmount), previousCumulativeAmount: undefined, cumulativeAmount: undefined, amount: undefined }
        : null;
      const reported = await fetch(`${live.apiUrl}/public/participant/record-redemption`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${live.token}` },
        body: JSON.stringify({ tx_hash: redeemTx }),
      });
      call.record_redemption = { status: reported.status, body: await readJson(reported) };
      log(`[pay] record-redemption HTTP ${reported.status}`);
    }
    call.paid = true;
    spentWei += verdict.priceWei;
    call.voucher_redeemed_tx = redeemTx;
    call.voucher_redeemed_link = dryRun ? null : txLink(redeemTx);
    if (!dryRun) record.explorer_links.push(txLink(redeemTx));
    log(`[pay] VoucherRedeemed tx ${redeemTx}${dryRun ? ' (fake)' : ''}`);

    const check = verifySealed(sealed);
    call.package_sha256 = check.expected;
    call.package_hash_ok = check.ok;
    if (check.ok) {
      call.package = sealed.package;
      log(`[package] ${offer.package_id} sha256 ${check.actual} verified`);
    } else {
      // Paid already (x402 hands the package over only after payment), so the record keeps a refund claim
      // against this merchant and the agent pays nothing more in this run. The AP4M payment is not reversed here.
      call.refund_claim = {
        amount_rlusd: fromWei(verdict.priceWei), claim_id: call.claim_id ?? null, voucher_redeemed_tx: redeemTx,
        reason: `package ${offer.package_id} failed verification: sha256 claimed ${check.expected}, computed ${check.actual}`,
        note: 'recorded off-chain in this run record; the payment already made is not reversed',
      };
      record.refund_claims.push({ week, ...call.refund_claim });
      halted = { week, reason: `package ${offer.package_id} failed verification; no further payments to this merchant in this run` };
      record.halted = halted;
      log(`[package] ${offer.package_id} REJECTED: sha256 mismatch (claimed ${check.expected}, computed ${check.actual}); refund claim recorded, no further payments this run`);
    }
  }

  record.total_paid_rlusd = fromWei(spentWei);
  record.total_refund_claimed_rlusd = fromWei(record.refund_claims.reduce((sum, r) => sum + toWei(r.amount_rlusd), 0n));
  if (spentWei > 0n) {
    if (dryRun) {
      record.settlement = { payout_tx: fakeTxHash('payout', channelId, spentWei), receipt_url: null, note: 'fake (DRY_RUN)' };
    } else {
      const settled = await live.sdk.settle(live.apiUrl, live.token, channelId);
      record.settlement = {
        ...settled,
        receipt_url: settled.receipt_url ? live.apiUrl + settled.receipt_url : null,
        payout_link: txLink(settled.payout_tx),
        settlement_link: txLink(settled.settlement_tx),
      };
      record.explorer_links.push(txLink(settled.payout_tx), txLink(settled.settlement_tx));
      log(`[settle] payout tx ${settled.payout_tx}, settlement tx ${settled.settlement_tx}`);
      if (record.settlement.receipt_url) log(`[settle] receipt ${record.settlement.receipt_url}`);
    }
    if (!dryRun && env.CLOSE_CHANNEL === '1') {
      const closed = await live.sdk.closeChannel(live.apiUrl, live.token, live.wallet, channelId);
      record.channel.close_tx = closed.tx_hash;
      record.explorer_links.push(txLink(closed.tx_hash));
    }
  }

  const balanceAfter = await balanceOf();
  record.payout_balance = dryRun
    ? { address: payout, before_rlusd: '0', after_rlusd: fromWei(spentWei), delta_rlusd: fromWei(spentWei), note: 'simulated (DRY_RUN)' }
    : {
      address: payout,
      token: live.context.x402.token,
      before_rlusd: fromWei(balanceBefore),
      after_rlusd: fromWei(balanceAfter),
      delta_rlusd: fromWei(balanceAfter - balanceBefore),
      link: `${explorer}/address/${payout}`,
    };
  if (!dryRun) record.explorer_links.push(record.payout_balance.link);
  record.explorer_links = record.explorer_links.filter(Boolean);
  record.finished_at = new Date().toISOString();

  mkdirSync(outDir, { recursive: true });
  const outFile = join(outDir, `run-${runId}.json`);
  writeFileSync(outFile, JSON.stringify(record, null, 2) + '\n');
  log(`[summary] paid ${record.calls.filter((c) => c.paid).length} of ${record.calls.length} calls, total ${record.total_paid_rlusd} RLUSD; payout balance ${record.payout_balance.before_rlusd} -> ${record.payout_balance.after_rlusd} RLUSD`
    + (record.refund_claims.length ? `; ${record.refund_claims.length} refund claim(s) for ${record.total_refund_claimed_rlusd} RLUSD, run halted after week ${record.halted.week}` : ''));
  log(`[summary] run record ${outFile}`);
  return { record, outFile };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const env = resolveEnv(join(HERE, '.env'));
  const merchantUrl = env.MERCHANT_URL || `http://127.0.0.1:${setting(env, 'MERCHANT_PORT')}`;
  runAgent({ dryRun: env.DRY_RUN === '1', env, merchantUrl }).catch((error) => {
    console.error(`[agent] ${error.message ?? error}`);
    process.exit(1);
  });
}
