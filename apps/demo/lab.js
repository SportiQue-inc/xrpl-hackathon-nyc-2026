// UniQLab, the researcher side. ?mode=before is today's flow (one contract per project, wait for
// people, no way to ask for a missing week). ?mode=after is the same lab with agents: one
// relationship per person covering several sub-projects, the study agent asks for exact gaps,
// data arrives weekly and is paid per delivered week in RLUSD.

import { DISPLAY_UNIT } from "../shared/ui.js";
import { MODE, INST, SUBS, NEW_SUB, ITEMS, PEOPLE, HERO, rl, weekPrice, subTotal, h, tag, send, listen, toast } from "./common.js";

const root = document.getElementById("app");
const st = MODE === "before" ? {
  view: "projects", day: 12, applicants: ["A-201", "A-202", "A-203", "A-204"], reviewed: new Set(),
  code: null, linked: false, lanes: 0, approved: new Set(), settled: false,
} : {
  view: "inst", sub: "S1", asked: false, filled: new Set(), joined: false, week: 3, running: false,
  feed: [
    { dot: "green", text: "Week 3 · 46 of 50 people delivered by their agents", sub: "Escrow released per delivery", amt: 736 },
    { dot: "green", text: "Week 2 · 49 of 50 delivered", sub: "Escrow released per delivery", amt: 784 },
  ],
  added: false, exception: null,
};

// ---------- shell ----------
function nav(id, label, extra) {
  return h("button", { class: `nav${st.view === id ? " on" : ""}`, onclick: () => go(id) }, label, extra && h("span", { class: "count" }, extra));
}
function go(v) { st.view = v; draw(); window.scrollTo(0, 0); }

function shell(body) {
  const side = MODE === "before"
    ? h("aside", { class: "lab-side" },
      h("div", { class: "lab-logo" }, h("b", {}, "UniQ"), "Lab"),
      nav("projects", "My projects", tag("3", "gray")),
      ...SUBS.map((s) => h("div", { class: "nav-sub" }, h("span", {}, s.name), tag("Contract", "gray"))),
      nav("project", "Recruiting · Sleep and fatigue"),
      nav("table", "Study data table"),
      nav("settle", "Settlement"),
      h("div", { class: "nav-sep" }),
      h("div", { class: "nav-label" }, INST.name))
    : h("aside", { class: "lab-side" },
      h("div", { class: "lab-logo" }, h("b", {}, "UniQ"), "Lab ", tag("AgentRail", "blue")),
      nav("inst", INST.short, tag("1 relationship", "blue")),
      h("div", { class: "tree", style: { margin: "4px 0 8px 22px" } },
        ...[...SUBS, ...(st.added ? [NEW_SUB] : [])].map((s) => h("div", { class: "spread small" }, s.name, s.id === "S4" ? tag("New", "blue") : tag("Live", "green")))),
      nav("agent", "Study agent", st.asked ? null : tag("3 gaps", "amber")),
      nav("weekly", "Weekly delivery", tag(`W${st.week}`, "gray")),
      nav("add", "Add a sub-project"));
  const top = h("header", { class: "lab-top" },
    MODE === "before"
      ? [tag("Today's flow", "gray"), h("span", { class: "muted small" }, `Settlement in ${DISPLAY_UNIT} after monthly batch`)]
      : [h("span", { class: "small", style: { color: "var(--brand)", fontWeight: 600 } }, `Budget ${rl(5000)} · signed once by 2`), tag("XRPL Testnet", "gray")],
    h("span", { class: "avatar" }), h("span", { class: "small" }, "Researcher A"));
  return h("div", { class: "lab" }, side, h("main", { class: "lab-main" }, top, h("div", { class: "lab-body" }, body)));
}

function kpi(label, v, sub, from) {
  return h("div", { class: "kpi" }, h("div", { class: "muted small" }, label),
    h("div", { class: `v${from ? " blue" : ""}` }, from && h("span", { class: "from" }, from), v), h("div", { class: "muted tiny" }, sub));
}

