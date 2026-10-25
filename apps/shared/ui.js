// Small DOM helpers, wording and the ledger receipt panel (R3), shared by both apps.

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  append(el, kids);
  return el;
}

function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k === null || k === undefined || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}

export let UNIT = "test USD";
export function setSettlementAsset(asset) {
  if (asset === "USD" || asset === "XRP") UNIT = asset === "USD" ? "test USD" : "Test XRP";
}
export const xrp = (n) => `${(Math.round((n || 0) * 100) / 100).toFixed(2)} ${UNIT}`;
export const short = (s, a = 4, b = 4) => (s && s.length > a + b + 1 ? `${s.slice(0, a)}…${b ? s.slice(-b) : ""}` : s || "");
export const sum = (xs, f = (x) => x) => xs.reduce((a, x) => a + (f(x) || 0), 0);
export const weeksLabel = (ws) => {
  if (!ws || !ws.length) return "";
  const s = [...ws].sort((a, b) => a - b);
  const contiguous = s.every((w, i) => i === 0 || w === s[i - 1] + 1);
  return contiguous && s.length > 2 ? `Weeks ${s[0]}–${s[s.length - 1]}` : `${s.length > 1 ? "Weeks" : "Week"} ${s.join(", ")}`;
};

export function ago(ts) {
  if (!ts) return "—";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
// Ledger deadlines (respond_by, CancelAfter) are seconds since the Ripple epoch, 2000-01-01.
export const ledgerDay = (t) => day(t + 946684800);
export const day = (ts) => new Date(ts * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });

export function tag(text, tone = "gray", attrs = {}) {
  return h("span", { class: `ar-tag ${tone}`, ...attrs }, text);
}

const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6.5 6.5 0 0 1 3.5 6"/>',
  flag: '<path d="M5 21V4h11l-2 4 2 4H5"/>',
  bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4l2-2Z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  back: '<path d="m15 6-6 6 6 6"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  ext: '<path d="M7 17 17 7M9 7h8v8"/>',
  clock: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
  shield: '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z"/>',
  rounds: '<path d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3"/><path d="M18 3v4h-4M6 21v-4h4"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  wallet: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M16 12h2"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
};
export function icon(name, size = 18) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  s.setAttribute("width", size);
  s.setAttribute("height", size);
  s.setAttribute("fill", "none");
  s.setAttribute("stroke", "currentColor");
  s.setAttribute("stroke-width", "1.8");
  s.setAttribute("stroke-linecap", "round");
  s.setAttribute("stroke-linejoin", "round");
  s.innerHTML = ICONS[name] || "";
  return s;
}

// ---------- wording shared by both sides (designer brief: common rules) ----------

// Weekly contribution state, same names and colours on the phone and in the console.
export const WEEK_STATE = {
  requested: { label: "Requested", tone: "outline" },
  escrowed: { label: "Locked", tone: "blue" },
  waiting: { label: "Locked", tone: "blue" },
  contributed: { label: "Delivered", tone: "green" },
  delivered: { label: "Delivered", tone: "green" },
  withheld: { label: "Withheld", tone: "gray" },
  refunded: { label: "Refunded to study", tone: "gray" },
  not_in_protocol: { label: "Not in protocol", tone: "ghost" },
  held: { label: "On your device", tone: "gray" },
  missing: { label: "No data", tone: "ghost" },
};

// Held 20% part of a round, and the completion bonus.
export function holdbackState(hb) {
  if (hb.kind === "bonus") {
    if (hb.status === "released") return { label: "Bonus paid", tone: "green" };
    if (hb.status === "returned" || hb.status === "returning") return { label: "Returned to study", tone: "gray" };
    return { label: "Bonus waiting", tone: "blue" };
  }
  return ({
    held: { label: "In review", tone: "blue" },
    suspected: { label: "Review extended", tone: "amber" },
    released: { label: "Paid", tone: "green" },
    withheld: { label: "Not paid", tone: "gray" },
    returning: { label: "Returned to study", tone: "gray" },
    returned: { label: "Returned to study", tone: "gray" },
  })[hb.status] || { label: hb.status, tone: "gray" };
}

export const ITEM_CLASS = {
  auto: { label: "Inside your consent", tone: "blue" },
  approval: { label: "Needs your OK", tone: "amber" },
  blocked: { label: "Not allowed", tone: "gray" },
};

export const SIGNAL = {
  copied_series: "looks copied from another contribution",
  impossible_value: "has values a body or device cannot produce",
  quality: "is below the data standard announced in the request",
};

