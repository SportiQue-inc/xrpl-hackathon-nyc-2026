// Shared pieces for the before/after demo: synthetic data, a tiny DOM helper, and the channel that
// links the UniQLab page and the UniQdata page (same browser, any window or iframe).
// All names and numbers are synthetic. Amounts are in the display unit (shared/ui.js) on XRPL Testnet.
import { DISPLAY_UNIT } from "../shared/ui.js";

export const MODE = new URLSearchParams(location.search).get("mode") === "after" ? "after" : "before";

export const INST = { name: "Northside Sleep Lab", short: "Northside", kind: "University hospital (synthetic)", irb: "IRB-SYN-2026-014" };

// One institution, several sub-projects. Today each is its own contract; with agents they share one relationship.
export const SUBS = [
  { id: "S1", name: "Sleep and fatigue", weeks: 6, items: ["hr", "fatigue"], status: "Live", pis: "Dr. Han" },
  { id: "S2", name: "Night-shift recovery", weeks: 6, items: ["hr", "sleep"], status: "Live", pis: "Dr. Park" },
  { id: "S3", name: "Clinic blood pressure follow-up", weeks: 6, items: ["bp"], status: "Live", pis: "Dr. Lee" },
];
export const NEW_SUB = { id: "S4", name: "Caffeine and sleep", weeks: 4, items: ["hr", "caffeine"], status: "New", pis: "Dr. Han" };

export const ITEMS = {
  hr: { label: "Heart rate", source: "Wearable", price: 3, sensitive: false },
  fatigue: { label: "Fatigue survey", source: "Survey app", price: 2, sensitive: false },
  sleep: { label: "Sleep stages", source: "Wearable", price: 3, sensitive: false },
  bp: { label: "Clinic blood pressure", source: "Clinic export", price: 5, sensitive: true },
  caffeine: { label: "Caffeine diary", source: "Survey app", price: 2, sensitive: false, newPurpose: true },
};

export const PEOPLE = ["P-014", "P-015", "P-016", "P-017", "P-018", "P-019"];
export const HERO = "P-017";
export const OPEN_STUDIES = 41;

export const rl = (n) => `${Number(n).toFixed(2)} ${DISPLAY_UNIT}`;
export const weekPrice = (sub) => sub.items.reduce((a, k) => a + ITEMS[k].price, 0);
export const subTotal = (sub) => weekPrice(sub) * sub.weeks;

// ---------- DOM ----------
export function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}
export const tag = (text, tone = "gray") => h("span", { class: `tag ${tone}` }, text);

// ---------- link between the two pages ----------
// BroadcastChannel reaches every same-origin window and iframe; the storage event is the fallback.
const NAME = `agentrail-demo-${MODE}`;
const chan = "BroadcastChannel" in window ? new BroadcastChannel(NAME) : null;
const handlers = [];
export function send(type, data = {}) {
  const msg = { type, data, at: Date.now() };
  if (chan) chan.postMessage(msg);
  else try { localStorage.setItem(NAME, JSON.stringify(msg)); } catch { /* private mode */ }
}
export function listen(fn) { handlers.push(fn); }
if (chan) chan.onmessage = (e) => handlers.forEach((fn) => fn(e.data));
else window.addEventListener("storage", (e) => {
  if (e.key === NAME && e.newValue) handlers.forEach((fn) => fn(JSON.parse(e.newValue)));
});
// The stage page asks both pages to start over.
listen((m) => { if (m.type === "reset") location.reload(); });

export function toast(root, text) {
  const t = h("div", { class: "toast" }, text);
  root.append(t);
  setTimeout(() => t.classList.add("gone"), 2600);
  setTimeout(() => t.remove(), 3100);
}
