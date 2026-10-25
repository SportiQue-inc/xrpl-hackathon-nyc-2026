// Structure + live log: the try-it view on the real engine. Left: person → institution → sub-projects,
// and the 50-person cohort week by week. Right: every ledger step as it happens, with its tx hash.
// Actions sign with the engine's demo keys (the simulated devices); nobody needs a passkey or wallet.

import { engine, watch } from "/apps/shared/api.js";

// Access code: visitors with it act through the demo devices; without it the page is read-only.
const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k); } catch { /* private mode */ } } };
const code = () => new URLSearchParams(location.search).get("code") || store.get("ar-code") || "";
export async function demoToken(sub) {
  const res = await fetch(`/api/dev/login/${encodeURIComponent(sub)}`, { method: "POST", headers: { "X-Sandbox-Code": code() } });
  if (!res.ok) throw Object.assign(new Error(`sign-in ${res.status}`), { status: res.status });
  return (await res.json()).access_token;
}
const api = engine("", { token: demoToken, sandboxCode: code() });
const root = document.getElementById("app");
const st = { study: null, inst: null, events: [], busy: null, error: null, asks: [], routing: null, settled: [], readOnly: false };

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

// Which protocol step each engine event is. Unlisted kinds stay out of the log.
const STEP = {
  credential: ["Credential", "gray"], deposit_auth: ["DepositAuth", "gray"], multisig: ["Treasury multisig", "gray"],
  mandate: ["Agent mandate", "gray"], spec: ["Agent finds gaps", "blue"], approval_open: ["Budget co-sign opened", "amber"],
  approval_signed: ["Co-signed (demo key)", "amber"], top_up: ["Budget released", "amber"], round: ["Requests sent", "blue"],
  ask_person: ["Asks the person", "amber"], provide: ["Agent answers", "blue"], batch: ["EscrowCreate (Batch)", "green"],
  escrowed: ["EscrowCreate", "green"], locked_delivery: ["Sealed delivery", "blue"], paid: ["EscrowFinish · paid", "green"],
  licence: ["Data licence (MPT)", "gray"], holdback: ["Payout · 20% held", "green"], consent: ["Consent", "blue"],
  subproject: ["Sub-project", "blue"], revoke: ["Withdrawn", "red"],
};
const txOf = (e) => e.tx || e.data?.tx_hash || (Array.isArray(e.data?.tx) ? e.data.tx[0] : null);
const explorer = (hash) => (st.study?.study.ledger === "testnet" ? `https://testnet.xrpl.org/transactions/${hash}` : null);

