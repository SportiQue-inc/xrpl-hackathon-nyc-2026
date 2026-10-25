// Participant app (mobile first): participation request (P1), consent by purpose (P2), preview and
// weekly status (P3), payment timeline (P4), stop or withdraw (P5), review notice (P6), and the
// ledger receipt (R3). Talks to the participant's own agent endpoints: GET /api/p/{pid} and friends.

import { engine, watchSelf } from "./api.js";
import {
  h, render, tag, icon, xrp, short, sum, day, ledgerDay, weeksLabel, txLink, banner, busy, WEEK_STATE, holdbackState,
  ITEM_CLASS, SIGNAL,
} from "./ui.js";

const SOURCE = { wearable: "Wearable", survey_app: "Survey app", clinic_export: "Clinic export" };

export function mountParticipant(root, { base = "", pid = "P-017", embedded = false, token } = {}) {
  const api = engine(base, { token });
  const st = { p: null, view: "request", rid: null, picked: null, consent: { sensitive: false, sharing: true },
               preview: null, sent: null, anim: 0, revoke: null, error: null, toast: null, showAll: false,
               sheet: null, open: new Set(), details: false };
  root.classList.add("ar");
  if (embedded) root.classList.add("embedded");

  async function load() {
    try {
      st.p = await api.participant(pid);
      st.error = null;
    } catch (e) {
      st.error = e;
    }
    draw();
  }
  const watcher = watchSelf(api, pid, (v) => {
    const typing = document.activeElement && root.contains(document.activeElement) && /INPUT|TEXTAREA/.test(document.activeElement.tagName);
    if (!typing && !st.sheet && !st.anim) { st.p = v; st.error = null; draw(); }
  });

  const current = () => {
    const rs = st.p.requests;
    return rs.find((r) => r.id === st.rid) || rs.find((r) => r.status === "open" || r.status === "partly_open") || rs[rs.length - 1] || null;
  };
  const ledgerName = () => (st.p.requests.some((r) => r.institution.badges.some((b) => b.url)) ? "Testnet" : "Practice ledger");
  const go = (view) => { st.view = view; st.sheet = null; draw(); window.scrollTo(0, 0); };
  const cellPrice = (r) => {
    const cells = sum(r.items, (i) => i.weeks.length);
    return cells ? r.reward_xrp / cells : 0;
  };

  // ---------- frame ----------
  function frame(title, body, foot, { back, tabs = true } = {}) {
    return h("div", { class: "ar-phone" },
      h("div", { class: "bar" },
        back && h("button", { class: "ar-iconbtn", style: { border: 0 }, onclick: back, "aria-label": "Back" }, icon("back")),
        h("span", { class: "title" }, title),
        st.p && tag(ledgerName(), "gray", { title: "No real value: XRPL Testnet or a practice ledger" }),
        h("span", { class: "ar-tag blue", title: st.p ? `Study pseudonym ${st.p.person.study_pseudonym}` : "" }, pid)),
      h("div", { class: "body" }, body),
      foot && h("div", { class: "foot" }, foot),
      tabs && !foot && h("nav", { class: "ar-tabs" },
        tabBtn("request", "Requests", "list"), tabBtn("pay", "Payments", "wallet"), tabBtn("stop", "Stop or withdraw", "stop")),
      st.sheet,
      st.toast && h("div", { class: "ar-toast" }, st.toast.text, st.toast.undo && h("button", { onclick: st.toast.undo }, "Undo")));
  }
  function tabBtn(view, label, ic) {
    const on = st.view === view || (view === "request" && ["consent", "preview", "status", "review"].includes(st.view))
      || (view === "stop" && st.view === "withdrawn");
    return h("button", { class: on ? "on" : "", onclick: () => go(view) }, h("div", {}, icon(ic, 20)), label);
  }

  function draw() {
    let out;
    if (st.error && !st.p) {
      out = frame("Research participation", [banner("red", "Could not reach your agent. ", h("button", { class: "ar-link", onclick: load }, "Retry")),
        h("span", { class: "tiny muted" }, st.error.message)]);
    } else if (!st.p) {
      out = frame("Research participation", [1, 2, 3].map(() => h("div", { class: "ar-skel", style: { height: "120px" } })));
    } else {
      const v = st.view;
      out = v === "consent" ? consentView() : v === "preview" ? previewView() : v === "status" ? statusView()
        : v === "pay" ? payView() : v === "stop" ? stopView() : v === "withdrawn" ? withdrawnView()
        : v === "review" ? reviewView() : requestView();
    }
    render(root, out);
  }

  // ---------- P1: participation request ----------
  function requestView() {
    const p = st.p;
    const r = current();
    const revoked = p.consent && p.consent.status === "revoked";
    const notices = [];
    const openCase = p.payout.cases.find((c) => c.status === "suspected");
    if (openCase) {
      notices.push(h("button", { class: "ar-banner amber", style: { border: 0, textAlign: "left" }, onclick: () => go("review") },
        icon("clock", 16), h("span", {}, h("b", {}, "Your held payment is under a longer review. "), "Tap to see why and respond.")));
    }
    if (p.payout.automatic_requests === "paused") {
      notices.push(banner("amber", h("div", { class: "col", style: { gap: "6px" } },
        h("span", {}, "Automatic requests are paused because two accepted rounds were missed. Nothing else changes."),
        h("button", { class: "ar-btn sm", onclick: async (e) => { if (await busy(e.target, "Resuming", () => api.resumeRequests(pid))) load(); } }, "Resume automatic requests"))));
    }
    if (revoked) notices.push(banner("gray", "You withdrew from this study. ", h("button", { class: "ar-link", onclick: () => go("withdrawn") }, "See what happened")));
    if (p.consent && p.consent.status === "paused") notices.push(banner("amber", "Future rounds stopped. ", h("button", { class: "ar-link", onclick: () => go("stop") }, "Resume")));
    if (!r) {
      return frame("Research participation", [...notices, h("div", { class: "ar-card col" }, h("h2", {}, "No requests right now"),
        h("p", { class: "muted" }, "Your agent will ask you when a study needs something outside your consent."))]);
    }
    const open = r.status === "open" || r.status === "partly_open";
    if (st.picked === null || st.picked.rid !== r.id) {
      st.picked = { rid: r.id, items: new Set(r.items.filter((i) => i.class === "approval" && !i.sensitive).map((i) => i.item)) };
    }
    const picked = st.picked.items;
    const autoItems = r.items.filter((i) => i.class === "auto");
    const credentialOk = r.institution.badges.some((b) => b.kind === "ethics_review" && b.on_ledger);
    const price = cellPrice(r);
    const pickedCells = sum(r.items.filter((i) => picked.has(i.item)), (i) => i.weeks.length);
    const autoCells = sum(autoItems, (i) => i.weeks.length);
    const decided = !open;

    const body = [
      ...notices,
      r.status === "partly_open" && autoItems.length ? banner("blue", h("div", {},
        h("b", {}, `Your agent sent ${autoItems.length} item${autoItems.length > 1 ? "s" : ""} inside your consent`),
        h("div", { class: "small" }, autoItems.map((i) => i.label).join(", ")))) : null,
      decided ? banner(r.status === "declined" ? "gray" : "green", r.status === "declined" ? "You skipped this round." : "You approved this request.",
        r.status !== "declined" ? h("button", { class: "ar-link", style: { marginLeft: "auto" }, onclick: () => go("status") }, "Weekly status") : null) : null,
      h("div", { class: "ar-card col" },
        h("span", { class: "small muted" }, "Participation request"),
        h("h2", {}, r.institution.name),
        h("div", { class: "row", style: { flexWrap: "wrap" } }, r.institution.badges.map((b) =>
          h("span", { class: "row", style: { gap: "4px" } }, tag(b.label, credentialOk ? "green" : "red"), txLink(b, { title: b.kind === "ethics_review" ? "Ethics review credential issued" : "Verified organization credential", kind: "CredentialCreate" })))),
        !credentialOk ? banner("red", "This lab's ethics review is not valid on the ledger.") : null,
        h("p", {}, r.summary),
        r.summary_source === "llm" ? h("span", { class: "tiny muted" }, "Written by the study's agent · checked by code") : null,
        h("div", { class: "small muted", title: r.duo.map((d) => `${d.code} ${d.label}`).join("\n") },
          `Sleep research · Health or biomedical research (${r.duo[0] ? r.duo[0].code : "DUO"})`)),
      h("div", { class: "col" },
        h("div", { class: "spread" }, h("h3", {}, "What the study asks for"), h("span", { class: "small muted" }, "Tap an item for weeks and reasons")),
        r.items.map((i) => itemCard(r, i, decided || !credentialOk))),
      h("div", { class: "ar-card col" },
        h("div", { class: "spread" }, h("h3", {}, "Participation payment"), h("b", {}, xrp(price * (pickedCells + autoCells)))),
        h("p", { class: "small" }, `${r.payment.first_week_pct}% of a verified week when it is delivered, rising with each consecutive week up to ${r.payment.max_pct}%; the rest after a ${r.payment.review} review. The held part is paid by default.`),
        r.completion_bonus_xrp ? h("p", { class: "small" }, `Completion bonus ${xrp(r.completion_bonus_xrp)} when every requested week is delivered.`) : null,
        h("p", { class: "small muted" }, "Locked on the ledger before you send. Released when your agent publishes the key.")),
      h("div", { class: "ar-card col" },
        h("h3", {}, "If you want to stop"),
        h("p", { class: "small" }, "Skip this round · Stop future rounds · Withdraw data access"),
        h("button", { class: "ar-link small", style: { alignSelf: "flex-start" }, onclick: () => go("stop") }, "Compare the three →")),
      h("div", { class: "ar-card col" },
        h("button", { class: "spread", style: { background: "none", border: 0, padding: 0 }, onclick: () => { st.details = !st.details; draw(); } },
          h("h3", {}, "Details"), icon(st.details ? "down" : "chevron", 16)),
        st.details && h("div", { class: "col small" },
          h("p", {}, "The study gets your participant number and the items you approve, never your name."),
          h("p", {}, r.international_transfer.planned ? "Transfer abroad is planned; it needs its own consent." : "No transfer outside your country is planned."),
          h("p", {}, "Access records are kept 2 years, permission changes 3 years."),
          p.consent && h("p", { class: "tiny muted" }, `Consent v${p.consent.version} · hash ${short(p.consent.doc_hash, 6, 0)}`))),
    ];
    const n = picked.size;
    const foot = open && !revoked ? [
      h("button", { class: "ar-btn primary block", disabled: !n || !credentialOk, onclick: () => go("consent") }, n ? `Review ${n} item${n > 1 ? "s" : ""}` : "Pick at least one item"),
      h("button", { class: "ar-btn block", onclick: (e) => skip(e, r) }, "Skip this round"),
    ] : null;
    return frame("Research participation", body, foot);
  }

  function itemCard(r, i, locked) {
    const picked = st.picked.items;
    const row = st.p.timeline.rows.find((x) => x.item === i.item);
    const gaps = st.p.gaps.filter((g) => g.item === i.item);
    const expanded = st.open.has(i.item);
    const cls = ITEM_CLASS[i.class] || ITEM_CLASS.approval;
    const selectable = i.class === "approval" && !locked;
    const sentByAgent = i.class === "auto";
    return h("div", { class: `ar-item${i.class === "blocked" ? " blocked" : ""}` },
      h("div", { class: "top" },
        i.class === "blocked" ? h("span", { style: { width: "20px" } })
          : h("input", { type: "checkbox", checked: sentByAgent || picked.has(i.item), disabled: !selectable,
              "aria-label": i.label, onchange: (e) => { e.target.checked ? picked.add(i.item) : picked.delete(i.item); draw(); } }),
        h("button", { class: "grow col", style: { background: "none", border: 0, padding: 0, textAlign: "left", gap: "4px" },
          onclick: () => { expanded ? st.open.delete(i.item) : st.open.add(i.item); draw(); } },
          h("b", {}, i.label),
          h("span", { class: "small muted" }, `${weeksLabel(i.weeks)} · ${SOURCE[i.source] || i.source || "—"}`),
          h("span", { class: "row", style: { flexWrap: "wrap", gap: "6px" } }, tag(sentByAgent ? "Sent by your agent" : cls.label, cls.tone),
            i.sensitive ? tag("Sensitive", "red") : null)),
        icon(expanded ? "down" : "chevron", 16)),
      i.class === "blocked" ? h("span", { class: "small" }, "Outside the purpose you allowed") : null,
      i.sensitive && selectable ? h("span", { class: "tiny muted" }, "Sensitive items are approved one by one.") : null,
      expanded && row && h("div", { class: "col", style: { gap: "6px" } },
        h("div", { class: "ar-weeks" }, row.cells.map((c) => h("div", { class: `ar-week ${c.state}`, title: (WEEK_STATE[c.state] || {}).label },
          c.state === "held" || c.state === "contributed" ? "✓" : `W${c.week}`))),
        gaps.map((g) => h("span", { class: "tiny" }, `Week ${g.week}: `, tag(g.verdict === "kept" ? "Kept" : g.verdict, g.verdict === "kept" ? "green" : "gray"), ` “${g.reason}”`))));
  }

  async function skip(e, r) {
    const res = await busy(e.target, "Skipping", () => api.decline(pid, r.id), () => toast("Could not reach your agent. Nothing changed."));
    if (res) { st.p = res; toast("Round skipped. Nothing was sent."); draw(); }
  }

  // ---------- P2: consent by purpose ----------
  function consentView() {
    const r = current();
    const items = r.items.filter((i) => st.picked.items.has(i.item));
    const sens = items.filter((i) => i.sensitive);
    const c = st.consent;
    const card = (title, on, set, rows, note, disabled) => h("div", { class: "ar-card col", style: disabled ? { background: "var(--ar-row)" } : {} },
      h("div", { class: "spread" }, h("h3", {}, title),
        disabled ? tag("Not planned") : h("label", { class: "ar-switch" }, h("input", { type: "checkbox", checked: on, onchange: (e) => { set(e.target.checked); draw(); } }), h("span", {}))),
      h("dl", { class: "ar-kv" }, rows.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])),
      note && h("p", { class: "tiny muted" }, note));
    const agreed = (sens.length ? (c.sensitive ? 1 : 0) : 0) + (c.sharing ? 1 : 0);
    const body = [
      h("p", { class: "muted small" }, "Each consent is separate. Saying no to one does not affect the others."),
      sens.length ? card("Sensitive health data", c.sensitive, (v) => { c.sensitive = v; },
        [["What", sens.map((i) => i.label).join(", ")], ["Weeks", weeksLabel([...new Set(sens.flatMap((i) => i.weeks))])],
         ["Purpose", "Sleep research"], ["Kept", "until the study ends"]],
        "You can say no. These items are then not sent and their part of the payment is not paid.") : null,
      card("Sharing with the study", c.sharing, (v) => { c.sharing = v; },
        [["Recipient", r.institution.name], ["Items", items.filter((i) => !i.sensitive || c.sensitive).map((i) => i.label).join(", ") || "—"],
         ["Purpose", "Sleep research"], ["If you withdraw", "person-level copies are deleted"]],
        "You can say no. Nothing is then sent this round."),
      card("Transfer abroad", false, () => {}, [["Status", "Not planned for this study"]], null, true),
      st.p.consent && h("p", { class: "tiny muted" }, `Consent v${st.p.consent.version} · hash ${short(st.p.consent.doc_hash, 6, 0)}`),
    ];
    const effective = items.filter((i) => c.sharing && (!i.sensitive || c.sensitive));
    const foot = [
      h("button", { class: "ar-btn primary block", onclick: () => {
        if (!effective.length) return skip({ target: null }, r).then(() => go("request"));
        st.send = effective.map((i) => i.item);
        st.preview = null;
        go("preview");
        loadPreview(r);
      } }, effective.length ? `Agree to ${agreed} and continue` : "Continue without these items"),
      h("button", { class: "ar-btn block", onclick: () => go("request") }, "Back"),
    ];
    return frame("Consent by purpose", body, foot, { back: () => go("request") });
  }

  async function loadPreview(r) {
    try {
      st.preview = await api.preview(pid, r.id);
    } catch (e) {
      st.preview = { error: e };
    }
    draw();
  }

  // ---------- P3: preview, then weekly status ----------
  function previewView() {
    const r = current();
    const pv = st.preview;
    const send = new Set(st.send || []);
    let body;
    if (!pv) body = [h("div", { class: "ar-skel", style: { height: "160px" } })];
    else if (pv.error) body = [banner("red", "Could not build the preview. ", h("button", { class: "ar-link", onclick: () => loadPreview(r) }, "Retry"))];
    else {
      const rows = pv.rows.map((row) => Object.fromEntries(Object.entries(row).filter(([k, v]) => k === "person" || k === "day" || (send.has(k) && v))))
        .filter((row) => Object.keys(row).length > 2);
      const withheld = r.items.filter((i) => i.class !== "auto" && !send.has(i.item));
      const shown = st.showAll ? rows : rows.slice(0, 5);
      body = [
        h("div", { class: "ar-card col" },
          h("b", {}, `Sent as ${pv.pseudonym}`),
          h("span", { class: "small muted" }, `Dates shifted · sealed for ${r.institution.name} · the operator cannot open it`)),
        h("h3", {}, "Exactly what leaves your device"),
        shown.map((row) => h("div", { class: "ar-prev" },
          h("div", {}, h("span", { class: "muted" }, "person"), h("span", { class: "mono" }, row.person)),
          h("div", {}, h("span", { class: "muted" }, "day"), h("span", {}, String(row.day))),
          Object.entries(row).filter(([k]) => k !== "person" && k !== "day").map(([k, v]) =>
            h("div", {}, h("span", { class: "muted" }, (r.items.find((i) => i.item === k) || {}).label || k),
              h("span", {}, Object.entries(v).map(([a, b]) => `${a.replace(/_/g, " ")} ${b}`).join(" · ")))))),
        rows.length > 5 ? h("button", { class: "ar-link", onclick: () => { st.showAll = !st.showAll; draw(); } }, st.showAll ? "Show fewer" : `Show all ${rows.length} rows`) : null,
        withheld.length ? banner("gray", `Withheld: ${withheld.map((i) => i.label).join(", ")}`) : null,
        h("p", { class: "tiny muted" }, `Not included at all: ${pv.not_included.join(", ")}`),
      ];
    }
    const foot = [
      h("button", { class: "ar-btn primary block", disabled: !pv || pv.error, onclick: async (e) => {
        const res = await busy(e.target, "Locking payment on the ledger", () => api.approve(pid, r.id, [...send]),
          () => toast("Could not lock the payment. Nothing was sent."));
        if (res) { st.p = res; st.anim = 1; go("status"); animate(); }
      } }, `Send ${send.size} item${send.size === 1 ? "" : "s"}`),
      h("button", { class: "ar-btn block", onclick: () => go("consent") }, "Back"),
    ];
    return frame("Preview", body, foot, { back: () => go("consent") });
  }

  function animate() {
    // Requested -> Locked -> final state, one step at a time (the demo's key moment).
    setTimeout(() => { st.anim = 2; draw(); }, 700);
    setTimeout(() => { st.anim = 0; draw(); }, 1500);
  }

  function statusView() {
    const p = st.p;
    const r = current();
    const items = r ? r.items.filter((i) => i.class !== "blocked") : [];
    const lines = [];
    for (const i of items) {
      const row = p.timeline.rows.find((x) => x.item === i.item);
      for (const w of i.weeks) {
        const cell = row && row.cells.find((c) => c.week === w);
        let state = cell ? cell.state : "requested";
        if (state === "held" || state === "missing" || (state === "requested" && ["contributed", "declined"].includes(r.status))) state = "withheld";
        if (st.anim === 1) state = "requested";
        if (st.anim === 2 && state === "contributed") state = "escrowed";
        const s = WEEK_STATE[state] || { label: state, tone: "gray" };
        const contrib = p.contributions.find((c) => c.weeks.includes(w) && c.items.includes(i.item));
        const tx = contrib && (contrib.finish.tx ? contrib.finish : contrib.cancel.tx ? contrib.cancel : contrib.escrow);
        lines.push(h("div", { class: "ar-item", style: { flexDirection: "row", alignItems: "center" } },
          h("div", { class: "grow col", style: { gap: "2px" } }, h("b", {}, `W${w} · ${i.label}`),
            contrib ? h("span", { class: "small muted" }, xrp(contrib.amount_xrp / contrib.items.length)) : null),
          h("span", { class: "col", style: { alignItems: "flex-end", gap: "4px" } },
            tag(s.label, s.tone, { class: `ar-tag ${s.tone} ar-week-anim` }),
            !st.anim && tx ? txLink(tx, { kind: tx === contrib.finish ? "EscrowFinish" : tx === contrib.cancel ? "EscrowCancel" : "EscrowCreate",
              title: tx === contrib.finish ? `Week ${w} participation payment released` : tx === contrib.cancel ? "Locked payment returned to the study" : `Payment locked for week ${w}`,
              amount: contrib.amount_xrp, to: "Your agent" }) : null)));
      }
    }
    const lic = p.licence;
    const body = [
      st.anim ? banner("blue", h("span", { class: "ar-spin" }), " Confirming on the ledger") : banner("green", icon("check", 16), "Sent. Each week shows its own state."),
      h("h3", {}, "Weekly status"),
      lines,
      lic ? h("div", { class: "ar-card spread" }, h("span", { class: "small" }, lic.clawback ? "Access licence taken back" : "Access licence issued to the study"),
        txLink(lic.clawback || lic.txs[lic.txs.length - 1], { title: lic.clawback ? "Access licence taken back" : "Access licence issued to the study", kind: lic.clawback ? "Clawback" : "MPTokenIssuanceCreate", memo: `licence ${short(lic.mpt_id, 6, 4)}` })) : null,
      h("p", { class: "tiny muted" }, "Locked weeks are released when the round closes. If you withdraw before that, they are never released and the payment returns to the study."),
    ];
    return frame("Your contribution", body, null, { back: () => go("request") });
  }

  // ---------- P4: payment timeline ----------
  function payView() {
    const p = st.p;
    const hbs = p.payout.holdbacks;
    const delivered = p.contributions.filter((c) => c.status === "delivered");
    const paid = sum(delivered, (c) => c.amount_xrp) + sum(hbs.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const inReview = sum(hbs.filter((x) => x.kind === "round" && (x.status === "held" || x.status === "suspected")), (x) => x.amount_xrp);
    const bonus = sum(hbs.filter((x) => x.kind === "bonus" && x.status === "held"), (x) => x.amount_xrp);
    const total = paid + inReview + bonus || 1;
    const r = p.requests[0];
    const events = [];
    for (const c of p.contributions) {
      const w = `Week ${c.weeks.join(", ")}`;
      if (c.status === "delivered") events.push([c.order_id, `${w} paid`, `+${xrp(c.amount_xrp)}`, "", c.finish, "EscrowFinish"]);
      else if (c.cancel && c.cancel.tx) events.push([c.order_id, `${w} returned to study`, xrp(c.amount_xrp), "gray", c.cancel, "EscrowCancel"]);
      else if (c.status === "escrowed") events.push([c.order_id, `${w} locked until the round closes`, xrp(c.amount_xrp), "blue", c.escrow, "EscrowCreate"]);
      else events.push([c.order_id, `${w} ${c.status}`, xrp(c.amount_xrp), "gray", c.escrow, "EscrowCreate"]);
    }
    for (const x of hbs) {
      const s = holdbackState(x);
      const label = x.kind === "bonus" ? "Completion bonus" : "Held 20% part";
      const t = x.release || x.return || x.create;
      events.push([1e6 + x.id, `${label} · ${s.label}`, `${x.status === "released" ? "+" : ""}${xrp(x.amount_xrp)}`,
        x.status === "released" ? "" : s.tone === "amber" ? "amber" : s.tone === "gray" ? "gray" : "blue", t,
        x.release ? "EscrowFinish" : x.return ? "EscrowCancel" : "EscrowCreate"]);
    }
    events.sort((a, b) => b[0] - a[0]);
    const body = [
      h("div", { class: "ar-card col" },
        h("div", { class: "ar-paybar" },
          h("i", { style: { width: `${(paid / total) * 100}%`, background: "#10b981" } }),
          h("i", { style: { width: `${(inReview / total) * 100}%`, background: "#2f6bff" } }),
          h("i", { style: { width: `${(bonus / total) * 100}%`, background: "#c7d2fe" } })),
        h("div", { class: "spread small" },
          h("span", {}, h("span", { class: "ar-dot", style: { background: "#10b981" } }), ` Paid ${xrp(paid)}`),
          h("span", {}, h("span", { class: "ar-dot", style: { background: "#2f6bff" } }), ` In review ${xrp(inReview)}`),
          h("span", {}, h("span", { class: "ar-dot", style: { background: "#c7d2fe" } }), ` Bonus ${xrp(bonus)}`))),
      hbs.filter((x) => x.kind === "round").map((x) => {
        const s = holdbackState(x);
        const card = h("div", { class: "ar-card col", style: s.tone === "green" ? { borderColor: "#a7f3d0" } : {} },
          h("div", { class: "spread" }, h("b", {}, `${xrp(x.amount_xrp)} held for review`), tag(s.label, s.tone)),
          h("span", { class: "small muted" }, x.status === "held" ? `Paid when the ${r ? r.payment.review : ""} review ends.`
            : x.status === "suspected" ? "The review was extended. Tap to see why." : x.status === "released" ? "Paid after review." : ""),
          txLink(x.release || x.return || x.create, { kind: x.release ? "EscrowFinish" : "EscrowCreate", amount: x.amount_xrp,
            title: x.release ? "Held part of the participation payment released" : "Held part locked for review" }));
        if (x.status === "suspected") { card.style.cursor = "pointer"; card.addEventListener("click", () => go("review")); }
        return card;
      }),
      h("div", { class: "ar-card col small" },
        h("p", {}, "20% of each round is paid after a short review so the study can check the data arrived complete. It is paid by default."),
        h("p", {}, "Stopping never takes back what was paid."),
        h("p", { class: "muted" }, "Review results are never written to the public ledger.")),
      h("h3", {}, "History"),
      events.length ? h("div", { class: "ar-card ar-vline" }, events.map(([, l, a, tone, t, kind]) => h("div", { class: "e" },
        h("span", { class: `d ${tone}` }), h("div", { class: "col", style: { gap: "2px" } }, h("span", {}, l), txLink(t, { kind, title: l })), h("b", {}, a))))
        : h("p", { class: "muted" }, "No payments yet. Your first payment arrives when a week is delivered."),
    ];
    return frame("Payments", body);
  }

  // ---------- P5: stop or withdraw ----------
  function stopView() {
    const p = st.p;
    const r = current();
    const canSkip = r && (r.status === "open" || r.status === "partly_open");
    const paused = p.consent && p.consent.status === "paused";
    const revoked = p.consent && p.consent.status === "revoked";
    const choice = (cls, title, stops, keeps, ledger, btn) => h("div", { class: `ar-choice ${cls}` },
      h("h3", {}, title),
      h("dl", {}, h("dt", {}, "What stops"), h("dd", {}, stops), h("dt", {}, "What stays"), h("dd", {}, keeps), h("dt", {}, "On the ledger"), h("dd", {}, ledger)),
      btn);
    const body = [
      revoked ? banner("gray", "You withdrew from this study. ", h("button", { class: "ar-link", onclick: () => go("withdrawn") }, "See what happened")) : null,
      paused ? banner("amber", "Future rounds stopped.") : null,
      choice("", "Skip this round", "This request only", "Your consent, past contributions and payments", "Nothing happens",
        h("button", { class: "ar-btn", disabled: !canSkip || revoked, onclick: (e) => skip(e, r) }, canSkip ? "Skip this round" : "No open request")),
      choice("", "Stop future rounds", "New requests", "Data already sent and payments. You can resume.", "Nothing happens",
        paused ? h("button", { class: "ar-btn", disabled: revoked, onclick: async (e) => { const res = await busy(e.target, "Resuming", () => api.resume(pid)); if (res) { st.p = res; draw(); } } }, "Resume rounds")
          : h("button", { class: "ar-btn", disabled: revoked, onclick: async (e) => {
            const res = await busy(e.target, "Stopping", () => api.pause(pid), () => toast("Could not reach your agent."));
            if (res) {
              st.p = res;
              toast("Future rounds stopped.", async () => { st.p = await api.resume(pid); st.toast = null; draw(); });
              draw();
            }
          } }, "Stop future rounds")),
      choice("red", "Withdraw data access", "Every use by the study", "Payments already made, your consent history, aggregate statistics",
        "Licence taken back, locked weeks returned to the study",
        h("button", { class: "ar-btn danger", disabled: revoked, onclick: () => { st.sheet = withdrawSheet(); draw(); } }, "Withdraw data access")),
      p.consent && h("div", { class: "ar-card col" }, h("h3", {}, "Consent history"),
        p.consent.history.slice().reverse().map((x) => h("div", { class: "spread small" }, h("span", {}, `v${x.version} ${x.status}`), h("span", { class: "muted" }, `${day(x.ts)} · ${short(x.doc_hash, 6, 0)}`)))),
    ];
    return frame("Stop or withdraw", body);
  }

  function withdrawSheet() {
    const p = st.p;
    const locked = p.contributions.filter((c) => c.status === "escrowed");
    const close = () => { st.sheet = null; draw(); };
    return h("div", {},
      h("div", { class: "ar-scrim", onclick: close }),
      h("div", { class: "ar-sheet" },
        h("h2", {}, "Withdraw data access?"),
        h("ul", { class: "small", style: { margin: 0, paddingLeft: "18px", display: "flex", flexDirection: "column", gap: "6px" } },
          h("li", {}, "The study's access licence is taken back on the ledger."),
          locked.length ? h("li", {}, `${locked.length} locked week${locked.length > 1 ? "s are" : " is"} never released; ${xrp(sum(locked, (c) => c.amount_xrp))} returns to the study.`) : null,
          h("li", {}, "The study must delete every person-level copy about you and confirm it."),
          h("li", {}, "You keep payments already made. Held parts of delivered weeks are still paid after review."),
          h("li", {}, "Only aggregate statistics already produced remain.")),
        h("button", { class: "ar-btn primary block", style: { background: "var(--ar-red)", borderColor: "var(--ar-red)" }, onclick: async (e) => {
          const res = await busy(e.target, "Confirming on the ledger", () => api.revoke(pid),
            () => toast("The ledger did not confirm the licence clawback. Your withdrawal is recorded and will retry."));
          if (res) { st.revoke = res; st.p = res; go("withdrawn"); }
        } }, "Withdraw data access"),
        h("button", { class: "ar-btn block", onclick: close }, "Cancel")));
  }

  function withdrawnView() {
    const p = st.p;
    const rv = st.revoke || [...p.withdrawals].reverse().find((x) => x.kind === "revoke");
    if (!rv) return stopView();
    const kept = sum(p.contributions.filter((c) => c.status === "delivered"), (c) => c.amount_xrp)
      + sum(p.payout.holdbacks.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const heldStill = sum(p.payout.holdbacks.filter((x) => x.kind === "round" && (x.status === "held" || x.status === "suspected")), (x) => x.amount_xrp);
    const refunded = p.contributions.filter((c) => c.cancel && c.cancel.tx);
    const pending = p.contributions.filter((c) => (rv.withheld || []).includes(c.order_id) && !(c.cancel && c.cancel.tx));
    const check = (ok, text, extra) => h("div", { class: "ar-check" }, h("span", { class: `ic ${ok ? "ok" : "wait"}` }, ok ? icon("check", 12) : icon("clock", 12)),
      h("span", { class: "grow small" }, text), extra);
    const d = rv.deletion || {};
    const body = [
      banner("green", icon("check", 16), `You withdrew from ${current() ? current().institution.name : "the study"}.`),
      h("div", { class: "ar-card" },
        check(!!rv.clawback, "Licence taken back from the study", rv.clawback ? txLink(rv.clawback, { kind: "Clawback", title: "Access licence taken back" }) : null),
        pending.map((c) => check(false, `Week ${c.weeks.join(", ")} not sent · ${xrp(c.amount_xrp)} returns to the study after the round deadline`)),
        refunded.map((c) => check(true, `Week ${c.weeks.join(", ")} refunded to study · ${xrp(c.amount_xrp)}`, txLink(c.cancel, { kind: "EscrowCancel", title: "Locked payment returned to the study", amount: c.amount_xrp }))),
        check(true, "Deletion requested from the study"),
        check(!!d.confirmation_hash, `The study deleted ${d.bundles_destroyed || 0} bundles and ${d.cells_destroyed || 0} cells · confirmation ${short(d.confirmation_hash, 4, 0)}`)),
      h("div", { class: "ar-card col small" },
        h("p", {}, `You keep ${xrp(kept)} already paid. Your consent history is kept. Only aggregate statistics remain.`),
        heldStill ? h("p", {}, `${xrp(heldStill)} is still paid after review.`) : null),
      p.consent && h("div", { class: "ar-card col" }, h("h3", {}, "Consent history"),
        p.consent.history.slice().reverse().map((x) => h("div", { class: "spread small" }, h("span", {}, `v${x.version} ${x.status}`), h("span", { class: "muted" }, day(x.ts))))),
    ];
    return frame("Withdrawal", body, null, { back: () => go("stop") });
  }

  // ---------- P6: review notice ----------
  function reviewView() {
    const p = st.p;
    const c = p.payout.cases.find((x) => x.status === "suspected") || p.payout.cases[p.payout.cases.length - 1];
    if (!c) return frame("Review", [h("p", { class: "muted" }, "No review is open.")], null, { back: () => go("request") });
    const hb = p.payout.holdbacks.find((x) => x.kind === "round" && x.request_id === c.request_id);
    const amount = hb ? xrp(hb.amount_xrp) : "your held part";
    const text = h("textarea", { class: "ar-textarea", maxlength: 500, placeholder: "Tell the reviewer what happened" });
    const closed = c.status === "cleared" || c.status === "confirmed";
    const body = [
      c.status === "cleared" ? banner("green", `Review closed · ${amount} paid`)
        : c.status === "confirmed" ? banner("gray", "Review closed · held part not paid. New requests stop for 180 days. Payments already made stay yours.")
        : banner("amber", h("b", {}, `Your held payment of ${amount} is under a longer review`)),
      h("div", { class: "ar-card col" }, h("h3", {}, "What the check found"),
        c.signals.map((s) => h("p", { class: "small" }, `Week ${s.week} ${(p.timeline.rows.find((r) => r.item === s.item) || {}).label || s.item} ${SIGNAL[s.code] || s.code}`)),
        h("p", { class: "tiny muted" }, "A person reviews this. Nothing is decided automatically.")),
      !closed && h("div", { class: "ar-card col" },
        h("p", { class: "small" }, ledgerName() === "Testnet" ? `Respond by ${ledgerDay(c.respond_by)}` : "Respond within 3 days (practice ledger time)"),
        c.response ? h("blockquote", { class: "small", style: { margin: 0, padding: "8px 12px", borderLeft: "3px solid var(--ar-border)" } }, c.response)
          : [text, h("button", { class: "ar-btn primary", onclick: async (e) => {
              const res = await busy(e.target, "Sending", () => api.respond(pid, c.id, text.value.trim()));
              if (res && res.ok) load(); else toast((res && res.message) || "Could not send.");
            } }, "Send to the reviewer")],
        c.response ? h("p", { class: "tiny muted" }, "The reviewer will reply when the review ends.") : null),
      h("div", { class: "ar-card col small" },
        h("p", {}, `If cleared: paid in full. If confirmed: the held ${amount} is not paid and new requests stop for 180 days. Payments already made stay yours.`),
        h("button", { class: "ar-link", style: { alignSelf: "flex-start" }, onclick: () => go("pay") }, "Why part of the payment is held →")),
    ];
    return frame("Review notice", body, null, { back: () => go("request") });
  }

  function toast(text, undo) {
    st.toast = { text, undo };
    draw();
    setTimeout(() => { if (st.toast && st.toast.text === text) { st.toast = null; draw(); } }, 5000);
  }

  load();
  return { reload: load, stop: () => watcher.stop() };
}
