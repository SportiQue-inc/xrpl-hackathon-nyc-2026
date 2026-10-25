// UniQdata, the participant side. ?mode=before is today's flow (browse every study, type a linking
// code, sign full-screen consent per project, approve every item every week). ?mode=after is the
// same person with an agent: only matched studies, one bottom sheet for a batch with the amount
// pinned and one passkey, weekly sends by the agent, and only new or late asks reach the person.

import { DISPLAY_UNIT } from "../shared/ui.js";
import { MODE, INST, SUBS, NEW_SUB, ITEMS, HERO, OPEN_STUDIES, rl, weekPrice, subTotal, h, tag, send, listen, toast } from "./common.js";

const root = document.getElementById("app");
const S1 = SUBS[0], S3 = SUBS[2];
const st = MODE === "before" ? {
  tab: "research", view: "home", code: "", lane: 0, notif: null, done: new Set(), signedFor: false,
} : {
  tab: "agent", view: "agent", pick: new Set(["S1", "S2"]), sheet: null, read: false, passkey: false, joined: [],
  notif: null, earned: 0, timeline: [], askedGap: false, newsub: false,
};

const RULES = [
  ["Heart rate", "auto", "green"], ["Sleep stages", "auto", "green"], ["Surveys in studies I joined", "auto", "green"],
  ["Anything new or late", "ask me", "amber"], ["Clinic records", "ask me", "amber"], ["Genome", "never", "red"],
];
const OTHER_STUDIES = [
  ["Metabolic drug study", "Seoul Metro Hospital"], ["Senior sleep pattern", "Busan Care Lab"], ["ADHD lifestyle", "Mind Research Center"],
  ["Genome and diet", "GeneBridge (SG)"], ["Running form", "Sports Science Inst."], ["Migraine diary", "Neuro Clinic"],
  ["Pregnancy wellbeing", "Women's Health Lab"], ["Cardio rehab", "Heart Institute"],
];

// ---------- frame ----------
function frame({ title, back, body, foot, tabs = true, extra = [] }) {
  return h("div", { class: "ph" },
    h("div", { class: "ph-status" }, h("span", {}, "9:41"), h("span", {}, "●●● ▮")),
    h("div", { class: "ph-bar" }, back && h("button", { class: "back", onclick: back, "aria-label": "Back" }, "‹"),
      h("span", { class: "title" }, title), MODE === "after" && tag("Testnet", "gray"), tag(HERO, "blue")),
    h("div", { class: "ph-body" }, body),
    foot && h("div", { class: "ph-foot" }, foot),
    tabs && !foot && tabBar(),
    st.notif && notif(st.notif),
    ...extra);
}
function tabBar() {
  const T = MODE === "before"
    ? [["home", "Home", "⌂"], ["research", "Research", "◎"], ["approvals", "Approvals", "✓"], ["me", "Me", "○"]]
    : [["agent", "My agent", "✦"], ["matched", "Matched", "◎"], ["activity", "Activity", "↻"], ["me", "Me", "○"]];
  return h("nav", { class: "ph-tabs" }, T.map(([id, label, ic]) => h("button", { class: st.tab === id ? "on" : "", onclick: () => goTab(id) },
    h("span", { class: "ic" }, ic), label,
    MODE === "before" && id === "approvals" && h("span", { class: "tag red", style: { padding: "0 6px", fontSize: "10px" } }, approvalsLeft()))));
}
function goTab(id) {
  st.tab = id;
  st.view = { home: "home", research: "home", approvals: "approvals", me: "me", agent: "agent", matched: "matched", activity: "activity" }[id];
  draw();
}
function notif(n) {
  return h("div", { class: `notif${n.sms ? " sms" : ""}`, onclick: () => { const f = n.tap; st.notif = null; f(); } },
    h("div", { class: "app" }, n.sms ? "✉" : "U"),
    h("div", { class: "grow" }, h("div", { class: "spread tiny muted" }, h("b", { style: { color: "var(--text)" } }, n.from), "now"),
      h("div", { class: "small" }, n.text)));
}

