import { FOOTNOTE, ITEM_LABELS, actionText, amount, api, el, key, remember, sign, signIn, tx } from "./contracts.js";

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
    el("p", {}, `${amount(t.price_per_item_drops)} per item per week, paid to you on the ledger when your agent releases each week. ${c.members} of ${t.capacity} joined.`),
    t.summary ? el("p", { class: "note" }, t.summary) : "");
  const k = await key(name);
  if (k.meta.pid) return mine();
  if (!invite) { $("#terms").append(el("p", { class: "err" }, "The invite code is missing from the link.")); return; }
  for (const i of t.items) $("#items").append(el("label", {}, el("input", { type: "checkbox", name: "item", value: i, checked: "" }), ITEM_LABELS[i] || i));
  $("#join").hidden = false;
  $("#form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    $("#err").textContent = "";
    try {
      const s = await api("POST", `/api/contracts/${cid}/join/start`, { invite_code: invite, public_key: k.publicHex, items: f.getAll("item"), automation: f.get("automation") });
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
  const asks = c.pending_approvals.map((a) => el("div", { class: "row" }, `Week ${a.week ?? "-"}: ${a.items.map((i) => ITEM_LABELS[i] || i).join(", ")}`,
    el("button", { class: "ar-btn sm primary", onclick: async (e) => {
      e.target.disabled = true;
      const text = await actionText(pid, cid, `approve:${a.request_id}:${[...a.items].sort().join(",")}`, c.consent_hash);
      await api("POST", `/api/p/${pid}/contracts/${cid}/requests/${a.request_id}/approve`, { items: a.items, signature: await sign(k, text) }, h).catch((x) => alert(x.message));
      mine();
    } }, "Approve this week")));
  const leave = el("button", { class: "ar-btn danger", onclick: async () => {
    if (!confirm("Withdraw? Weeks not yet released stay unpaid and the escrow returns to the institution. Payments made stay yours.")) return;
    const text = await actionText(pid, cid, "withdraw", c.consent_hash);
    await api("POST", `/api/p/${pid}/contracts/${cid}/withdraw`, { signature: await sign(k, text) }, h).catch((x) => alert(x.message));
    mine();
  } }, "Withdraw");
  const hist = el("table", {}, el("tr", {}, el("th", {}, "Week"), el("th", {}, "Amount"), el("th", {}, "Status"), el("th", {}, "Tx")),
    ...v.history.filter((o) => o.contract === cid).map((o) => el("tr", {}, el("td", {}, o.slot.split("week")[1]), el("td", {}, amount(o.amount_drops)),
      el("td", {}, o.status === "delivered" ? "paid" : o.status), el("td", {}, tx(o.escrow_finish.tx ? o.escrow_finish : o.escrow_create)))));
  box.replaceChildren(el("h2", {}, `You joined as ${pid}`),
    el("p", {}, `Status: ${c.status} · your choice: ${c.automation} · paid ${amount(c.settled_drops)} · held ${amount(c.held_drops)}`),
    el("p", { class: "note" }, `Signed consent ${c.consent_hash.slice(0, 16)}…`),
    asks.length ? el("div", { class: "items" }, el("h3", {}, "Waiting for you"), ...asks) : el("p", { class: "note" }, "Nothing is waiting for you."),
    el("h3", {}, "Payments"), hist, c.status === "active" ? leave : "");
}

start().catch((e) => $("#terms").replaceChildren(el("p", { class: "err" }, e.message)));
