const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (!r.ok) { let m = path + " " + r.status; try { m = (await r.json()).detail || m; } catch {} throw new Error(m); }
  return r.json();
};
const post = (path, body) => api(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });
const params = new URLSearchParams(location.search);
let ME = params.get("as") || (() => { try { return localStorage.getItem("vm-as"); } catch { return null; } })() || "dana";
let META = null, USER = null;
const xrp = (units) => `${(+(units || 0) * (META?.unit_xrp || 0.01)).toFixed(2)} XRP`;   // price units -> what moves on the ledger
const hhmm = (t) => new Date(t * 1000).toTimeString().slice(0, 8);
async function topbar(page) {
  META = await api("/api/meta");
  USER = await api("/api/me");
  if (USER.user && !params.get("as")) ME = USER.user.account;
  const accts = await api("/api/accounts");
  $("acct").innerHTML = accts.map((a) => `<option value="${a.id}">${a.id.startsWith("u-") ? "You · " : ""}${esc(a.name)}${a.type === "org" ? " (company)" : ""}</option>`).join("");
  if (!accts.some((a) => a.id === ME)) ME = "dana";
  $("acct").value = ME;
  $("acct").previousElementSibling.textContent = USER.user ? "Viewing" : USER.public ? "Viewing demo account" : "Signed in as (demo)";
  memberBar();
  $("acct").onchange = (e) => { ME = e.target.value; try { localStorage.setItem("vm-as", ME); } catch {} refresh(); };
  $("ledgerTag").textContent = ({ testnet: "XRPL Testnet", devnet: "XRPL Devnet" })[META.ledger] || "TEST LEDGER (not real)";
  $("ledgerTag").className = "tag " + (META.ledger === "mock" ? "red" : "blue");
  $("modelTag").textContent = META.model === "rules" ? "agents: written rules (no LLM key)" : `agents: ${META.model}`;
  if (META.connected < META.accounts) $("banner").hidden = false, $("banner").textContent = `Funding wallets on the ledger: ${META.connected} of ${META.accounts}. Funded accounts are already trading.`;
  else $("banner").hidden = true;
}
function chatBox(el, data) {
  const draft = $("say")?.value || "", focused = document.activeElement?.id === "say";
  const open = el.dataset.open === "1";
  el.innerHTML = `<button class="head" type="button" id="chatHead"><span>Ask my agent</span><span>${open ? "▾" : "▸"} ${data.chat.filter((c) => c.actions && !c.done).length ? '<span class="tag red">needs you</span>' : ""}</span></button>
    ${open ? `<div class="msgs" id="msgs">${data.chat.map((c) => `<div class="msg ${c.role === "me" ? "me" : "agent"}"><div>${esc(c.text)}</div>${c.actions ? `<div class="acts">${c.actions.map((a, i) => `<button type="button" data-c="${c.id}" data-i="${i}" ${c.done ? "disabled" : ""} class="${i === 0 ? "primary" : ""}">${esc(a.t)}</button>`).join("")}</div>` : ""}</div>`).join("") || '<p class="muted small">Say what to sell or what you need.</p>'}</div>
    <form id="chatForm"><input type="text" id="say" placeholder="e.g. sell my sleep logs, or I need air-quality data" aria-label="Message to my agent"><button class="primary">Send</button></form>` : ""}`;
  $("chatHead").onclick = () => { el.dataset.open = open ? "0" : "1"; chatBox(el, data); };
  if (open) {
    $("msgs").scrollTop = 1e9; $("say").value = draft; if (focused) $("say").focus();
    el.querySelectorAll("[data-c]").forEach((b) => b.onclick = async () => { await post(`/api/account/${ME}/chat/${b.dataset.c}/act`, { i: +b.dataset.i }); refresh(); });
    $("chatForm").onsubmit = async (e) => { e.preventDefault(); const t = $("say").value.trim(); if (!t) return; $("say").value = ""; await post(`/api/account/${ME}/chat`, { text: t }); refresh(); };
  }
}
function live() { try { const es = new EventSource("/api/stream"); es.onmessage = () => refresh(); } catch { setInterval(refresh, 5000); } }