// ---------- before ----------
const APPROVALS = [];
for (let w = 1; w <= 6; w++) {
  APPROVALS.push({ item: "hr", week: w, sub: S1 }, { item: "fatigue", week: w, sub: S1 }, { item: "bp", week: w, sub: S3 });
}
const aKey = (a) => `${a.item}:${a.week}`;
const expired = (a) => a.item === "fatigue" && a.week === 3;
const approvalsLeft = () => APPROVALS.filter((a) => !st.done.has(aKey(a))).length;

function beforeHome() {
  return frame({
    title: "Research",
    body: [
      h("div", { class: "pcard", style: { background: "var(--brand-weak)", borderColor: "var(--brand-line)" } },
        h("b", {}, "Got a linking code from a researcher?"),
        h("p", { class: "small muted" }, "Enter the code they sent you to join their project."),
        h("button", { class: "btn primary", onclick: () => { st.view = "code"; draw(); } }, "Enter linking code")),
      h("div", { class: "spread" }, h("h2", {}, `Open studies (${OPEN_STUDIES})`), h("span", { class: "muted small" }, "Newest")),
      h("p", { class: "muted small" }, "Browse each one yourself to see if it fits you."),
      ...[[S1.name, INST.name], ...OTHER_STUDIES].map(([n, o]) => h("div", { class: "pcard" },
        h("div", { class: "spread" }, h("b", {}, n), tag("Recruiting", "gray")), h("div", { class: "muted small" }, `${o} · read the notice to check eligibility`))),
      h("div", { class: "muted small", style: { textAlign: "center" } }, `${OPEN_STUDIES - 9} more`),
    ],
  });
}

function beforeCode() {
  const digits = st.code.padEnd(6, " ").split("");
  const press = (d) => { if (st.code.length < 6) { st.code += d; draw(); } };
  return frame({
    title: "Linking code", back: () => { st.view = "home"; draw(); }, tabs: false,
    body: [
      h("p", { class: "muted small", style: { textAlign: "center" } }, "Type the 6-digit code from the research team's text message."),
      h("div", { class: "code-box" }, digits.map((d) => h("span", {}, d.trim()))),
      h("div", { class: "keypad", style: { marginTop: "auto" } },
        ..."123456789".split("").map((d) => h("button", { onclick: () => press(d) }, d)),
        h("button", { onclick: () => { st.code = ""; draw(); } }, "C"), h("button", { onclick: () => press("0") }, "0"),
        h("button", { onclick: () => { st.code = st.code.slice(0, -1); draw(); } }, "⌫")),
    ],
    foot: h("button", { class: "btn primary block", disabled: st.code.length < 6, onclick: () => { send("linked"); st.view = "consent"; st.lane = 1; draw(); } }, "Link to project"),
  });
}

function typeCode(code) {
  st.view = "code"; st.code = ""; draw();
  const ds = code.replace(/\s/g, "").split("");
  ds.forEach((d, i) => setTimeout(() => { st.code += d; draw(); }, 350 * (i + 1)));
}

const LANES = [null,
  { title: "Research participation", law: "Bioethics and Safety Act, Article 16" },
  { title: "Sensitive health collection", law: "Personal Information Protection Act, Article 23" }];