// ---------- before ----------
const STEPS = ["Study design", "IRB prep", "Open recruiting", "Applicant review", "Linking code", "Consent request", "Waiting for participants"];
function stepper(now) {
  return h("div", { class: "steps" }, STEPS.map((s, i) =>
    h("div", { class: `step ${i < now ? "done" : i === now ? "now" : "locked"}` }, h("span", { class: "n" }, i + 1), i === now ? `⏱ ${s}` : s)));
}

function beforeProjects() {
  return [
    h("div", { class: "spread" }, h("div", {}, h("h1", {}, "My projects"), h("p", { class: "muted" }, `${INST.name} · each project runs on its own`)),
      h("button", { class: "btn primary", onclick: () => toast(root, "New project: design → IRB → recruit → contract, from the start") }, "+ New project")),
    h("div", { class: "kpis" },
      kpi("Contracts per participant", "3", "one per project"),
      kpi("Consent signatures", "6", "2 lanes × 3 projects"),
      kpi("Manual approvals", "18", "per person, 6 weeks"),
      kpi("Time to fill a gap", "weeks", "re-recruit · illustrative")),
    h("div", { class: "grid3" }, SUBS.map((s, i) => h("div", { class: "sub-card" },
      h("div", { class: "spread" }, h("h3", {}, s.name), tag(i === 0 ? "Waiting" : "Recruiting", "amber")),
      h("div", { class: "muted small" }, `${s.pis} · ${s.weeks} weeks · ${s.items.map((k) => ITEMS[k].label).join(", ")}`),
      h("div", { class: "col small", style: { gap: "4px", marginTop: "6px" } },
        h("div", { class: "spread" }, "Contract", h("span", { class: "mono" }, `NSL-2026-0${41 + i}`)),
        h("div", { class: "spread" }, "IRB", h("span", { class: "muted" }, "own review")),
        h("div", { class: "spread" }, "Recruiting", h("span", { class: "muted" }, "own post, own applicants")),
        h("div", { class: "spread" }, "Consent forms", h("span", { class: "muted" }, "2 per person"))),
      h("div", { class: "bar-track", style: { marginTop: "8px" } }, h("div", { class: "bar-fill", style: { width: `${[86, 57, 43][i]}%`, background: "#f59e0b" } })),
      h("button", { class: "btn sm", style: { alignSelf: "flex-start", marginTop: "6px" }, onclick: () => go("project") }, "Open")))),
    h("div", { class: "note gray" }, "The same person joining all three projects gets three contracts, three recruiting flows and six consent forms."),
  ];
}

function beforeProject() {
  const s = SUBS[0];
  return [
    h("div", { class: "spread" }, h("div", {}, h("h1", {}, s.name), h("p", { class: "muted" }, `${INST.name} · ${INST.irb} · Contract NSL-2026-041`)),
      h("div", { class: "card", style: { padding: "10px 16px", borderColor: "#fcd34d", background: "#fffbeb" } },
        h("div", { class: "small", style: { color: "var(--amber)" } }, "Waiting for participants"),
        h("div", { class: "clock", style: { fontSize: "22px", fontWeight: 700, color: "var(--amber)" } }, `Day ${st.day}`))),
    stepper(6),
    h("div", { class: "grid2" },
      h("div", { class: "card col", style: { gap: "12px" } },
        h("div", { class: "spread" }, h("h2", {}, "Applicant queue"), tag(`${st.applicants.length - st.reviewed.size} to review`, "amber")),
        h("p", { class: "muted small" }, "Every applicant is reviewed by hand before a linking code can go out."),
        ...st.applicants.map((a) => h("div", { class: "spread", style: { padding: "8px 0", borderTop: "1px solid var(--border)" } },
          h("span", {}, a, h("span", { class: "muted small" }, " · applied 3 days ago")),
          st.reviewed.has(a) ? tag("Reviewed", "green")
            : h("button", { class: "btn sm", onclick: () => { st.reviewed.add(a); draw(); } }, "Review")))),
      h("div", { class: "col", style: { gap: "18px" } },
        h("div", { class: "card col", style: { gap: "10px" } },
          h("h2", {}, "Linking code"),
          h("p", { class: "muted small" }, "Issue a code and send it outside the app. The person types it into UniQdata."),
          st.code
            ? h("div", { class: "col" },
              h("div", { class: "spread" }, h("span", { class: "mono", style: { fontSize: "20px" } }, st.code), tag(st.linked ? "Linked" : "Sent by text · not entered yet", st.linked ? "green" : "amber")),
              !st.linked && h("p", { class: "muted tiny" }, `Waiting for ${HERO} to enter it.`))
            : h("button", { class: "btn primary", onclick: issueCode }, `Issue code for ${HERO} and text it`)),
        h("div", { class: "card col", style: { gap: "10px" } },
          h("div", { class: "spread" }, h("h2", {}, "Consent requests"), tag(`${14 - (st.lanes === 2 ? 1 : 0)} waiting`, "amber")),
          h("div", { class: "spread small" }, `${HERO} · research participation`, st.lanes >= 1 ? tag("Signed", "green") : tag("Waiting", "gray")),
          h("div", { class: "spread small" }, `${HERO} · sensitive health collection`, st.lanes >= 2 ? tag("Signed", "green") : tag("Waiting", "gray")),
          h("p", { class: "muted tiny" }, "This project only. The other two projects ask again.")))),
  ];
}

