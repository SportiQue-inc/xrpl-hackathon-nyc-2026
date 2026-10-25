// UniQdata side on the real engine: one relationship with the institution, its sub-projects listed
// under it with their own payouts, and only outside-scope or T3 items asked here.
// Consent and answers sign with the person's demo key on the server (no passkey needed to try it).

import { engine, watchSelf } from "/apps/shared/api.js";
import { UNIT, UNIT_NOTE, setSettlementAsset } from "/apps/shared/ui.js";

const pid = new URLSearchParams(location.search).get("pid") || "P-017";
const api = engine("", { token: async (sub) => {
  const r = await fetch(`/api/dev/login/${encodeURIComponent(sub)}`, { method: "POST", headers: { "X-Sandbox-Code": code() } });
  if (!r.ok) throw Object.assign(new Error("sign-in"), { status: r.status });
  return (await r.json()).access_token;
} });
const root = document.getElementById("app");
const st = { rel: null, sheet: false, doc: null, checked: new Set(), items: new Set(), read: false, busy: null, error: null, toast: null };

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
const money = (n) => `${Number(n || 0).toFixed(2)} ${UNIT}`;

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
  try { st.rel = await call("GET", `${P}/relationship`); setSettlementAsset(st.rel.asset); st.error = null; } catch (e) { st.error = e.status === 404 ? "This engine doesn't have institution relationships yet." : (e.detail || e.message); }
  draw();
}
async function act(label, fn, done) {
  st.busy = label; draw();
  try { await fn(); st.toast = done; } catch (e) { st.error = `${label}: ${e.detail || e.message}`; }
  st.busy = null; await load();
  setTimeout(() => { st.toast = null; draw(); }, 2500);
}
// The person may narrow the scope: items left out come back to them in every sub-project.
const consent = () => {
  const all = st.rel.scope.data_types || [];
  const items = all.filter((i) => st.items.has(i));
  const narrowed = items.length < all.length;
  return act("Signing", () => call("POST", `${P}/relationship/consent`, { institution: st.rel.institution.id, ...(narrowed ? { items } : {}) }),
    narrowed ? `Consent recorded · ${items.length} of ${all.length} data types; the rest come back to you` : "Consent recorded · one signature for the whole scope");
};
const openSheet = () => { st.sheet = true; st.doc = null; st.items = new Set(st.rel.consented?.items || st.rel.scope.data_types || []); draw(); };
const decide = (p, allow) => act("Answering", () => call("POST", `${P}/subprojects/${encodeURIComponent(p.sid)}/decision`, { item: p.item, allow }), allow ? "Allowed · your agent sends it" : "Declined · nothing sent");

// One document per consent, each read to the end before it can be checked (as on /participant).
// One signature covers the checked set; each document keeps its own record. MRI, CT and genomic data are never in it.
function docs(r) {
  const items = (r.scope.data_types || []).join(", ");
  const purposes = (r.scope.purposes || []).join(", ");
  return [
    { key: "research", title: "Study participation", sections: [
      ["What you agree to", `${r.institution.name} may ask your agent for ${items} for ${purposes}. You agree once; each sub-project inside this scope is routed by your agent and settled on its own, with no new contract.`],
      ["Sub-projects today", r.subprojects.map((x) => `· ${x.name}`).join("\n") || "None yet"],
      ["Payment", "Each sub-project pays for each round your agent delivers: 50% of a first week at delivery, 10 points more for each consecutive week up to 90%, the rest after a 7-day review."],
      ["Always asked first", "Anything outside this scope, a new purpose, and MRI, CT or genomic data come back to you for a yes or no."]] },
    { key: "third_party", title: "Providing data to the institution", sections: [
      ["Who receives it", `${r.institution.name} and its approved study roles, under a study pseudonym.`],
      ["What is sent", `Weekly records of ${items}, sealed until payment releases the key.`],
      ["Retention", "As the study protocol states. Withdrawing access ends further use and asks the institution to delete its copy."]] },
    { key: "sensitive", title: "Health information", sections: [
      ["Why separate consent", "Health records are sensitive information and need their own consent."],
      ["What is included", `Only ${items}. MRI, CT and genomic data are excluded and always need a fresh decision.`],
      ["Record", `Recorded on the ledger. Amounts are in ${UNIT}. ${UNIT_NOTE}`]] },
  ];
}

