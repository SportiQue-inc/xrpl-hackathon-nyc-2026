import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { keccak256 } from '../lib/keccak.mjs';
import { decodeVoucherRedeemed, VOUCHER_REDEEMED_TOPIC, voucherRedeemedEvents } from '../lib/ledger-events.mjs';
import { fromWei } from '../lib/units.mjs';

const { log } = JSON.parse(readFileSync(new URL('./fixtures/voucher-redeemed-log.json', import.meta.url), 'utf8'));

test('keccak256 matches known vectors', () => {
  assert.equal(keccak256(''), '0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470');
  assert.equal(keccak256('Transfer(address,address,uint256)'), '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef');
});

test('VoucherRedeemed topic0 from the SDK signature equals the real ledger log', () => {
  assert.equal(VOUCHER_REDEEMED_TOPIC, '0xe3de5c3755abd99a01530fd79b85708f309453f6d26eb9bb5dde4c14cd5f7175');
  assert.equal(log.topics[0], VOUCHER_REDEEMED_TOPIC);
});

test('decodes a real XRPL EVM Testnet VoucherRedeemed log', () => {
  const event = decodeVoucherRedeemed(log);
  assert.equal(event.ledger, '0xcab42800a5ecf0d253fa2581bb3334b4daefae91');
  assert.equal(event.channelId, '0x1b1ff1bde3e03fc94da5a21983faa75fd32ab81b4f961cfc8003dedba4704583');
  assert.equal(event.claimId, '0x3a8c852ad940ef83f01a6dba14e56de17d42b8fd2de4e7cb66b7934f6dffaf23');
  assert.equal(event.allocationId, '0xe4b74b58fcd7fdcf3dbc1630d5a28b1e0e04fac4ad52993b01bf2bae8636fa43');
  assert.equal(event.payout, '0xc46d99faae8482f3876f49cae56b9f09057ce2b8');
  assert.equal(event.submitter, '0xbafce1aebbcca3b073b7e680dfaff6d4ad2e1709');
  assert.equal(event.agent, '0x8ed22266368e78820da1e82e7b35ce2feacf38e6');
  assert.equal(fromWei(event.amount), '0.01');
  assert.equal(fromWei(event.previousCumulativeAmount), '0.03');
  assert.equal(fromWei(event.cumulativeAmount), '0.04');
  assert.equal(event.cumulativeAmount - event.previousCumulativeAmount, event.amount);
});

test('ignores other events and other contracts', () => {
  assert.equal(decodeVoucherRedeemed({ ...log, topics: ['0x' + '0'.repeat(64), ...log.topics.slice(1)] }), null);
  assert.equal(voucherRedeemedEvents({ logs: [log] }, '0x0000000000000000000000000000000000000001').length, 0);
  assert.equal(voucherRedeemedEvents({ logs: [log] }, '0xcAB42800A5ECF0D253Fa2581Bb3334B4DAEfaE91').length, 1);
});
