// UniQdata side on the real engine: one relationship with the institution, its sub-projects listed
// under it with their own payouts, and only outside-scope or T3 items asked here.
// Consent and answers sign with the person's demo key on the server (no passkey needed to try it).

import { engine, watchSelf } from "/apps/shared/api.js";

const pid = new URLSearchParams(location.search).get("pid") || "P-017";
const api = engine("", { token: async (sub) => {
  const r = await fetch(`/api/dev/login/${encodeURIComponent(sub)}`, { method: "POST", headers: { "X-Sandbox-Code": code() } });
  if (!r.ok) throw Object.assign(new Error("sign-in"), { status: r.status });
  return (await r.json()).access_token;
} });
const root = document.getElementById("app");
const st = { rel: null, sheet: false, read: false, busy: null, error: null, toast: null };

const h = (tag, props, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : String(c));
  return el;
};
const tag = (t, tone = "gray") => h("span", { class: `tag ${tone}` }, t);
const money = (n) => `${Number(n || 0).toFixed(2)} RLUSD`;   // test token standing in for RLUSD (footer says so)

const code = () => { try { return new URLSearchParams(location.search).get("code") || localStorage.getItem("ar-code") || ""; } catch { return ""; } };
async function call(method, path, body) {
  const login = await fetch(`/api/dev/login/${encodeURIComponent(pid)}`, { method: "POST", headers: { "X-Sandbox-Code": code() } });
  if (!login.ok) throw Object.assign(new Error("sign-in"), { status: login.status, detail: "Enter the access code on the start page to act as this participant." });
  const t = await login.json();
  const res = await fetch(path, { method, headers: { Authorization: `Bearer ${t.access_token}`, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  if (!res.ok) throw Object.assign(new Error(`${path} -> ${res.status}`), { detail: await res.text() });
  return res.json();
}
const P = `/api/p/${encodeURIComponent(pid)}`;
async function load() {
  try { st.rel = await call("GET", `${P}/relationship`); st.error = null; } catch (e) { st.error = e.status === 404 ? "This engine doesn't have institution relationships yet." : (e.detail || e.message); }
  draw();
}
async function act(label, fn, done) {
  st.busy = label; draw();
  try { await fn(); st.toast = done; } catch (e) { st.error = `${label}: ${e.detail || e.message}`; }
  st.busy = null; await load();
  setTimeout(() => { st.toast = null; draw(); }, 2500);
}
const consent = () => act("Signing", () => call("POST", `${P}/relationship/consent`, { institution: st.rel.institution.id }), "Consent recorded · one signature for the whole scope");
const decide = (p, allow) => act("Answering", () => call("POST", `${P}/subprojects/${encodeURIComponent(p.sid)}/decision`, { item: p.item, allow }), allow ? "Allowed · your agent sends it" : "Declined · nothing sent");

function sheet() {
  const r = st.rel;
  const total = r.subprojects.reduce((a, s) => a + (s.budget_share || 0), 0);
  const onScroll = (e) => {
    const sc = e.target;
    if (!st.read && sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 8) { st.read = true; sc.closest(".sheet").querySelector(".act .btn.primary").disabled = false; }
  };
  return [h("div", { class: "scrim", onclick: () => { st.sheet = false; draw(); } }),
    h("div", { class: "sheet" }, h("div", { class: "grab" }),
      h("div", { class: "pin" },
        h("div", { class: "spread" }, h("span", { class: "small muted" }, `${r.institution.name} · ${r.subprojects.length} sub-projects`), tag("Pinned", "gray")),
        h("div", { class: "amount" }, total ? `Up to ${money(total)}` : "Paid in RLUSD per delivered round"),
        h("div", { class: "small muted" }, "Each sub-project pays for each round your agent delivers. 80% at delivery, 20% after review.")),
      h("div", { class: "scroll", onscroll: onScroll },
        h("div", { class: "sec" }, h("h3", {}, "One relationship with this institution"),
          h("p", {}, "You agree once to the scope below. New sub-projects inside it are routed by your agent and settled on their own, with no new contract.")),
        h("div", { class: "sec" }, h("h3", {}, "Scope"), h("ul", {}, (r.scope.data_types || []).map((d) => h("li", {}, d))),
          h("p", { class: "small muted" }, `Purposes: ${(r.scope.purposes || []).join(", ")}`)),
        h("div", { class: "sec" }, h("h3", {}, "Sub-projects today"), r.subprojects.map((s) => h("p", {}, `· ${s.name}`))),
        h("div", { class: "sec" }, h("h3", {}, "Always asked here first"),
          h("p", {}, "Anything outside this scope, and genomic, CT or MRI data (T3), comes back to you for a yes or no.")),
        h("div", { class: "sec" }, h("h3", {}, "If you want to stop"), h("p", {}, "Stop any sub-project or withdraw the whole relationship. Unsent rounds are returned.")),
        h("div", { class: "sec" }, h("h3", {}, "Record"), h("p", {}, `Recorded on the ledger. Amounts are in ${r.asset_label || r.asset}.`))),
      h("div", { class: "act" },
        h("button", { class: "btn primary block", disabled: !st.read || !!st.busy, onclick: () => { st.sheet = false; consent(); } }, "Agree once (demo key)"),
        h("button", { class: "btn ghost", onclick: () => { st.sheet = false; draw(); } }, "Not now")))];
}

function draw() {
  const body = [];
  if (!st.rel) body.push(st.error ? h("div", { class: "note red" }, st.error) : h("p", { class: "muted" }, "Loading…"));
  else {
    const r = st.rel;
    body.push(h("div", { class: "pcard", style: "background:var(--brand-weak);border-color:var(--brand-line)" },
      h("div", { class: "spread" }, h("b", {}, r.institution.name), r.consented ? tag("1 relationship", "blue") : tag("Not joined", "gray")),
      h("div", { class: "small muted" }, r.consented ? `One consent · ${r.subprojects.length} sub-projects under it` : "Agree once to this institution's scope; your agent handles each sub-project inside it."),
      r.consented?.tx && h("div", { class: "tiny mono muted" }, `consent tx ${r.consented.tx.slice(0, 12)}…`),
      !r.consented && h("button", { class: "btn primary", onclick: () => { st.sheet = true; st.read = false; draw(); } }, "Review and agree")));
    if (r.pending.length) body.push(h("div", { class: "pcard" }, h("b", {}, "Your agent asks"),
      r.pending.map((p) => h("div", { class: "col", style: "gap:4px;padding:8px 0;border-top:1px solid var(--border)" },
        h("div", { class: "small" }, h("b", {}, p.item), ` · ${r.subprojects.find((s) => s.id === p.sid)?.name || p.sid}`),
        h("div", { class: "tiny muted" }, p.reason === "T3" ? "Genomic, CT or MRI (T3): always asked" : "Outside the scope you agreed to"),
        h("div", { class: "row" }, h("button", { class: "btn sm primary", disabled: !!st.busy, onclick: () => decide(p, true) }, "Allow (demo key)"),
          h("button", { class: "btn sm", disabled: !!st.busy, onclick: () => decide(p, false) }, "Not this one"))))));
    body.push(...r.subprojects.map((s) => h("div", { class: "pcard" },
      h("div", { class: "spread" }, h("b", {}, s.name), h("span", { class: "small", style: "color:var(--green);font-weight:600" }, money(s.total))),
      h("div", { class: "tiny muted" }, s.items.map((i) => `${i.item}: ${i.decision}`).join(" · ")),
      s.payouts.length ? h("div", { class: "timeline" }, s.payouts.slice(-4).reverse().map((p) => h("div", { class: "it" }, h("span", { class: "dot green" }),
        h("div", { class: "grow small" }, `Round ${p.round} · ${p.status}`),
        p.tx && h("span", { class: "tiny mono muted" }, `${String(p.tx).slice(0, 8)}…`),
        h("span", { class: "small", style: "font-weight:600" }, `+${money(p.amount, p.asset)}`)))) : h("div", { class: "tiny muted" }, "No rounds yet"))));
    body.push(h("p", { class: "tiny muted", style: "text-align:center" }, r.asset_label || ""));
  }
  const ph = h("div", { class: "ph" },
    h("div", { class: "ph-bar" }, h("span", { class: "title" }, "My institutions"), tag(pid, "blue")),
    h("div", { class: "ph-body" }, body),
    st.sheet && sheet(),
    st.toast && h("div", { class: "toast" }, st.toast));
  root.replaceChildren(ph);
}

watchSelf(api, pid, () => load(), { interval: 2000 });
load();
