const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const api = async (path, opts) => { const r = await fetch(path, opts); if (!r.ok) throw new Error(path + " " + r.status); return r.json(); };
const post = (path, body) => api(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });
const params = new URLSearchParams(location.search);
let ME = params.get("as") || (() => { try { return localStorage.getItem("vm-as"); } catch { return null; } })() || "dana";
let META = null;
const hhmm = (t) => new Date(t * 1000).toTimeString().slice(0, 8);
async function topbar(page) {
  META = await api("/api/meta");
  const accts = await api("/api/accounts");
  $("acct").innerHTML = accts.map((a) => `<option value="${a.id}">${esc(a.name)}${a.type === "org" ? " (company)" : ""}</option>`).join("");
  $("acct").value = ME;
  $("acct").onchange = (e) => { ME = e.target.value; try { localStorage.setItem("vm-as", ME); } catch {} refresh(); };
  $("ledgerTag").textContent = META.ledger === "testnet" ? "XRPL Testnet" : "TEST LEDGER (not real)";
  $("ledgerTag").className = "tag " + (META.ledger === "testnet" ? "blue" : "red");
  $("modelTag").textContent = META.model === "rules" ? "agents: written rules (no LLM key)" : `agents: ${META.model}`;
  if (META.connected < META.accounts) $("banner").hidden = false, $("banner").textContent = `Connecting accounts to the ledger: ${META.connected} of ${META.accounts}…`;
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