function coverageBefore() {
  const cols = 6;
  const cell = (p, w) => {
    if (p !== HERO) return "ok";
    if (w === 3) return "gap";
    const both = ["hr", "fatigue"].every((k) => st.approved.has(`${k}:${w}`));
    return both ? "ok" : "wait";
  };
  return h("div", { class: "cov", style: { gridTemplateColumns: `70px repeat(${cols}, 1fr)` } },
    h("span", {}), ...Array.from({ length: cols }, (_, i) => h("span", { class: "hd" }, `W${i + 1}`)),
    ...PEOPLE.flatMap((p) => [h("span", { style: { fontWeight: p === HERO ? 600 : 400 } }, p),
      ...Array.from({ length: cols }, (_, i) => h("div", { class: `cell ${cell(p, i + 1)}` }))]));
}

function beforeTable() {
  return [
    h("div", {}, h("h1", {}, "Study data table"), h("p", { class: "muted" }, "Sleep and fatigue · 6 weeks · heart rate and fatigue survey")),
    h("div", { class: "card col", style: { gap: "14px" } },
      coverageBefore(),
      h("div", { class: "row small muted", style: { gap: "16px" } },
        h("span", { class: "row" }, h("span", { class: "cell ok", style: { width: "16px", height: "12px" } }), "Delivered"),
        h("span", { class: "row" }, h("span", { class: "cell wait", style: { width: "16px", height: "12px" } }), "Waiting for the person to approve"),
        h("span", { class: "row" }, h("span", { class: "cell gap", style: { width: "16px", height: "12px" } }), "Missing")),
      h("div", { class: "note red" }, `⊗ ${HERO} missed week 3. There is no way to ask for that one week again.`),
      h("div", { class: "row" },
        h("button", { class: "btn", onclick: () => toast(root, "Re-recruit: new post, new applicants, new contract, new consent") }, "Re-recruit a replacement"),
        h("span", { class: "muted small" }, "One replacement costs about $19.5k on average (industry estimate)."))),
  ];
}

function beforeSettle() {
  return [
    h("div", {}, h("h1", {}, "Settlement"), h("p", { class: "muted" }, "Paid in a monthly batch after the whole period is reviewed")),
    h("div", { class: "card flat" }, h("table", { class: "t" },
      h("tr", {}, h("th", {}, "Participant"), h("th", {}, "Project"), h("th", {}, "Weeks counted"), h("th", {}, "Amount"), h("th", {}, "Status")),
      ...PEOPLE.map((p) => h("tr", {}, h("td", {}, p), h("td", {}, "Sleep and fatigue"),
        h("td", {}, p === HERO ? "5 of 6" : "6 of 6"), h("td", {}, rl(p === HERO ? 25 : 30)),
        h("td", {}, st.settled ? tag("Scheduled · next month", "gray") : tag("In batch", "amber")))))),
    h("div", { class: "row" }, h("button", { class: "btn primary", disabled: st.settled, onclick: () => { st.settled = true; draw(); } }, "Approve October batch"),
      h("span", { class: "muted small" }, "People wait until the batch is approved and paid.")),
  ];
}