// A document short enough to show whole has been read once it is on screen: no scroll event will ever fire.
function fitsCheck(sc) {
  requestAnimationFrame(() => {
    if (!st.read && sc.isConnected && sc.scrollHeight <= sc.clientHeight + 8) {
      st.read = true;
      const b = sc.closest(".sheet")?.querySelector(".act .btn.primary");
      if (b) b.disabled = false;
    }
  });
  return sc;
}

function sheet() {
  const r = st.rel;
  const all = docs(r);
  if (st.doc) {
    const d = all.find((x) => x.key === st.doc);
    const onScroll = (e) => {
      const sc = e.target;
      if (!st.read && sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 8) { st.read = true; sc.closest(".sheet").querySelector(".act .btn.primary").disabled = false; }
    };
    return [h("div", { class: "scrim", onclick: () => { st.doc = null; draw(); } }),
      h("div", { class: "sheet" }, h("div", { class: "grab" }),
        h("div", { class: "pin" }, h("div", { class: "spread" }, h("b", {}, d.title), tag(`${all.findIndex((x) => x.key === d.key) + 1} of ${all.length}`, "gray"))),
        fitsCheck(h("div", { class: "scroll", onscroll: onScroll },
          d.sections.map(([hd, v]) => h("div", { class: "sec" }, h("h3", {}, hd), String(v).split("\n").map((x) => h("p", {}, x)))),
          h("p", { class: "tiny muted", style: "text-align:center" }, "— End —"))),
        h("div", { class: "act" },
          h("button", { class: "btn primary block", disabled: !st.read, onclick: () => { st.checked.add(d.key); st.doc = null; draw(); } }, "I agree to this document"),
          h("button", { class: "btn ghost", onclick: () => { st.doc = null; draw(); } }, "Back")))];
  }
  const ready = all.every((x) => st.checked.has(x.key)) && st.items.size > 0;
  const types = r.scope.data_types || [];
  return [h("div", { class: "scrim", onclick: () => { st.sheet = false; draw(); } }),
    h("div", { class: "sheet" }, h("div", { class: "grab" }),
      h("div", { class: "pin" },
        h("div", { class: "spread" }, h("span", { class: "small muted" }, `${r.institution.name} · ${r.subprojects.length} sub-projects`), tag("Pinned", "gray")),
        h("div", { class: "amount" }, `Paid in ${UNIT} per delivered round`),
        h("div", { class: "small muted" }, "Read each document to the end, then agree once.")),
      h("div", { class: "scroll" },
        all.map((x) => h("button", { class: "pcard", style: "width:100%;text-align:left;cursor:pointer", onclick: () => { st.doc = x.key; st.read = false; draw(); } },
          h("div", { class: "spread" }, h("b", {}, x.title), st.checked.has(x.key) ? tag("Read · agreed", "blue") : tag("Read to the end", "gray")))),
        h("div", { class: "pcard" }, h("div", { class: "spread" }, h("b", {}, "What you allow"), tag(`${st.items.size} of ${types.length}`, st.items.size < types.length ? "amber" : "gray")),
          h("div", { class: "tiny muted" }, "Untick anything you don't want sent automatically. It comes back to you whenever a sub-project asks for it."),
          types.map((i) => h("label", { class: "row small", style: "gap:8px;padding:4px 0;cursor:pointer" },
            h("input", { type: "checkbox", checked: st.items.has(i), onchange: (e) => { e.target.checked ? st.items.add(i) : st.items.delete(i); draw(); } }), i)))),
      h("div", { class: "act" },
        h("button", { class: "btn primary block", disabled: !ready || !!st.busy, onclick: () => { st.sheet = false; consent(); } }, st.items.size < types.length ? `Agree once to ${st.items.size} of ${types.length} data types (demo key)` : `Agree once (${st.checked.size} of ${all.length} documents, demo key)`),
        h("button", { class: "btn ghost", onclick: () => { st.sheet = false; draw(); } }, "Not now")))];
}

