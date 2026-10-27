import { FOOTNOTE, ITEM_LABELS, actionText, amount, api, el, key, payLink, payState, remember, sign, signIn, tx } from "./contracts.js";

const $ = (s) => document.querySelector(s);
$("#foot").textContent = FOOTNOTE;
const q = new URLSearchParams(location.search);
const cid = q.get("contract");
const invite = q.get("invite");
const name = `member:${cid}`;

async function start() {
  if (!cid) { $("#terms").replaceChildren(el("p", { class: "err" }, "Open the invite link you were given.")); return; }
  const c = await api("GET", `/api/contracts/${cid}`);
  const t = c.terms;
  $("#terms").replaceChildren(el("h2", {}, t.title), el("p", { class: "sub" }, `${t.institution} · IRB ${t.irb_approval} (${t.irb_checked}) · weeks ${t.weeks[0]}-${t.weeks[1]}`),
    el("p", {}, t.payment_rail === "ap4m"
      ? `${amount(t.price_per_item_drops)} per item per week, paid through AP4M (XRPL EVM Testnet) as soon as your agent delivers each week${t.round_every_s ? `; a week runs every ${t.round_every_s} s` : ""}. ${c.members} of ${t.capacity} joined.`
      : `${amount(t.price_per_item_drops)} per item per week, paid to you on the ledger when your agent releases each week. ${c.members} of ${t.capacity} joined.`),
    t.summary ? el("p", { class: "note" }, t.summary) : "");
  const k = await key(name);
  if (k.meta.pid) return mine();
  if (!invite) { $("#terms").append(el("p", { class: "err" }, "The invite code is missing from the link.")); return; }
  if (t.payment_rail !== "ap4m") $("#payout-row").hidden = true;
  for (const i of t.items) $("#items").append(el("label", {}, el("input", { type: "checkbox", name: "item", value: i, checked: "" }), ITEM_LABELS[i] || i));
  $("#join").hidden = false;
  $("#form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    $("#err").textContent = "";
    try {
      const s = await api("POST", `/api/contracts/${cid}/join/start`, { invite_code: invite, public_key: k.publicHex, items: f.getAll("item"), automation: f.get("automation"), ...(f.get("payout") ? { payout_address: f.get("payout") } : {}) });
      const weeks = f.get("testdata") ? Array.from({ length: t.weeks[1] - t.weeks[0] + 1 }, (_, i) => t.weeks[0] + i) : [];
      await api("POST", `/api/contracts/${cid}/join/complete`, { pid: s.pid, signature: await sign(k, s.sign), generate_test_weeks: weeks });
      remember(name, { pid: s.pid, consent_hash: s.consent_hash });
      $("#join").hidden = true;
      mine();
    } catch (e) { $("#err").textContent = e.message; }
  });
}

async function mine() {
  const k = await key(name);
  const pid = k.meta.pid;
  const h = await signIn(pid, k);
  const v = await api("GET", `/api/p/${pid}/contracts`, undefined, h);
  const c = v.contracts.find((x) => x.contract === cid);
  const box = $("#mine");
  box.hidden = false;
  // A week question (kind "round") confirms one week. A scope question (kind "scope", no week) asks to widen
  // your consent to items you did not agree to: allow them, or decline (approve with no items; the server
  // then closes the question without widening consent).
  const answer = async (e, a, picked) => {
    e.target.disabled = true;
    const text = await actionText(pid, cid, `approve:${a.request_id}:${[...picked].sort().join(",")}`, c.consent_hash);
    await api("POST", `/api/p/${pid}/contracts/${cid}/requests/${a.request_id}/approve`, { items: picked, signature: await sign(k, text) }, h).catch((x) => alert(x.message));
    mine();
  };
  const asks = c.pending_approvals.map((a) => {
    const items = a.items.map((i) => ITEM_LABELS[i] || i).join(", ");
    if (a.kind === "scope" || a.week == null)
      return el("div", { class: "row" }, `New items asked, outside what you agreed to: ${items}`,
        el("button", { class: "ar-btn sm primary", onclick: (e) => answer(e, a, a.items) }, "Allow these items"),
        el("button", { class: "ar-btn sm", onclick: (e) => answer(e, a, []) }, "Decline"));
    return el("div", { class: "row" }, `Week ${a.week}: ${items}`,
      el("button", { class: "ar-btn sm primary", onclick: (e) => answer(e, a, a.items) }, "Approve this week"));
  });
  const leave = el("button", { class: "ar-btn danger", onclick: async () => {
    if (!confirm("Withdraw? Your agent stops answering: weeks not yet delivered are not paid (an open escrow returns to the institution). Payments made stay yours.")) return;
    const text = await actionText(pid, cid, "withdraw", c.consent_hash);
    await api("POST", `/api/p/${pid}/contracts/${cid}/withdraw`, { signature: await sign(k, text) }, h).catch((x) => alert(x.message));
    mine();
  } }, "Withdraw");
  const hist = el("table", {}, el("tr", {}, el("th", {}, "Week"), el("th", {}, "Amount"), el("th", {}, "Status"), el("th", {}, "Receipt / tx")),
    ...v.history.filter((o) => o.contract === cid).map((o) => el("tr", {}, el("td", {}, o.slot.split("week")[1]), el("td", {}, amount(o.amount_drops)),
      el("td", {}, payState(o.payment) || o.status), el("td", {}, payLink(o)))));
  box.replaceChildren(el("h2", {}, `You joined as ${pid}`),
    el("p", {}, `Status: ${c.status} · your choice: ${c.automation} · paid ${amount(c.settled_drops)} · held ${amount(c.held_drops)}`),
    el("p", { class: "note" }, `Signed consent ${c.consent_hash.slice(0, 16)}…`),
    asks.length ? el("div", { class: "items" }, el("h3", {}, "Waiting for you"), ...asks) : el("p", { class: "note" }, "Nothing is waiting for you."),
    el("h3", {}, "Payments"), hist, c.status === "active" ? leave : "");
}

start().catch((e) => $("#terms").replaceChildren(el("p", { class: "err" }, e.message)));