function issueCode() {
  st.code = "4821 77";
  send("code", { code: st.code });
  draw();
}

// ---------- after ----------
const GAPS = [
  { sub: "S1", p: HERO, w: 3, item: "fatigue" },
  { sub: "S2", p: "P-015", w: 4, item: "sleep" },
  { sub: "S3", p: "P-019", w: 2, item: "bp" },
];
const gapKey = (g) => `${g.sub}:${g.p}:${g.w}`;

function afterInst() {
  const subs = [...SUBS, ...(st.added ? [NEW_SUB] : [])];
  return [
    h("div", { class: "spread" }, h("div", {}, h("h1", {}, INST.name), h("p", { class: "muted" }, `${INST.kind} · one relationship with each person, many sub-projects under it`)),
      h("button", { class: "btn primary", onclick: () => go("add") }, "+ Add a sub-project")),
    h("div", { class: "kpis" },
      kpi("Contracts per participant", "1", "institution relationship", "3"),
      kpi("Consent signatures", "1", "one passkey for the batch", "6"),
      kpi("Manual approvals", "1 + 1", "rule set once + 1 exception", "18"),
      kpi("Time to fill a gap", "minutes", "ask the exact week", "weeks")),
    h("div", { class: "grid2" },
      h("div", { class: "card col", style: { gap: "12px" } },
        h("div", { class: "spread" }, h("h2", {}, "Structure"), tag("Person → Institution → Sub-projects", "blue")),
        h("div", { class: "sub-card", style: { background: "var(--brand-weak)", borderColor: "var(--brand-line)" } },
          h("div", { class: "spread" }, h("h3", {}, `${INST.name} · relationship`), tag("50 people", "blue")),
          h("div", { class: "small muted" }, "Signed once per person with a passkey. Each sub-project inside its scope uses it, and the person's agent checks every request against their rules.")),
        h("div", { class: "tree" }, subs.map((s) => h("div", { class: `sub-card${s.id === "S4" ? " new" : ""}` },
          h("div", { class: "spread" }, h("h3", {}, s.name), s.id === "S4" ? tag("Added today · no new contract", "blue") : tag("Live", "green")),
          h("div", { class: "spread small muted" }, `${s.pis} · ${s.items.map((k) => ITEMS[k].label).join(", ")}`, h("span", {}, `${rl(weekPrice(s))} / person / week`)))))),
      h("div", { class: "col", style: { gap: "18px" } },
        h("div", { class: "card col", style: { gap: "10px" } },
          h("h2", {}, "What it saves"),
          h("div", { class: "spread small" }, "Contracts to draft and keep", h("span", {}, h("s", { class: "muted" }, "3 per person"), " → 1")),
          h("div", { class: "spread small" }, "Recruiting for a new sub-project", h("span", {}, h("s", { class: "muted" }, "new post"), " → reuse the relationship")),
          h("div", { class: "spread small" }, "Filling one missing week", h("span", {}, h("s", { class: "muted" }, "~$19.5k replacement"), ` → ${rl(ITEMS.fatigue.price)}`)),
          h("div", { class: "spread small" }, "Paying people", h("span", {}, h("s", { class: "muted" }, "monthly batch"), " → per delivered week")),
          h("div", { class: "spread small" }, "Budget approval", h("span", {}, h("s", { class: "muted" }, "per project"), " → once, split across sub-projects")),
          h("p", { class: "muted tiny" }, "Replacement cost is an industry estimate; other figures are from this demo's synthetic study.")),
        h("div", { class: "card col", style: { gap: "8px" } },
          h("h2", {}, "Budget"),
          h("div", { class: "spread small" }, "Approved", h("b", {}, rl(5000))),
          h("div", { class: "spread small" }, "Paid so far (per delivered week)", h("b", {}, rl(paidSoFar()))),
          h("div", { class: "bar-track" }, h("div", { class: "bar-fill", style: { width: `${Math.min(100, paidSoFar() / 50)}%` } })),
          h("p", { class: "muted tiny" }, "Signed once by the PI and compliance. Nothing is paid for a week that never arrives.")))),
  ];
}
function paidSoFar() { return st.feed.reduce((a, f) => a + (f.amt || 0), 0); }

