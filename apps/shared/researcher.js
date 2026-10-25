// Researcher console: Participants overview, directory and detail (Figma 56:12480, 56:12554,
// 56:12628, 59:12377-12379), round proposal with two-signer budget approval (R1), study details
// (R2) and the ledger receipt (R3). Reads GET /api/study only; the participant's own records stay
// with the participant's agent.

import { engine, watch } from "./api.js";
import {
  h, render, tag, icon, xrp, short, sum, ago, day, ledgerDay, weeksLabel, txLink, openReceipt, banner, busy, WEEK_STATE,
  holdbackState, SIGNAL, UNIT, codeGate,
} from "./ui.js";

const OPENED = new Map();   // order_id -> opened bundle result, kept across poll re-renders

const LIVE_STUDY = "Sleep and fatigue study (synthetic)";
const SAMPLE_STUDIES = [
  ["Metabolic drug study", "Prospective"],
  ["Senior sleep pattern", "Retrospective"],
  ["ADHD lifestyle", "Mixed"],
];
const ITEM = {
  "sleep.daily": "Sleep", "activity.daily": "Activity", "heart_rate.daily": "Heart rate",
  "fatigue.survey": "Fatigue survey", "blood_pressure.daily": "Blood pressure",
};
const itemName = (i) => ITEM[i] || i;

// ---------------- model: one row per participant, derived from GET /api/study ----------------