// ---------------- members: sign up, sign in, link a personal wallet ----------------
function memberBar() {
  let el = $("member");
  if (!el) { el = document.createElement("span"); el.id = "member"; el.className = "acts"; $("acct").after(el); }
  el.innerHTML = USER.user
    ? `<button type="button" id="mWallet">${USER.user.wallet_tx ? "Wallet linked ✓" : "Link my wallet"}</button><button type="button" id="mOut">Sign out</button>`
    : `<button type="button" class="primary" id="mIn">Sign up / Sign in</button>`;
  if (USER.user) { $("mWallet").onclick = walletDlg; $("mOut").onclick = async () => { await post("/api/logout"); location.href = location.pathname; }; }
  else $("mIn").onclick = authDlg;
}
function dlg(html) {
  let d = $("mDlg");
  if (!d) { d = document.createElement("dialog"); d.id = "mDlg"; d.style.maxWidth = "min(480px, calc(100vw - 32px))"; document.body.append(d); }
  d.innerHTML = `<div class="dlg" style="max-width:440px">${html}<p class="small n" id="mErr"></p><div class="acts"><button type="button" id="mClose">Close</button></div></div>`;
  $("mClose").onclick = () => d.close();
  if (!d.open) d.showModal();
  return d;
}
function authDlg() {
  dlg(`<h1 style="font-size:19px">Your own vault and agent</h1>
    <p class="small muted">Sign up to get an empty DB, an agent that asks you before every sale, and its own wallet on the XRPL ${esc(META.ledger)}. You can link your personal wallet so sales pay out straight to it.</p>
    <form id="mForm" style="display:grid;gap:8px"><label class="small">Username<input id="mU" autocomplete="username" required minlength="3" maxlength="20" pattern="[a-zA-Z0-9_]+"></label>
    <label class="small">Password<input id="mP" type="password" autocomplete="current-password" required minlength="8"></label>
    <div class="acts"><button class="primary" data-a="signup">Sign up</button><button data-a="login">Sign in</button></div></form>`);
  let action = "signup";
  $("mForm").querySelectorAll("button").forEach((b) => b.onclick = () => { action = b.dataset.a; });
  $("mForm").onsubmit = async (e) => {
    e.preventDefault();
    try { await post("/api/" + action, { username: $("mU").value, password: $("mP").value }); location.href = "/vault"; }
    catch (err) { $("mErr").textContent = err.message; }
  };
}
function walletDlg() {
  const u = USER.user;
  dlg(`<h1 style="font-size:19px">Link my wallet</h1>
    <p class="small muted">Your agent trades from its own wallet (${esc(USER.agent_wallet || "being funded…")}). Link your personal XRPL wallet (Xaman, GemWallet, Crossmark, any) and buyers' escrows pay out straight to it. We never see its keys.</p>
    ${u.wallet_tx ? `<p class="small">Linked: <span class="mono">${esc(u.wallet)}</span></p>` : ""}
    <form id="wForm" style="display:grid;gap:8px"><label class="small">My wallet address<input id="wA" class="mono" placeholder="r…" value="${esc(u.wallet || "")}" required></label>
    <button class="primary">Get my check code</button></form><div id="wStep"></div>`);
  const step = (link) => {
    $("wStep").innerHTML = `<ol class="small" style="padding-left:18px;display:grid;gap:6px;margin-top:10px">
      <li>From <span class="mono">${esc(link.address)}</span>, send <b>1 drop (0.000001 XRP)</b> on the XRPL ${esc(META.ledger)}</li>
      <li>to <span class="mono">${esc(link.send_to)}</span></li><li>with destination tag <b class="mono">${link.destination_tag}</b>.</li></ol>
      <p class="small muted">That payment proves the wallet is yours. Then press Check.</p><button type="button" class="primary" id="wCheck">Check</button><p class="small" id="wRes"></p>`;
    $("wCheck").onclick = async () => {
      try { const r = await post("/api/me/wallet/verify"); $("wRes").innerHTML = r.ok ? `Linked ✓ ${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">see the payment</a>` : ""}` : esc(r.why); if (r.ok) { USER = await api("/api/me"); memberBar(); } }
      catch (err) { $("mErr").textContent = err.message; }
    };
  };
  if (u.wallet && !u.wallet_tx && u.wallet_tag) step({ address: u.wallet, send_to: USER.platform, destination_tag: u.wallet_tag });
  $("wForm").onsubmit = async (e) => {
    e.preventDefault();
    try { step(await post("/api/me/wallet", { address: $("wA").value.trim() })); } catch (err) { $("mErr").textContent = err.message; }
  };
}
window.addEventListener("unhandledrejection", (e) => {
  const b = $("banner"); if (!b) return;
  b.hidden = false; b.textContent = e.reason?.message || String(e.reason);
  setTimeout(() => { b.hidden = true; }, 6000);
});

// "Tell my agent": the request goes to the agent as a chat message, and its answer comes back in the chat
async function tellAgent(text) {
  const el = $("chat"); el.dataset.open = "1";
  await post(`/api/account/${ME}/chat`, { text });
  await refresh();
  $("msgs")?.scrollIntoView({ block: "nearest" });
}
