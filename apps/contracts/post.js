import { DISPLAY_UNIT } from "../shared/ui.js";
import { FOOTNOTE, ITEM_LABELS, amount, api, el, key, payLink, payState, remember, signIn, tx } from "./contracts.js";

const $ = (s) => document.querySelector(s);
document.querySelectorAll(".unit").forEach((u) => (u.textContent = DISPLAY_UNIT));
$("#foot").textContent = FOOTNOTE;
for (const [id, label] of Object.entries(ITEM_LABELS))
  $("#items").append(el("label", {}, el("input", { type: "checkbox", name: "item", value: id, ...(id === "heart_rate.daily" ? {} : { checked: "" }) }), label));

const params = new URLSearchParams(location.search);
let cid = params.get("contract");

$("#form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const f = new FormData(ev.target);
  $("#form-err").textContent = "";
  try {
    const k = await key("researcher");
    const terms = { title: f.get("title"), institution: f.get("institution"), irb_approval: f.get("irb_approval"),
      purpose: "sleep_research", items: f.getAll("item"), weeks: [+f.get("w0"), +f.get("w1")],
      price_per_item_drops: Math.round(+f.get("price") * 1e6), budget_drops: Math.round(+f.get("budget") * 1e6),
      capacity: +f.get("capacity"), summary: f.get("summary"), round_every_s: f.get("every") ? +f.get("every") : null };
    const out = await api("POST", "/api/contracts", { terms, researcher_key: k.publicHex },
      f.get("code") ? { "X-Posting-Code": f.get("code") } : {});
    cid = out.contract.id;
    remember("researcher", { [cid]: out.researcher_sub });
    const link = `${location.origin}/apps/contracts/join.html?contract=${cid}&invite=${encodeURIComponent(out.invite_code)}`;
    $("#posted").hidden = false;
    $("#posted").replaceChildren(el("h2", {}, `Posted ${cid}`),
      el("p", {}, "Invite link (shown once; share it with the people you invite):"), el("p", {}, el("code", {}, link)),
      el("p", { class: "note" }, "Ethics credential on the ledger: ", tx(out.ethics_credential) || "(mock ledger)"));
    history.replaceState(null, "", `?contract=${cid}`);
    $("#form-card").hidden = true;
    show();
  } catch (e) { $("#form-err").textContent = e.message; }
});

async function auth() {
  const k = await key("researcher");
  const sub = k.meta[cid];
  if (!sub) throw new Error("this browser did not post that contract");
  return signIn(sub, k);
}

async function show() {
  if (!cid) return;
  const box = $("#console");
  box.hidden = false;
  try {
    const c = await api("GET", `/api/contracts/${cid}/console`, undefined, await auth());
    $("#form-card").hidden = true;
    const [w0, w1] = c.terms.weeks;
    const week = el("select", { class: "ar-input" }, ...Array.from({ length: w1 - w0 + 1 }, (_, i) => el("option", { value: w0 + i }, `Week ${w0 + i}`)));
    const msg = el("p", { class: "note" });
    const run = el("button", { class: "ar-btn primary", onclick: async () => {
      run.disabled = true; msg.textContent = "Asking each member's agent…";
      try {
        const r = await api("POST", `/api/contracts/${cid}/rounds`, { week: +week.value }, await auth());
        msg.textContent = `Week ${r.week}: ` + Object.entries(r.summary).map(([k, v]) => `${k} ${v}`).join(", ");
        show();
      } catch (e) { msg.textContent = e.message; run.disabled = false; }
    } }, "Run week");
    const members = el("table", {}, el("tr", {}, el("th", {}, "Member"), el("th", {}, "Items"), el("th", {}, "Their choice"), el("th", {}, "Status")),
      ...c.member_list.map((m) => el("tr", {}, el("td", {}, m.pid), el("td", {}, m.items.length), el("td", {}, m.automation), el("td", {}, m.status))));
    const orders = el("table", {}, el("tr", {}, el("th", {}, "Order"), el("th", {}, "Week"), el("th", {}, "Amount"), el("th", {}, "Status"), el("th", {}, "Payment"), el("th", {}, "Receipt / tx")),
      ...c.orders.slice(-60).reverse().map((o) => el("tr", {}, el("td", {}, o.order_id), el("td", {}, o.slot.split("week")[1]),
        el("td", {}, amount(o.amount_drops)), el("td", {}, o.status), el("td", {}, payState(o.payment)), el("td", {}, payLink(o)))));
    const p = c.payments;
    const auto = c.terms.round_every_s;
    box.replaceChildren(el("h2", {}, c.terms.title), el("p", { class: "sub" }, `${c.terms.institution} · ${c.members} member${c.members === 1 ? "" : "s"} · paid ${amount(p.paid_drops)} in ${p.paid_count} payments${p.unpaid_count ? ` · ${p.unpaid_count} delivered, payment pending` : ""} · budget ${amount(c.budget_drops)} · ${p.rail === "ap4m" ? "AP4M on XRPL EVM Testnet" : c.ledger}`),
      auto ? el("p", { class: "note" }, `The institution's agent runs the next week on its own every ${auto} s; each member's agent answers from their consent and each delivered week is paid at once. This page refreshes itself.`) : "",
      el("div", { class: "row" }, week, run), msg, el("h3", {}, "Members"), members, el("h3", {}, "Orders"), orders);
    clearTimeout(window._refresh);
    if (auto && c.status === "open") window._refresh = setTimeout(show, 10000);
  } catch (e) { box.replaceChildren(el("p", { class: "err" }, e.message)); }
}
show();