async function act(label, fn) {
  st.busy = label; st.error = null; draw();
  try { await fn(); } catch (e) { st.error = `${label}: ${e.detail || e.message}`; }
  st.busy = null; await refresh();
}
const findGaps = () => act("Agent finds gaps", () => api.setGoal(""));
const coSign = () => act("Budget co-sign", async () => {
  const a = await api.openApproval();
  for (const s of ["owner", "compliance"]) await api.signApproval(s, a.id);
});
const sendRound = () => act("Send requests", () => api.send());
const nextWeek = () => act("Close the week", () => api.closeRound());
const signAsPerson = (p) => act(`Sign as ${p.person}`, async () => {
  const v = await api.participant(p.person);
  const r = v.requests.find((x) => x.status === "open" || x.status === "partly_open");
  if (r) await api.approve(p.person, r.id, p.items);
});
const createSub = (form) => act("Create sub-project", async () => {
  const fd = new FormData(form);
  st.routing = await fetchJSON("/api/institution/subprojects", {
    name: fd.get("name"), purpose: fd.get("purpose"),
    data_types: String(fd.get("types")).split(",").map((s) => s.trim()).filter(Boolean),
    budget: Number(fd.get("budget")), weeks: Number(fd.get("weeks")),
  });
});
const runSub = (sub) => act(`Run a round of ${sub.name}`, async () => {
  const r = await fetchJSON(`/api/institution/subprojects/${encodeURIComponent(sub.id)}/run`, {});
  st.settled = r.settled.map((x) => ({ ...x, sub: sub.name, round: r.round })).concat(st.settled).slice(0, 60);
});
async function fetchJSON(path, body) {
  const t = await demoToken(`researcher@${st.study.study.id}`);
  const res = await fetch(path, { method: body ? "POST" : "GET", headers: { Authorization: `Bearer ${t}`, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  if (!res.ok) throw Object.assign(new Error(`${path} -> ${res.status}`), { detail: await res.text() });
  return res.json();
}

// A handful of sub-projects under the institution's scope, so the structure is never empty:
// in scope, one outside-scope item, one T3 item.
const SEEDS = [
  { name: "Night-shift recovery", purpose: "sleep_research", data_types: ["heart_rate.daily", "sleep.daily"], budget: 20, weeks: 6 },
  { name: "Clinic blood pressure follow-up", purpose: "sleep_research", data_types: ["blood_pressure.daily"], budget: 20, weeks: 6 },
  { name: "Diet and sleep", purpose: "sleep_research", data_types: ["sleep.daily", "meal.kcal"], budget: 15, weeks: 4 },
  { name: "Sleep apnea imaging", purpose: "sleep_research", data_types: ["sleep.daily", "imaging.mri"], budget: 25, weeks: 4 },
];
let seeding = false;
async function seed() {
  if (seeding || !st.inst || st.inst.subprojects.length) return;
  seeding = true;
  for (const x of SEEDS) await fetchJSON("/api/institution/subprojects", x).catch(() => null);
  seeding = false;
}

async function refresh() {
  try {
    if (st.readOnly) {
      const v = await (await fetch("/api/public/live")).json();
      st.study = { ...v, responses: { people: [] } };
      st.inst = v.institution;
      st.events = v.events;
    } else {
      st.study = await api.study();
      st.asks = st.study.responses.people.filter((p) => p.class === "approval" && p.status === "open");
      st.inst = await fetchJSON("/api/institution").catch(() => null);
      if (st.inst && !st.inst.subprojects.length) { await seed(); st.inst = await fetchJSON("/api/institution").catch(() => st.inst); }
    }
    st.error = null;
  } catch (e) {
    if (e.status === 403 && !st.readOnly) { st.readOnly = true; return refresh(); }
    st.error = e.detail || e.message;
  }
  draw();
}

// ---------- views ----------
function structure() {
  const s = st.study.study;
  const subs = st.inst?.subprojects || [{ id: "study", name: s.protocol.split(",")[0], status: "Live", data_types: [], paid: st.study.settlement.paid_xrp }];
  const unit = st.inst?.subprojects?.[0]?.asset || st.study.settlement.asset || "XRP";
  return h("div", { class: "card col" },
    h("div", { class: "spread" }, h("h2", {}, "Structure"), tag("Person → Institution → Sub-projects", "blue")),
    h("div", { class: "node person" }, h("b", {}, `${st.study.heatmap.rows.length} people`), h("span", { class: "muted small" }, "each with their own agent and demo wallet")),
    h("div", { class: "edge" }, "one consent to the institution's scope"),
    h("div", { class: "node inst" }, h("b", {}, s.name), h("span", { class: "muted small" },
      st.inst ? `scope: ${st.inst.scope.data_types.join(", ")}` : "scope: sleep and fatigue research")),
    h("div", { class: "tree" }, subs.map((x) => h("div", { class: "node sub" },
      h("div", { class: "spread" }, h("b", {}, x.name), tag(x.status || "Live", "green")),
      h("div", { class: "spread small muted" }, h("span", {}, (x.data_types || []).join(", ")),
        h("span", {}, st.inst ? `budget ${x.budget} · round ${x.rounds || 0} · paid ${Number(x.paid || 0).toFixed(2)} ${unit}` : `paid ${Number(x.paid || 0).toFixed(2)} ${unit}`)),
      st.inst && !st.readOnly && h("button", { class: "btn sm", style: "align-self:flex-start;margin-top:4px", disabled: !!st.busy, onclick: () => runSub(x) }, "Run a round · agents deliver, escrow settles")))),
    st.inst && h("p", { class: "muted tiny" }, st.inst.asset_label || ""),
    st.routing && routingView(st.routing, unit),
    st.inst && !st.readOnly ? h("form", { class: "subform", onsubmit: (e) => { e.preventDefault(); createSub(e.target); } },
      h("b", { class: "small" }, "New sub-project under this scope (no new contract)"),
      h("input", { name: "name", value: "Caffeine and sleep", required: true }),
      h("input", { name: "purpose", value: "sleep_research" }),
      h("input", { name: "types", value: "heart_rate.daily, caffeine", title: "in scope: heart_rate.daily, fatigue.survey · outside: caffeine · T3: genome.vcf, mri" }),
      h("div", { class: "row" }, h("input", { name: "budget", type: "number", value: "20", step: "0.01", title: `budget in ${unit}` }), h("input", { name: "weeks", type: "number", value: "4", title: "weeks" })),
      h("button", { class: "btn primary", disabled: !!st.busy }, "Create · agents route it")) :
      null);
}

function routingView(r, unit) {
  const by = { auto: 0, ask: 0, blocked: 0 };
  for (const x of r.routing || []) by[x.decision] = (by[x.decision] || 0) + 1;
  const asks = (r.routing || []).filter((x) => x.decision !== "auto");
  return h("div", { class: "note blue col", style: "gap:4px" },
    h("b", {}, `${r.name || r.subproject?.name}: routed by each person's agent`),
    h("span", {}, `${by.auto} answered inside the scope · ${by.ask} go back to the person · ${by.blocked} blocked`),
    asks.slice(0, 4).map((x) => h("span", { class: "tiny" }, `${x.pid_pseudonym} · ${x.item} · ${x.reason === "T3" ? "T3 (genomic, CT, MRI) asks the person" : x.reason.replace("_", " ")}`)));
}

const CELL = { contributed: "ok", held: "held", waiting: "wait", missing: "gap" };
function cohort() {
  const hm = st.study.heatmap;
  return h("div", { class: "card col" },
    h("div", { class: "spread" }, h("h2", {}, "Cohort"), h("span", { class: "muted small" }, `${hm.rows.length} people × ${hm.weeks.length} weeks`)),
    h("div", { class: "hm", style: `grid-template-columns: 46px repeat(${hm.weeks.length}, 1fr)` },
      h("span", {}), hm.weeks.map((w) => h("span", { class: "hd" }, `W${w}`)),
      hm.rows.map((r) => [h("span", { class: "pid" }, r.person), r.cells.map((c) => h("i", { class: CELL[c.s] || "wait", title: `${r.person} · ${c.s}` }))])),
    h("div", { class: "row tiny muted legend" },
      h("span", {}, h("i", { class: "ok" }), "sent this round"), h("span", {}, h("i", { class: "held" }), "held already"),
      h("span", {}, h("i", { class: "wait" }), "waiting"), h("span", {}, h("i", { class: "gap" }), "missing")));
}

function codeBox() {
  return h("form", { class: "card col", onsubmit: (e) => { e.preventDefault(); store.set("ar-code", new FormData(e.target).get("code")); location.reload(); } },
    h("h2", {}, "Watching"),
    h("p", { class: "muted small" }, "You can see the structure and every ledger step. To run the study and sign as the simulated people, enter the access code."),
    h("div", { class: "row" }, h("input", { name: "code", type: "password", placeholder: "Access code", style: "flex:1;font:inherit;border:1px solid var(--border);border-radius:8px;padding:8px 10px" }),
      h("button", { class: "btn primary" }, "Enter")));
}

function actions() {
  if (st.readOnly) return codeBox();
  const sp = st.study.spec_status;
  return h("div", { class: "card col" },
    h("h2", {}, "Run it"),
    h("p", { class: "muted small" }, "Signatures use demo keys held by the server for the simulated people and approvers. Everything settles on the ledger shown above."),
    h("div", { class: "steps" },
      h("button", { class: "btn", disabled: !!st.busy, onclick: findGaps }, "1 · Agent finds gaps"),
      h("button", { class: "btn", disabled: !!st.busy || sp === "none", onclick: coSign }, "2 · Budget co-sign (demo keys)"),
      h("button", { class: "btn primary", disabled: !!st.busy || sp === "none", onclick: sendRound }, "3 · Send requests"),
      h("button", { class: "btn", disabled: !!st.busy, onclick: nextWeek }, "Close the week")),
    st.asks.length ? h("div", { class: "col" },
      h("b", { class: "small" }, `${st.asks.length} people were asked (outside their consent or sensitive)`),
      st.asks.slice(0, 6).map((p) => h("div", { class: "spread small" }, h("span", {}, `${p.person} · ${p.items.join(", ")} · ${p.reason}`),
        h("button", { class: "btn sm", disabled: !!st.busy, onclick: () => signAsPerson(p) }, `Sign as ${p.person} (demo key)`)))) : null,
    st.busy && h("div", { class: "note blue" }, `${st.busy}…`),
    st.error && h("div", { class: "note red" }, st.error));
}

function log() {
  const subRows = st.settled.map((x) => ({ ts: Date.now() / 1000, kind: "subproject", actor: x.person,
    message: `${x.sub} · round ${x.round}: ${x.status} ${x.amount} ${x.asset} (EscrowCreate ${String(x.escrow_create || "").slice(0, 8)}…)`,
    tx: x.escrow_finish || x.escrow_create, url: x.url }));
  const rows = subRows.concat(st.events.filter((e) => STEP[e.kind]).slice(-200).reverse());
  return h("div", { class: "card log" },
    h("div", { class: "spread" }, h("h2", {}, "Live transaction log"), tag(st.study.study.ledger === "testnet" ? "XRPL Testnet" : "Practice ledger", "gray")),
    h("div", { class: "rows" }, rows.length ? rows.map((e) => {
      const [label, tone] = STEP[e.kind];
      const hash = txOf(e);
      const url = e.url || e.data?.url || (hash && explorer(hash));
      return h("div", { class: "lrow" },
        h("span", { class: "t mono" }, new Date(e.ts * 1000).toLocaleTimeString([], { hour12: false })),
        tag(label, tone),
        h("div", { class: "grow" }, h("div", { class: "small" }, e.message), h("div", { class: "tiny muted" }, e.actor)),
        hash ? (url ? h("a", { class: "mono", href: url, target: "_blank", rel: "noopener" }, `${hash.slice(0, 8)}… ↗`) : h("span", { class: "mono muted" }, `${hash.slice(0, 8)}…`)) : null);
    }) : h("p", { class: "muted small" }, "Nothing yet. Press 1 to start.")));
}

function draw() {
  if (!st.study) { root.replaceChildren(h("div", { class: "pad" }, st.error ? h("div", { class: "note red" }, st.error) : "Connecting to the engine…")); return; }
  const keep = root.querySelector(".log .rows")?.scrollTop || 0;
  root.replaceChildren(h("div", { class: "live" },
    h("header", {}, h("b", { class: "logo" }, "AgentRail"), h("span", { class: "muted" }, "UniQLab · UniQdata · live on the engine"),
      h("span", { class: "grow" }), h("a", { href: "/console" }, "UniQLab console"), h("a", { href: "/participant?pid=P-017" }, "UniQdata app")),
    h("div", { class: "cols" }, h("div", { class: "col left" }, structure(), actions(), cohort()), log())));
  const rows = root.querySelector(".log .rows");
  if (rows) rows.scrollTop = keep;
}

const watcher = watch(api, (got, first) => {
  if (first) st.events = [];
  st.events = st.events.concat(got.filter((e) => e.kind !== "access"));
  refresh();
});
// Read-only visitors cannot read the researcher's event stream; poll the public view instead.
setInterval(() => { if (st.readOnly) { watcher.stop(); refresh(); } }, 2000);
refresh();
