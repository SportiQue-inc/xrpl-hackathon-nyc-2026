const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (!r.ok) { let m = path + " " + r.status; try { m = (await r.json()).detail || m; } catch {} throw new Error(m); }
  return r.json();
};
const post = (path, body) => api(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });
let ME = null, META = null, USER = {user: null, public: true};
const sym = () => META?.asset || "XRP";
const amount = (v, asset = sym()) => `${Number(v || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 6})} ${asset}`;
const xrp = (units) => amount(+(units || 0) * (META?.unit_xrp || 0.01));
const micro = (m, asset = sym()) => amount(+(m || 0) / 1e6, asset);
const hhmm = (t) => new Date(t * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"});
function showError(err) {
  const b = $("banner"); if (!b) return;
  b.hidden = false; b.className = "banner error"; b.setAttribute("role", "alert"); b.textContent = err.message || String(err);
}
function canAct() {
  if (USER.user && ME === USER.user.account) return true;
  authDlg();
  return false;
}
async function topbar(page) {
  [META, USER] = await Promise.all([api("/api/meta"), api("/api/me")]);
  if (!USER.user) {await post('/api/demo-session');USER=await api('/api/me');}
  ME = USER.user?.account || null;
  const nav=document.querySelector('.top nav');
  if(nav)nav.innerHTML=[['/','Market'],['/vault','My DB'],['/assets','Assets'],['/demo','Demo'],['/report','Report']].map(([h,t])=>`<a href="${h}">${t}</a>`).join('');
  if(nav)nav.insertAdjacentHTML('beforeend',`<a class="home-link" href="${esc(META.engine_url||'https://agentrail-try-production.up.railway.app/apps/try/index.html')}" target="_blank" rel="noopener" title="The AgentRail engine this market runs on">About AgentRail ↗</a>`);
  document.querySelectorAll('nav a').forEach(a=>{if(a.getAttribute('href')===location.pathname)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  $("accountName").textContent = USER.user?.username || "";
  const brand=document.querySelector(".brand");if(brand)brand.after($("accountName"));
  memberBar();
  $("ledgerTag").textContent = META.asset === "test USD" ? "Testnet · test USD" : `Testnet · ${sym()}`;
  $("ledgerTag").title = META.asset_note || "";
  $("ledgerTag").hidden = true;
  $("modelTag").hidden = true;
}
function memberBalance(account) {
  const el=$("accountName");
  if (USER.user) el.textContent=`${USER.user.demo?'Demo vault (synthetic)':USER.user.username} · ${account.balance==null?'Wallet connecting':amount(account.balance)}`;
}
function chatBox(el, data) {
  const draft = $("say")?.value || "", focused = document.activeElement?.id === "say";
  const prior = $("msgs"), scrollTop = prior?.scrollTop || 0;
  const follow = !prior || prior.scrollHeight-prior.scrollTop-prior.clientHeight < 32;
  const open = el.dataset.open === "1";
  if (!ME) {
    el.innerHTML = '<div class="empty"><h3>Your agent, your data</h3><p>Sign in to upload data, set your minimum price and track each sale.</p><button class="primary" id="agentSignIn">Sign in to start</button></div>';
    $("agentSignIn").onclick = authDlg;
    return;
  }
  const approvals=data.chat.filter(c=>c.actions&&!c.done&&!c.text.startsWith('From your own DB'));
  const conversation=data.chat.filter(c=>!approvals.includes(c));
  const message=(c)=>`<div class="msg ${c.role==='me'?'me':'agent'}"><div>${c.done&&/lot of at least \d+ people/.test(c.text)?'<span class="small muted">Earlier group request · inactive</span><br>':''}${esc(c.text)}</div>${c.actions?`<div class="acts">${c.actions.map((a,i)=>`<button type="button" data-c="${c.id}" data-i="${i}" ${c.done?'disabled':''}>${esc(a.t)}</button>`).join('')}</div>`:''}</div>`;
  el.innerHTML = `<button class="head" type="button" id="chatHead"><span>Ask my agent</span><span>${open ? "▾" : "▸"} ${data.chat.filter((c) => c.actions && !c.done).length ? '<span class="tag red">needs you</span>' : ""}</span></button>
    ${open ? `${approvals.length?`<details class="pending-approvals"><summary>${approvals.length} requests waiting for your approval</summary>${approvals.map(message).join('')}</details>`:''}<div class="msgs" id="msgs">${conversation.map(message).join('') || '<p class="muted small">Tell me what you want to do, or ask what you can sell.</p>'}</div>
    <form id="chatForm"><input type="text" id="say" placeholder="e.g. sell my sleep logs, or I need air-quality data" aria-label="Message to my agent"><button class="primary">Send</button></form>` : ""}`;
  $("chatHead").onclick = () => { el.dataset.open = open ? "0" : "1"; chatBox(el, data); };
  if (open) {
    $("msgs").scrollTop = follow ? 1e9 : scrollTop; $("say").value = draft; if (focused) $("say").focus();
    el.querySelectorAll("[data-c]").forEach((b) => b.onclick = async () => { if (!canAct()) return; try { await post(`/api/account/${ME}/chat/${b.dataset.c}/act`, { i: +b.dataset.i }); await refresh(); } catch (err) { showError(err); } });
    $("chatForm").onsubmit = async (e) => { e.preventDefault(); const t = $("say").value.trim(); if (!t) return; if (await tellAgent(t)) $("say").value = ""; };
  }
}
// trades land every second; redraw at most every 4 s so open tabs don't flood the server
let _liveTimer = null;
function live() { const soon = () => { if (_liveTimer || document.hidden) return; _liveTimer = setTimeout(() => { _liveTimer = null; refresh(); }, 4000); };
  try { const es = new EventSource("/api/stream"); es.onmessage = soon; } catch { setInterval(refresh, 5000); } }

// ---------------- members: sign up, sign in, link a personal wallet ----------------
function memberBar() {
  let el=$("member");if(!el){el=document.createElement("span");el.id="member";el.className="acts";$("accountName").after(el);}
  if(USER.user?.demo){el.innerHTML='<button type="button" id="mIn">Use my own vault</button>';$("mIn").onclick=authDlg;return;}
  el.innerHTML=USER.user?`<button type="button" id="mWallet">${USER.user.wallet_tx?'Wallet linked ✓':'Link my wallet'}</button><button type="button" id="mOut">Sign out</button>`:'<button type="button" id="mIn">Sign in</button>';
  if(USER.user){$("mWallet").onclick=walletDlg;$("mOut").onclick=async()=>{await post('/api/logout');location.href=location.pathname;};}else $("mIn").onclick=authDlg;
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
    <p class="small muted">Keep your data, agent and trade history together. Create a vault account, link your payout wallet, then import your first file. Browsing the market is open.</p>
    <form id="mForm" style="display:grid;gap:8px"><label class="small">Username<input id="mU" autocomplete="username" required minlength="3" maxlength="20" pattern="[a-zA-Z0-9_]+"></label>
    <label class="small">Password<input id="mP" type="password" autocomplete="current-password" required minlength="8"></label>
    <div class="acts"><button class="primary" data-a="signup">Sign up</button><button data-a="login">Sign in</button></div></form>`);
  let action = "signup";
  $("mForm").querySelectorAll("button").forEach((b) => b.onclick = () => { action = b.dataset.a; });
  $("mForm").onsubmit = async (e) => {
    e.preventDefault();
    try { await post("/api/" + action, { username: $("mU").value, password: $("mP").value }); location.href = location.pathname; }
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
window.addEventListener("unhandledrejection", (e) => { e.preventDefault(); showError(e.reason); });

// "Tell my agent": the request goes to the agent as a chat message, and its answer comes back in the chat
async function tellAgent(text) {
  if (!canAct()) return false;
  const el = $("chat"); el.dataset.open = "1";
  try {
    await post(`/api/account/${ME}/chat`, {text});
    await refresh();
    $("agentQueue")?.scrollIntoView({block: "nearest"});
    return true;
  } catch (err) { showError(err); return false; }
}
async function queueSale(id) {
  if (!canAct()) return;
  try {
    await post(`/api/account/${ME}/sell-now/${id}`);
    await refresh();
    $("agentQueue")?.scrollIntoView({block: "nearest"});
  } catch (err) { showError(err); }
}