function beforeConsent() {
  const lane = LANES[st.lane];
  const para = "This consent applies to the project named above only. The research team will collect the items listed for the period stated, keep them for the retention period in the protocol, and use them for the stated purpose. You may withdraw at any time through the app; data already analyzed may remain in results. Questions go to the research team listed in the notice.";
  return frame({
    title: `Consent ${st.lane} of 2`, back: () => { st.view = "home"; draw(); }, tabs: false,
    body: h("div", { class: "doc", style: { margin: "-16px", minHeight: "100%" } },
      h("div", { class: "tiny muted" }, `${S1.name} · ${INST.name} · Contract NSL-2026-041`),
      h("h2", { style: { margin: "6px 0 2px" } }, lane.title),
      h("div", { class: "tiny muted" }, lane.law),
      ...["1. Purpose", "2. Items collected", "3. Period and retention", "4. Who receives it", "5. Risks and benefits", "6. Payment", "7. Withdrawal", "8. Contact"]
        .map((t) => [h("h3", {}, t), h("p", {}, para)])),
    foot: h("button", { class: "btn primary block", onclick: signLane }, `I agree and sign (${st.lane} of 2)`),
  });
}
function signLane() {
  send("lane", { n: st.lane });
  if (st.lane === 1) { st.lane = 2; draw(); root.querySelector(".ph-body").scrollTop = 0; return; }
  st.signedFor = true; st.view = "signed"; draw();
}
function beforeSigned() {
  return frame({
    title: "Signed", tabs: false,
    body: [
      h("div", { class: "pcard" }, h("b", {}, `You joined ${S1.name}`), h("p", { class: "small muted" }, "Two consent forms signed for this project.")),
      h("div", { class: "note amber" }, `${S3.name} is a separate project at the same lab. It needs its own linking code and its own two consent forms.`),
      h("div", { class: "note gray" }, "Each week, every item waits in Approvals until you approve it."),
    ],
    foot: h("button", { class: "btn primary block", onclick: () => goTab("approvals") }, "Go to approvals"),
  });
}

function beforeApprovals() {
  const left = approvalsLeft();
  return frame({
    title: "Approvals",
    body: [
      h("div", { class: "spread" }, h("span", { class: "muted small" }, "Every item, every week, by hand"), tag(`${left} waiting`, "red")),
      ...APPROVALS.filter((a) => !st.done.has(aKey(a))).map((a) => h("div", { class: "approval", "data-k": aKey(a) },
        h("div", { class: "grow" },
          h("div", { class: "small", style: { fontWeight: 600 } }, `Approve ${ITEMS[a.item].label} · Week ${a.week}`),
          h("div", { class: "tiny muted" }, `${a.sub.name}${ITEMS[a.item].sensitive ? " · sensitive health collection" : ""}`)),
        expired(a) ? tag("Expired", "gray")
          : [h("button", { class: "btn sm primary", onclick: (e) => approve(a, e) }, "Approve"), h("button", { class: "btn sm" }, "Later")])),
    ],
  });
}
function approve(a, e) {
  const row = e.target.closest(".approval");
  row.classList.add("done");
  setTimeout(() => { st.done.add(aKey(a)); send("approve", { item: a.item, week: a.week }); draw(); }, 280);
}

function beforeMe() {
  return frame({ title: "Me", body: [
    h("div", { class: "pcard" }, h("b", {}, "My projects"),
      h("div", { class: "rule" }, S1.name, st.signedFor ? tag("Joined · contract 1", "green") : tag("Not joined", "gray")),
      h("div", { class: "rule" }, SUBS[1].name, tag("Needs code + 2 forms", "gray")),
      h("div", { class: "rule" }, S3.name, tag("Needs code + 2 forms", "gray"))),
    h("div", { class: "pcard" }, h("b", {}, "Payments"), h("p", { class: "small muted" }, "Paid after the monthly settlement batch is approved by the lab.")),
  ] });
}