// XRPL transaction kind -> one readable line (R3 titles)
export const TX_TITLE = {
  EscrowCreate: "Payment locked",
  EscrowFinish: "Participation payment released",
  EscrowCancel: "Locked payment returned to the study",
  Payment: "Study budget approved by 2 signers",
  MPTokenIssuanceCreate: "Access licence issued to the study",
  Clawback: "Access licence taken back",
  CredentialCreate: "Ethics review credential issued",
};

// ---------- ledger link and receipt panel (R3) ----------

export function txLink(tx, receipt = {}) {
  if (!tx || !tx.tx) return null;
  return h("button", { class: "ar-tx", type: "button", onclick: (e) => { e.stopPropagation(); openReceipt({ ...receipt, tx: tx.tx, url: tx.url }); } },
    "Tx ", h("span", { class: "h" }, short(tx.tx)), " · ", h("span", { class: "v" }, "View ↗"));
}

let panel = null;
export function openReceipt(r, host = document.querySelector(".ar") || document.body) {
  closeReceipt();
  const mock = !r.url;
  const scrim = h("div", { class: "ar-scrim", onclick: closeReceipt });
  const copy = h("button", { class: "ar-link small", onclick: () => navigator.clipboard?.writeText(r.tx) }, "Copy");
  const body = h("div", { class: "ar-panel", role: "dialog", "aria-label": "Ledger receipt" },
    h("div", { class: "spread" }, h("span", { class: "small muted" }, "Ledger receipt"),
      h("button", { class: "ar-iconbtn", onclick: closeReceipt, "aria-label": "Close" }, icon("x", 16))),
    h("h2", {}, r.title || TX_TITLE[r.kind] || "Recorded on the ledger"),
    mock ? h("div", { class: "ar-banner gray" }, "Practice ledger · no explorer link")
         : h("div", { class: "ar-banner green" }, icon("check", 16), "Confirmed on XRPL Testnet"),
    h("dl", {},
      r.kind && [h("dt", {}, "Transaction"), h("dd", {}, r.kind + (r.kindNote ? ` · ${r.kindNote}` : ""))],
      r.amount != null && [h("dt", {}, "Amount"), h("dd", {}, xrp(r.amount))],
      r.from && [h("dt", {}, "From"), h("dd", {}, r.from)],
      r.to && [h("dt", {}, "To"), h("dd", {}, r.to)],
      [h("dt", {}, "Tx hash"), h("dd", { class: "mono" }, r.tx, " ", copy)],
      r.memo && [h("dt", {}, "Reference"), h("dd", { class: "mono" }, r.memo)],
      [h("dt", {}, "Network"), h("dd", {}, mock ? "Practice ledger (mock)" : "XRPL Testnet")],
    ),
    h("p", { class: "small muted" }, "Your data and review results are not on the ledger."),
    h("div", { class: "row", style: { marginTop: "auto" } },
      !mock && h("a", { class: "ar-btn primary grow", href: r.url, target: "_blank", rel: "noopener" }, "Open in explorer ↗"),
      h("button", { class: "ar-btn grow", onclick: closeReceipt }, "Close")),
  );
  panel = h("div", {}, scrim, body);
  host.append(panel);
}
export function closeReceipt() {
  if (panel) panel.remove();
  panel = null;
}

// Replace a node's children, keeping scroll position.
export function render(el, ...kids) {
  el.replaceChildren();
  append(el, kids);
}

export function banner(tone, ...kids) {
  return h("div", { class: `ar-banner ${tone}` }, ...kids);
}

// A public demo deploy answers only visitors with the access code; ask for it in place of an error.
export function codeGate(what = "your agent") {
  const input = h("input", { type: "password", placeholder: "Access code", class: "ar-input",
    style: { flex: "1", font: "inherit", border: "1px solid #d0d5dd", borderRadius: "10px", padding: "10px 12px" } });
  const submit = (e) => {
    e.preventDefault();
    const u = new URL(location.href);
    u.searchParams.set("code", input.value.trim());
    location.href = u.toString();
  };
  return h("form", { class: "col", style: { gap: "10px" }, onsubmit: submit },
    banner("blue", `Enter the demo access code to reach ${what}.`),
    h("div", { class: "row", style: { gap: "8px" } }, input, h("button", { class: "ar-btn primary", type: "submit" }, "Continue")));
}

// Run an engine call with a busy state on a button; returns the result or null on error.
export async function busy(btn, label, fn, onError) {
  const old = btn ? [...btn.childNodes] : null;
  if (btn) {
    btn.disabled = true;
    btn.replaceChildren(h("span", { class: "ar-spin" }), " ", label);
  }
  try {
    return await fn();
  } catch (e) {
    if (onError) onError(e);
    return null;
  } finally {
    if (btn && btn.isConnected) {
      btn.disabled = false;
      btn.replaceChildren(...old);
    }
  }
}
