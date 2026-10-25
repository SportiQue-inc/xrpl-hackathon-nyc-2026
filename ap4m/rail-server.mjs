// AP4M payment rail shared by the Data Vault Market and the research contracts.
//
// One process owns the Agent key, the merchant submitter and the payout wallet, and pays one request at a
// time, so nonces and the Channel's cumulative Voucher amount never race. Each payment:
//   1. starts a one-off x402 Merchant on loopback that sells `content` (e.g. the data key K) at the amount;
//   2. the Agent buys it with buyResource: an EIP-712 Voucher on the open Channel, redeemed on-chain by the
//      merchant (VoucherRedeemed on the PaymentLedger), and gets `content` back;
//   3. reports the redemption; settlement (the AP4M service pays RLUSD from the vault to the payout wallet) runs
//      in the background every AP4M_SETTLE_EVERY_MS for all unsettled claims at once and fills in each ref's
//      receipt_url, so a payment does not wait up to two minutes for payout confirmations (AP4M_SETTLE_INLINE=1
//      settles inside the payment as before);
//   4. optionally forwards the same amount as RLUSD from the payout wallet to `forward_to` (second hop), so a
//      seller or participant is paid on-chain, not only the team's Merchant.
// Results are kept per `ref` before and after paying: the same ref never pays twice.
//
//   POST /pay      {ref, amount_micro, pool, memo?, content?, forward_to?}   Authorization: Bearer AP4M_RAIL_TOKEN
//   GET  /pay/:ref the stored result for that ref (same token)
//   GET  /health   public: channel, per-pool spend and caps, payment count (no keys, no content)
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { payoutAddress, resolveEnv, setting } from './lib/env.mjs';
import { voucherRedeemedEvents } from './lib/ledger-events.mjs';
import { fromWei } from './lib/units.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const MICRO = 10n ** 12n;                       // 1 micro-RLUSD in wei (18 decimals)
const ERC20_ABI = ['function transfer(address,uint256) returns (bool)', 'function balanceOf(address) view returns (uint256)'];

export function parsePools(text) {
  const pools = {};
  for (const part of String(text || 'vault:5,research:5').split(',')) {
    const [name, cap] = part.split(':').map((s) => s.trim());
    if (name && cap) pools[name] = BigInt(Math.round(Number(cap) * 1e6));   // micro-RLUSD
  }
  return pools;
}

const refKey = (ref) => createHash('sha256').update(String(ref)).digest('hex');

/** Validate one request against the per-payment cap and the pool budget; returns a reason or null. */
export function refuse(body, { pools, spent, perPaymentMicro }) {
  const amount = Number(body?.amount_micro);
  if (!body || typeof body.ref !== 'string' || !body.ref || body.ref.length > 200) return 'ref is required (<= 200 chars)';
  if (!Number.isSafeInteger(amount) || amount < 1) return 'amount_micro must be a positive integer';
  if (BigInt(amount) > perPaymentMicro) return `amount ${amount / 1e6} RLUSD exceeds the per-payment cap ${Number(perPaymentMicro) / 1e6} RLUSD`;
  if (!(body.pool in pools)) return `unknown pool ${body.pool}`;
  if ((spent[body.pool] ?? 0n) + BigInt(amount) > pools[body.pool]) return `budget: pool ${body.pool} has ${Number(pools[body.pool] - (spent[body.pool] ?? 0n)) / 1e6} RLUSD left`;
  if (body.forward_to != null && !/^0x[0-9a-fA-F]{40}$/.test(body.forward_to)) return 'forward_to must be an EVM address';
  return null;
}