// ---------- after ----------
function afterAgent() {
  const rel = st.joined.length > 0;
  return frame({
    title: "My agent",
    body: [
      h("div", { class: "pcard" }, h("div", { class: "spread" }, h("b", {}, "My rules"), h("span", { class: "muted tiny" }, "set once")),
        h("div", {}, RULES.map(([k, v, tone]) => h("div", { class: "rule" }, k, tag(v, tone))))),
      h("div", { class: "pcard sel", onclick: () => goTab("matched"), style: { cursor: "pointer" } },
        h("div", { class: "spread" }, h("b", {}, "Matched for you"), tag(`2 of ${OPEN_STUDIES}`, "blue")),
        h("div", { class: "small muted" }, `Your agent checked ${OPEN_STUDIES} open studies against your rules. Only 2 sub-projects at ${INST.name} fit.`)),
      rel && relationshipCard(),
      st.timeline.length > 0 && h("div", { class: "pcard" }, h("div", { class: "spread" }, h("b", {}, "This week"), st.earned > 0 && h("span", { class: "small", style: { color: "var(--green)", fontWeight: 600 } }, `+${rl(st.earned)}`)),
        h("div", { class: "timeline" }, st.timeline.slice(0, 3).map(tl))),
    ],
  });
}
function relationshipCard() {
  const subs = [...SUBS.filter((s) => st.joined.includes(s.id)), ...(st.newsub === "allowed" ? [NEW_SUB] : [])];
  return h("div", { class: "pcard", style: { background: "var(--brand-weak)", borderColor: "var(--brand-line)" } },
    h("div", { class: "spread" }, h("b", {}, INST.name), tag("1 relationship", "blue")),
    h("div", { class: "small muted" }, `One consent, ${subs.length} sub-projects. Your agent sends weekly inside it.`),
    ...subs.map((s) => h("div", { class: "spread small" }, `· ${s.name}`, h("span", { class: "muted" }, `${rl(weekPrice(s))} / week`))));
}

function afterMatched() {
  const subs = SUBS.map((s) => ({ ...s, why: s.id === "S3" ? "Clinic records: your rule is ask me" : `${s.items.map((k) => ITEMS[k].label).join(" + ")} · inside your rules` }));
  const picked = subs.filter((s) => st.pick.has(s.id));
  const joined = st.joined.length > 0;
  return frame({
    title: "Matched",
    body: [
      h("div", { class: "note blue" }, `Your agent checked ${OPEN_STUDIES} open studies and set aside ${OPEN_STUDIES - 3} (genome, outside your rules, or not recruiting someone like you). Two sub-projects here match; the third needs your OK.`),
      h("div", { class: "pcard" },
        h("div", { class: "spread" }, h("b", {}, INST.name), tag("Verified organization", "green")),
        h("div", { class: "tiny muted" }, `${INST.kind} · ${INST.irb} approved`),
        ...subs.map((s) => {
          const on = st.pick.has(s.id);
          const isJoined = st.joined.includes(s.id);
          return h("div", { class: "row", style: { alignItems: "flex-start", padding: "8px 0", borderTop: "1px solid var(--border)", cursor: isJoined ? "default" : "pointer" },
            onclick: () => { if (isJoined) return; on ? st.pick.delete(s.id) : st.pick.add(s.id); draw(); } },
          isJoined ? tag("Joined", "green") : h("span", { class: `check${on ? " on" : ""}` }, on ? "✓" : ""),
          h("div", { class: "grow" }, h("div", { class: "spread" }, h("b", { class: "small" }, s.name), h("span", { class: "small" }, rl(subTotal(s)))),
            h("div", { class: "tiny muted" }, `${s.weeks} weeks · ${s.why}`)));
        })),
    ],
    foot: joined && picked.every((s) => st.joined.includes(s.id)) ? null
      : h("button", { class: "btn primary block", disabled: !picked.length, onclick: openConsent }, `Review ${picked.length} together`),
  });
}

function openConsent() { st.sheet = "consent"; st.read = false; draw(); }
function watchRead() {
  const sc = root.querySelector(".sheet .scroll");
  if (!sc || st.read) return;
  sc.addEventListener("scroll", () => {
    if (!st.read && sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 8) {
      st.read = true;
      root.querySelector(".sheet .act .btn.primary").disabled = false;
      root.querySelector(".sheet .act .hint").textContent = READ_HINT;
    }
  });
}
const READ_HINT = "You've read it all. One passkey signs every item above.";

