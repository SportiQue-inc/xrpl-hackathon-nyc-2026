// DRY_RUN stand-ins: a fake signer and a fake redeem. No chain, no AP4M service, no keys.
import { createHash, createHmac, randomUUID } from 'node:crypto';

import { canonical } from './pkg.mjs';

export const DRY_PAYOUT = '0x000000000000000000000000000000000000d4a7';
export const DRY_AGENT = '0x000000000000000000000000000000000000a6e7';
const DRY_KEY = 'dry-run-only-not-a-key';

// A fresh fake Channel per run, so the fake ledger's cumulative amount starts at zero each time.
export function dryChannelId() {
  return fakeTxHash('dry-channel', randomUUID());
}

export function fakeSignVoucher(voucher) {
  return `0x${createHmac('sha256', DRY_KEY).update(canonical(voucher)).digest('hex')}`;
}

export function fakeVerifyVoucher(voucher, signature) {
  return fakeSignVoucher(voucher) === signature;
}

export function fakeTxHash(...parts) {
  return `0x${createHash('sha256').update(parts.join('|')).digest('hex')}`;
}
