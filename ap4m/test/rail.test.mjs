import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { adoptUnsettled, createRail, createStore, parsePools, refuse, settleReceipts } from '../rail-server.mjs';

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

test('paid claims get their published receipt later, also refs paid before this', async () => {
  const pay = async (job) => ({ ok: true, ref: job.ref, amount_rlusd: '0.007', claim_id: job.ref === 'a' ? '0xAA' : '0xBB', settlement: 'scheduled' });
  const { server, store, base, post } = await start({ AP4M_RAIL_TOKEN: 't', AP4M_POOLS: 'vault:1' }, pay);
  try {
    await post({ ref: 'a', amount_micro: 7000, pool: 'vault' });
    store.put('old', { ok: true, status: 'paid', ref: 'old', claim_id: '0xCC', receipt_url: null, settle_error: 'Unexpected token <' });
    assert.deepEqual(store.unsettled(), { '0xaa': 'a' });
    assert.equal(adoptUnsettled(store), 1);
    const d = '0x' + 'd'.repeat(64);
    const pages = { '0xaa': JSON.stringify({ receipts: [`https://svc/public/evidence/claims/0xaa/${d}.json`] }), '0xcc': JSON.stringify({ urls: [`/public/evidence/claims/0xcc/${d}.json`] }) };
    const asked = [];
    const fetchText = async (url) => { asked.push(url); return pages[url.split('/').pop()] ?? ''; };
    assert.equal(await settleReceipts({ apiUrl: 'https://svc' }, store, () => {}, fetchText), 2);
    const got = await (await fetch(`${base}/pay/a`, { headers: { Authorization: 'Bearer t' } })).json();
    assert.equal(got.receipt_url, `https://svc/public/evidence/claims/0xaa/${d}.json`);
    assert.equal(store.get('old').receipt_url, `https://svc/public/evidence/claims/0xcc/${d}.json`);
    assert.deepEqual(store.unsettled(), {});
    assert.equal(await settleReceipts({ apiUrl: 'https://svc' }, store, () => {}, fetchText), 0);
    assert.equal(asked.length, 2);
  } finally {
    server.close();
  }
});

test('a retry reuses the resource URL the first attempt bound its Merchant store to', async () => {
  const { DatabaseSync } = await import('node:sqlite');
  const { priorResourceUrl } = await import('../rail-server.mjs');
  const dir = mkdtempSync(join(tmpdir(), 'merchant-'));
  assert.equal(priorResourceUrl(dir), null);
  const db = new DatabaseSync(join(dir, 'merchant.sqlite'));
  db.exec('CREATE TABLE identity (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL) STRICT');
  db.prepare('INSERT INTO identity VALUES (1, ?)').run(JSON.stringify({ schemaId: 'x', resourceUrl: 'http://127.0.0.1:41234/resource' }));
  db.close();
  assert.equal(priorResourceUrl(dir), 'http://127.0.0.1:41234/resource');
});