function consentSheet() {
  const subs = SUBS.filter((s) => st.pick.has(s.id) && !st.joined.includes(s.id));
  const total = subs.reduce((a, s) => a + subTotal(s), 0);
  const sens = subs.some((s) => s.items.some((k) => ITEMS[k].sensitive));
  return [
    h("div", { class: "scrim", onclick: () => { st.sheet = null; draw(); } }),
    h("div", { class: "sheet" },
      h("div", { class: "grab" }),
      h("div", { class: "pin" },
        h("div", { class: "spread" }, h("span", { class: "small muted" }, `${INST.name} · ${subs.length} sub-projects`), tag("Pinned", "gray")),
        h("div", { class: "amount" }, `Up to ${rl(total)}`),
        h("div", { class: "small muted" }, "6 weeks · paid for each week your agent delivers · 80% at delivery, 20% after a 7-day review")),
      h("div", { class: "scroll" },
        h("div", { class: "sec" }, h("h3", {}, "What you're joining"),
          ...subs.map((s) => h("div", { class: "pcard", style: { padding: "10px" } },
            h("div", { class: "spread" }, h("b", { class: "small" }, s.name), h("span", { class: "small" }, `${rl(weekPrice(s))} / week`)),
            ...s.items.map((k) => h("div", { class: "spread tiny muted" }, h("span", {}, `${ITEMS[k].label} · ${ITEMS[k].source}`), h("span", {}, rl(ITEMS[k].price))))))),
        h("div", { class: "sec" }, h("h3", {}, "One relationship with this lab"),
          h("p", {}, `This creates one relationship with ${INST.name}. Later sub-projects there that stay inside your rules use it, so you don't sign again. Anything new or late is asked here first.`)),
        h("div", { class: "sec" }, h("h3", {}, "Purpose"), h("p", {}, "Sleep and recovery research (health or biomedical research, DUO:0000006). Not for marketing or insurance decisions.")),
        h("div", { class: "sec" }, h("h3", {}, "Who receives it"), h("p", {}, `${INST.name} only, under your study number. No third party. No transfer abroad.`)),
        h("div", { class: "sec" }, h("h3", {}, "Sensitive information"), h("p", {}, sens ? "Clinic records are sensitive health information and are approved one by one." : "None in this batch. Clinic records stay off until you say otherwise.")),
        h("div", { class: "sec" }, h("h3", {}, "How it's sent"), h("p", {}, "Your agent sends each week's data sealed. The lab can open it only after the payment for that week is locked on the ledger.")),
        h("div", { class: "sec" }, h("h3", {}, "If you want to stop"),
          h("ul", {}, h("li", {}, "Skip a week: nothing is sent or paid for it."), h("li", {}, "Stop: no more weeks are sent."), h("li", {}, "Withdraw: the lab's access ends and unsent weeks are returned."))),
        h("div", { class: "sec" }, h("h3", {}, "Record"), h("p", {}, "Your consent is recorded per item on XRPL Testnet with a hash of this text."))),
      h("div", { class: "act" },
        h("div", { class: "tiny muted hint", style: { textAlign: "center" } }, st.read ? READ_HINT : "Scroll to the end to continue"),
        h("button", { class: "btn primary block", disabled: !st.read, onclick: () => passkey(subs) }, `Approve ${subs.length} with passkey`),
        h("button", { class: "btn ghost", onclick: () => { st.sheet = null; draw(); } }, "Not now"))),
  ];
}

function passkey(subs) {
  st.passkey = true; draw();
  setTimeout(() => {
    st.passkey = false; st.sheet = null;
    st.joined.push(...subs.map((s) => s.id));
    st.pick = new Set();
    st.timeline.unshift({ text: `Joined ${subs.length} sub-projects at ${INST.short}`, sub: "One passkey · consent recorded per item", dot: "blue" });
    send("consented", { subs: subs.map((s) => s.id) });
    st.tab = "agent"; st.view = "agent";
    draw();
    toast(root, `Joined ${subs.length} sub-projects with one passkey`);
  }, 1500);
}

