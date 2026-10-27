import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, before, test } from 'node:test';

import { runAgent, taskConsent } from '../agent.mjs';
import { startMerchant } from '../merchant.mjs';
import { DRY_PAYOUT } from '../lib/dry.mjs';
import { packageSha256, sealPackage, verifySealed } from '../lib/pkg.mjs';
import { syntheticPackage } from '../lib/catalog.mjs';
import { buildPolicy, decide } from '../lib/policy.mjs';
import { toWei } from '../lib/units.mjs';

const quiet = () => {};
let merchant;
let outDir;

before(async () => {
  merchant = await startMerchant({ dryRun: true, env: {}, port: 0, log: quiet });
  outDir = mkdtempSync(join(tmpdir(), 'ap4m-test-'));
});
after(async () => {
  await merchant.close();
  rmSync(outDir, { recursive: true, force: true });
});

const baseEnv = { PER_CALL_CAP_RLUSD: '0.10', BUDGET_RLUSD: '0.20' };
const run = (env = {}, extra = {}) => runAgent({ dryRun: true, env: { ...baseEnv, ...env }, merchantUrl: merchant.url, outDir, log: quiet, ...extra });

const offer = (overrides = {}) => ({
  pseudonym: 'P-017', week: 3, items: ['resting_heart_rate_bpm', 'fatigue_score'],
  purpose: { study: 'SLEEP-01', duo: 'HMB' }, price_rlusd: '0.05', pay_to: DRY_PAYOUT, ...overrides,
});
const policy = buildPolicy({ perCallCapRlusd: '0.10', budgetRlusd: '0.20', payeeAllowlist: [DRY_PAYOUT] });

test('pays within cap: weeks 3-5 are paid and their packages verified', async () => {
  const { record } = await run();
  const paid = record.calls.filter((c) => c.paid);
  assert.deepEqual(paid.map((c) => c.offer.week), [3, 4, 5]);
  assert.ok(paid.every((c) => c.package_hash_ok && /^0x[0-9a-f]{64}$/.test(c.voucher_redeemed_tx)));
  assert.equal(record.total_paid_rlusd, '0.15');
  assert.equal(record.payout_balance.delta_rlusd, '0.15');
  assert.ok(paid.every((c) => c.package.synthetic === true && !('date' in c.package.days[0])));
});

test('refuses the scripted week 6 request with no payment, naming every rule it breaks', async () => {
  const { record } = await run();
  const extra = record.calls.at(-1);
  assert.equal(extra.scripted, true);
  assert.equal(extra.decision, 'refuse');
  assert.equal(extra.paid, false);
  assert.equal(extra.voucher_redeemed_tx, undefined);
  // over the cap, over the remaining budget, and outside the consented weeks: three independent refusals
  assert.ok(extra.reasons.some((r) => /exceeds per-call cap/.test(r)), extra.reason);
  assert.ok(extra.reasons.some((r) => /over the delegated budget/.test(r)), extra.reason);
  assert.ok(extra.reasons.some((r) => /week 6 is outside consented weeks 3,4,5/.test(r)), extra.reason);
  assert.match(extra.reason, /exceeds per-call cap/);
  const over = decide(offer({ price_rlusd: '0.11' }), policy, taskConsent(), 0n);
  assert.equal(over.pay, false);
  assert.deepEqual(over.reasons, ['price 0.11 RLUSD exceeds per-call cap 0.1 RLUSD']);   // the cap alone
});

test('consent covers the task only: week 6 inside the cap and the budget is still refused', () => {
  assert.deepEqual(taskConsent().weeks, [3, 4, 5]);
  const v = decide(offer({ week: 6 }), policy, taskConsent(), 0n);          // 0.05 RLUSD: cap and budget are fine
  assert.equal(v.pay, false);
  assert.deepEqual(v.reasons, ['week 6 is outside consented weeks 3,4,5']);
  assert.equal(decide(offer({ week: 5 }), policy, taskConsent(), 0n).pay, true);
});

test('an offer without a valid price still names the other rules it breaks', () => {
  const v = decide(offer({ price_rlusd: 'free', week: 6 }), policy, taskConsent(), 0n);
  assert.equal(v.pay, false);
  assert.equal(v.priceWei, null);
  assert.deepEqual(v.reasons, ['offer has no valid price', 'week 6 is outside consented weeks 3,4,5']);
});