export function createStore(dir) {
  mkdirSync(join(dir, 'refs'), { recursive: true, mode: 0o700 });
  const file = (ref) => join(dir, 'refs', `${refKey(ref)}.json`);
  const write = (path, value) => { writeFileSync(`${path}.tmp`, JSON.stringify(value, null, 2) + '\n', { mode: 0o600 }); renameSync(`${path}.tmp`, path); };
  const spentFile = join(dir, 'spent.json');
  const spent = existsSync(spentFile) ? Object.fromEntries(Object.entries(JSON.parse(readFileSync(spentFile, 'utf8'))).map(([k, v]) => [k, BigInt(v)])) : {};
  return {
    dir,
    spent,
    get: (ref) => (existsSync(file(ref)) ? JSON.parse(readFileSync(file(ref), 'utf8')) : null),
    put: (ref, value) => write(file(ref), value),
    charge(pool, micro) {
      spent[pool] = (spent[pool] ?? 0n) + BigInt(micro);
      write(spentFile, Object.fromEntries(Object.entries(spent).map(([k, v]) => [k, v.toString()])));
    },
    readJson: (name) => (existsSync(join(dir, name)) ? JSON.parse(readFileSync(join(dir, name), 'utf8')) : null),
    writeJson: (name, value) => write(join(dir, name), value),
    // claims paid but not yet settled, claim_id -> ref; settleReceipts() fills their receipts in
    unsettled: () => (existsSync(join(dir, 'unsettled.json')) ? JSON.parse(readFileSync(join(dir, 'unsettled.json'), 'utf8')) : {}),
    markUnsettled(claim, ref) { const u = this.unsettled(); u[claim.toLowerCase()] = ref; write(join(dir, 'unsettled.json'), u); },
    clearUnsettled(claims) { const u = this.unsettled(); for (const c of claims) delete u[c]; write(join(dir, 'unsettled.json'), u); },
  };
}

/** The resource URL an earlier attempt's Merchant store was created for, or null. */
export function priorResourceUrl(dir) {
  const db = join(dir, 'merchant.sqlite');
  if (!existsSync(db)) return null;
  try {
    const conn = new DatabaseSync(db, { readOnly: true });
    try { return JSON.parse(conn.prepare('SELECT value FROM identity').get()?.value ?? 'null')?.resourceUrl ?? null; } finally { conn.close(); }
  } catch { return null; }
}

function freePort() {
  return new Promise((resolve, reject) => {
    const s = createServer();
    s.once('error', reject);
    s.listen(0, '127.0.0.1', () => { const { port } = s.address(); s.close(() => resolve(port)); });
  });
}

async function connect(env, store, log) {
  for (const name of ['AGENT_PRIVATE_KEY', 'TEAM_NAME', 'MERCHANT_ID', 'MERCHANT_SUBMITTER_KEY']) if (!env[name]) throw new Error(`${name} is not set`);
  const payout = payoutAddress(env);
  if (!payout) throw new Error('MERCHANT_PAYOUT is not set');
  const { ethers } = await import('ethers');
  const { default: sdk } = await import(pathToFileURL(join(HERE, 'vendor/ap4m-hackathon-sdk.cjs')).href);
  const x402 = await import(pathToFileURL(join(HERE, 'vendor/ap4m-x402.mjs')).href);
  const apiUrl = setting(env, 'AP4M_API_URL');
  const config = await (await fetch(`${apiUrl}/public/config`)).json();
  const provider = new ethers.JsonRpcProvider(env.AP4M_RPC_URL || config.network.rpcUrl);
  const wallet = new ethers.Wallet(env.AGENT_PRIVATE_KEY, provider);
  const submitter = new ethers.Wallet(env.MERCHANT_SUBMITTER_KEY, provider);
  const forwarder = new ethers.Wallet(env.FORWARD_PRIVATE_KEY || env.MERCHANT_SUBMITTER_KEY, provider);
  if (forwarder.address.toLowerCase() !== payout.toLowerCase()) log('[rail] forward key is not the payout wallet: second-hop forwarding is off');
  const context = await x402.loadX402Context(apiUrl);
  const explorer = config.network.explorerUrl ?? 'https://explorer.testnet.xrplevm.org';
  let session = { token: null, at: 0 };
  const token = async () => {
    if (!session.token || Date.now() - session.at > 10 * 60_000) session = { token: (await sdk.signIn(apiUrl, env.TEAM_NAME, wallet)).token, at: Date.now() };
    return session.token;
  };
  let channelId = env.AP4M_CHANNEL_ID || store.readJson('channel.json')?.channel_id;
  if (!channelId) {
    const capRlusd = env.AP4M_CHANNEL_CAP || '10';
    log(`[rail] requestChannel cap ${capRlusd} RLUSD`);
    const channel = await sdk.requestChannel(apiUrl, await token(), wallet, { capRlusd, merchantId: env.MERCHANT_ID });
    channelId = channel.channel_id;
    store.writeJson('channel.json', { channel_id: channelId, request_tx: channel.request_tx, cap_rlusd: capRlusd, opened_at: new Date().toISOString() });
  }
  const rlusd = new ethers.Contract(context.x402.token, ERC20_ABI, forwarder);
  log(`[rail] channel ${channelId}, agent ${wallet.address}, payout ${payout}`);
  return { ethers, sdk, x402, apiUrl, provider, wallet, submitter, forwarder, payout, context, explorer, token, channelId, rlusd,
    forwardOn: forwarder.address.toLowerCase() === payout.toLowerCase() };
}

