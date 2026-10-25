// RLUSD has 18 decimals. Dependency-free conversions so the dry run and tests need no packages.
const DECIMALS = 18n;
const SCALE = 10n ** DECIMALS;

export function toWei(rlusd) {
  const text = String(rlusd).trim();
  if (!/^\d+(\.\d{1,18})?$/.test(text)) throw new Error(`invalid RLUSD amount: ${text}`);
  const [whole, fraction = ''] = text.split('.');
  return BigInt(whole) * SCALE + BigInt(fraction.padEnd(18, '0'));
}

export function fromWei(wei) {
  const value = BigInt(wei);
  const whole = value / SCALE;
  const fraction = (value % SCALE).toString().padStart(18, '0').replace(/0+$/, '');
  return fraction ? `${whole}.${fraction}` : `${whole}`;
}
