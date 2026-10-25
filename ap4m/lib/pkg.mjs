// Package hashing. Keys are sorted so the hash survives the SDK's canonical JSON round trip.
import { createHash } from 'node:crypto';

export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function packageSha256(pkg) {
  return createHash('sha256').update(canonical(pkg)).digest('hex');
}

export function sealPackage(pkg) {
  return { package: pkg, sha256: packageSha256(pkg) };
}

// Returns { ok, expected, actual } so the caller can log why a package was rejected.
export function verifySealed(sealed) {
  if (!sealed || typeof sealed !== 'object' || !sealed.package || typeof sealed.sha256 !== 'string') {
    return { ok: false, expected: null, actual: null };
  }
  const actual = packageSha256(sealed.package);
  return { ok: actual === sealed.sha256, expected: sealed.sha256, actual };
}