function exceptionSheet() {
  const g = { item: "fatigue", week: 3 };
  return [
    h("div", { class: "scrim" }),
    h("div", { class: "sheet short" }, h("div", { class: "grab" }),
      h("div", { class: "pin" }, h("div", { class: "tiny", style: { color: "var(--amber)", fontWeight: 700 } }, "YOUR AGENT ASKS · LATE REQUEST"),
        h("h2", {}, `${ITEMS[g.item].label} · Week ${g.week}`),
        h("div", { class: "small muted" }, `${S1.name} · ${INST.name}`)),
      h("div", { class: "scroll" }, h("div", { class: "spread" }, h("span", {}, "Payment for this week"), h("b", { style: { color: "var(--brand)" } }, rl(ITEMS[g.item].price))),
        h("p", { class: "small muted" }, "You missed this week. The lab asks for that one week only. Your rule says ask me for anything late.")),
      h("div", { class: "act" },
        h("button", { class: "btn primary block", onclick: () => answerGap(true) }, "Allow this week"),
        h("button", { class: "btn ghost", onclick: () => answerGap(false) }, "Not this one"))),
  ];
}
function answerGap(allow) {
  st.sheet = null;
  send("exception", { allow });
  if (allow) { st.earned += ITEMS.fatigue.price; st.timeline.unshift({ text: `${ITEMS.fatigue.label} · Week 3 sent by your agent`, sub: "Late week · you allowed it", amt: ITEMS.fatigue.price, dot: "green" }); }
  draw();
  toast(root, allow ? `Sent · ${rl(ITEMS.fatigue.price)} paid` : "Declined · nothing sent");
}

function newPurposeSheet() {
  return [
    h("div", { class: "scrim" }),
    h("div", { class: "sheet short" }, h("div", { class: "grab" }),
      h("div", { class: "pin" }, h("div", { class: "tiny", style: { color: "var(--amber)", fontWeight: 700 } }, "YOUR AGENT ASKS · NEW PURPOSE"),
        h("h2", {}, NEW_SUB.name), h("div", { class: "small muted" }, `New sub-project at ${INST.name} · same relationship`)),
      h("div", { class: "scroll" },
        h("div", { class: "spread small" }, `${ITEMS.hr.label}`, tag("Inside your rules · auto", "green")),
        h("div", { class: "spread small" }, `${ITEMS.caffeine.label} · ${rl(ITEMS.caffeine.price)} / week`, tag("New · needs your OK", "amber")),
        h("p", { class: "small muted" }, "No new contract. Only the new item needs a yes.")),
      h("div", { class: "act" },
        h("button", { class: "btn primary block", onclick: () => answerNew(true) }, "Allow caffeine diary"),
        h("button", { class: "btn ghost", onclick: () => answerNew(false) }, "Heart rate only"))),
  ];
}
function answerNew(allow) {
  st.sheet = null; st.newsub = allow ? "allowed" : "hr-only";
  send("newpurpose", { allow });
  st.timeline.unshift({ text: `${NEW_SUB.name}: ${allow ? "caffeine diary allowed" : "heart rate only"}`, sub: "Same relationship · no new contract", dot: "blue" });
  draw();
}

const tl = (t) => h("div", { class: `it${t.fresh ? " new" : ""}` }, h("span", { class: `dot ${t.dot || "green"}` }),
  h("div", { class: "grow" }, h("div", { class: "small" }, t.text), h("div", { class: "tiny muted" }, t.sub)),
  t.amt ? h("span", { class: "small", style: { color: "var(--green)", fontWeight: 600 } }, `+${rl(t.amt)}`) : null);