function coverageAfter(subId) {
  const sub = SUBS.find((s) => s.id === subId);
  const cell = (p, w) => {
    const g = GAPS.find((x) => x.sub === subId && x.p === p && x.w === w);
    if (g) return st.filled.has(gapKey(g)) ? "ok" : st.asked ? "asked" : "gap";
    return w <= st.week ? "ok" : w === st.week + 1 && st.running ? "asked" : "wait";
  };
  return h("div", { class: "cov", style: { gridTemplateColumns: `70px repeat(${sub.weeks}, 1fr)` } },
    h("span", {}), ...Array.from({ length: sub.weeks }, (_, i) => h("span", { class: "hd" }, `W${i + 1}`)),
    ...PEOPLE.flatMap((p) => [h("span", { style: { fontWeight: p === HERO ? 600 : 400 } }, p),
      ...Array.from({ length: sub.weeks }, (_, i) => h("div", { class: `cell ${cell(p, i + 1)}` }))]));
}

function afterAgent() {
  const open = GAPS.filter((g) => !st.filled.has(gapKey(g)));
  return [
    h("div", {}, h("h1", {}, "Study agent"), h("p", { class: "muted" }, "Finds the exact gaps across every sub-project and asks only those people's agents")),
    h("div", { class: "agent-bar" }, h("span", { class: "who" }, "Study agent"),
      h("div", { class: "grow" },
        h("div", { style: { fontWeight: 600, color: "var(--brand)", fontSize: "16px" } },
          st.asked ? (open.length ? `Asked ${GAPS.length} people for ${GAPS.length} weeks · ${open.length} still open` : "All gaps filled · paid per week")
            : `Found ${GAPS.length} gaps in ${GAPS.length} sub-projects`),
        h("div", { class: "small muted" }, GAPS.map((g) => `${g.p} · W${g.w} · ${ITEMS[g.item].label}`).join("   ·   "))),
      !st.asked && h("button", { class: "btn primary", onclick: askGaps }, `Ask for these ${GAPS.length} weeks`)),
    h("div", { class: "row" }, ...SUBS.map((s) => h("button", { class: `btn sm${st.sub === s.id ? " primary" : ""}`, onclick: () => { st.sub = s.id; draw(); } }, s.name))),
    h("div", { class: "grid2" },
      h("div", { class: "card col", style: { gap: "12px" } },
        h("div", { class: "spread" }, h("h2", {}, "Coverage"), h("span", { class: "muted small" }, `${SUBS.find((s) => s.id === st.sub).name}`)),
        coverageAfter(st.sub),
        h("div", { class: "row small muted", style: { gap: "16px" } },
          h("span", { class: "row" }, h("span", { class: "cell ok", style: { width: "16px", height: "12px" } }), "Delivered"),
          h("span", { class: "row" }, h("span", { class: "cell gap", style: { width: "16px", height: "12px" } }), "Gap"),
          h("span", { class: "row" }, h("span", { class: "cell asked", style: { width: "16px", height: "12px" } }), "Asked"))),
      h("div", { class: "card col", style: { gap: "8px" } },
        h("h2", {}, "Requests"),
        ...GAPS.map((g) => {
          const done = st.filled.has(gapKey(g));
          const how = g.p === HERO ? (st.exception === false ? "Declined by the person" : "Their rule says ask me · asking the person") : "Inside their rules · agent answers";
          return h("div", { class: "col", style: { gap: "2px", padding: "8px 0", borderTop: "1px solid var(--border)" } },
            h("div", { class: "spread" }, h("b", {}, `${g.p} · W${g.w} · ${ITEMS[g.item].label}`),
              !st.asked ? tag("Not asked", "gray") : done ? tag(`Paid ${rl(ITEMS[g.item].price)}`, "green") : st.exception === false && g.p === HERO ? tag("Declined", "gray") : tag("Asked", "blue")),
            h("div", { class: "muted small" }, st.asked ? (done ? "Delivered · EscrowFinish · paid on Testnet" : how) : `${SUBS.find((s) => s.id === g.sub).name} · ${rl(ITEMS[g.item].price)} locked in escrow when asked`));
        }))),
  ];
}