/** One payment end to end. `live` comes from connect(); the store already holds a pending record for ref. */
export async function payOnce(live, env, body) {
  const amountWei = BigInt(body.amount_micro) * MICRO;
  const op = `p-${refKey(body.ref).slice(0, 40)}`;
  // A retry of the same ref must offer the same resource URL: the Merchant store and the Agent's signed intent are
  // bound to it. Reuse the URL the first attempt recorded, and clear a lock a crashed attempt left behind.
  const merchantDir = join(env.AP4M_STATE_DIR, 'merchant', op);
  const resourceUrl = priorResourceUrl(merchantDir) ?? `http://127.0.0.1:${await freePort()}/resource`;
  const port = Number(new URL(resourceUrl).port);
  rmSync(join(merchantDir, 'merchant.lock'), { force: true });   // payments are serial: no other Merchant uses this directory
  const content = { ref: body.ref, memo: body.memo ?? null, ...(body.content ? { content: body.content } : {}) };
  const merchant = live.x402.createX402Merchant({
    context: live.context, provider: live.provider, submitter: live.submitter,
    stateDirectory: merchantDir, resourceUrl,
    merchantParticipantId: env.MERCHANT_ID, payout: live.payout, amount: amountWei.toString(), content,
  });
  await new Promise((resolve, reject) => { merchant.server.once('error', reject); merchant.server.listen(port, '127.0.0.1', resolve); });
  let purchase;
  try {
    purchase = await live.x402.buyResource({
      context: live.context, provider: live.provider, wallet: live.wallet,
      stateDirectory: join(env.AP4M_STATE_DIR, 'agent', op), resourceUrl,
      channelId: live.channelId, maximumAmount: amountWei.toString(), operation: op,
    });
  } finally {
    await merchant.close();
  }
  const tx = purchase.transactionHash;
  const receipt = await live.provider.getTransactionReceipt(tx);
  const [event] = voucherRedeemedEvents(receipt, live.context.participantRequest.ledger).filter((e) => e.claimId === purchase.claimId.toLowerCase());
  const verified = Boolean(receipt?.status === 1 && event && event.amount === amountWei && event.channelId === live.channelId.toLowerCase());
  const tokenValue = await live.token();
  await fetch(`${live.apiUrl}/public/participant/record-redemption`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokenValue}` }, body: JSON.stringify({ tx_hash: tx }),
  });
  const result = {
    ok: true, ref: body.ref, pool: body.pool, memo: body.memo ?? null, amount_rlusd: fromWei(amountWei),
    claim_id: purchase.claimId, channel_id: live.channelId, voucher_redeemed_tx: tx, voucher_url: `${live.explorer}/tx/${tx}`,
    verified, agent: live.wallet.address, merchant_payout: live.payout, content: purchase.resource?.content ?? null,
  };
  if (env.AP4M_SETTLE_INLINE !== '1') {
    result.settlement = 'scheduled';   // settleReceipts() adds settlement_tx, payout_tx and receipt_url to this ref
  } else try {
    const settled = await live.sdk.settle(live.apiUrl, tokenValue, live.channelId);
    const mine = (settled.receipts ?? []).find((r) => r.claim_id?.toLowerCase() === purchase.claimId.toLowerCase());
    Object.assign(result, {
      settlement_tx: settled.settlement_tx, payout_tx: settled.payout_tx,
      settlement_url: settled.settlement_tx ? `${live.explorer}/tx/${settled.settlement_tx}` : null,
      payout_url: settled.payout_tx ? `${live.explorer}/tx/${settled.payout_tx}` : null,
      receipt_url: mine?.receipt_url ?? (settled.claim_id === purchase.claimId && settled.receipt_url ? live.apiUrl + settled.receipt_url : null),
    });
  } catch (error) {
    result.settle_error = error.message.slice(0, 200);   // redeemed and paid on-chain; the service settles it later
  }
  if (body.forward_to && live.forwardOn) {
    try {
      const sent = await live.rlusd.transfer(body.forward_to, amountWei);
      const done = await sent.wait();
      Object.assign(result, { forward_to: body.forward_to, forward_tx: sent.hash, forward_url: `${live.explorer}/tx/${sent.hash}`, forward_ok: done?.status === 1 });
    } catch (error) {
      Object.assign(result, { forward_to: body.forward_to, forward_ok: false, forward_error: error.message.slice(0, 200) });
    }
  }
  return result;
}

/** Settle every paid claim that has no receipt yet in one call and write the receipts into their refs. */
export async function settleReceipts(live, store, log = console.log) {
  const open = store.unsettled();
  if (!Object.keys(open).length) return 0;
  const settled = await live.sdk.settle(live.apiUrl, await live.token(), live.channelId);
  const done = [];
  for (const r of settled.receipts ?? []) {
    const claim = r.claim_id?.toLowerCase();
    const ref = claim && open[claim];
    if (!ref || !r.receipt_url) continue;
    const rec = store.get(ref);
    if (rec) {
      store.put(ref, { ...rec, settlement: 'settled', receipt_url: r.receipt_url, settlement_tx: settled.settlement_tx ?? rec.settlement_tx ?? null,
        payout_tx: settled.payout_tx ?? rec.payout_tx ?? null,
        settlement_url: settled.settlement_tx ? `${live.explorer}/tx/${settled.settlement_tx}` : rec.settlement_url ?? null,
        payout_url: settled.payout_tx ? `${live.explorer}/tx/${settled.payout_tx}` : rec.payout_url ?? null });
    }
    done.push(claim);
  }
  if (done.length) { store.clearUnsettled(done); log(`[rail] settled ${done.length} claim(s), ${Object.keys(open).length - done.length} still waiting`); }
  return done.length;
}

export function createRail({ env, store, pay, log = console.log }) {
  const pools = parsePools(env.AP4M_POOLS);
  const perPaymentMicro = BigInt(Math.round(Number(env.PER_PAYMENT_CAP_RLUSD || '0.10') * 1e6));
  let chain = Promise.resolve();
  const public_ = (r) => (r ? Object.fromEntries(Object.entries(r).filter(([k]) => k !== 'content')) : r);

  async function handlePay(body) {
    const prior = store.get(body?.ref);
    if (prior?.ok) return prior;                    // idempotent: the same ref returns the same receipt
    const why = prior?.status === 'pending' ? null : refuse(body, { pools, spent: store.spent, perPaymentMicro });
    if (why) return { ok: false, ref: body?.ref ?? null, reason: why };
    const job = prior?.status === 'pending' ? prior.request : body;
    if (!prior) { store.put(job.ref, { status: 'pending', request: job, at: new Date().toISOString() }); store.charge(job.pool, job.amount_micro); }
    try {
      const result = await pay(job);
      store.put(job.ref, { ...result, status: 'paid', at: new Date().toISOString() });
      if (result.claim_id && !result.receipt_url) store.markUnsettled(result.claim_id, job.ref);
      log(`[rail] paid ${job.ref} ${result.amount_rlusd} RLUSD claim ${result.claim_id}`);
      return result;
    } catch (error) {
      // Stays pending with its budget held: a retry with the same ref resumes the same signed purchase.
      log(`[rail] ${job.ref} failed: ${error.message}`);
      return { ok: false, ref: job.ref, reason: `payment error: ${error.message.slice(0, 200)}`, retry: true };
    }
  }

  const serial = (fn) => { const run = chain.then(fn, fn); chain = run.catch(() => {}); return run; };
  const authorized = (req) => !env.AP4M_RAIL_TOKEN || req.headers.authorization === `Bearer ${env.AP4M_RAIL_TOKEN}`;

  return createServer(async (req, res) => {
    const send = (status, body) => { const t = JSON.stringify(body); res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(t); };
    try {
      const url = new URL(req.url, 'http://rail.local');
      if (req.method === 'GET' && url.pathname === '/health') {
        return send(200, { ok: true, channel_id: store.readJson('channel.json')?.channel_id ?? env.AP4M_CHANNEL_ID ?? null,
          pools: Object.fromEntries(Object.entries(pools).map(([k, cap]) => [k, { cap_rlusd: Number(cap) / 1e6, spent_rlusd: Number(store.spent[k] ?? 0n) / 1e6 }])),
          per_payment_cap_rlusd: Number(perPaymentMicro) / 1e6 });
      }
      if (!authorized(req)) return send(401, { ok: false, reason: 'unauthorized' });
      const got = req.method === 'GET' && url.pathname.match(/^\/pay\/(.+)$/);
      if (got) return send(200, store.get(decodeURIComponent(got[1])) ?? { ok: false, reason: 'unknown ref' });
      if (req.method === 'POST' && url.pathname === '/pay') {
        let raw = '';
        for await (const chunk of req) { raw += chunk; if (raw.length > 70_000) return send(413, { ok: false, reason: 'body too large' }); }
        let body;
        try { body = JSON.parse(raw); } catch { return send(400, { ok: false, reason: 'invalid JSON' }); }
        const result = await serial(() => handlePay(body));
        return send(200, url.searchParams.get('public') ? public_(result) : result);
      }
      return send(404, { ok: false, reason: 'not found' });
    } catch (error) {
      return send(500, { ok: false, reason: error.message.slice(0, 200) });
    }
  });
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const env = resolveEnv(join(HERE, '.env'));
  env.AP4M_STATE_DIR ||= join(HERE, 'state', 'rail');
  const log = (line) => console.log(line);
  const store = createStore(env.AP4M_STATE_DIR);
  const live = await connect(env, store, log);
  const server = createRail({ env, store, log, pay: (job) => payOnce(live, env, job) });
  const port = Number(env.PORT || env.AP4M_RAIL_PORT || 4500);
  server.listen(port, env.AP4M_RAIL_HOST || '0.0.0.0', () => log(`[rail] listening on ${port}`));
  const every = Number(env.AP4M_SETTLE_EVERY_MS || 60_000);
  const tick = async () => {
    try { await settleReceipts(live, store, log); } catch (error) { log(`[rail] settle: ${error.message.slice(0, 200)}`); }
    setTimeout(tick, every);
  };
  setTimeout(tick, every);
}
