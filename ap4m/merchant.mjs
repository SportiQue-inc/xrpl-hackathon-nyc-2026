// Synthetic "clinic record export" merchant.
//
//   GET /export/:pseudonym/:week   402 with the offer (price per call, payTo, purpose, x402 resource URL)
//
// Payment uses the AP4M x402 toolkit. createX402Merchant serves exactly one fixed-price GET /resource,
// so each export package gets its own x402 instance on its own loopback port (MERCHANT_PORT + 1 + n).
// The agent pays that resource URL; the merchant redeems the Voucher on-chain and returns the sealed package.
// DRY_RUN=1 swaps the x402 instances for a fake redeem at /dry/resource/:id on the same port.
import { createServer } from 'node:http';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { findListing, LISTINGS, packageId, STUDY, syntheticPackage } from './lib/catalog.mjs';
import { DRY_PAYOUT, fakeTxHash, fakeVerifyVoucher } from './lib/dry.mjs';
import { payoutAddress, resolveEnv, setting } from './lib/env.mjs';
import { sealPackage } from './lib/pkg.mjs';
import { toWei } from './lib/units.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

function send(response, status, body, headers = {}) {
  const encoded = JSON.stringify(body);
  response.writeHead(status, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(encoded), 'Cache-Control': 'no-store', ...headers });
  response.end(encoded);
}

function listen(server, port, host) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => { server.off('error', reject); resolve(server.address().port); });
  });
}

/**
 * @param {{ dryRun: boolean, env: Record<string,string>, port?: number, host?: string, log?: (line: string) => void }} options
 *   port 0 picks a free port (tests); live mode needs a fixed port because x402 instances use port + 1 + n.
 */
export async function startMerchant({ dryRun, env, port, host = '127.0.0.1', log = console.log }) {
  const payout = dryRun ? DRY_PAYOUT : payoutAddress(env);
  const basePort = port ?? Number(setting(env, 'MERCHANT_PORT'));
  const instances = new Map(); // packageId -> { resourceUrl, close }
  const dryRedeemed = new Map(); // channelId -> cumulative wei (fake ledger)
  let network = 'eip155:1449000';
  let asset = null;

  if (!dryRun) {
    for (const name of ['MERCHANT_ID', 'MERCHANT_SUBMITTER_KEY']) if (!env[name]) throw new Error(`${name} is not set`);
    if (!payout) throw new Error('MERCHANT_PAYOUT (or MERCHANT_PAYOUT_ADDRESS) is not set');
    const { ethers } = await import('ethers');
    const { createX402Merchant, loadX402Context } = await import(pathToFileURL(join(HERE, 'vendor/ap4m-x402.mjs')).href);
    const apiUrl = setting(env, 'AP4M_API_URL');
    const context = await loadX402Context(apiUrl);
    const config = await (await fetch(`${apiUrl}/public/config`)).json();
    const provider = new ethers.JsonRpcProvider(env.AP4M_RPC_URL || config.network.rpcUrl);
    const submitter = new ethers.Wallet(env.MERCHANT_SUBMITTER_KEY, provider);
    network = context.network;
    asset = context.x402.token;
    for (const [index, listing] of LISTINGS.entries()) {
      const id = packageId(listing.pseudonym, listing.week);
      const instancePort = basePort + 1 + index;
      const resourceUrl = `http://127.0.0.1:${instancePort}/resource`;
      const merchant = createX402Merchant({
        context, provider, submitter,
        stateDirectory: join(HERE, 'state', `merchant-${id}`),
        resourceUrl,
        merchantParticipantId: env.MERCHANT_ID,
        payout,
        amount: toWei(listing.priceRlusd).toString(),
        content: sealPackage(syntheticPackage(listing.pseudonym, listing.week)),
      });
      await listen(merchant.server, instancePort, '127.0.0.1');
      instances.set(id, { resourceUrl, close: () => merchant.close() });
    }
  }

  const server = createServer((request, response) => {
    handle(request, response).catch((error) => send(response, 500, { error: 'merchant_error', detail: error.message }));
  });

  async function handle(request, response) {
    const url = new URL(request.url, 'http://merchant.local');
    const exportMatch = request.method === 'GET' && url.pathname.match(/^\/export\/([A-Za-z0-9-]{1,32})\/(\d{1,3})$/);
    if (exportMatch) {
      const listing = findListing(exportMatch[1], exportMatch[2]);
      if (!listing) return send(response, 404, { error: 'no_such_export' });
      const id = packageId(listing.pseudonym, listing.week);
      const resourceUrl = dryRun ? `${base}/dry/resource/${id}` : instances.get(id).resourceUrl;
      return send(response, 402, {
        x402Version: 2,
        error: 'payment_required',
        offer: {
          package_id: id,
          pseudonym: listing.pseudonym,
          week: listing.week,
          items: [...STUDY.items],
          purpose: { study: STUDY.id, duo: STUDY.duo, description: 'participation compensation for a synthetic study export' },
          price_rlusd: listing.priceRlusd,
          pay_to: payout,
          network,
          asset,
          scheme: 'ap4m-x402 batch-settlement (Channel + EIP-712 Voucher)',
          resource_url: resourceUrl,
        },
      });
    }
    const dryMatch = dryRun && request.method === 'GET' && url.pathname.match(/^\/dry\/resource\/([a-z0-9-]{1,64})$/);
    if (dryMatch) {
      const listing = LISTINGS.find((entry) => packageId(entry.pseudonym, entry.week) === dryMatch[1]);
      if (!listing) return send(response, 404, { error: 'no_such_export' });
      const header = request.headers['x-dry-payment'];
      if (!header) return send(response, 402, { error: 'payment_required' });
      let payment;
      try { payment = JSON.parse(header); } catch { return send(response, 400, { error: 'invalid_payment' }); }
      const { voucher, signature } = payment;
      if (!voucher || !fakeVerifyVoucher(voucher, signature)) return send(response, 400, { error: 'invalid_payment' });
      const previous = dryRedeemed.get(voucher.channelId) ?? 0n;
      if (BigInt(voucher.cumulativeAmount) - previous !== toWei(listing.priceRlusd)) return send(response, 400, { error: 'wrong_amount' });
      dryRedeemed.set(voucher.channelId, BigInt(voucher.cumulativeAmount));
      return send(response, 200, {
        resource: sealPackage(syntheticPackage(listing.pseudonym, listing.week)),
        transaction: fakeTxHash('VoucherRedeemed', voucher.channelId, voucher.cumulativeAmount, signature),
      });
    }
    return send(response, 404, { error: 'not_found' });
  }

  const boundPort = await listen(server, basePort, host);
  const base = `http://${host}:${boundPort}`;
  log(`[merchant] ${dryRun ? 'DRY_RUN ' : ''}serving ${base}/export/:pseudonym/:week, payout ${payout}`);
  return {
    url: base,
    async close() {
      await new Promise((resolve) => server.close(() => resolve()));
      for (const instance of instances.values()) await instance.close();
    },
  };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const env = resolveEnv(join(HERE, '.env'));
  const merchant = await startMerchant({ dryRun: env.DRY_RUN === '1', env }).catch((error) => {
    console.error(`[merchant] failed to start: ${error.message}`);
    process.exit(1);
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => { merchant.close().finally(() => process.exit(0)); });
}
