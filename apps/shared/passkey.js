// WebAuthn in the browser for the participant's approvals. The engine (or UniQdata, through the
// engine) sends options with base64url fields; the authenticator (Touch ID, a phone, a security
// key) answers; we send back base64url fields named as UniQdata names them.

const toBuf = (s) => {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0)).buffer;
};
const toB64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const creds = (list) => (list || []).map((c) => ({ ...c, id: toBuf(c.id) }));

export const passkeySupported = () => !!(window.PublicKeyCredential && navigator.credentials);

// The person's root key comes from the passkey's PRF output for a fixed per-person salt. It stays
// in this page as a non-extractable HKDF key; only hashes and sealed bundles go to the engine.
// Where PRF is missing, a device-bound key kept in this browser stands in for it.
const enc = new TextEncoder();
const sha256 = async (s) => new Uint8Array(await crypto.subtle.digest("SHA-256", typeof s === "string" ? enc.encode(s) : s));
const roots = new Map();
export const prfSalt = (pid) => sha256(`agentrail-vault-v1|${pid}`);

export async function createPasskey(publicKey) {
  const c = await navigator.credentials.create({ publicKey: {
    ...publicKey, challenge: toBuf(publicKey.challenge), user: { ...publicKey.user, id: toBuf(publicKey.user.id) },
    excludeCredentials: creds(publicKey.excludeCredentials), extensions: { ...(publicKey.extensions || {}), prf: {} } } });
  const ext = c.getClientExtensionResults ? c.getClientExtensionResults() : {};
  return { credentialId: toB64u(c.rawId), rawId: toB64u(c.rawId), attestationObject: toB64u(c.response.attestationObject),
           clientDataJson: toB64u(c.response.clientDataJSON),
           transports: c.response.getTransports ? c.response.getTransports() : [], prf: !!(ext.prf && ext.prf.enabled) };
}

async function deviceRoot(pid) {
  const db = await new Promise((ok, no) => {
    const r = indexedDB.open("agentrail-vault", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("keys");
    r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error);
  });
  const op = (mode, f) => new Promise((ok, no) => {
    const t = db.transaction("keys", mode); const r = f(t.objectStore("keys"));
    r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error);
  });
  let key = await op("readonly", (s) => s.get(pid));
  if (!key) {
    const wrap = await crypto.subtle.generateKey({ name: "HMAC", hash: "SHA-256", length: 256 }, false, ["sign"]);
    await op("readwrite", (s) => s.put(wrap, pid));
    key = wrap;
  }
  const ikm = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(`agentrail-vault-v1|${pid}`)));
  return crypto.subtle.importKey("raw", ikm, "HKDF", false, ["deriveKey", "deriveBits"]);
}

// Whether this page holds the person's root key, and whether it came from the passkey.
export const rootKey = (pid) => roots.get(pid) || null;

// K for one trade: HKDF(root, "trade|<order id>|<bundle hash>"), 32 raw bytes. Raw, because the page
// publishes K in EscrowFinish once the person releases it (docs/API.md, push delivery).
async function tradeKeyBytes(pid, orderId, bundleHash) {
  const r = roots.get(pid) || { key: await deviceRoot(pid), from: "device" };
  roots.set(pid, r);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "HKDF", hash: "SHA-256", salt: new Uint8Array(0),
    info: enc.encode(`trade|${orderId}|${bundleHash}`) }, r.key, 256));
}

const hex = (u8) => [...u8].map((b) => b.toString(16).padStart(2, "0")).join("");
// PREIMAGE-SHA-256 crypto-condition for K, as the escrow expects it.
export const escrowCondition = async (k) => `A0258020${hex(await sha256(k))}810120`.toUpperCase();

// Seal a bundle with its trade key, then encrypt it to the institution (ECDH P-256 + HKDF + AES-GCM).
// Returns the record for the engine, the escrow condition, and K, which stays in this page until reveal.
export async function sealBundle(pid, orderId, bundle, institutionJwk) {
  const bundleHash = hex(await sha256(bundle));
  const k = await tradeKeyBytes(pid, orderId, bundleHash);
  const kk = await crypto.subtle.importKey("raw", k, "AES-GCM", false, ["encrypt"]);
  const iv1 = crypto.getRandomValues(new Uint8Array(12));
  const inner = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: iv1 }, kk, bundle));
  const them = await crypto.subtle.importKey("jwk", institutionJwk, { name: "ECDH", namedCurve: "P-256" }, false, []);
  const eph = await crypto.subtle.generateKey({ name: "ECDH", namedCurve: "P-256" }, true, ["deriveBits"]);
  const shared = await crypto.subtle.deriveBits({ name: "ECDH", public: them }, eph.privateKey, 256);
  const hk = await crypto.subtle.importKey("raw", shared, "HKDF", false, ["deriveKey"]);
  const wrap = await crypto.subtle.deriveKey({ name: "HKDF", hash: "SHA-256", salt: new Uint8Array(0),
    info: enc.encode(`seal|${orderId}|${bundleHash}`) }, hk, { name: "AES-GCM", length: 256 }, false, ["encrypt"]);
  const iv2 = crypto.getRandomValues(new Uint8Array(12));
  const body = new Uint8Array(iv1.length + inner.length); body.set(iv1); body.set(inner, iv1.length);
  const outer = await crypto.subtle.encrypt({ name: "AES-GCM", iv: iv2 }, wrap, body);
  const pub = await crypto.subtle.exportKey("jwk", eph.publicKey);
  return { record: { order_id: orderId, bundle_hash: bundleHash, epk: { kty: pub.kty, crv: pub.crv, x: pub.x, y: pub.y },
                     iv: toB64u(iv2), sealed: toB64u(outer), root: roots.get(pid).from },
           condition: await escrowCondition(k), key_b64u: toB64u(k) };
}

export async function signWithPasskey(publicKey, pid) {
  const salt = pid ? await prfSalt(pid) : null;
  const a = await navigator.credentials.get({ publicKey: {
    ...publicKey, challenge: toBuf(publicKey.challenge), allowCredentials: creds(publicKey.allowCredentials),
    ...(salt ? { extensions: { ...(publicKey.extensions || {}), prf: { eval: { first: salt } } } } : {}) } });
  const ext = a.getClientExtensionResults ? a.getClientExtensionResults() : {};
  const first = ext.prf && ext.prf.results && ext.prf.results.first;
  if (pid && first) {
    roots.set(pid, { key: await crypto.subtle.importKey("raw", first, "HKDF", false, ["deriveKey", "deriveBits"]), from: "passkey" });
  }
  const out = { credentialId: toB64u(a.rawId), rawId: toB64u(a.rawId), authenticatorData: toB64u(a.response.authenticatorData),
                clientDataJson: toB64u(a.response.clientDataJSON), signature: toB64u(a.response.signature) };
  if (a.response.userHandle) out.userHandle = toB64u(a.response.userHandle);
  if (publicKey.challengeId) out.challengeId = publicKey.challengeId;
  return out;
}