function afterActivity() {
  return frame({
    title: "Activity",
    body: [
      h("div", { class: "pcard" }, h("div", { class: "muted small" }, "Paid to you so far"), h("div", { class: "amount" }, rl(st.earned)),
        h("div", { class: "tiny muted" }, `${DISPLAY_UNIT} · demo amounts · each week paid when your agent delivers it`)),
      st.timeline.length ? h("div", { class: "pcard timeline" }, st.timeline.map(tl))
        : h("div", { class: "note gray" }, "Nothing yet. Join a matched study and your agent sends each week for you."),
    ],
  });
}
function afterMe() {
  return frame({ title: "Me", body: [
    st.joined.length ? relationshipCard() : h("div", { class: "note gray" }, "No relationships yet."),
    h("div", { class: "pcard" }, h("b", {}, "Passkey"), h("p", { class: "small muted" }, "One passkey on this phone signs a whole batch. Your agent never signs consent for you.")),
    h("div", { class: "pcard" }, h("b", {}, "Stop or withdraw"), h("p", { class: "small muted" }, "Skip a week, stop future weeks, or withdraw the lab's access. Unsent weeks are returned.")),
  ] });
}

// ---------- messages from UniQLab ----------
listen(({ type, data }) => {
  if (MODE === "before") {
    if (type === "code") st.notif = { sms: true, from: "Messages", text: `[${INST.short}] Your UniQdata linking code is ${data.code}. Enter it in the app to join ${S1.name}.`, tap: () => typeCode(data.code) };
  } else {
    if (type === "request" && data.gaps.some((g) => g.p === HERO)) {
      st.notif = { from: "UniQdata · your agent", text: `${INST.short} asks for ${ITEMS.fatigue.label} · Week 3 (${rl(ITEMS.fatigue.price)}). It's late, so your agent is asking you.`, tap: () => { st.sheet = "exception"; draw(); } };
    }
    if (type === "week") {
      const subs = SUBS.filter((s) => st.joined.includes(s.id));
      const list = subs.length ? subs : [S1];
      list.forEach((s) => s.items.forEach((k) => {
        st.earned += ITEMS[k].price;
        st.timeline.unshift({ text: `${ITEMS[k].label} · Week ${data.n} sent by your agent`, sub: s.name, amt: ITEMS[k].price, dot: "green", fresh: true });
      }));
      toast(root, `Week ${data.n} sent by your agent`);
    }
    if (type === "newsub") {
      st.notif = { from: "UniQdata · your agent", text: `${INST.short} added ${NEW_SUB.name}. Heart rate is inside your rules. The caffeine diary is new, so your agent is asking you.`, tap: () => { st.sheet = "newpurpose"; draw(); } };
    }
  }
  draw();
  st.timeline?.forEach((t) => { t.fresh = false; });
});

// ---------- draw ----------
function draw() {
  const body = root.querySelector(".ph-body");
  const keep = body && !st.sheet ? body.scrollTop : 0;
  let view;
  if (MODE === "before") {
    view = { home: beforeHome, code: beforeCode, consent: beforeConsent, signed: beforeSigned, approvals: beforeApprovals, me: beforeMe }[st.view]();
  } else {
    view = { agent: afterAgent, matched: afterMatched, activity: afterActivity, me: afterMe }[st.view]();
    const ph = view;
    if (st.sheet === "consent") ph.append(...consentSheet());
    if (st.sheet === "exception") ph.append(...exceptionSheet());
    if (st.sheet === "newpurpose") ph.append(...newPurposeSheet());
    if (st.passkey) ph.append(h("div", { class: "passkey" }, h("div", { class: "box" }, h("div", { class: "face" }, "◉"), h("b", {}, "Face ID"), h("div", { class: "tiny muted" }, "One passkey for the whole batch"))));
  }
  const toasts = [...root.querySelectorAll(".toast")];
  root.replaceChildren(view, ...toasts);
  const nb = root.querySelector(".ph-body");
  if (nb && keep) nb.scrollTop = keep;
  if (st.sheet === "consent") watchRead();
}
const start = new URLSearchParams(location.search).get("view");
if (start) { st.view = start; st.tab = start === "code" || start === "consent" ? "research" : start; if (start === "consent") st.lane = 1; }
draw();