// Three ways to step back, as on /participant. Nothing already paid is taken back.
async function openRequest() {
  const v = await call("GET", P);
  return (v.requests || []).find((x) => x.status === "open" || x.status === "partly_open");
}
const skipRound = () => act("Skipping", async () => {
  const r = await openRequest();
  if (!r) throw Object.assign(new Error("no open request"), { detail: "There is no open request to skip this round." });
  await call("POST", `${P}/requests/${r.id}/decline`, {});
}, "Skipped this round · nothing was sent");
const stopFuture = () => act("Stopping", () => call("POST", `${P}/pause`, {}), "Future requests stopped · past data and payments stay");
const withdraw = () => act("Withdrawing", () => call("POST", `${P}/revoke`, {}), "Access withdrawn · licence revoked, unreleased escrows return");
function stepBack() {
  const opt = (title, d, label, fn) => h("div", { class: "col", style: "gap:4px;padding:8px 0;border-top:1px solid var(--border)" },
    h("b", { class: "small" }, title), h("div", { class: "tiny muted" }, d),
    h("button", { class: "btn sm", style: "align-self:flex-start", disabled: !!st.busy, onclick: fn }, label));
  return h("div", { class: "pcard" }, h("b", {}, "Stop or withdraw"),
    opt("Skip this round", "This request only. Earlier contributions, consent history and payments stay.", "Skip this round", skipRound),
    opt("Stop future requests", "No new requests from any sub-project. Past data and payments stay.", "Stop future requests", stopFuture),
    opt("Withdraw access", "Revokes the data licence and asks the institution to delete its copy. Amounts received and shares in review stay with you.", "Withdraw access (demo key)", withdraw));
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
      r.consented?.items && h("div", { class: "tiny muted" }, `You allow ${r.consented.items.length} of ${(r.scope.data_types || []).length}: ${r.consented.items.join(", ")}`),
      !r.consented ? h("button", { class: "btn primary", onclick: openSheet }, "Review and agree")
        : h("button", { class: "btn sm", style: "align-self:flex-start", disabled: !!st.busy, onclick: openSheet }, "Change what you allow")));
    if (r.pending.length) body.push(h("div", { class: "pcard" }, h("b", {}, "Your agent asks"),
      r.pending.map((p) => h("div", { class: "col", style: "gap:4px;padding:8px 0;border-top:1px solid var(--border)" },
        h("div", { class: "small" }, h("b", {}, p.item), ` · ${r.subprojects.find((s) => s.id === p.sid)?.name || p.sid}`),
        h("div", { class: "tiny muted" }, p.reason === "T3" ? "Genomic, CT or MRI (T3): always asked" : p.reason === "narrowed" ? "You left this out when you agreed" : r.subprojects.find((s) => s.id === p.sid)?.purpose && !(r.scope.purposes || []).includes(r.subprojects.find((s) => s.id === p.sid).purpose) ? `New purpose: ${r.subprojects.find((s) => s.id === p.sid).purpose}` : "Outside the scope you agreed to"),
        h("div", { class: "row" }, h("button", { class: "btn sm primary", disabled: !!st.busy, onclick: () => decide(p, true) }, "Allow (demo key)"),
          h("button", { class: "btn sm", disabled: !!st.busy, onclick: () => decide(p, false) }, "Not this one"))))));
    body.push(...r.subprojects.map((s) => h("div", { class: "pcard" },
      h("div", { class: "spread" }, h("b", {}, s.name), h("span", { class: "small", style: "color:var(--green);font-weight:600" }, money(s.total))),
      h("div", { class: "tiny muted" }, s.items.map((i) => `${i.item}: ${i.decision}`).join(" · ")),
      s.payouts.length ? h("div", { class: "timeline" }, s.payouts.slice(-4).reverse().map((p) => h("div", { class: "it" }, h("span", { class: "dot green" }),
        h("div", { class: "grow small" }, `Round ${p.round} · ${p.status}`),
        p.tx && h("span", { class: "tiny mono muted" }, `${String(p.tx).slice(0, 8)}…`),
        h("span", { class: "small", style: "font-weight:600" }, `+${money(p.amount, p.asset)}`)))) : h("div", { class: "tiny muted" }, "No rounds yet"))));
    if (r.consented) body.push(stepBack());
    body.push(h("p", { class: "tiny muted", style: "text-align:center" }, `Amounts in ${UNIT}. ${UNIT_NOTE}`));
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