function askGaps() {
  st.asked = true;
  send("request", { gaps: GAPS });
  draw();
  // Other people's agents answer inside their rules.
  GAPS.filter((g) => g.p !== HERO).forEach((g, i) => setTimeout(() => {
    st.filled.add(gapKey(g));
    st.feed.unshift({ dot: "green", text: `${g.p} · W${g.w} ${ITEMS[g.item].label} delivered by their agent`, sub: "Gap filled · EscrowFinish", amt: ITEMS[g.item].price });
    draw();
  }, 1400 + i * 900));
}

function afterWeekly() {
  const subs = [...SUBS, ...(st.added ? [NEW_SUB] : [])];
  const nextAmt = subs.reduce((a, s) => a + weekPrice(s) * 47, 0);
  return [
    h("div", { class: "spread" }, h("div", {}, h("h1", {}, "Weekly delivery"), h("p", { class: "muted" }, "People's agents send each week inside their consent. Each delivered week is paid on its own.")),
      h("button", { class: "btn primary", disabled: st.running || st.week >= 6, onclick: runWeek }, st.running ? `Week ${st.week + 1} arriving…` : st.week >= 6 ? "Study complete" : `Run week ${st.week + 1}`)),
    h("div", { class: "kpis" },
      kpi("This week", `W${st.week}`, "of 6"),
      kpi("Delivered this week", st.running ? "…" : "47 / 50", "by people's agents"),
      kpi("Paid so far", rl(paidSoFar()), "per delivered week"),
      kpi("Next week (est.)", rl(nextAmt), "locked in escrow first")),
    h("div", { class: "grid2" },
      h("div", { class: "card col", style: { gap: "12px" } },
        h("h2", {}, "Sub-projects this week"),
        ...subs.map((s) => {
          const pct = st.running ? 40 : s.id === "S4" ? 0 : 94;
          return h("div", { class: "col", style: { gap: "4px" } },
            h("div", { class: "spread small" }, h("b", {}, s.name), h("span", { class: "muted" }, s.id === "S4" ? "starts next week" : `${Math.round(pct / 2)} / 50 · ${rl(weekPrice(s))} per person`)),
            h("div", { class: "bar-track" }, h("div", { class: "bar-fill", style: { width: `${pct}%` } })));
        })),
      h("div", { class: "card col", style: { gap: "4px" } },
        h("h2", {}, "Ledger feed"),
        h("div", { class: "feed" }, st.feed.slice(0, 7).map((f) => h("div", { class: "it" }, h("span", { class: `dot ${f.dot}` }),
          h("div", { class: "grow" }, h("div", { class: "small" }, f.text), h("div", { class: "muted tiny" }, f.sub)),
          f.amt ? h("span", { class: "small", style: { fontWeight: 600 } }, rl(f.amt)) : null))))),
  ];
}

function runWeek() {
  st.running = true;
  draw();
  setTimeout(() => {
    st.week += 1;
    st.running = false;
    const amt = [...SUBS, ...(st.added ? [NEW_SUB] : [])].reduce((a, s) => a + weekPrice(s) * 47, 0);
    st.feed.unshift({ dot: "green", text: `Week ${st.week} · 47 of 50 people delivered by their agents`, sub: "Escrow released per delivery", amt });
    send("week", { n: st.week });
    draw();
  }, 2200);
}

