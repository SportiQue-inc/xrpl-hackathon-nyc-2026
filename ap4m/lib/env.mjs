// Minimal .env reader (no dotenv dependency). Values are never printed.
import { existsSync, readFileSync } from 'node:fs';

export function loadEnvFile(path) {
  const values = {};
  if (!existsSync(path)) return values;
  for (const line of readFileSync(path, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    values[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
  return values;
}

// Process environment wins over the file, so a single run can override one value.
export function resolveEnv(path) {
  return { ...loadEnvFile(path), ...process.env };
}

export function payoutAddress(env) {
  return env.MERCHANT_PAYOUT || env.MERCHANT_PAYOUT_ADDRESS || '';
}

export const DEFAULTS = Object.freeze({
  AP4M_API_URL: 'https://hackathon.ap4m.build',
  MERCHANT_PORT: '4400',
  PER_CALL_CAP_RLUSD: '0.10',
  BUDGET_RLUSD: '0.20',
});

export function setting(env, name) {
  return env[name] || DEFAULTS[name];
}