export function buildModel(s, events = []) {
  const revoked = new Map(s.withdrawals.filter((x) => x.kind === "revoke").map((x) => [x.person, x.ts]));
  const pausedNow = new Map();
  const lastSeen = new Map();
  for (const e of events) {
    const who = personOf(e);
    if (!who) continue;
    lastSeen.set(who, Math.max(lastSeen.get(who) || 0, e.ts || 0));
    if (e.kind === "paused") pausedNow.set(who, true);
    if (e.kind === "resumed" || e.kind === "revoked") pausedNow.set(who, false);
  }
  const reqs = new Map(s.responses.people.map((r) => [r.person, r]));
  const rows = s.heatmap.rows.map((hm) => {
    const pid = hm.person;
    const req = reqs.get(pid);
    const contribs = s.contributions.filter((c) => c.person === pid);
    const hbs = s.payout.holdbacks.filter((x) => x.person === pid);
    const cases = s.payout.cases.filter((x) => x.person === pid);
    const openCase = cases.find((x) => x.status === "suspected");
    const delivered = contribs.filter((c) => c.status === "delivered");
    const paid = sum(delivered, (c) => c.amount_xrp) + sum(hbs.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const held = sum(hbs.filter((x) => x.kind === "round" && (x.status === "held" || x.status === "suspected")), (x) => x.amount_xrp);
    const refunded = sum(contribs.filter((c) => c.cancel && c.cancel.tx), (c) => c.amount_xrp)
      + sum(hbs.filter((x) => x.status === "returned"), (x) => x.amount_xrp);
    const withdrawn = revoked.has(pid);
    const paused = !withdrawn && pausedNow.get(pid);
    let consent, readiness, status;
    if (withdrawn) consent = tag("Withdrawn", "red");
    else if (!req) consent = tag("Enrolled", "gray");
    else if (req.status === "contributed") consent = tag("Verified", "green");
    else if (req.status === "declined") consent = tag("Skipped", "gray");
    else if (req.status === "blocked") consent = tag("Not allowed", "gray");
    else consent = tag("Pending", "amber");

    const weeksAsked = contribs.length;
    if (withdrawn) readiness = h("span", { class: "muted" }, "Person-level data deleted");
    else if (paused) readiness = h("span", {}, "Paused by participant");
    else if (!req) readiness = h("span", { class: "muted" }, "Not requested");
    else if (req.status === "declined") readiness = h("span", { class: "muted" }, "Skipped this round");
    else if (req.status === "open") readiness = h("span", {}, "Waiting for participant");
    else if (req.status === "partly_open") readiness = h("span", {}, `Partly approved · ${delivered.length}/${Math.max(weeksAsked, 1)}`);
    else if (weeksAsked && delivered.length === weeksAsked) readiness = h("span", { style: { color: "var(--ar-green)" } }, "Delivered");
    else readiness = h("span", { style: { color: "var(--ar-brand)" } }, `Ready · ${delivered.length}/${weeksAsked}`);

    if (withdrawn) status = ["Withdrawn", "red"];
    else if (openCase) status = ["Review", "amber"];
    else if (paused) status = ["Paused", "amber"];
    else if (req && req.status === "contributed") status = ["Active", "green"];
    else if (req && (req.status === "open" || req.status === "partly_open")) status = ["Pending", "amber"];
    else if (req && req.status === "declined") status = ["Skipped", "gray"];
    else status = ["Enrolled", "gray"];

    return {
      pid, req, contribs, delivered, hbs, cases, openCase, paid, held, refunded, withdrawn, paused,
      withdrawnAt: revoked.get(pid), consent, readiness, status,
      pseudonym: (contribs[0] && contribs[0].pseudonym) || null,
      last: lastSeen.get(pid) || null,
      licence: s.licences[pid] || null,
      cells: hm.cells,
    };
  });
  const by = (st) => rows.filter((r) => r.status[0] === st).length;
  const withdrawnN = rows.filter((r) => r.withdrawn).length;
  const awaiting = by("Pending");
  return {
    rows,
    kpi: { enrolled: rows.length, withdrawn: withdrawnN, awaiting, active: rows.length - withdrawnN - awaiting,
           delivered: rows.filter((r) => r.req && r.req.status === "contributed").length, review: by("Review") },
  };
}

function personOf(e) {
  if (/^P-\d+$/.test(e.actor || "")) return e.actor;
  const m = /\bP-\d{3}\b/.exec(e.message || "");
  return m ? m[0] : null;
}

// Engine event kind -> activity row (event, stage, status). Others are not participant activity.
const ACTIVITY = {
  ask_person: ["Asked for the participant's OK", "Consent", ["Pending", "amber"]],
  provide: ["Items sent by the participant's agent", "Contribution", ["Sent", "blue"]],
  escrowed: ["Payment locked for a week", "Payment", ["Locked", "blue"]],
  locked_delivery: ["Week sealed until the round closes", "Contribution", ["Locked", "blue"]],
  paid: ["Payment released", "Payment", ["Paid", "green"]],
  holdback: ["20% held for review", "Payment", ["In review", "blue"]],
  licence: ["Access licence issued", "Authorization", ["On ledger", "green"]],
  bonus: ["Completion bonus", "Payment", ["Bonus", "blue"]],
  paused: ["Future rounds stopped by participant", "Consent", ["Paused", "amber"]],
  resumed: ["Rounds resumed by participant", "Consent", ["Active", "green"]],
  revoked: ["Data access withdrawn", "Withdrawal", ["Withdrawn", "red"]],
  clawback: ["Access licence taken back", "Withdrawal", ["On ledger", "gray"]],
  deletion_confirmed: ["Deletion confirmed", "Withdrawal", ["Confirmed", "green"]],
  refund: ["Refunded to study", "Payment", ["Refunded", "gray"]],
  decline: ["Round skipped by participant", "Consent", ["Skipped", "gray"]],
  review: ["Review opened", "Review", ["Review", "amber"]],
};

// ---------------- app ----------------

export function mountResearcher(root, { base = "", embedded = false, basePath = "", token } = {}) {
  const api = engine(base, { token });
  const st = { s: null, events: [], model: null, route: parseRoute(), filters: { q: "", status: "", consent: "" },
               studyMenu: false, approvalReq: null, lastApprove: null, sendResult: null, error: null,
               goal: "", flash: new Set() };
  root.classList.add("ar");
  if (embedded) root.classList.add("embedded");

  function parseRoute() {
    const hsh = (location.hash || "#/overview").slice(1);
    const [, a, b] = hsh.split("/");
    return { page: a || "overview", id: b ? decodeURIComponent(b) : null };
  }
  const go = (path) => { location.hash = path; };
  window.addEventListener("hashchange", () => { st.route = parseRoute(); draw(); });

  async function load() {
    try {
      st.s = await api.study();
      if (!st.s.approval || !st.s.approval.tx) st.s.approval = null;   // {} until the budget is signed
      // Contributions and withdrawals carry the study pseudonym only; the cohort table maps it to a row.
      const byPseudonym = new Map(st.s.heatmap.rows.map((r) => [r.pseudonym, r.person]));
      for (const x of [...st.s.contributions, ...st.s.withdrawals]) if (!x.person) x.person = byPseudonym.get(x.pseudonym);
      if (st.approvalReq && st.approvalReq.status === "open") st.approvalReq = await api.approval(st.approvalReq.id);
      st.model = buildModel(st.s, st.events);
      st.error = null;
    } catch (e) {
      st.error = e;
    }
    draw();
  }

  const watcher = watch(api, (evs, first) => {
    if (first) st.events = [];
    st.events = st.events.concat(evs);
    for (const e of evs) { const p = personOf(e); if (p) st.flash.add(p); }
    const focused = document.activeElement && root.contains(document.activeElement) &&
      /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if (!focused) load();
  });

  // ---------- shell ----------
  function shell(content) {
    if (embedded) return h("div", { class: "ar-content" }, content);
    const pg = st.route.page;
    const active = pg === "p" || pg === "directory" ? "directory" : pg === "rounds" ? "rounds" : pg === "study" ? "study" : "overview";
    const nav = (key, ic, label) => h("a", { class: `ew-nav${active === key ? " on" : ""}`, href: `#/${key}` }, icon(ic, 20), h("span", { class: "lbl" }, label));
    const crumb = { overview: "Overview", directory: pg === "p" ? "Participant detail" : "Directory", rounds: "Rounds", study: "Study details" }[active];
    const budget = st.s ? st.s.study.budget_xrp : 0;
    return h("div", { class: "ar-shell ew" },
      h("aside", { class: "ar-side ew-side" },
        h("div", { class: "ew-logo" }, "UniQdata"),
        h("label", { class: "ew-search" }, icon("search", 20), h("input", {
          placeholder: "Search", value: st.filters.q,
          onkeydown: (e) => { if (e.key === "Enter") { st.filters.q = e.target.value; go("#/directory"); } },
        })),
        h("div", { class: "ew-navs" },
          h("p", { class: "ew-cap" }, "RESEARCHER WORKSPACE"),
          nav("overview", "home", "Overview"), nav("directory", "users", "Directory"), nav("rounds", "layers", "Rounds"), nav("study", "list", "Study details")),
        h("div", { class: "ew-div" }),
        h("div", { class: "ew-study" }, h("span", { class: "n" }, "Sleep and fatigue"), h("span", { class: "s" }, "Synthetic · live"),
          h("span", { class: "i" }, st.s ? st.s.study.irb : ""))),
      h("div", { class: "ar-main" },
        h("header", { class: "ew-gnb" },
          h("span", { class: "ctx" }, `Sleep and fatigue study  /  ${crumb}`),
          h("div", { class: "right" },
            h("span", { class: "budget" }, `Study budget ${Math.round(budget)} ${UNIT}`),
            h("span", { class: "net" }, st.s && st.s.study.ledger === "testnet" ? "Testnet · no cash value" : "Practice ledger · no cash value"),
            h("span", { class: "prof" }, h("span", { class: "av" }, "R"), "Researcher"))),
        h("main", { class: "ar-content ew-main" }, content),
      ));
  }
  const roundLabel = (x) => ({ none: "—", draft: "Draft", approved: "Approved", sent: "Sent" })[x] || x;

  function studySelector() {
    const btn = h("button", { class: "ar-ddbtn", onclick: () => { st.studyMenu = !st.studyMenu; draw(); } },
      h("span", { class: "col", style: { gap: "0" } }, h("b", {}, LIVE_STUDY), h("span", { class: "tiny muted" }, `Active · ${st.s.study.irb}`)),
      icon("down", 16));
    return h("div", { class: "ar-dd" }, btn, st.studyMenu && h("div", { class: "menu" },
      h("div", { class: "opt" }, h("span", {}, h("b", {}, LIVE_STUDY), h("div", { class: "tiny muted" }, `Active · ${st.s.study.irb}`)), tag("Live", "green")),
      SAMPLE_STUDIES.map(([n, t]) => h("div", { class: "opt", title: "Sample study, no live data" },
        h("span", { class: "muted" }, n, h("div", { class: "tiny" }, t)), tag("Sample")))));
  }

  // ---------- pages ----------
  function draw() {
    let page;
    if (st.error && !st.s && st.error.status === 403) {
      page = h("div", { class: "col" }, codeGate("the study"));
    } else if (st.error && !st.s) {
      page = h("div", { class: "col" }, banner("red", "Could not reach the engine. ", h("button", { class: "ar-link", onclick: load }, "Retry")),
        h("span", { class: "tiny muted" }, String(st.error.message || st.error)));
    } else if (!st.s) {
      page = skeleton();
    } else {
      const p = st.route.page;
      page = p === "directory" ? directory() : p === "p" ? detail(st.route.id) : p === "rounds" ? rounds()
        : p === "study" ? studyDetails() : overview();
    }
    const scroll = window.scrollY;
    render(root, shell(page));
    window.scrollTo(0, scroll);
    st.flash.clear();
  }

  function skeleton() {
    return h("div", { class: "col" }, h("div", { class: "ar-skel", style: { height: "40px", width: "40%" } }),
      h("div", { class: "ar-grid k4" }, [1, 2, 3, 4].map(() => h("div", { class: "ar-skel", style: { height: "104px" } }))),
      h("div", { class: "ar-skel", style: { height: "240px" } }));
  }

  function overview() {
    const { kpi, rows } = st.model;
    const tone = { green: "ok", amber: "warn", red: "danger", blue: "brand", gray: "" };
    const etag = (tn, label) => h("span", { class: `fg-pill ${tone[tn] ?? tn}` }, h("span", {}, { green: "✓", amber: "!", red: "×", blue: "●" }[tn] || "●"), h("span", {}, label));
    const kc = (label, v, red) => h("div", { class: "ew-kpi" }, h("p", { class: "t" }, label), h("p", { class: `v${red ? " red" : ""}` }, String(v)));
    const count = (f) => rows.filter(f).length;
    const ready = [
      ["green", `Ready · ${count((r) => r.req && r.req.status === "contributed" && r.delivered.length < r.contribs.length)}`],
      ["blue", `Waiting for participant · ${count((r) => r.req && r.req.status === "open")}`],
      ["amber", `Partly approved · ${count((r) => r.req && r.req.status === "partly_open")}`],
      ["red", `Paused by participant · ${count((r) => r.paused)}`],
      ["green", `Delivered · ${count((r) => r.contribs.length && r.delivered.length === r.contribs.length)}`],
    ];
    const evs = [];
    for (let i = st.events.length - 1; i >= 0 && evs.length < 4; i--) {
      const e = st.events[i], pid = personOf(e), a = ACTIVITY[e.kind];
      if (!pid || !a) continue;
      const bg = { green: "ok", amber: "warn", red: "danger", blue: "brand", gray: "gray" }[a[2][1]];
      evs.push(h("button", { class: `ew-ev ${bg}`, title: e.message, onclick: () => go(`#/p/${pid}`) },
        h("p", { class: "t" }, a[0]), h("p", { class: "d" }, `${pid}${e.amount_xrp ? ` · ${e.amount_xrp.toFixed(2)} ${UNIT}` : ""} · ${ago(e.ts)}`)));
    }
    const lastTx = [...st.events].reverse().find((e) => e.tx && ACTIVITY[e.kind]);
    return h("div", { class: "ew-col" },
      h("div", { class: "ew-head" }, h("div", {}, h("h1", {}, "Participants"), h("p", { class: "sub" }, LIVE_STUDY)), etag("blue", "Live study")),
      h("div", { class: "ew-row" }, kc("Enrolled", kpi.enrolled), kc("Active", kpi.active), kc("Awaiting consent", kpi.awaiting), kc("Withdrawn", kpi.withdrawn, true)),
      h("div", { class: "ew-row mid" },
        h("div", { class: "ew-card w388" }, h("p", { class: "t" }, "Contribution readiness"), h("p", { class: "d" }, "Same event names used in participant UI"),
          ready.map(([tn, l]) => etag(tn, l))),
        h("div", { class: "ew-card grow" }, h("p", { class: "t" }, "Recent participant activity"),
          evs.length ? evs : [h("p", { class: "d" }, "No participant activity yet. Start a round to send participation requests."),
            h("a", { class: "fg-btn", href: "#/rounds", style: { width: "auto", display: "inline-grid", placeItems: "center" } }, "Open rounds")])),
      h("div", { class: "ew-card brand" }, h("p", { class: "t" }, "Synced event contract"),
        h("p", { class: "d" }, "P3 Delivered updates readiness, detail timeline and payment state from the same event."),
        lastTx ? txLink({ tx: lastTx.tx, url: lastTx.url }, { title: ACTIVITY[lastTx.kind][0] }) : null),
    );
  }

  function kpiCard(label, num, sub, badge, tone) {
    return h("div", { class: `ar-card ar-kpi ${tone}` },
      h("div", { class: "spread" }, h("span", { class: "muted" }, label), badge),
      h("div", { class: "num" }, String(num)), h("div", { class: "small muted" }, sub));
  }

  function weekChart(hm) {
    const W = 560, H = 150, n = hm.weeks.length;
    const live = hm.rows;
    const vals = hm.weeks.map((_, i) => {
      const ok = live.filter((r) => ["held", "contributed"].includes(r.cells[i].s)).length;
      return live.length ? ok / live.length : 0;
    });
    const x = (i) => 16 + (i * (W - 32)) / (n - 1);
    const y = (v) => H - 20 - v * (H - 40);
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H + 18}`);
    svg.setAttribute("width", "100%");
    const add = (tagName, attrs, text) => {
      const el = document.createElementNS(NS, tagName);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      if (text) el.textContent = text;
      svg.append(el);
      return el;
    };
    [0, 0.25, 0.5, 0.75, 1].forEach((g) => add("line", { x1: 16, x2: W - 16, y1: y(g), y2: y(g), stroke: "#eef0f3" }));
    add("polyline", { points: vals.map((v, i) => `${x(i)},${y(v)}`).join(" "), fill: "none", stroke: "#2f6bff", "stroke-width": 2 });
    vals.forEach((v, i) => {
      add("circle", { cx: x(i), cy: y(v), r: 4, fill: "#fff", stroke: "#2f6bff", "stroke-width": 2 });
      add("text", { x: x(i), y: H + 12, "text-anchor": "middle", "font-size": 11, fill: "#9ca3af" }, `W${hm.weeks[i]}`);
      add("text", { x: x(i), y: y(v) - 9, "text-anchor": "middle", "font-size": 10, fill: "#6b7280" }, `${Math.round(v * 100)}%`);
    });
    return svg;
  }

  function donut(parts, total) {
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 120 120");
    svg.setAttribute("width", "120");
    const R = 48, C = 2 * Math.PI * R;
    let off = 0;
    const ring = document.createElementNS(NS, "circle");
    Object.entries({ cx: 60, cy: 60, r: R, fill: "none", stroke: "#eef0f3", "stroke-width": 16 }).forEach(([k, v]) => ring.setAttribute(k, v));
    svg.append(ring);
    for (const [, v, color] of parts) {
      const c = document.createElementNS(NS, "circle");
      const len = total ? (v / total) * C : 0;
      Object.entries({ cx: 60, cy: 60, r: R, fill: "none", stroke: color, "stroke-width": 16,
        "stroke-dasharray": `${len} ${C - len}`, "stroke-dashoffset": -off, transform: "rotate(-90 60 60)" }).forEach(([k, val]) => c.setAttribute(k, val));
      svg.append(c);
      off += len;
    }
    const pct = total ? Math.round((parts[0][1] / total) * 100) : 0;
    return h("div", { class: "ar-donut" },
      h("div", { style: { position: "relative", width: "120px", height: "120px" } }, svg,
        h("div", { style: { position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" } },
          h("div", {}, h("div", { style: { fontSize: "22px", fontWeight: 700 } }, `${pct}%`), h("div", { class: "tiny muted" }, "active")))),
      h("ul", {}, parts.map(([l, v, c]) => h("li", {}, h("span", { class: "ar-dot", style: { background: c } }), l, h("b", {}, String(v))))));
  }

  function activityTable(limit) {
    const rows = [];
    for (let i = st.events.length - 1; i >= 0 && rows.length < limit; i--) {
      const e = st.events[i];
      const pid = personOf(e);
      const a = ACTIVITY[e.kind];
      if (!pid || !a) continue;
      rows.push(h("tr", { class: "click", title: e.message, onclick: () => go(`#/p/${pid}`) },
        h("td", { class: "strong" }, pid), h("td", {}, a[0]), h("td", { class: "muted" }, a[1]),
        h("td", { class: "muted" }, ago(e.ts)), h("td", {}, tag(a[2][0], a[2][1])),
        h("td", {}, e.tx ? txLink({ tx: e.tx, url: e.url }, { title: a[0] }) : "")));
    }
    if (!rows.length) {
      return h("div", { class: "col", style: { alignItems: "flex-start" } },
        h("p", { class: "muted" }, "No participant activity yet. Start a round to send participation requests."),
        h("a", { class: "ar-btn primary", href: "#/rounds" }, "Open rounds"));
    }
    return h("table", { class: "ar-table" },
      h("thead", {}, h("tr", {}, ["Participant", "Event", "Study stage", "Time", "Status", "Ledger"].map((x) => h("th", {}, x)))),
      h("tbody", {}, rows));
  }

  function filteredRows() {
    const f = st.filters;
    return st.model.rows.filter((r) => (!f.q || r.pid.toLowerCase().includes(f.q.toLowerCase()) ||
      (r.pseudonym || "").toLowerCase().includes(f.q.toLowerCase()))
      && (!f.status || r.status[0] === f.status)
      && (!f.consent || r.consent.textContent === f.consent)
      && (!f.payment || paymentStatus(r) === f.payment));
  }
  const paymentStatus = (r) => (r.refunded ? "Refunded" : r.held ? "In review" : r.paid ? "Paid" : "None");

  function directory() {
    const { kpi } = st.model;
    const rows = filteredRows();
    const sel = (key, label, opts) => h("select", { class: "ar-select", onchange: (e) => { st.filters[key] = e.target.value; draw(); } },
      h("option", { value: "" }, label), opts.map((o) => h("option", { value: o, selected: st.filters[key] === o }, o)));
    return h("div", { class: "col", style: { gap: "16px" } },
      h("div", { class: "ar-pagehead" },
        h("div", {}, h("h1", {}, "All participants"),
          h("p", { class: "sub" }, `${LIVE_STUDY} · ${kpi.enrolled} enrolled · ${kpi.active} active`)),
        h("div", { class: "row" },
          h("button", { class: "ar-btn", onclick: () => exportCsv(st.model.rows) }, "Export status (pseudonymous)"),
          h("button", { class: "ar-btn primary", onclick: () => go("#/rounds") }, "Send participation request"))),
      h("div", { class: "ar-card ar-filters" },
        h("label", { class: "ar-search grow", style: { margin: 0 } }, icon("search", 16), h("input", {
          placeholder: "Search participant ID or pseudonym", value: st.filters.q,
          oninput: (e) => { st.filters.q = e.target.value; },
          onkeydown: (e) => { if (e.key === "Enter") draw(); }, onblur: draw,
        })),
        sel("status", "All status", ["Active", "Pending", "Review", "Paused", "Skipped", "Withdrawn", "Enrolled"]),
        sel("consent", "Consent", ["Verified", "Pending", "Skipped", "Withdrawn", "Enrolled"]),
        sel("payment", "Payment status", ["Paid", "In review", "Refunded", "None"]),
        h("button", { class: "ar-link", onclick: () => { st.filters = { q: "", status: "", consent: "", payment: "" }; draw(); } }, "Clear filters")),
      h("div", { class: "ar-card pad0", style: { overflow: "auto" } },
        h("table", { class: "ar-table" },
          h("thead", {}, h("tr", {}, ["Participant ID", "Consent", "Data readiness", "Last activity", "Payment", "Status", ""].map((x) => h("th", {}, x)))),
          h("tbody", {}, rows.map((r) => h("tr", { class: "click", onclick: () => go(`#/p/${r.pid}`) },
            h("td", { class: "strong", title: r.pseudonym ? `Study pseudonym ${r.pseudonym}` : "" }, r.pid),
            h("td", {}, r.consent.cloneNode(true)),
            h("td", {}, r.readiness.cloneNode(true)),
            h("td", { class: "muted" }, ago(r.last)),
            h("td", {}, paymentCell(r)),
            h("td", {}, tag(...r.status)),
            h("td", { style: { color: "var(--ar-text-3)" } }, icon("chevron"))))))),
      h("p", { class: "small muted" }, `Showing ${rows.length} of ${kpi.enrolled} participants`));
  }

  function paymentCell(r) {
    if (r.withdrawn) {
      return h("span", { class: "small" }, `Paid ${xrp(r.paid)}`, r.refunded ? h("div", { class: "tiny muted" }, `${xrp(r.refunded)} refunded to study`) : null);
    }
    if (!r.paid && !r.held) return h("span", { class: "muted" }, "—");
    return h("span", {}, h("b", {}, xrp(r.paid)), r.held ? h("div", { class: "tiny muted" }, `+${xrp(r.held)} held for review`) : null);
  }

  function exportCsv(rows) {
    // No participant names or addresses: the study pseudonym and statuses only.
    const lines = [["study_pseudonym", "consent", "data_readiness", "paid_xrp", "held_xrp", "refunded_xrp", "status"]];
    for (const r of rows) {
      lines.push([r.pseudonym || "", r.consent.textContent, r.readiness.textContent, r.paid.toFixed(2), r.held.toFixed(2),
        r.refunded.toFixed(2), r.status[0]]);
    }
    const blob = new Blob([lines.map((l) => l.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n")], { type: "text/csv" });
    const a = h("a", { href: URL.createObjectURL(blob), download: "participants-status-pseudonymous.csv" });
    document.body.append(a);
    a.click();
    a.remove();
  }

  function detail(pid) {
    const r = st.model.rows.find((x) => x.pid === pid);
    if (!r) return h("div", {}, banner("amber", `No participant ${pid} in this study.`));
    const s = st.s;
    const ethics = s.study.credentials.find((c) => c.kind === "ethics_review");
    const verified = s.study.credentials.find((c) => c.kind === "verified_org");
    const lastFinish = [...r.delivered].reverse().find((c) => c.finish && c.finish.tx);
    const items = r.req ? r.req.items : [];
    const deliveredItems = [...new Set(r.delivered.flatMap((c) => c.items || []))];
    const stage = r.withdrawn ? "Withdrawn" : !r.req ? "Enrolled" : r.req.status === "contributed"
      ? (r.held ? "Payment review" : "Delivered") : r.req.status === "declined" ? "Round skipped" : "Waiting for participant";
    const releasedHeld = r.hbs.find((x) => x.kind === "round" && x.status === "released");
    const steps = [
      ["Request received", !!r.req, "blue"],
      ["Items approved", r.req && r.req.status !== "open" && r.req.status !== "declined", "blue"],
      [r.delivered.length ? `Week ${r.delivered[r.delivered.length - 1].weeks.join(", ")} delivered` : "Week delivered", r.delivered.length > 0, "blue"],
      ["Payment released", !!releasedHeld, "green"],
    ];
    const flash = st.flash.has(pid) ? " flash" : "";
    return h("div", { class: "col", style: { gap: "16px" } },
      h("div", { class: "ar-crumbs" }, h("a", { href: "#/directory", class: "row", style: { color: "inherit" } }, icon("back", 16), "Participants"), "/", h("b", {}, pid)),
      h("div", { class: "ar-pagehead" },
        h("div", {}, h("h1", {}, `Participant ${pid}`),
          h("p", { class: "sub" }, r.withdrawn ? `Withdrawn · person-level data deleted ${day(r.withdrawnAt)}`
            : "Pseudonymous record · shows only items this participant approved")),
        h("div", { class: "row" },
          h("button", { class: "ar-btn", disabled: true, title: "Coming soon" }, "Send reminder"),
          h("button", { class: "ar-btn", onclick: () => exportCsv([r]) }, "Export status"))),
      h("div", { class: `ar-card${flash}` },
        h("div", { class: "row", style: { gap: "28px", flexWrap: "wrap" } },
          h("div", { class: "row", style: { gap: "14px" } },
            h("div", { style: { width: "54px", height: "54px", borderRadius: "50%", background: "var(--ar-brand-weak)", color: "var(--ar-brand)", display: "grid", placeItems: "center", fontWeight: 700 } }, pid.replace("P-", "P")),
            h("div", { class: "col", style: { gap: "2px" } }, h("b", { style: { fontSize: "17px" } }, pid),
              h("span", { class: "small muted" }, r.pseudonym ? `Study pseudonym ${r.pseudonym}` : "No contribution yet"),
              h("span", {}, tag(...r.status)))),
          field("Study", "Sleep and fatigue study"),
          field("Last activity", ago(r.last)),
          field("Paid so far", h("span", {}, xrp(r.paid), r.held ? h("div", { class: "tiny muted" }, `+${xrp(r.held)} held for review`) : null)),
          field("Review", r.openCase ? h("span", { style: { color: "var(--ar-amber)" } }, `Review open (${respondBy(r.openCase)})`)
            : h("span", { style: { color: "var(--ar-green)" } }, "Review: none")))),
      h("div", { class: "ar-grid k2" },
        h("div", { class: "ar-card" },
          h("h2", {}, "Authorization & data access"),
          h("p", { class: "small muted", style: { marginBottom: "8px" } }, "Checked against the participant's consent and the ledger."),
          checkRow("Consent", r.consent.cloneNode(true), r.req && r.req.status === "contributed"),
          checkRow("Ethics review · On ledger", ethics ? txLink(ethics, { title: "Ethics review credential issued", kind: "CredentialCreate", from: "Ethics board (synthetic)", to: "Study" }) : tag("Missing", "amber"), !!ethics),
          checkRow("Verified organization", verified ? txLink(verified, { title: "Verified organization credential", kind: "CredentialCreate" }) : tag("Missing", "amber"), !!verified),
          checkRow("Study budget approval · 2 of 2 signers", s.approval ? txLink(s.approval, { title: "Study budget approved by 2 signers", kind: "Payment", kindNote: "multi-signed", amount: s.approval.amount_xrp }) : tag("Not yet", "gray"), !!s.approval),
          checkRow("Access licence", r.licence ? tag(r.licence.clawed_back ? "Taken back" : "Held by study", r.licence.clawed_back ? "gray" : "green") : tag("Not issued", "gray"), !!r.licence && !r.licence.clawed_back),
          h("div", { class: "spread", style: { background: "var(--ar-row)", borderRadius: "8px", padding: "10px 12px", marginTop: "8px" } },
            lastFinish ? txLink(lastFinish.finish, { title: `Week ${lastFinish.weeks.join(", ")} participation payment released`, kind: "EscrowFinish", kindNote: "payment unlocked", amount: lastFinish.amount_xrp, memo: `bundle ${short(lastFinish.bundle_hash, 8, 4)}` })
              : h("span", { class: "small muted" }, "No ledger record yet"),
            lastFinish && h("span", { class: "small muted mono" }, `Bundle ${short(lastFinish.bundle_hash, 6, 6)}`))),
        h("div", { class: "ar-card" },
          h("h2", { style: { marginBottom: "12px" } }, "Study participation"),
          h("dl", { class: "ar-kv", style: { gridTemplateColumns: "120px 1fr" } },
            h("dt", {}, "Enrollment"), h("dd", { style: { textAlign: "left", fontWeight: 600 } }, r.withdrawn ? "Withdrawn" : "Enrolled"),
            h("dt", {}, "Study period"), h("dd", { style: { textAlign: "left", fontWeight: 600 } }, "Weeks 1–8"),
            h("dt", {}, "Current stage"), h("dd", { style: { textAlign: "left", fontWeight: 600 } }, stage),
            h("dt", {}, "Data scope"), h("dd", { style: { textAlign: "left", fontWeight: 600 } }, deliveredItems.length ? deliveredItems.map(itemName).join(", ") : "—"),
            h("dt", {}, "Requested"), h("dd", { style: { textAlign: "left" } }, items.length ? `${items.map(itemName).join(", ")} · ${weeksLabel([...new Set(r.contribs.flatMap((c) => c.weeks))])}` : "—")),
          h("div", { class: "ar-banner green", style: { marginTop: "12px", flexDirection: "column", gap: "2px" } },
            h("b", {}, `Delivered rounds: ${r.delivered.length}`),
            h("span", { class: "tiny" }, deliveredItems.length ? `items: ${deliveredItems.map(itemName).join(", ")}` : "nothing delivered yet")))),
      h("div", { class: "ar-grid k2" },
        h("div", { class: "ar-card" },
          h("h2", {}, "Participation timeline"),
          h("div", { class: "ar-steps" }, steps.map(([l, done, tone]) => h("div", { class: `s ${done ? (tone === "green" ? "done-g" : "") : "todo"}` },
            h("span", { class: "dot" }), h("b", {}, l), h("span", { class: "tiny muted" }, done ? "done" : "—")))),
          weekStrip(r),
          r.contribs.length ? h("table", { class: "ar-table", style: { marginTop: "12px" } },
            h("thead", {}, h("tr", {}, ["Week", "Amount", "State", "Ledger", ""].map((x) => h("th", {}, x)))),
            h("tbody", {}, r.contribs.map((c) => {
              const ws = WEEK_STATE[c.cancel && c.cancel.tx ? "refunded" : c.status] || { label: c.status, tone: "gray" };
              const t = c.finish && c.finish.tx ? c.finish : c.cancel && c.cancel.tx ? c.cancel : c.escrow;
              const kind = t === c.finish ? "EscrowFinish" : t === c.cancel ? "EscrowCancel" : "EscrowCreate";
              const out = h("span", { class: "tiny muted" }, OPENED.get(c.order_id) || "");
              return h("tr", {}, h("td", {}, `W${c.weeks.join(", ")}`), h("td", {}, xrp(c.amount_xrp)), h("td", {}, tag(ws.label, ws.tone)),
                h("td", {}, txLink(t, { kind, amount: c.amount_xrp, title: kind === "EscrowFinish" ? `Week ${c.weeks.join(", ")} participation payment released` : undefined })),
                h("td", {}, c.status === "delivered" && !r.withdrawn ? h("button", { class: "ar-link small", onclick: async (e) => {
                  const b = await busy(e.target, "Opening", () => api.bundle(c.order_id), () => { out.textContent = "Could not open"; });
                  if (!b) return;
                  if (!b.ok) { out.textContent = b.message || "Could not open"; return; }
                  // The key that opened the bundle is the Fulfillment the payment release put on the ledger.
                  out.replaceChildren(h("span", { class: "col", style: { gap: "2px" } },
                    h("span", {}, b.hash_matches ? `Opened · ${b.rows ? b.rows.length : 0} row${b.rows && b.rows.length === 1 ? "" : "s"} match what was sent` : "Hash mismatch"),
                    b.key_from ? h("span", { class: "row", style: { gap: "4px" } }, "Key from the payment release", txLink(b.key_from, { kind: "EscrowFinish", kindNote: "same key that released the payment" })) : null,
                    b.fulfillment_on_ledger ? h("span", { class: "mono", title: b.fulfillment_on_ledger }, `Fulfillment ${short(b.fulfillment_on_ledger, 10, 6)}`) : null));
                } }, "Open bundle") : null, out));
            }))) : null),
        controls(r)),
    );
  }

  // Practice ledger time is not wall-clock time, so only Testnet shows a date.
  const respondBy = (c) => (st.s.study.ledger === "testnet" ? `respond by ${ledgerDay(c.respond_by)}` : "respond within 3 days");

  function field(label, value) {
    return h("div", { class: "col", style: { gap: "4px" } }, h("span", { class: "small muted" }, label), h("b", {}, value));
  }
  function checkRow(label, right, ok) {
    return h("div", { class: "ar-check" }, h("span", { class: `ic ${ok ? "ok" : "wait"}` }, ok ? icon("check", 12) : "·"), h("span", { class: "grow" }, label), right);
  }

  function weekStrip(r) {
    const asked = new Map();
    for (const c of r.contribs) for (const w of c.weeks) asked.set(w, c.cancel && c.cancel.tx ? "refunded" : c.status === "delivered" ? "contributed" : "escrowed");
    return h("div", { style: { marginTop: "14px" } },
      h("div", { class: "small muted", style: { marginBottom: "6px" } }, "Weeks this participant was asked for"),
      h("div", { class: "ar-weeks" }, st.s.heatmap.weeks.map((w, i) => {
        const cell = r.cells[i].s;
        const state = asked.get(w) || (cell === "waiting" ? "requested" : cell === "withdrawn" ? "withheld" : cell);
        return h("div", { class: `ar-week ${state}`, title: (WEEK_STATE[state] || {}).label || state }, `W${w}`);
      })));
  }

  function controls(r) {
    const c = r.openCase;
    const reviewer = h("input", { class: "ar-input", placeholder: "Reviewer ID (a named person)", value: "reviewer-kim" });
    const msg = h("div");
    const decide = (confirm) => async (e) => {
      const res = await busy(e.target, "Recording", () => api.decideCase(c.id, reviewer.value.trim(), confirm),
        (err) => render(msg, banner("red", "Could not record the decision. ", h("span", { class: "tiny" }, err.message))));
      if (res && !res.ok) render(msg, banner("amber", res.message));
      else if (res) load();
    };
    const approvalTx = st.s.approval;
    return h("div", { class: "ar-card col", style: { gap: "10px" } },
      h("h2", {}, "Researcher controls"),
      h("p", { class: "small muted" }, "Actions are logged and visible to the participant."),
      h("button", { class: "ar-btn primary block", disabled: !approvalTx, onclick: () => approvalTx && openReceipt({
        ...approvalTx, title: "Study budget approved by 2 signers", kind: "Payment", kindNote: "multi-signed", amount: approvalTx.amount_xrp,
        from: "Study treasury (2 of 2 signers)", to: "Study agent" }) }, "View authorization record"),
      c ? h("div", { class: "col", style: { gap: "8px" } },
        banner("amber", h("div", {}, h("b", {}, "Review open"), h("div", { class: "small" },
          c.signals.map((x) => `Week ${x.week} ${itemName(x.item)} ${SIGNAL[x.code] || x.code}`).join(" · ")),
          h("div", { class: "tiny" }, c.response ? `Participant response: “${c.response}”` : `Participant can ${respondBy(c)}`))),
        reviewer,
        h("div", { class: "row" },
          h("button", { class: "ar-btn grow", onclick: decide(false) }, "Clear · pay held part"),
          h("button", { class: "ar-btn danger grow", onclick: decide(true) }, "Confirm signal")),
        h("p", { class: "tiny muted" }, "A person decides. Confirming is refused before the response period ends."), msg)
        : h("button", { class: "ar-btn block", disabled: true, title: "Opens when the code review finds a signal in a contribution" }, "Hold payment for review"),
      h("p", { class: "tiny muted" }, "Only the participant can stop or withdraw. The study can ask for a review."));
  }

  // ---------- R1: round proposal and two-signer approval ----------
  function rounds() {
    const s = st.s;
    const status = s.spec_status;
    const p = s.proposal;
    const stepCls = (n) => {
      const stage = { none: 1, draft: 2, approved: 4, sent: 5 }[status] || 1;
      return n < stage ? "ar-step done" : n === stage || (n === 3 && stage === 2) ? "ar-step on" : "ar-step off";
    };
    const goal = h("textarea", { class: "ar-textarea", placeholder: "Raise power to 0.8 for fatigue vs sleep, weeks 3–5" }, st.goal || s.goal || "");
    const msg = h("div");
    const err = (e) => {
      if (e.status === 409 && /already approved/.test(e.detail || "")) { load(); return render(msg, banner("blue", "This round's budget is already approved by both signers. Send it, or set a new goal for a new round.")); }
      if (e.status === 403 && /reset/.test(e.message)) return render(msg, banner("blue", "The shared sandbox can't be reset from the browser. Set a new goal to start a new round."));
      render(msg, banner("red", "The engine did not answer. ", h("span", { class: "tiny" }, e.message)));
    };
    return h("div", { class: "col", style: { gap: "16px" } },
      h("div", { class: "ar-pagehead" },
        h("div", {}, h("h1", {}, "Rounds"), h("p", { class: "sub" }, `${LIVE_STUDY} · propose, approve and send a participation round`)),
        h("div", { class: "row" }, tag(roundLabel(status), status === "sent" ? "green" : status === "none" ? "gray" : "blue"))),
      msg,
      h("div", { class: "ar-stepper" },
        h("div", { class: stepCls(1) }, h("span", { class: "n" }, "1"), h("div", { class: "ar-card col" },
          h("h2", {}, "Goal"),
          goal,
          h("div", { class: "spread" },
            h("span", { class: "small muted" }, `Power ${s.heatmap.power_before ?? s.heatmap.power} → target ${s.power_target} · ${s.heatmap.complete_pairs} of ${s.heatmap.total} pairs`),
            h("button", { class: "ar-btn primary", disabled: status === "approved", title: status === "sent" ? "Propose the next round" : undefined, onclick: async (e) => {
              st.goal = goal.value;
              const r = await busy(e.target, "The agent is reading the coverage table", () => api.setGoal(goal.value), err);
              if (r) { st.lastApprove = null; load(); }
            } }, "Propose")),
          heatmap(s.heatmap))),
        h("div", { class: stepCls(2) }, h("span", { class: "n" }, "2"), h("div", { class: "ar-card col" },
          h("div", { class: "spread" }, h("h2", {}, "Proposal"),
            p && h("span", { class: "small muted" }, p.source === "llm" ? "Proposed by the study's agent · checked by code" : "Rule baseline · checked by code")),
          p ? proposal(p) : h("p", { class: "muted" }, "Write a goal and press Propose. The agent reads the coverage table and code checks every claim."))),
        h("div", { class: stepCls(3) }, h("span", { class: "n" }, "3"), h("div", { class: "ar-card col" },
          h("h2", {}, "Budget approval"),
          h("p", { class: "small muted" }, `Treasury ${short(s.study.treasury.address, 4, 3)} · needs ${s.study.treasury.quorum} of ${s.study.treasury.signers.length} signers`),
          h("div", { class: "ar-grid k2e" }, s.study.treasury.signers.map((who) => {
            const req = st.approvalReq;
            const signed = (s.approval && s.approval.signers.includes(who)) || (req && req.signatures.some((x) => x.signer === who));
            return h("div", { class: `ar-signer${signed ? " on" : ""}` },
              h("div", { class: "col", style: { gap: "2px" } }, h("b", {}, who === "owner" ? "Owner" : "Compliance"),
                h("span", { class: "small muted" }, signed ? "Signed on their device" : req ? "Waiting for their signature" : "Not asked yet")),
              req && req.status === "open" && !signed && h("button", { class: "ar-btn sm", onclick: async (e) => {
                const r = await busy(e.target, "Signing on their device", () => api.signApproval(who, req.id), err);
                if (r) { st.approvalReq = r; st.lastApprove = r; load(); }
              } }, "Sign on their device"));
          })),
          approveBanner(),
          h("button", { class: "ar-btn primary", disabled: status !== "draft" || (st.approvalReq && st.approvalReq.status === "open"), onclick: async (e) => {
            const r = await busy(e.target, "Asking both signers", () => api.openApproval(), err);
            if (r) { st.approvalReq = r; st.lastApprove = null; draw(); }
          } }, "Ask both signers to approve the budget"))),
        h("div", { class: stepCls(4) }, h("span", { class: "n" }, "4"), h("div", { class: "ar-card col" },
          h("h2", {}, "Send participation requests"),
          status === "sent" ? h("div", { class: "col" },
            h("div", { class: "ar-grid k4" },
              kpiCard("Handled by agents", s.responses.auto, "inside each person's consent", null, "green"),
              kpiCard("Waiting for the person", s.responses.approval, "needs their OK", null, "amber"),
              kpiCard("Not allowed", s.responses.blocked, "outside the purpose", null, ""),
              kpiCard("Paid so far", xrp(s.settlement.paid_xrp), `${s.settlement.people_paid} people · ${xrp(s.settlement.refunded_xrp)} refunded`, null, "")),
            h("a", { href: "#/directory", style: { fontWeight: 500 } }, "Open the participant directory →"))
            : h("p", { class: "muted" }, "Requests go out after the budget is approved. Each participant's agent answers inside their consent and asks them for anything else."),
          h("div", { class: "row", style: { flexWrap: "wrap" } },
            h("button", { class: "ar-btn primary", disabled: status !== "approved", onclick: async (e) => {
              const r = await busy(e.target, "Locking payments on the ledger", () => api.send(), err);
              if (r) load();
            } }, "Send participation request"),
            h("button", { class: "ar-btn", disabled: status !== "sent", title: "Release weeks the agents sealed until the round closes", onclick: async (e) => {
              if (await busy(e.target, "Closing", () => api.closeRound(), err)) load();
            } }, "Close round"),
            h("button", { class: "ar-btn", disabled: status !== "sent", title: "Pay held 20% parts whose review ended", onclick: async (e) => {
              if (await busy(e.target, "Releasing", () => api.releaseHeld(), err)) load();
            } }, "Release reviewed payments"),
            h("button", { class: "ar-btn", disabled: status !== "sent", title: "Return locked payments for weeks that were never released", onclick: async (e) => {
              if (await busy(e.target, "Returning", () => api.sweep(), err)) load();
            } }, "Return unreleased to study"))))),
      h("div", { class: "ar-card" }, h("div", { class: "spread" },
        h("span", { class: "small muted" }, "Demo: start again with a fresh synthetic cohort (50 participants)."),
        h("button", { class: "ar-btn sm", onclick: async (e) => {
          if (await busy(e.target, "Resetting", () => api.reset(), err)) { watcher.restart(); st.lastApprove = null; st.approvalReq = null; load(); }
        } }, "Reset demo"))));
  }

  function approveBanner() {
    const r = st.lastApprove;
    if (st.s.approval) {
      return banner("green", icon("check", 16), h("span", {}, `Approved by ${st.s.approval.signers.length} signers · ${xrp(st.s.approval.amount_xrp)} `,
        txLink(st.s.approval, { title: "Study budget approved by 2 signers", kind: "Payment", kindNote: "multi-signed", amount: st.s.approval.amount_xrp })));
    }
    const req = st.approvalReq;
    if (req && req.status === "open") {
      const n = req.signatures.length;
      return banner("amber", h("div", {}, h("b", {}, `${n} of ${req.quorum} signed, waiting`),
        h("div", { class: "small" }, n ? "Nothing moves on the ledger until the second signer signs on their own device."
          : "Each signer sees the amount and destination on their own device before signing.")));
    }
    if (r && r.ok === false) {
      return banner("amber", h("div", {}, h("b", {}, "Refused"), h("div", { class: "tiny" }, r.message || r.result || "")));
    }
    return null;
  }

  function heatmap(hm) {
    return h("div", { class: "col", style: { gap: "6px" } },
      h("div", { class: "ar-heat", style: { gridTemplateColumns: `repeat(${hm.weeks.length}, 1fr)` } },
        hm.rows.flatMap((r) => r.cells.map((c, i) => h("span", { class: `c ${c.s}`, title: `${r.person} · W${hm.weeks[i]} · ${c.s}` })))),
      h("div", { class: "ar-legend" }, [["held", "#c7d2fe", "On participant's device"], ["contributed", "#10b981", "Delivered"],
        ["waiting", "#fbbf24", "Locked or waiting"], ["missing", "#fff", "Missing"], ["withdrawn", "#fca5a5", "Withdrawn"]]
        .map(([, c, l]) => h("span", {}, h("i", { style: { background: c, outline: "1px solid #e5e7eb" } }), l))));
  }

  function proposal(p) {
    const verdictTag = (v) => tag(v[0].toUpperCase() + v.slice(1), v === "kept" ? "green" : v === "narrowed" ? "amber" : "gray");
    return h("div", { class: "col" },
      h("table", { class: "ar-table" },
        h("thead", {}, h("tr", {}, ["Item", "Proposed weeks", "Evidence", "Code check", "Kept weeks"].map((x) => h("th", {}, x)))),
        h("tbody", {}, p.claims.map((c) => h("tr", { title: c.code_reason },
          h("td", { class: c.verdict === "removed" ? "strike strong" : "strong" }, itemName(c.item)),
          h("td", {}, weeksLabel(c.weeks)),
          h("td", { class: "small muted" }, c.llm_evidence || "—"),
          h("td", {}, verdictTag(c.verdict), h("div", { class: "tiny muted" }, c.code_reason)),
          h("td", {}, c.kept_weeks && c.kept_weeks.length ? weeksLabel(c.kept_weeks) : "—"))))),
      p.notes && p.notes.length ? h("p", { class: "tiny muted" }, p.notes.join(" · ")) : null,
      h("div", { class: "row", style: { gap: "16px" } },
        h("b", {}, `${p.people} people · ${p.cells} cells · ${p.budget_xrp} ${UNIT}`),
        p.verdict === "rejected" ? tag("Nothing in the table supports this goal", "amber") : null),
      h("div", { class: "ar-banner blue", style: { flexDirection: "column", gap: "4px" } },
        h("span", { class: "tiny" }, "Participants will read"), h("span", {}, p.summary_for_participants)));
  }

  // ---------- R2: study details ----------
  function studyDetails() {
    const s = st.s.study;
    return h("div", { class: "col", style: { gap: "16px" } },
      h("div", { class: "ar-pagehead" }, h("div", {}, h("h1", {}, "Study details"), h("p", { class: "sub" }, s.name))),
      h("div", { class: "ar-grid k2e" },
        h("div", { class: "ar-card" }, h("dl", { class: "ar-kv", style: { gridTemplateColumns: "140px 1fr" } },
          ...[["Study name", LIVE_STUDY], ["Study type", "Prospective"], ["Purpose", "Sleep research"],
            ["Data use codes", s.duo.map((d) => d.code).join(" · ")], ["IRB number", s.irb], ["Ethics board", "Ethics board (synthetic)"],
            ["Protocol", s.protocol]].flatMap(([k, v]) => [h("dt", {}, k), h("dd", { style: { textAlign: "left" } }, v)]))),
        h("div", { class: "ar-card col" },
          h("h2", {}, "On the ledger"),
          s.credentials.map((c) => checkRow(c.label, txLink(c, { title: c.kind === "ethics_review" ? "Ethics review credential issued" : "Verified organization credential", kind: "CredentialCreate" }), c.on_ledger)),
          h("div", { class: "ar-divider" }),
          h("p", {}, `Treasury ${short(s.treasury.address, 4, 3)} · ${s.treasury.quorum} of ${s.treasury.signers.length} signers: Owner, Compliance`),
          h("p", {}, `Budget ${xrp(s.budget_xrp)} · spent ${xrp(s.spent_xrp)} · reserved ${xrp(s.reserved_xrp)}`),
          s.credentials.some((c) => c.kind === "ethics_review")
            ? null : banner("amber", "No ethics review on the ledger. Sensitive items cannot be requested."))));
  }

  load();
  return { reload: load, stop: () => watcher.stop() };
}