function afterAdd() {
  return [
    h("div", {}, h("h1", {}, "Add a sub-project"), h("p", { class: "muted" }, `Under ${INST.name}. People who already have a relationship are not asked to sign again.`)),
    h("div", { class: "grid2" },
      h("div", { class: "card col", style: { gap: "12px" } },
        h("div", { class: "col", style: { gap: "4px" } }, h("span", { class: "muted small" }, "Name"), h("b", {}, NEW_SUB.name)),
        h("div", { class: "col", style: { gap: "4px" } }, h("span", { class: "muted small" }, "Lead"), h("span", {}, NEW_SUB.pis)),
        h("div", { class: "col", style: { gap: "4px" } }, h("span", { class: "muted small" }, "Items"),
          ...NEW_SUB.items.map((k) => h("div", { class: "spread small" }, ITEMS[k].label, h("span", {}, `${rl(ITEMS[k].price)} / week `, ITEMS[k].newPurpose ? tag("New purpose", "amber") : tag("In scope", "green"))))),
        h("div", { class: "col", style: { gap: "4px" } }, h("span", { class: "muted small" }, "Budget"), h("span", {}, `From the approved ${rl(5000)} · no new signing round`)),
        st.added ? h("div", { class: "note green" }, "Created. People's agents are checking it against their rules now.")
          : h("button", { class: "btn primary", onclick: addSub }, "Create under the existing relationship")),
      h("div", { class: "card col", style: { gap: "10px" } },
        h("h2", {}, "What happens next"),
        ...[
          ["No new contract", "The relationship already covers sub-projects in its scope."],
          ["No new recruiting", "The 50 people in the relationship are matched by their agents."],
          ["Heart rate: answered by agents", "Inside each person's rules, so it starts next week."],
          ["Caffeine diary: asks the person", "A new purpose, so each agent asks once on the phone."],
        ].map(([a, b]) => h("div", { class: "row", style: { alignItems: "flex-start" } }, h("span", { style: { color: st.added ? "var(--green)" : "var(--text-3)" } }, st.added ? "✓" : "○"),
          h("div", {}, h("b", { class: "small" }, a), h("div", { class: "muted small" }, b)))))),
  ];
}

function addSub() {
  st.added = true;
  send("newsub", { sub: NEW_SUB });
  st.feed.unshift({ dot: "amber", text: `${NEW_SUB.name} created under the ${INST.short} relationship`, sub: "Agents checking scope · new purpose goes to the person" });
  draw();
}

// ---------- messages from the phone ----------
listen(({ type, data }) => {
  if (MODE === "before") {
    if (type === "linked") { st.linked = true; toast(root, `${HERO} entered the linking code`); }
    if (type === "lane") { st.lanes = data.n; toast(root, `${HERO} signed consent ${data.n} of 2 for this project`); }
    if (type === "approve") st.approved.add(`${data.item}:${data.week}`);
  } else {
    if (type === "consented") {
      st.joined = true;
      st.feed.unshift({ dot: "blue", text: `${HERO} joined ${data.subs.length} sub-projects with one passkey`, sub: `${INST.short} relationship · consent recorded per item on the ledger` });
      toast(root, `${HERO} joined ${data.subs.length} sub-projects · one passkey`);
    }
    if (type === "exception") {
      st.exception = data.allow;
      const g = GAPS[0];
      if (data.allow) {
        st.filled.add(gapKey(g));
        st.feed.unshift({ dot: "green", text: `${HERO} allowed W3 ${ITEMS.fatigue.label} · agent sent it`, sub: "Gap filled · EscrowFinish", amt: ITEMS.fatigue.price });
      }
      toast(root, data.allow ? `${HERO} allowed this week · paid ${rl(ITEMS.fatigue.price)}` : `${HERO} declined · escrow returned`);
    }
    if (type === "newpurpose") {
      st.feed.unshift({ dot: data.allow ? "green" : "gray", text: `${HERO} ${data.allow ? "allowed" : "declined"} ${ITEMS.caffeine.label} for ${NEW_SUB.name}`, sub: "Asked once on the phone" });
      toast(root, `${HERO} ${data.allow ? "allowed" : "declined"} the new purpose`);
    }
  }
  draw();
});

// ---------- draw ----------
const VIEWS = MODE === "before"
  ? { projects: beforeProjects, project: beforeProject, table: beforeTable, settle: beforeSettle }
  : { inst: afterInst, agent: afterAgent, weekly: afterWeekly, add: afterAdd };
function draw() {
  const keep = window.scrollY;
  const toasts = [...root.querySelectorAll(".toast")];
  root.replaceChildren(shell(VIEWS[st.view]()), ...toasts);
  window.scrollTo(0, keep);
}
if (MODE === "before") setInterval(() => { st.day += 1; if (st.view === "project") draw(); }, 2500);
const start = new URLSearchParams(location.search).get("view");
if (start && VIEWS[start]) st.view = start;
draw();
