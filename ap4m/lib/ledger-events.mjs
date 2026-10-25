// Decoder for the PaymentLedger VoucherRedeemed event, dependency-free.
//
// Signature from the AP4M SDK ABI (@ap4m/sdk dist/participant-requests.js):
//   VoucherRedeemed(bytes32 indexed channelId, bytes32 indexed claimId, bytes32 indexed voucherDigest,
//                   bytes32 allocationId, address agent, bytes32 merchantId, address payout, address submitter,
//                   uint256 previousCumulativeAmount, uint256 cumulativeAmount, uint256 amount)
// keccak256 of the canonical form is 0xe3de5c37..., which is topic0 of the logs the deployed ledger emits.
// Note: the XRPL EVM RPC's web3_sha3 hashes its parameter as UTF-8 text, so passing it the hex-encoded
// signature yields 0xef5859fc..., a hash of the hex characters, not of the signature.
import { keccak256 } from './keccak.mjs';

export const VOUCHER_REDEEMED_SIGNATURE =
  'VoucherRedeemed(bytes32,bytes32,bytes32,bytes32,address,bytes32,address,address,uint256,uint256,uint256)';
export const VOUCHER_REDEEMED_TOPIC = keccak256(VOUCHER_REDEEMED_SIGNATURE);

const DATA_FIELDS = ['allocationId', 'agent', 'merchantId', 'payout', 'submitter', 'previousCumulativeAmount', 'cumulativeAmount', 'amount'];
const ADDRESS_FIELDS = new Set(['agent', 'payout', 'submitter']);
const UINT_FIELDS = new Set(['previousCumulativeAmount', 'cumulativeAmount', 'amount']);

/** Decode one raw log ({ address, topics, data }); returns null when it is not a VoucherRedeemed log. */
export function decodeVoucherRedeemed(log) {
  if (!log?.topics || log.topics[0]?.toLowerCase() !== VOUCHER_REDEEMED_TOPIC || log.topics.length !== 4) return null;
  const data = String(log.data).replace(/^0x/, '');
  if (data.length !== DATA_FIELDS.length * 64) throw new Error('VoucherRedeemed data has the wrong length');
  const event = {
    ledger: log.address?.toLowerCase(),
    channelId: log.topics[1].toLowerCase(),
    claimId: log.topics[2].toLowerCase(),
    voucherDigest: log.topics[3].toLowerCase(),
  };
  DATA_FIELDS.forEach((name, index) => {
    const word = data.slice(index * 64, (index + 1) * 64);
    if (ADDRESS_FIELDS.has(name)) event[name] = `0x${word.slice(24)}`;
    else if (UINT_FIELDS.has(name)) event[name] = BigInt(`0x${word}`);
    else event[name] = `0x${word}`;
  });
  return event;
}

/** All VoucherRedeemed events a transaction receipt emitted from the given ledger. */
export function voucherRedeemedEvents(receipt, ledger) {
  return (receipt?.logs ?? [])
    .filter((log) => !ledger || log.address?.toLowerCase() === ledger.toLowerCase())
    .map(decodeVoucherRedeemed)
    .filter(Boolean);
}