test('refuses unknown payee: nothing is paid when the payee is not allowlisted', async () => {
  const { record } = await run({ PAYEE_ALLOWLIST: '0x000000000000000000000000000000000000beef' });
  assert.equal(record.calls.filter((c) => c.paid).length, 0);
  assert.ok(record.calls.every((c) => /not in the allowlist/.test(c.reason)));
  assert.equal(record.total_paid_rlusd, '0');
});

test('refuses after budget exhausted', async () => {
  const { record } = await run({ BUDGET_RLUSD: '0.10' });
  assert.deepEqual(record.calls.filter((c) => c.paid).map((c) => c.offer.week), [3, 4]);
  assert.match(record.calls[2].reason, /over the delegated budget/);
  assert.equal(record.calls[2].paid, false);
  assert.equal(decide(offer(), policy, taskConsent(), toWei('0.16')).pay, false);
});

test('tampered package hash is rejected, claimed back, and stops every later payment', async () => {
  const tamperingFetch = async (url, init) => {
    const response = await fetch(url, init);
    if (!String(url).includes('/dry/resource/sleep-01-p-017-w3') || response.status !== 200) return response;
    const body = await response.json();
    body.resource.package.days[0].resting_heart_rate_bpm += 1;
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  const { record } = await run({}, { fetchImpl: tamperingFetch });
  const [w3, w4, w5, w6] = record.calls;
  // week 3 was paid before the package could be checked (x402 delivers after payment): rejected, claim recorded
  assert.equal(w3.paid, true);
  assert.equal(w3.package_hash_ok, false);
  assert.equal(w3.package, undefined);
  assert.match(w3.refund_claim.reason, /failed verification/);
  assert.equal(w3.refund_claim.amount_rlusd, '0.05');
  // weeks 4 and 5 would have passed every rule; nothing more is paid to this merchant in the run
  for (const c of [w4, w5]) {
    assert.equal(c.paid, false);
    assert.equal(c.decision, 'refuse');
    assert.match(c.reason, /halted after week 3/);
    assert.equal(c.voucher_redeemed_tx, undefined);
  }
  assert.equal(w6.paid, false);
  assert.equal(record.total_paid_rlusd, '0.05');
  assert.equal(record.total_refund_claimed_rlusd, '0.05');
  assert.equal(record.halted.week, 3);
  assert.equal(record.refund_claims.length, 1);

  const sealed = sealPackage(syntheticPackage('P-017', 3));
  assert.equal(verifySealed(sealed).ok, true);
  sealed.package.week = 4;
  assert.equal(verifySealed(sealed).ok, false);
});

test('a refund claim is on disk before the run can fail later', async () => {
  // week 3's package is tampered; the request for week 4 then fails outright, so the run never reaches its final write
  const fetchImpl = async (url, init) => {
    if (String(url).endsWith('/export/P-017/4')) throw new Error('merchant unreachable');
    const response = await fetch(url, init);
    if (!String(url).includes('/dry/resource/sleep-01-p-017-w3') || response.status !== 200) return response;
    const body = await response.json();
    body.resource.package.days[0].resting_heart_rate_bpm += 1;
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  await assert.rejects(run({}, { fetchImpl, runId: 'interim' }), /merchant unreachable/);
  const interim = JSON.parse(readFileSync(join(outDir, 'run-interim.json'), 'utf8'));
  assert.equal(interim.finished_at, null);
  assert.equal(interim.halted.week, 3);
  assert.equal(interim.refund_claims.length, 1);
  assert.equal(interim.refund_claims[0].amount_rlusd, '0.05');
  assert.equal(interim.total_refund_claimed_rlusd, '0.05');
  assert.equal(interim.calls[0].paid_rlusd, '0.05');
});

test('purpose outside consent is refused', () => {
  assert.equal(decide(offer({ purpose: { study: 'SLEEP-01', duo: 'GRU' } }), policy, taskConsent(), 0n).pay, false);
  assert.equal(decide(offer({ items: ['resting_heart_rate_bpm', 'location'] }), policy, taskConsent(), 0n).pay, false);
});

test('package hash is stable across key order', () => {
  const pkg = syntheticPackage('P-017', 5);
  const reordered = Object.fromEntries(Object.entries(pkg).reverse());
  assert.equal(packageSha256(pkg), packageSha256(reordered));
});
