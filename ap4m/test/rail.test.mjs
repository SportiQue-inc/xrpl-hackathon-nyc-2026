import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { createRail, createStore, parsePools, refuse, settleReceipts } from '../rail-server.mjs';

async function start(env, pay) {
  const store = createStore(mkdtempSync(join(tmpdir(), 'rail-')));
  const server = createRail({ env, store, pay, log: () => {} });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;
  const post = async (body, token = 't') => (await fetch(`${base}/pay`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(body) })).json();
  return { server, store, base, post };
}

test('pools and refusals', () => {
  const pools = parsePools('vault:5,research:0.05');
  assert.equal(pools.research, 50000n);
  const ctx = { pools, spent: { research: 40000n }, perPaymentMicro: 100000n };
  assert.match(refuse({ ref: 'a', amount_micro: 100001, pool: 'vault' }, ctx), /per-payment cap/);
  assert.match(refuse({ ref: 'a', amount_micro: 20000, pool: 'research' }, ctx), /^budget/);
  assert.match(refuse({ ref: 'a', amount_micro: 100, pool: 'x' }, ctx), /unknown pool/);
  assert.match(refuse({ ref: 'a', amount_micro: 100, pool: 'vault', forward_to: 'nope' }, ctx), /EVM address/);
  assert.equal(refuse({ ref: 'a', amount_micro: 10000, pool: 'research' }, ctx), null);
});

test('same ref pays once, payments are serial, budget is charged', async () => {
  let calls = 0, inFlight = 0, maxInFlight = 0;
  const pay = async (job) => {
    calls++; inFlight++; maxInFlight = Math.max(maxInFlight, inFlight);
    await new Promise((r) => setTimeout(r, 20));
    inFlight--;
    return { ok: true, ref: job.ref, amount_rlusd: String(job.amount_micro / 1e6), claim_id: `0x${calls}`, content: job.content };
  };
  const { server, post, base } = await start({ AP4M_RAIL_TOKEN: 't', AP4M_POOLS: 'vault:0.1' }, pay);
  try {
    const [a, b, c] = await Promise.all([
      post({ ref: 'r1', amount_micro: 50000, pool: 'vault', content: { k: 'ab' } }),
      post({ ref: 'r1', amount_micro: 50000, pool: 'vault' }),
      post({ ref: 'r2', amount_micro: 50000, pool: 'vault' }),
    ]);
    assert.equal(calls, 2);
    assert.equal(maxInFlight, 1);
    assert.equal(a.claim_id, b.claim_id);
    assert.deepEqual(a.content, { k: 'ab' });
    assert.ok(c.ok);
    const over = await post({ ref: 'r3', amount_micro: 1, pool: 'vault' });
    assert.equal(over.ok, false);
    assert.match(over.reason, /^budget/);
    const health = await (await fetch(`${base}/health`)).json();
    assert.equal(health.pools.vault.spent_rlusd, 0.1);
    assert.equal((await post({ ref: 'r9', amount_micro: 1, pool: 'vault' }, 'wrong')).reason, 'unauthorized');
  } finally { server.close(); }
});

test('a failed payment stays pending and resumes with the same ref', async () => {
  let fail = true, calls = 0;
  const pay = async (job) => { calls++; if (fail) throw new Error('rpc down'); return { ok: true, ref: job.ref, claim_id: '0xc' }; };
  const { server, post, store } = await start({ AP4M_POOLS: 'vault:1' }, pay);
  try {
    const first = await post({ ref: 'x', amount_micro: 30000, pool: 'vault' });
    assert.equal(first.ok, false);
    assert.equal(first.retry, true);
    assert.equal(store.get('x').status, 'pending');
    fail = false;
    const second = await post({ ref: 'x', amount_micro: 30000, pool: 'vault' });
    assert.ok(second.ok);
    assert.equal(store.spent.vault, 30000n);   // charged once
    assert.equal(calls, 2);
  } finally { server.close(); }
});

test('paid claims settle later in one call and the ref gets its receipt', async () => {
  const pay = async (job) => ({ ok: true, ref: job.ref, amount_rlusd: '0.007', claim_id: job.ref === 'a' ? '0xAA' : '0xBB', settlement: 'scheduled' });
  const { server, store, base, post } = await start({ AP4M_RAIL_TOKEN: 't', AP4M_POOLS: 'vault:1' }, pay);
  try {
    await post({ ref: 'a', amount_micro: 7000, pool: 'vault' });
    await post({ ref: 'b', amount_micro: 7000, pool: 'vault' });
    assert.deepEqual(store.unsettled(), { '0xaa': 'a', '0xbb': 'b' });
    let settles = 0;
    const live = { apiUrl: 'x', token: async () => 'tok', channelId: '0xch', explorer: 'https://ex', sdk: { settle: async () => {
      settles++;
      return { settlement_tx: '0xs', payout_tx: '0xp', receipts: [{ claim_id: '0xaa', receipt_url: 'https://r/aa.json' }, { claim_id: '0xbb', receipt_url: null }] };
    } } };
    assert.equal(await settleReceipts(live, store, () => {}), 1);
    const got = await (await fetch(`${base}/pay/a`, { headers: { Authorization: 'Bearer t' } })).json();
    assert.equal(got.receipt_url, 'https://r/aa.json');
    assert.equal(got.payout_url, 'https://ex/tx/0xp');
    assert.deepEqual(store.unsettled(), { '0xbb': 'b' });
    store.clearUnsettled(['0xbb']);
    assert.equal(await settleReceipts(live, store, () => {}), 0);
    assert.equal(settles, 1);                       // nothing open: no settle call
  } finally {
    server.close();
  }
});
