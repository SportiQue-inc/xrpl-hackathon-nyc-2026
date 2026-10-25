// Research contracts (docs/RESEARCH_CONTRACTS.md). Keys are made in this browser with WebCrypto
// Ed25519 and kept here; only the public half goes to the engine.
import { DISPLAY_UNIT } from "../shared/ui.js";

const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
const b64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window: key lives for this page only */ } },
};

export async function key(name) {
  const saved = store.get(`ar-contract-key:${name}`);
  if (saved) {
    const priv = await crypto.subtle.importKey("pkcs8", unb64(saved.pkcs8), { name: "Ed25519" }, false, ["sign"]);
    return { priv, publicHex: saved.publicHex, meta: saved.meta || {} };
  }
  const pair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
  const publicHex = hex(await crypto.subtle.exportKey("raw", pair.publicKey));
  store.set(`ar-contract-key:${name}`, { pkcs8: b64(await crypto.subtle.exportKey("pkcs8", pair.privateKey)), publicHex, meta: {} });
  return { priv: pair.privateKey, publicHex, meta: {} };
}

export function remember(name, meta) {
  const saved = store.get(`ar-contract-key:${name}`);
  if (saved) store.set(`ar-contract-key:${name}`, { ...saved, meta: { ...(saved.meta || {}), ...meta } });
}

export async function sign(k, text) {
  return hex(await crypto.subtle.sign({ name: "Ed25519" }, k.priv, new TextEncoder().encode(text)));
}

export async function api(method, path, body, headers = {}) {
  const res = await fetch(path, { method, headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body) });
  const out = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof out.detail === "string" ? out.detail : `${res.status}`);
  return out;
}

export async function signIn(sub, k) {
  const { nonce } = await api("POST", "/api/auth/challenge", { sub });
  const t = await api("POST", "/api/auth/token", { sub, nonce, signature: await sign(k, `agentrail-login|agentrail-api|${sub}|${nonce}`) });
  return { Authorization: `Bearer ${t.access_token}` };
}

// The message a member signs for one approval or a withdrawal (research_contracts.action_message).
export async function actionText(pid, cid, action, consentHash) {
  const h = hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${action}|${cid}|${consentHash}`)));
  return `agentrail-consent|${pid}|${h}`;
}

export const amount = (micro) => `${((micro || 0) / 1e6).toLocaleString(undefined, { maximumFractionDigits: 6 })} ${DISPLAY_UNIT}`;
export const FOOTNOTE = `Testnet: a test USD token stands in for ${DISPLAY_UNIT}. Test accounts only, no real health data.`;
export const ITEM_LABELS = { "sleep.daily": "Sleep (wearable)", "activity.daily": "Activity (wearable)",
  "heart_rate.daily": "Resting heart rate (wearable)", "fatigue.survey": "Fatigue survey",
  "blood_pressure.daily": "Blood pressure (clinic visit, sensitive)" };
export const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "class" ? (e.className = v) : k.startsWith("on") ? e.addEventListener(k.slice(2), v) : e.setAttribute(k, v);
  for (const c of kids.flat()) e.append(c instanceof Node ? c : document.createTextNode(c ?? ""));
  return e;
};
export const tx = (t) => (t && t.url ? el("a", { href: t.url, target: "_blank", rel: "noopener" }, t.tx.slice(0, 10) + "…") : t && t.tx ? t.tx.slice(0, 10) + "…" : "");
