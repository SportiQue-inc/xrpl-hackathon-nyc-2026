import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { runAgent } from '../agent.mjs';
import { DRY_AGENT, DRY_PAYOUT, dryChannelId } from '../lib/dry.mjs';
import { startMerchant } from '../merchant.mjs';
import { toWei } from '../lib/units.mjs';

const quiet = () => {};

async function withMerchant(check) {
  const merchant = await startMerchant({ dryRun: true, env: {}, port: 0, log: quiet });
  const directory = mkdtempSync(join(tmpdir(), 'ap4m-live-authority-'));
  try { await check(merchant.url, directory); }
  finally { await merchant.close(); rmSync(directory, { recursive: true, force: true }); }
}

function connection(payout, buyResource) {
  return {
    wallet: { address: DRY_AGENT }, config: { network: {} }, context: { participantRequest: { ledger: 'test-ledger' } },
    rlusd: { balanceOf: async () => 0n },
    sdk: {
      requestChannel: async () => ({ channel_id: dryChannelId(), payout }),
      getChannelState: async () => ({ cap: toWei('0.2'), redeemed: 0n }),
    },
    readChannel: async () => ({ payout }),
    buyResource,
  };
}

test('live purchase ceiling is the approved offer price, below the per-call cap', async () => {
  await withMerchant(async (merchantUrl, stateDirectory) => {
    let intent;
    const live = connection(DRY_PAYOUT, async (value) => { intent = value; throw new Error('purchase intercepted'); });
    await assert.rejects(runAgent({ dryRun: false, env: { MERCHANT_PAYOUT: DRY_PAYOUT }, merchantUrl,
      stateDirectory, connect: async () => live, log: quiet }), /purchase intercepted/);
    assert.equal(intent.maximumAmount, toWei('0.05').toString());
    assert.equal(intent.stateDirectory, stateDirectory);
  });
});

test('an on-chain payout outside the allowlist is refused before buying', async () => {
  await withMerchant(async (merchantUrl, stateDirectory) => {
    let bought = false;
    const live = connection('0x000000000000000000000000000000000000beef', async () => { bought = true; throw new Error('purchase attempted'); });
    await assert.rejects(runAgent({ dryRun: false, env: { MERCHANT_PAYOUT: DRY_PAYOUT }, merchantUrl,
      stateDirectory, connect: async () => live, log: quiet }), /channel payout.*allowlist/i);
    assert.equal(bought, false);
  });
});

test('an unresolved SDK purchase blocks a new run before connecting or opening a channel', async () => {
  const stateDirectory = mkdtempSync(join(tmpdir(), 'ap4m-unresolved-'));
  const file = join(stateDirectory, 'purchase.json');
  const retained = JSON.stringify({ complete: false, intent: { operation: 'prior-purchase' } });
  writeFileSync(file, retained);
  let connected = false;
  try {
    await assert.rejects(runAgent({ dryRun: false, env: {}, merchantUrl: 'http://127.0.0.1:1', stateDirectory,
      connect: async () => { connected = true; throw new Error('connected'); }, log: quiet }), /unresolved purchase.*resume/i);
    assert.equal(connected, false);
    assert.equal(readFileSync(file, 'utf8'), retained);
  } finally { rmSync(stateDirectory, { recursive: true, force: true }); }
});

test('a corrupt retained purchase cannot start a new payment run', async () => {
  const stateDirectory = mkdtempSync(join(tmpdir(), 'ap4m-corrupt-'));
  writeFileSync(join(stateDirectory, 'purchase.json'), 'null');
  try {
    await assert.rejects(runAgent({ dryRun: false, env: {}, merchantUrl: 'http://127.0.0.1:1', stateDirectory,
      connect: async () => { throw new Error('connected'); }, log: quiet }), /cannot verify.*purchase state/i);
  } finally { rmSync(stateDirectory, { recursive: true, force: true }); }
});

test('a completed retained purchase permits a new run', async () => {
  const stateDirectory = mkdtempSync(join(tmpdir(), 'ap4m-complete-'));
  writeFileSync(join(stateDirectory, 'purchase.json'), JSON.stringify({ complete: true }));
  try {
    await assert.rejects(runAgent({ dryRun: false, env: {}, merchantUrl: 'http://127.0.0.1:1', stateDirectory,
      connect: async () => { throw new Error('connection reached'); }, log: quiet }), /connection reached/);
  } finally { rmSync(stateDirectory, { recursive: true, force: true }); }
});

test('the approved offer must name the actual channel payout even if both are allowlisted', async () => {
  await withMerchant(async (merchantUrl, stateDirectory) => {
    const other = '0x000000000000000000000000000000000000beef';
    const live = connection(other, async () => { throw new Error('purchase attempted'); });
    await assert.rejects(runAgent({ dryRun: false,
      env: { MERCHANT_PAYOUT: DRY_PAYOUT, PAYEE_ALLOWLIST: `${DRY_PAYOUT},${other}` }, merchantUrl,
      stateDirectory, connect: async () => live, log: quiet }), /offer payee.*channel payout/i);
  });
});
