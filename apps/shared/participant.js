// 참여자 앱: 연구 참여 요청, 패스키 승인, 내 데이터, 기록(거래 · 나간 데이터 · 공유 이력 · 감사 기록),
// 참여 지급, 중단과 철회, 검토 알림. GET /api/p/{pid}와 그 하위 경로만 씁니다.

import { engine, watchSelf } from "./api.js";
import { createPasskey, passkeySupported, signWithPasskey } from "./passkey.js";
import { consentPages, textHash } from "./consent.js";
import { h, render, tag, icon, short, sum, banner, busy, UNIT } from "./ui.js";

const ITEM = {
  "heart_rate.daily": "안정시 심박", "fatigue.survey": "피로 설문", "blood_pressure.daily": "혈압(진료 기록)",
  "sleep.daily": "수면", "activity.daily": "활동량",
};
const SOURCE_KO = { wearable: "웨어러블", survey_app: "설문 앱", clinic_export: "진료 기록" };
const PURPOSE = { sleep_research: "수면 연구" };
let SOURCE = SOURCE_KO;
const EVENT = {
  passkey_registered: "패스키 등록", passkey_signed: "패스키로 승인", approval_bound: "승인과 결제 연결",
  approve: "승인", decline: "이번 회차 건너뜀", consent: "동의 변경", ask_person: "본인 확인 요청",
  provide: "데이터 준비", escrowed: "참여 지급액 예치", paid: "전달 완료 · 지급", holdback: "검토 후 지급분 예치",
  bonus: "완료 보너스 예치", licence: "열람 권한 발급", revoked: "철회", paused: "새 요청 멈춤", resumed: "새 요청 다시 받기",
  swap: "지급 통화 변환", deposit_auth: "입금 보호 설정", uniqdata_upload: "UniQdata에 저장", uniqdata_read: "UniQdata에서 읽음",
  released: "검토 후 지급", returned: "연구로 반환", clawback: "열람 권한 회수",
};
const KO = (new URLSearchParams(location.search).get("lang") || navigator.language || "en").toLowerCase().startsWith("ko");
const T = (en, ko) => (KO ? ko : en);
const ITEM_EN = {
  "heart_rate.daily": "Resting heart rate", "fatigue.survey": "Fatigue survey", "blood_pressure.daily": "Blood pressure (clinic)",
  "sleep.daily": "Sleep", "activity.daily": "Activity",
};
const SOURCE_EN = { wearable: "Wearable", survey_app: "Survey app", clinic_export: "Clinic record" };
const purposeName = (x) => (KO ? PURPOSE[x] : { sleep_research: "sleep research" }[x]) || x;
const md = (ts) => (ts ? new Date(ts * 1000).toLocaleDateString(KO ? "ko-KR" : "en-US", { month: "short", day: "numeric" }) : "");
const CONSENT = { research: "연구 참여", third_party: "제3자 제공", sensitive: "민감정보", international: "국외 이전" };
const itemName = (i) => (KO ? ITEM : ITEM_EN)[i] || i;
const won = (x) => `${(Math.round((x || 0) * 100) / 100).toFixed(2)} ${UNIT}`;
const weeks = (ws) => {
  const s = [...new Set(ws)].sort((a, b) => a - b);
  if (!s.length) return "";
  const runs = [];
  for (const w of s) {
    const last = runs[runs.length - 1];
    if (last && w === last[1] + 1) last[1] = w; else runs.push([w, w]);
  }
  if (!KO) return (runs.length === 1 && runs[0][0] === runs[0][1] ? "Week " : "Weeks ") + runs.map(([a, b]) => (a === b ? `${a}` : `${a}–${b}`)).join(", ");
  return runs.map(([a, b]) => (a === b ? `${a}주 차` : `${a}–${b}주 차`)).join(", ");
};
const when = (ts) => (ts ? new Date(ts * 1000).toLocaleString(KO ? "ko-KR" : "en-US", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "");

function txA(tx) {
  if (!tx || !tx.tx) return null;
  const label = `${short(tx.tx, 6, 4)}`;
  return tx.url ? h("a", { class: "ar-hash", href: tx.url, target: "_blank", rel: "noopener" }, label, " ", icon("ext", 12))
    : h("span", { class: "ar-hash" }, label);
}

export function mountParticipant(root, { base = "", pid = "P-017", embedded = false, token } = {}) {
  const api = engine(base, { token });
  if (!KO) SOURCE = SOURCE_EN;
  const st = { receipt: null, locking: false, p: null, view: "home", rid: null, picked: null, sheet: null, flow: null, batch: new Set(), error: null, toast: null,
               data: undefined, from: {}, tab: "trade", details: false };
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
    if ((!st.sheet || st.sheet.phase !== "busy") && !st.flow && !st.receipt && !st.locking) { st.p = v; st.error = null; draw(); }
  });

  const go = (view, keepFlow) => { st.view = view; st.sheet = null; st.receipt = null; if (!keepFlow) st.flow = null; draw(); window.scrollTo(0, 0); };
  const current = () => st.p.requests.find((r) => r.id === st.rid) || null;
  const openReqs = () => st.p.requests.filter((r) => r.status === "open" || r.status === "partly_open");
  const lab = (r) => (r ? r.institution.name.replace(/\s*\(synthetic\)/i, "") : "");
  const cellPrice = (r) => {
    const cells = sum(r.items, (i) => i.weeks.length);
    return cells ? r.reward_xrp / cells : 0;
  };

  // ---------- frame ----------
  function frame(title, body, foot, { back } = {}) {
    return h("div", { class: "ar-phone" },
      h("div", { class: "bar" },
        back ? h("button", { class: "ar-iconbtn", style: { border: 0 }, onclick: back, "aria-label": "뒤로" }, icon("back")) : null,
        h("span", { class: "title" }, title)),
      h("div", { class: "body" }, body),
      foot ? h("div", { class: "foot" }, foot)
        : h("nav", { class: "ar-tabs four" },
          tabBtn("home", T("Requests", "요청"), "list"), tabBtn("data", T("My data", "내 데이터"), "data"),
          tabBtn("record", T("Records", "기록"), "history"), tabBtn("pay", T("Payments", "지급"), "wallet")),
      st.sheet ? sheetView() : null,
      st.flow && st.flow.open ? flowView() : null,
      st.toast && h("div", { class: "ar-toast" }, st.toast));
  }
  function tabBtn(view, label, ic) {
    const on = st.view === view || (view === "home" && ["request", "consent", "preview", "status", "done", "stop", "review"].includes(st.view));
    return h("button", { class: on ? "on" : "", onclick: () => { if (view === "data") loadData(); go(view); } },
      h("div", {}, icon(ic, 20)), label);
  }

  function draw() {
    let out;
    if (st.error && !st.p) {
      out = frame("연구 참여", [banner("red", "연결할 수 없어요. ", h("button", { class: "ar-link", onclick: load }, "다시 시도"))]);
    } else if (!st.p) {
      out = frame("연구 참여", [1, 2].map(() => h("div", { class: "ar-skel", style: { height: "120px" } })));
    } else {
      const v = st.view;
      out = v === "request" ? requestView() : v === "consent" ? consentView() : v === "preview" ? previewView()
        : v === "status" || v === "done" ? statusView() : v === "data" ? dataView()
        : v === "record" ? recordView() : v === "pay" ? payView() : v === "stop" ? stopView()
        : v === "review" ? reviewView() : homeView();
    }
    render(root, out);
    if (st.flow) afterFlowDraw();
  }

  // ---------- Figma "UniQdata Research Contribution" frames ----------
  // Top bar (eyebrow + title + XRPL Testnet badge), content column, sticky action bar.
  function fig(eyebrow, title, body, act, { back, gap11 } = {}) {
    return h("div", { class: "fg" },
      h("div", { class: "fg-top" },
        h("div", { class: "nav" },
          back ? h("button", { class: "back", onclick: back, "aria-label": T("Back", "뒤로") }, "‹") : null,
          h("div", { class: "copy" }, h("span", { class: "eb" }, eyebrow), h("span", { class: "tt" }, title))),
        h("span", { class: "fg-pill env" }, h("span", {}, "◌"), h("span", {}, "XRPL Testnet"))),
      h("div", { class: `fg-body${gap11 ? " g11" : ""}` }, body),
      act ? h("div", { class: "fg-act" }, act)
        : h("nav", { class: "ar-tabs four fg-tabs" },
          tabBtn("home", T("Requests", "요청"), "list"), tabBtn("data", T("My data", "내 데이터"), "data"),
          tabBtn("record", T("Records", "기록"), "history"), tabBtn("pay", T("Payments", "지급"), "wallet")),
      st.sheet ? sheetView() : null,
      st.flow && st.flow.open ? flowView() : null,
      st.receipt ? receiptView() : null,
      st.toast && h("div", { class: "ar-toast" }, st.toast));
  }
  const pill = (tone, label) => h("span", { class: `fg-pill ${tone}` },
    h("span", {}, { ok: "✓", warn: "!", danger: "×", brand: "●" }[tone] || "●"), h("span", {}, label));
  const card = (tone, title, ...kids) => h("div", { class: `fg-card ${tone || ""}` }, title ? h("p", { class: "t" }, title) : null, kids);
  const d = (...t) => h("p", { class: "d" }, ...t);
  const n = (t, strong) => h("p", { class: `n${strong ? " strong" : ""}` }, t);
  const row = (l, v, tone = "") => h("div", { class: "fg-row" }, h("span", { class: "l" }, l), h("span", { class: `v ${tone}` }, v));
  const btn = (label, onclick, { secondary, disabled } = {}) => h("button", { class: `fg-btn${secondary ? " secondary" : ""}`, disabled, onclick }, label);
  const sub = (label, onclick) => h("button", { class: "fg-sub", onclick }, label);
  const h1 = (t) => h("h1", { class: "fg-h1" }, t);
  const lead = (t) => h("p", { class: "fg-lead" }, t);
  const ledger = (tx, rc) => (tx && tx.tx ? h("button", { class: "fg-ledger", onclick: () => { st.receipt = { ...rc, tx }; draw(); } },
    `Tx ${short(tx.tx, 4, 4)} · ${T("View", "보기")} ↗`) : null);
  const testnet = T("XRPL Testnet · no cash value", "XRPL Testnet · 현금 가치 없음");
  const split = (r, price) => {
    const pay = r.payment || { max_pct: 90 };
    return { now: price * pay.max_pct / 100, held: price * (100 - pay.max_pct) / 100, days: String(pay.review || "7").replace(/\D+/g, "") || "7" };
  };

  // ---------- requests ----------
  function homeView() {
    const p = st.p;
    const revoked = p.consent && p.consent.status === "revoked";
    const paused = p.consent && p.consent.status === "paused";
    const openCase = p.payout.cases.find((c) => c.status === "suspected");
    const pending = openReqs();
    const done = p.requests.filter((r) => !pending.includes(r)).slice().reverse();
    const reqCard = (r) => {
      const asks = r.items.filter((i) => i.class === "approval");
      const batchable = pending.includes(r) && defaultSend(r).length;
      const picked = st.batch.has(r.id);
      const state = r.status === "declined" ? pill("", T("Skipped", "건너뜀")) : r.status === "contributed" ? pill("ok", T("Approved", "승인함"))
        : pill("warn", T("Needs your OK", "승인 필요"));
      return h("div", { class: `fg-card${picked ? " brand" : ""}`, role: "button", tabindex: 0, style: { cursor: "pointer" },
          onclick: () => { st.rid = r.id; st.picked = null; go("request"); } },
        h("p", { class: "fg-kicker" }, `${lab(r)} · ${T("synthetic", "합성")}`),
        h("p", { class: "t" }, `${asks.map((i) => itemName(i.item)).join(", ") || T("No items", "요청 항목 없음")} · ${weeks(asks.flatMap((i) => i.weeks))}`),
        row(T("Participation payment", "참여 지급액"), won(r.reward_xrp), "brand"),
        h("div", { class: "fg-decide" }, state,
          batchable ? h("button", { class: `fg-box${picked ? " on" : ""}`, "aria-pressed": String(picked), "aria-label": T("Select for batch approval", "일괄 승인에 넣기"),
            onclick: (e) => { e.stopPropagation(); picked ? st.batch.delete(r.id) : st.batch.add(r.id); draw(); } }, picked ? "✓" : "") : null));
    };
    const body = [
      revoked ? card("", T("You withdrew from this study", "이 연구에서 철회했어요")) : null,
      paused ? h("button", { class: "fg-card warn", onclick: () => go("stop") }, h("p", { class: "t" }, T("Future rounds are stopped", "새 요청을 멈춘 상태예요")),
        h("p", { class: "go" }, T("Resume →", "다시 받기 →"))) : null,
      openCase ? h("button", { class: "fg-card warn", onclick: () => go("review") }, h("p", { class: "t" }, T("Your held part needs review", "검토 후 지급분 확인이 필요해요")),
        h("p", { class: "go" }, T("Open review notice →", "검토 알림 보기 →"))) : null,
      h1(T("Participation requests", "참여 요청")),
      lead(T("Requests inside your consent are handled by your agent. These need your OK. Tick several to approve them with one passkey after reading each consent.",
        "동의 범위 안의 요청은 에이전트가 처리해요. 아래는 승인이 필요한 요청이에요. 여러 건을 고르면 동의서를 모두 읽은 뒤 패스키 한 번으로 승인할 수 있어요.")),
      pending.length ? pending.map(reqCard) : card("", null, d(T("Nothing needs your OK right now.", "지금 승인할 요청이 없어요."))),
      done.length ? [h("p", { class: "fg-group" }, T("Earlier requests", "지난 요청")), done.map(reqCard)] : null,
      h("button", { class: "fg-sub", style: { textAlign: "left", marginTop: "6px" }, onclick: () => go("stop") }, T("Manage participation →", "참여 관리 →")),
    ];
    const chosen = pending.filter((r) => st.batch.has(r.id));
    const act = chosen.length ? [btn(T(`Review ${chosen.length} requests together`, `${chosen.length}건 함께 검토`),
      () => startFlow(chosen.map((r) => ({ r, send: defaultSend(r) }))))] : null;
    return fig(T("Research contribution", "연구 기여"), T("Requests", "참여 요청"), body, act);
  }
  const defaultSend = (r) => r.items.filter((i) => i.class === "approval" && !i.sensitive);

  // ---------- P1 request ----------
  function requestView() {
    const r = current();
    if (!r) return homeView();
    const open = r.status === "open" || r.status === "partly_open";
    if (!st.picked || st.picked.rid !== r.id) st.picked = { rid: r.id, items: new Set(defaultSend(r).map((i) => i.item)) };
    const picked = st.picked.items;
    const asks = r.items.filter((i) => i.class === "approval");
    const auto = r.items.filter((i) => i.class === "auto");
    const blocked = r.items.filter((i) => i.class === "blocked");
    const ethics = r.institution.badges.find((b) => b.kind === "ethics_review" && b.on_ledger);
    const send = asks.filter((i) => picked.has(i.item));
    const price = cellPrice(r) * sum(send, (i) => i.weeks.length);
    const sp = split(r, price);
    const wk = weeks(asks.flatMap((i) => i.weeks));
    const body = [
      h("p", { class: "fg-kicker" }, `${lab(r)} · ${T("synthetic", "합성")}`),
      h1(T(`Help complete the ${wk.toLowerCase()} comparison`, `${wk} 비교를 완성하는 데 참여해 주세요`)),
      lead(KO ? `연구실에 ${wk} ${asks.map((i) => itemName(i.item)).join(", ")} 기록이 비어 있어요. 보내 주시면 비교를 완성할 수 있어요.` : r.summary),
      !ethics ? card("danger", T("Ethics approval not confirmed", "IRB 승인 확인 안 됨"), d(T("The lab's ethics credential is not on the ledger, so this cannot be approved.", "이 기관의 IRB 승인을 원장에서 확인할 수 없어 승인할 수 없어요."))) : null,
      card("", T("Requested contribution", "요청한 기여"),
        asks.map((i) => h("div", { class: "fg-decide" },
          h("div", {}, d(`${itemName(i.item)} · ${weeks(i.weeks)}`), d(`${SOURCE[i.source] || i.source} · ${T("health or biomedical research", "건강·의생명 연구")}`)),
          i.sensitive ? pill("danger", T("Separate approval", "따로 승인")) :
            h("button", { class: `fg-box${picked.has(i.item) ? " on" : ""}`, disabled: !open || !ethics, "aria-label": itemName(i.item),
              onclick: () => { picked.has(i.item) ? picked.delete(i.item) : picked.add(i.item); draw(); } }, picked.has(i.item) ? "✓" : ""))),
        h("div", { class: "fg-tags" },
          auto.length ? pill("ok", T("Inside your consent", "동의 범위 안")) : null,
          asks.length ? pill("warn", T("Needs your OK", "승인 필요")) : null),
        auto.length ? n(T(`${auto.map((i) => itemName(i.item)).join(", ")} is inside your consent; your agent sends it.`, `${auto.map((i) => itemName(i.item)).join(", ")}은 동의 범위 안이라 에이전트가 보내요.`)) : null,
        blocked.length ? n(T(`${blocked.map((i) => itemName(i.item)).join(", ")} is outside the allowed purpose and is not sent.`, `${blocked.map((i) => itemName(i.item)).join(", ")}은 허용한 목적 밖이라 보내지 않아요.`)) : null),
      card("brand", T("Participation payment", "참여 지급액"),
        d(`${won(price)} · ${testnet}`),
        row(T("Paid as weeks deliver (up to)", "회차 전달 시 지급 (최대)"), won(sp.now), "brand"),
        row(T(`${sp.days}-day review holdback`, `${sp.days}일 검토 후 지급`), won(sp.held), "warn"),
        r.completion_bonus_xrp ? row(T("Separate completion payment", "완료 시 별도 지급"), won(r.completion_bonus_xrp), "ok") : null),
      card("warn", T("Before you continue", "계속하기 전에"),
        d(T("A person makes the final review decision. You can respond by the stated deadline. Amounts already paid stay with you.",
          "검토 결정은 사람이 해요. 정해진 기한 안에 소명할 수 있어요. 이미 받은 금액은 그대로예요.")),
        ethics ? h("button", { class: "lk", onclick: () => { st.receipt = { kind: "credential", tx: ethics, title: T("Ethics credential", "IRB 자격 증명") }; draw(); } },
          `${T("Synthetic ethics credential", "합성 IRB 자격 증명")} · ${r.ethics_approval || ""} ↗`) : null),
    ];
    const act = open && ethics ? [
      btn(send.length ? T(`Review ${send.length} item${send.length > 1 ? "s" : ""}`, `${send.length}개 항목 검토`) : T("Choose items to send", "보낼 항목을 골라 주세요"),
        () => startFlow([{ r, send }]), { disabled: !send.length }),
      sub(T("Skip this round", "이번 회차 건너뛰기"), (e) => skip(e, r)),
    ] : null;
    return fig(T("Step 1 of 3", "1 / 3단계"), T("Participation request", "참여 요청"), body, act, { back: () => go("home"), gap11: true });
  }

  // ---------- passkey sheet (withdrawal) ----------
  function openSheet(spec) { st.sheet = { ...spec, phase: "review", error: null }; draw(); }
  function closeSheet() { if (st.sheet && st.sheet.phase !== "busy") { st.sheet = null; draw(); } }
  function revokeSheet() {
    const p = st.p;
    const locked = p.contributions.filter((c) => c.status === "escrowed");
    const kept = sum(p.contributions.filter((c) => c.status === "delivered"), (c) => c.amount_xrp);
    const r = p.requests[p.requests.length - 1];
    return {
      title: T("Withdraw study access", "열람 권한 철회"), danger: true,
      sub: T(`${r ? lab(r) : "The lab"} loses access and rounds not yet sent stop.`, `${r ? lab(r) : "연구 기관"}의 열람 권한을 회수하고, 아직 보내지 않은 회차를 멈춥니다.`),
      rows: [
        { icon: "unlock", label: T("Study access", "열람 권한"), value: T("Revoked on the ledger right away.", "원장에서 바로 회수합니다.") },
        locked.length ? { icon: "coin", label: T("Locked payments", "예치금"), value: T(`${won(sum(locked, (c) => c.amount_xrp))} for ${locked.length} undelivered round(s) returns to the study.`, `아직 전달 전인 ${locked.length}회차 ${won(sum(locked, (c) => c.amount_xrp))}는 연구로 돌아갑니다.`) } : null,
        { icon: "timer", label: T("Deletion", "삭제"), value: T("Eligible copies are requested for deletion; the study confirms separately. Retention exceptions may apply.", "삭제 가능한 사본의 삭제를 요청하고, 결과는 연구 기관이 따로 확인합니다. 보관 의무가 있는 자료는 남을 수 있습니다.") },
        { icon: "shield", label: T("Already paid", "받은 지급액"), value: T(`${won(kept)} stays with you.`, `이미 받은 ${won(kept)}는 그대로예요.`) },
      ].filter(Boolean),
      passkeyNote: T("Continuing opens this device's passkey prompt.", "계속하면 이 기기의 패스키(생체·PIN) 인증 창이 열립니다."),
      confirm: T("Withdraw with passkey", "철회하고 패스키로 인증"), cancel: T("Cancel", "취소"),
      sign: async () => {
        const ch = await api.revokeChallenge(pid);
        return api.revoke(pid, await signWithPasskey(ch.publicKey, pid));
      },
      unsigned: () => api.revoke(pid),
      done: (res) => { st.p = res; draw(); },
      cancelled: T("Cancelled. Nothing changed.", "철회를 취소했어요. 바뀐 것은 없어요."),
    };
  }

  async function confirmSheet() {
    const sh = st.sheet;
    const pk = st.p.passkey || { registered: false };
    sh.phase = "busy"; sh.error = null; draw();
    try {
      let res;
      if (!pk.registered && !passkeySupported()) res = await sh.unsigned();
      else {
        if (!pk.registered) {
          sh.step = T("Creating passkey", "패스키 만드는 중"); draw();
          const { publicKey } = await api.passkeyOptions(pid);
          const { prf, ...body } = await createPasskey(publicKey);
          await api.passkeyComplete(pid, body);
          st.p = { ...st.p, passkey: { ...pk, registered: true } };
        }
        sh.step = T("Verifying", "본인 확인 중"); draw();
        res = await sh.sign();
      }
      st.sheet = null;
      sh.done(res);
    } catch (err) {
      sh.phase = "review"; sh.step = null;
      sh.error = err && err.name === "NotAllowedError" ? sh.cancelled : T("Could not confirm. Nothing changed.", "확인하지 못했어요. 아무것도 바뀌지 않았어요.");
      draw();
    }
  }

  function sheetView() {
    const sh = st.sheet;
    const pk = st.p.passkey || { registered: false };
    const busyNow = sh.phase === "busy";
    const firstTime = !pk.registered && passkeySupported();
    return h("div", { class: "ar-sheet-wrap", onclick: (e) => { if (e.target === e.currentTarget) closeSheet(); } },
      h("div", { class: "ar-sheet", role: "dialog", "aria-modal": "true", "aria-label": sh.title },
        h("div", { class: "grab" }),
        h("h2", { class: "t" }, sh.title),
        h("p", { class: "sub" }, sh.sub),
        h("div", { class: "ar-disclose" }, sh.rows.map((x) => h("div", { class: "r" },
          h("span", { class: "ic" }, icon(x.icon, 20)),
          h("div", { class: "grow col", style: { gap: "2px", minWidth: 0 } }, h("span", { class: "l" }, x.label), h("div", { class: "v" }, x.value))))),
        h("div", { class: "ar-pkbox" }, h("span", { class: "ic" }, icon("fingerprint", 22)),
          h("span", {}, firstTime ? T("A passkey is created on this device first, then the passkey prompt opens.", "처음 한 번 이 기기에 패스키를 만든 뒤, 이어서 패스키(생체·PIN) 인증 창이 열립니다.") : sh.passkeyNote)),
        sh.error ? h("div", { role: "status", "aria-live": "polite" }, banner("red", sh.error)) : null,
        h("div", { class: "act" },
          h("button", { class: `ar-fill${sh.danger ? " danger" : ""}`, disabled: busyNow, onclick: confirmSheet },
            icon("unlock", 18), busyNow ? (sh.step || T("Confirming", "확인 중")) : sh.confirm),
          h("button", { class: "ar-text-btn", disabled: busyNow, onclick: closeSheet }, sh.cancel))));
  }

  // ---------- P2 consent by purpose ----------
  // One card per consent, per request. A card can be ticked only after its full text was read to the end.
  // Several requests: every card of every request must be read and ticked before Continue, then one passkey.
  const KIND = {
    research: [T("Study participation", "연구 참여"), (e) => [`${e.org} · ${e.purpose}`, T("Explanation, payment, withdrawal", "설명, 참여 지급, 철회")]],
    third_party: [T("Sharing with the study", "연구 기관에 제공"), (e) => [`${e.org} · ${T("selected items", "선택한 항목")}`, T("Deletion follows your request and applicable retention duties", "삭제는 요청과 법령상 보관 의무에 따라요")]],
    sensitive: [T("Sensitive health data", "민감정보(건강)"), (e) => [`${e.items} · ${e.wk}`, T(`Purpose: ${e.purpose} · kept until study end`, `목적: ${e.purpose} · 연구 종료까지 보관`)]],
    international: [T("Transfer abroad", "국외 이전"), () => [T("Planned for this study", "이 연구에 예정되어 있어요")]],
  };
  function startFlow(list) {
    const entries = list.map(({ r, send }) => {
      const price = cellPrice(r) * sum(send, (i) => i.weeks.length);
      return { r, send, price, pages: consentPages(r, send, price,
        { org: lab(r), purpose: purposeName(r.purpose), item: itemName, weeks }, KO ? "ko" : "en") };
    });
    const steps = entries.flatMap((e, n) => e.pages.map((p) => ({ e, n, p, key: `${e.r.id}:${p.kind}` })));
    st.flow = { entries, steps, open: null, read: new Set(), checked: new Set(), scroll: {}, phase: "read", error: null };
    go("consent", true);
  }
  function closeFlow() { if (st.flow && st.flow.phase !== "busy") { st.flow.open = null; draw(); } }

  function afterFlowDraw() {
    const f = st.flow;
    const box = root.querySelector(".ar-clause");
    if (!f || !f.open || !box) return;
    const key = f.open;
    box.scrollTop = f.scroll[key] || 0;
    const atEnd = () => box.scrollTop + box.clientHeight >= box.scrollHeight - 8;
    if (!f.read.has(key) && atEnd()) { f.read.add(key); requestAnimationFrame(draw); }
    box.addEventListener("scroll", () => {
      f.scroll[key] = box.scrollTop;
      if (!f.read.has(key) && atEnd()) { f.read.add(key); draw(); }
    }, { passive: true });
  }

  function consentView() {
    const f = st.flow;
    if (!f) return homeView();
    const all = f.steps.length;
    const done = f.steps.filter((s) => f.checked.has(s.key)).length;
    const cardFor = (s) => {
      const e = { org: lab(s.e.r), purpose: purposeName(s.e.r.purpose), items: s.e.send.map((i) => itemName(i.item)).join(", "), wk: weeks(s.e.send.flatMap((i) => i.weeks)) };
      const [title, lines] = KIND[s.p.kind] || [s.p.title, () => []];
      const read = f.read.has(s.key), on = f.checked.has(s.key);
      return h("div", { class: `fg-card${on ? " brand" : ""}` },
        h("p", { class: "t" }, title), lines(e).map((x) => d(x)),
        h("button", { class: "lk", onclick: () => { f.open = s.key; draw(); } }, read ? T("Read · open full text again →", "읽음 · 원문 다시 보기 →") : T("Read the full text →", "원문 끝까지 읽기 →")),
        h("div", { class: "fg-decide" },
          h("span", { class: `s${read ? "" : " off"}` }, on ? T("I agree · selected", "동의함 · 선택됨") : read ? T("Tick to agree", "체크해서 동의") : T("Read to the end to tick", "끝까지 읽으면 체크할 수 있어요")),
          h("button", { class: `fg-box${on ? " on" : ""}`, disabled: !read, "aria-label": title,
            onclick: () => { on ? f.checked.delete(s.key) : f.checked.add(s.key); draw(); } }, on ? "✓" : "")));
    };
    const naCard = (x) => (x.r.international_transfer && x.r.international_transfer.planned ? null
      : h("div", { class: "fg-card" }, h("p", { class: "t" }, T("Transfer abroad", "국외 이전")), d(T("Not planned for this study", "이 연구에는 예정이 없어요")),
        h("div", { class: "fg-decide" }, h("span", { class: "s off" }, T("Not applicable", "해당 없음")), h("span", { class: "fg-box", style: { cursor: "default" } }))));
    const body = [
      h1(T("Choose each purpose separately", "목적마다 따로 동의해 주세요")),
      lead(T("Nothing is selected for you. Read each consent to the end, then tick it.", "미리 선택된 것은 없어요. 동의서를 하나씩 끝까지 읽고 체크해 주세요.")),
      f.entries.map((x) => [
        f.entries.length > 1 ? h("p", { class: "fg-group" }, `${lab(x.r)} · ${won(x.price)}`) : null,
        f.steps.filter((s) => s.e === x).map(cardFor), naCard(x)]),
      card("", T(`Consent v${(st.p.consent && st.p.consent.version) || 1}`, `동의서 v${(st.p.consent && st.p.consent.version) || 1}`),
        d(T("Scope, recipient and purpose are recorded with your choice. Each consent is recorded separately, even with one passkey.",
          "범위, 받는 자, 목적이 선택과 함께 기록돼요. 패스키는 한 번이어도 동의는 하나씩 따로 기록돼요.")),
        n(T(`${done} of ${all} read and agreed`, `${all}개 중 ${done}개 읽고 동의함`))),
    ];
    const act = [btn(done === all ? T(`Continue with ${all} selected`, `${all}개 선택하고 계속`) : T(`Read and tick all ${all} to continue`, `${all}개를 모두 읽고 체크해 주세요`),
      () => go("preview", true), { disabled: done !== all }),
      sub(T("Back", "뒤로"), () => { st.flow = null; go(f.entries.length > 1 ? "home" : "request"); })];
    return fig(T("Step 2 of 3", "2 / 3단계"), T("Consent by purpose", "목적별 동의"), body, act,
      { back: () => { st.flow = null; go(f.entries.length > 1 ? "home" : "request"); }, gap11: true });
  }

  // full text reader: bottom sheet, one consent, must reach the end
  function flowView() {
    const f = st.flow;
    const s = f.steps.find((x) => x.key === f.open);
    const p = s.p;
    const read = f.read.has(s.key);
    return h("div", { class: "ar-sheet-wrap", onclick: (ev) => { if (ev.target === ev.currentTarget) closeFlow(); } },
      h("div", { class: "ar-flow", role: "dialog", "aria-modal": "true", "aria-label": p.title },
        h("div", { class: "grab" }),
        h("div", { class: "bar" }, h("span", { class: "title", style: { paddingLeft: "12px" } }, p.title),
          h("button", { class: "ar-iconbtn", style: { border: 0 }, onclick: closeFlow, "aria-label": T("Close", "닫기") }, icon("x"))),
        h("div", { class: "ar-flowstep" }, h("div", { class: "spread small" }, h("b", {}, lab(s.e.r)), h("span", { class: "muted" }, won(s.e.price)))),
        h("div", { class: "main" },
          h("div", { class: "ar-clause", tabindex: 0, "aria-label": p.title },
            h("p", { class: "basis" }, p.basis),
            p.sections.map(([hd, v]) => h("section", {}, h("h4", {}, hd), Array.isArray(v) ? v.map((x) => h("p", {}, x)) : h("p", {}, v))),
            h("p", { class: "end" }, T("— End —", "— 끝 —"))),
          !read ? h("p", { class: "tiny muted", style: { margin: "0", textAlign: "center" } }, T("Scroll to the end to agree.", "끝까지 읽으면 동의할 수 있어요.")) : null),
        h("div", { class: "foot" }, h("button", { class: "ar-fill", disabled: !read,
          onclick: () => { f.checked.add(s.key); f.open = null; draw(); } }, p.agree))));
  }

  // ---------- P3 preview, lock, delivered ----------
  function previewView() {
    const f = st.flow;
    if (!f) return homeView();
    const total = sum(f.entries, (x) => x.price);
    const r0 = f.entries[0].r;
    const sp = split(r0, total);
    const withheld = f.entries.flatMap((x) => x.r.items.filter((i) => i.class === "blocked" || (i.class === "approval" && !x.send.includes(i))));
    const body = [
      pill("brand", T("Ready to lock", "예치 준비됨")),
      h1(T("Check the contribution package", "보낼 내용을 확인해 주세요")),
      card("", T("Contribution preview", "기여 미리보기"),
        d(T("The package includes the selected items and a study pseudonym.", "선택한 항목과 연구용 가명만 들어가요.")),
        row(T("Study pseudonym", "연구용 가명"), st.p.person.study_pseudonym || pid, "brand"),
        f.entries.map((x) => row(`${lab(x.r)}`, `${x.send.map((i) => itemName(i.item)).join(", ")} · ${weeks(x.send.flatMap((i) => i.weeks))}`)),
        row(T("Purpose", "목적"), [...new Set(f.entries.map((x) => purposeName(x.r.purpose)))].join(", ")),
        row(T("Withheld", "보내지 않음"), withheld.length ? [...new Set(withheld.map((i) => itemName(i.item)))].join(", ") : T("None", "없음"), "neutral")),
      card("", T("Destination and access", "받는 곳과 접근"),
        d(`${[...new Set(f.entries.map((x) => lab(x.r)))].join(", ")} · ${T("approved study roles", "승인된 연구 담당자")}`),
        d(T("Access and retention follow the study protocol.", "접근과 보관은 연구 프로토콜을 따라요."))),
      card("brand", T("Payment locks before release", "보내기 전에 지급액을 먼저 예치해요"),
        d(`${won(total)} · ${testnet}`),
        n(T(`Up to ${won(sp.now)} is paid as weeks deliver. At least ${won(sp.held)} is reviewed for ${sp.days} days; a person decides and you may respond.`,
          `최대 ${won(sp.now)}는 회차가 전달될 때 지급돼요. 최소 ${won(sp.held)}는 ${sp.days}일 검토 뒤 지급되고, 결정은 사람이 하며 소명할 수 있어요.`)),
        n(T(`One passkey signature records each of the ${f.steps.length} consents separately.`, `패스키 서명 한 번으로 동의 ${f.steps.length}개가 각각 따로 기록돼요.`))),
      f.error ? card("danger", f.error) : null,
    ];
    const act = [btn(T("Lock payment and continue", "예치하고 계속"), signFlow), sub(T("Back", "뒤로"), () => go("consent", true))];
    return fig(T("Step 3 of 3", "3 / 3단계"), T("Review before sending", "보내기 전 확인"), body, act, { back: () => go("consent", true), gap11: true });
  }

  async function signFlow() {
    const f = st.flow;
    const pk = st.p.passkey || { registered: false };
    f.phase = "busy"; f.error = null; st.view = "status"; st.locking = true; draw();
    try {
      const entries = [];
      for (const x of f.entries) {
        entries.push({ request: x.r.id, items: x.send.map((i) => i.item),
          consents: await Promise.all(x.pages.map(async (p) => ({ kind: p.kind, text_hash: await textHash(p.text) }))) });
      }
      if (!pk.registered) {
        const { publicKey } = await api.passkeyOptions(pid);
        const { prf, ...body } = await createPasskey(publicKey);
        await api.passkeyComplete(pid, body);
        st.p = { ...st.p, passkey: { ...pk, registered: true } };
      }
      const ch = await api.consentChallenge(pid, entries);
      const res = await api.consentApprove(pid, entries, await signWithPasskey(ch.publicKey, pid));
      st.lastReqs = f.entries.map((x) => x.r.id);
      st.flow = null; st.batch.clear(); st.locking = false;
      st.p = res; st.lastBatch = res.signed_batch;
      go("status");
    } catch (err) {
      st.locking = false; f.phase = "read"; st.view = "preview";
      f.error = err && err.name === "NotAllowedError" ? T("Passkey cancelled. Nothing was sent.", "인증을 취소했어요. 아무것도 보내지 않았어요.") : T("Could not confirm. Nothing was sent.", "확인하지 못했어요. 아무것도 보내지 않았어요.");
      draw();
    }
  }

  async function skip(e, r) {
    const res = await busy(e.target, T("Working", "처리 중"), () => api.decline(pid, r.id), () => toast(T("Could not connect. Nothing changed.", "연결할 수 없어요. 바뀐 것은 없어요.")));
    if (res) { st.p = res; toast(T("Skipped this round. Nothing was sent.", "이번 회차를 건너뛰었어요. 아무것도 보내지 않았어요.")); go("home"); }
  }

  function statusView() {
    const p = st.p;
    if (st.locking) {
      const f = st.flow;
      const total = f ? sum(f.entries, (x) => x.price) : 0;
      const step = (mark, cls, label) => h("div", { class: cls }, h("i", { class: mark === "✓" ? "c-ok" : mark === "●" ? "c-brand" : "" }, mark), label);
      return fig(T("Payment first", "지급액 먼저"), T("Submission status", "전달 상태"), [
        pill("brand", T("Locked", "예치 중")),
        h1(T("Confirming the payment lock", "지급액 예치를 확인하고 있어요")),
        lead(T("No study access has been recorded yet. The contribution releases only after the lock is confirmed.", "아직 연구 기관의 열람은 기록되지 않았어요. 예치가 확인된 뒤에만 기록이 전달돼요.")),
        card("", T("Contribution state", "기여 상태"), d(T("Requested → Locked → Delivered", "요청 → 예치 → 전달")),
          h("div", { class: "fg-steps" }, step("✓", "", T("Requested", "요청")), step("●", "on", T("Locked", "예치")), step("○", "", T("Delivered", "전달")))),
        card("brand", T("Participation payment", "참여 지급액"), d(`${won(total)} · ${testnet}`),
          row(T("Status", "상태"), T("Confirming", "확인 중"), "brand"), row(T("Contribution access", "기록 열람"), T("Not released", "아직 안 열림"), "neutral")),
        card("brand", T("Confirming on XRPL Testnet", "XRPL Testnet에서 확인 중"), d(T("This usually completes shortly. Repeated taps cannot create another lock.", "보통 금방 끝나요. 여러 번 눌러도 예치가 또 생기지 않아요."))),
      ], [btn(T("Confirming…", "확인 중…"), null, { disabled: true }), sub(T("View reviewed terms", "확인한 조건 보기"), null)]);
    }
    const ids = new Set(st.lastReqs || p.approvals.map((a) => a.request));
    const cs = p.contributions.filter((c) => ids.has(c.request_id) || (p.approvals.find((a) => a.orders.some((o) => o.order_id === c.order_id) && ids.has(a.request))));
    const delivered = cs.filter((c) => c.status === "delivered");
    const reqs = p.requests.filter((r) => ids.has(r.id));
    const firstFinish = delivered.find((c) => c.finish && c.finish.tx);
    const allDone = cs.length && delivered.length === cs.length;
    const body = [
      allDone ? pill("ok", T("Delivered", "전달됨")) : pill("brand", T("Locked", "예치됨")),
      h1(allDone ? T("Contribution delivered", "기록이 전달됐어요") : T("Payment locked", "지급액이 예치됐어요")),
      lead(allDone ? T("Approved study roles can now access the delivered items under the protocol.", "승인된 연구 담당자가 프로토콜에 따라 전달된 항목을 볼 수 있어요.")
        : T("Each week is delivered after its lock is confirmed. Delivered weeks release their payment.", "회차마다 예치가 확인되면 전달되고, 전달되면 지급돼요.")),
      card(delivered.length ? "ok" : "brand", `${p.person.study_pseudonym || pid} · ${T("selected items", "선택한 항목")}`,
        d(T(`Dates shifted · sealed for ${reqs.map(lab).join(", ")}`, `날짜 이동 · ${reqs.map(lab).join(", ")}만 열 수 있게 봉인`))),
      cs.flatMap((c) => c.weeks.map((w) => h("div", { class: "fg-week" }, `${T("Week", "")} ${w}${KO ? "주 차" : ""}${cs.length > 1 && c.items ? ` · ${c.items.map(itemName).join(", ")}` : ""}`,
        h("span", { class: c.status === "delivered" ? "ok" : c.cancel && c.cancel.tx ? "gray" : "" },
          c.status === "delivered" ? T("Delivered", "전달됨") : c.cancel && c.cancel.tx ? T("Returned", "반환") : T("Locked", "예치됨"))))),
      card("", T("Payment evidence", "지급 증빙"),
        d(`${cs.length ? won(cs[0].amount_xrp) : ""} ${T("per delivered week", "회차당")} · ${testnet}`),
        ledger(firstFinish ? firstFinish.finish : cs[0] && cs[0].escrow, { kind: firstFinish ? "finish" : "escrow", amount: cs[0] && cs[0].amount_xrp, week: cs[0] && cs[0].weeks[0] })),
    ];
    return fig(allDone ? T("Contribution delivered", "기여 전달 완료") : T("Payment locked", "예치 완료"), T("Submission status", "전달 상태"), body,
      [btn(T("View payment timeline", "지급 내역 보기"), () => go("pay")), sub(T("Manage participation", "참여 관리"), () => go("stop"))], { back: () => go("home"), gap11: true });
  }

  // ---------- 내 데이터 ----------
  async function loadData() {
    try {
      st.data = await api.myData(pid);
    } catch (e) {
      st.data = e.status === 404 ? null : { error: true };
    }
    if (st.view === "data") draw();
  }
  function dataView() {
    const d = st.data;
    let body;
    if (d === undefined) body = [h("div", { class: "ar-skel", style: { height: "160px" } })];
    else if (d === null) body = [h("div", { class: "ar-card col" }, h("b", {}, "UniQdata 계정이 연결되지 않았어요"),
      h("p", { class: "small muted" }, "연결되면 여기에서 저장된 기록을 볼 수 있어요."))];
    else if (d.error) body = [banner("red", "불러오지 못했어요. ", h("button", { class: "ar-link", onclick: loadData }, "다시 시도"))];
    else {
      body = [
        h("div", { class: "ar-card col" },
          h("div", { class: "spread" }, h("b", {}, "UniQdata"), tag(d.connected ? "연결됨" : "연결 안 됨", d.connected ? "green" : "gray")),
          h("div", { class: "spread small" }, h("span", { class: "muted" }, "기록"), h("b", {}, `${d.records}건`)),
          d.period ? h("div", { class: "spread small" }, h("span", { class: "muted" }, "기간"), h("span", {}, `${d.period.from} – ${d.period.to}`)) : null,
          h("p", { class: "small muted" }, "승인하기 전에는 아무것도 공유되지 않아요.")),
        d.sources.map((s) => h("div", { class: "col", style: { gap: "8px" } },
          h("h3", {}, SOURCE[s.source] || s.source),
          s.items.length ? s.items.map((i) => h("div", { class: "ar-item row", style: { alignItems: "center" } },
            h("div", { class: "grow col", style: { gap: "2px" } }, h("b", {}, itemName(i.item)),
              h("span", { class: "small muted" }, `${weeks(i.weeks)} · ${i.records}건`))))
            : h("p", { class: "small muted" }, "아직 기록이 없어요."))),
      ];
    }
    const foot = d && !d.error && d.records === 0 ? [h("button", { class: "ar-btn primary block", onclick: async (e) => {
      const res = await busy(e.target, "가져오는 중", () => api.upload(pid), () => toast("가져오지 못했어요."));
      if (res) { st.data = res; toast(`${res.written}건을 UniQdata에 저장했어요.`); draw(); }
    } }, icon("upload", 16), " 기록 가져오기")] : null;
    return frame("내 데이터", body, foot, foot ? { back: () => go("home") } : {});
  }

  // ---------- 기록 ----------
  function recordView() {
    const p = st.p;
    const seg = (k, label) => h("button", { class: st.tab === k ? "on" : "", onclick: () => { st.tab = k; draw(); } }, label);
    const delivered = p.contributions.filter((c) => c.status === "delivered");
    let content;
    if (st.tab === "trade") {
      content = p.approvals.length ? p.approvals.slice().reverse().map((a) => h("div", { class: "ar-card col" },
        h("div", { class: "spread" }, h("b", {}, lab(p.requests.find((r) => r.id === a.request))), tag(a.status === "bound" ? "체결" : "처리 중", a.status === "bound" ? "green" : "blue")),
        h("dl", { class: "ar-kv left small" },
          h("dt", {}, "승인"), h("dd", {}, `${when(a.signed_at)} · 패스키`),
          h("dt", {}, "항목"), h("dd", {}, a.statement.items.map(itemName).join(", ")),
          h("dt", {}, "기간"), h("dd", {}, weeks(Object.keys(a.statement.weeks).map(Number))),
          h("dt", {}, "금액"), h("dd", {}, won(a.statement.price_drops / 1e6)),
          (a.statement.consents || []).length ? [h("dt", {}, "개별 동의"), h("dd", {}, a.statement.consents.map((c) => CONSENT[c.kind] || c.kind).join(" · "))] : null,
          h("dt", {}, "서명 해시"), h("dd", {}, h("span", { class: "ar-hash" }, short(a.statement_hash, 8, 6))),
          a.consent_hash ? [h("dt", {}, "UniQdata 동의"), h("dd", {}, h("span", { class: "ar-hash" }, short(a.consent_hash, 8, 6)))] : null),
        a.orders.map((o) => h("div", { class: "spread small" }, h("span", {}, `예치 · ${o.weeks.join(", ")}주 차`), txA(o.escrow)))))
        : h("p", { class: "muted small" }, "패스키로 승인한 거래가 여기에 남아요.");
    } else if (st.tab === "left") {
      content = delivered.length ? delivered.slice().reverse().map((c) => h("div", { class: "ar-card col" },
        h("div", { class: "spread" }, h("b", {}, `${c.weeks.join(", ")}주 차`), h("span", { class: "small" }, won(c.amount_xrp))),
        h("span", { class: "small" }, c.items.map(itemName).join(", ")),
        h("div", { class: "spread small" }, h("span", { class: "muted" }, "전달 · 지급"), txA(c.finish)),
        (st.from[c.order_id] || []).length ? h("span", { class: "tiny muted" }, `레코드 해시 ${st.from[c.order_id].map((x) => short(x, 6, 0)).join(" ")}`) : null))
        : h("p", { class: "muted small" }, "아직 전달된 데이터가 없어요.");
    } else if (st.tab === "share") {
      const hist = (p.consent ? p.consent.history : []).slice().reverse();
      const STATUS = { active: "허용", paused: "멈춤", revoked: "철회" };
      content = [
        hist.length ? h("div", { class: "ar-card ar-vline" }, hist.map((x) => h("div", { class: "e" },
          h("span", { class: `d ${x.status === "revoked" ? "gray" : x.status === "paused" ? "amber" : ""}` }),
          h("div", { class: "col", style: { gap: "2px" } }, h("span", {}, `동의 v${x.version} · ${STATUS[x.status] || x.status}`),
            h("span", { class: "ar-hash" }, short(x.doc_hash, 8, 6))),
          h("span", { class: "small muted" }, when(x.ts))))) : h("p", { class: "muted small" }, "공유 이력이 없어요."),
        p.withdrawals.length ? h("div", { class: "ar-card col small" }, p.withdrawals.map((x) => h("div", { class: "spread" },
          h("span", {}, { decline_round: "회차 건너뜀", pause: "새 요청 멈춤", revoke: "철회" }[x.kind] || x.kind), h("span", { class: "muted" }, when(x.ts))))) : null,
      ];
    } else {
      const runs = [];
      for (const e of p.audit.slice().reverse()) {
        const last = runs[runs.length - 1];
        if (last && last.kind === e.kind && !e.tx && !last.tx) { last.n += 1; last.prev_hash = e.prev_hash; }
        else runs.push({ ...e, n: 1 });
      }
      content = runs.length ? h("div", { class: "ar-card col ar-audit" }, runs.map((e) => h("div", { class: "row" },
        h("div", { class: "grow col", style: { gap: "2px" } },
          h("span", { class: "small" }, EVENT[e.kind] || e.kind, e.n > 1 ? h("span", { class: "muted" }, ` · ${e.n}건`) : null),
          h("span", { class: "ar-hash" }, `${short(e.hash, 8, 0)} ← ${short(e.prev_hash, 8, 0)}`)),
        h("div", { class: "col", style: { alignItems: "flex-end", gap: "2px" } }, h("span", { class: "tiny muted" }, when(e.ts)), txA(e.tx)))))
        : h("p", { class: "muted small" }, "기록이 없어요.");
    }
    const body = [
      h("div", { class: "ar-seg" }, seg("trade", "거래"), seg("left", "나간 데이터"), seg("share", "공유 이력"), seg("audit", "감사 기록")),
      st.tab === "audit" ? h("p", { class: "tiny muted" }, "각 기록은 앞 기록의 해시에 이어져 있어 바뀌면 알 수 있어요.") : null,
      content,
    ];
    return frame("기록", body);
  }

  // ---------- P4 payment timeline ----------
  function payView() {
    const p = st.p;
    const hbs = p.payout.holdbacks;
    const delivered = p.contributions.filter((c) => c.status === "delivered");
    const paid = sum(delivered, (c) => c.amount_xrp) + sum(hbs.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const held = hbs.filter((x) => x.kind === "round" && (x.status === "held" || x.status === "suspected"));
    const inReview = sum(held, (x) => x.amount_xrp);
    const roundPay = sum(p.contributions, (c) => c.amount_xrp) + sum(hbs.filter((x) => x.kind === "round"), (x) => x.amount_xrp);
    const bonus = sum(hbs.filter((x) => x.kind === "bonus"), (x) => x.amount_xrp);
    const openCase = p.payout.cases.find((c) => c.status === "suspected");
    if (openCase) return extendedView(openCase, paid, inReview);
    const lines = [];
    for (const c of p.contributions) {
      const w = `${KO ? `${c.weeks.join(", ")}주 차` : `Week ${c.weeks.join(", ")}`} · ${(c.items || []).map(itemName).join(", ")}`;
      if (c.status === "delivered") lines.push([w, T(`paid · +${won(c.amount_xrp)}`, `지급 · +${won(c.amount_xrp)}`), "", c.finish, "finish", c]);
      else if (c.cancel && c.cancel.tx) lines.push([w, T("returned to study", "연구로 반환"), "neutral", c.cancel, "cancel", c]);
      else lines.push([w, T(`locked · ${won(c.amount_xrp)}`, `예치 · ${won(c.amount_xrp)}`), "brand", c.escrow, "escrow", c]);
    }
    for (const x of hbs) {
      const label = x.kind === "bonus" ? T("Completion payment", "완료 지급") : T("Review part", "검토 후 지급분");
      const stt = x.status === "released" ? T("paid", "지급") : x.status === "returned" ? T("returned", "반환") : x.status === "withheld" ? T("not paid", "미지급") : T(`${(p.requests[0] && split(p.requests[0], 0).days) || 7}-day review`, "검토 중");
      lines.push([label, `${stt} · ${won(x.amount_xrp)}`, x.status === "released" ? "ok" : "warn", x.release || x.return || x.create, x.status === "released" ? "release" : "holdback", x]);
    }
    const lastHeld = held[0];
    const body = [
      inReview ? pill("brand", T("In review", "검토 중")) : paid ? pill("ok", T("Paid", "지급됨")) : pill("brand", T("Locked", "예치됨")),
      h1(T("Participation payment", "참여 지급")),
      card("brand", T(`${won(paid)} paid · ${won(inReview)} in review`, `${won(paid)} 지급 · ${won(inReview)} 검토 중`), d(testnet),
        row(T("Round payment", "회차 지급액"), won(roundPay), "brand"),
        bonus ? row(T("Separate completion payment", "완료 시 별도 지급"), won(bonus), "ok") : null),
      card("", T("Payment timeline", "지급 내역"),
        lines.length ? lines.map(([l, v, tone, tx, kind, src]) => h("div", { class: "fg-row", style: { cursor: tx && tx.tx ? "pointer" : "default" },
          onclick: () => { if (tx && tx.tx) { st.receipt = { kind, tx, amount: src.amount_xrp, week: src.weeks ? src.weeks[0] : null }; draw(); } } },
          h("span", { class: "l" }, l), h("span", { class: `v ${tone}` }, v))) : d(T("No payments yet.", "아직 지급 내역이 없어요."))),
      inReview ? card("warn", T(`${won(inReview)} held for review`, `${won(inReview)} 검토 중`),
        d(T("Paid by default after the review window. A person handles any exception; you can respond before a decision.", "검토 기간이 지나면 기본으로 지급돼요. 예외는 사람이 처리하고, 결정 전에 소명할 수 있어요.")),
        lastHeld ? ledger(lastHeld.create, { kind: "holdback", amount: lastHeld.amount_xrp }) : null) : null,
      h("p", { class: "fg-foot" }, T("Stopping does not take back amounts already paid. Review details stay off the public ledger.", "중단해도 이미 받은 금액은 돌려주지 않아요. 검토 내용은 공개 원장에 올라가지 않아요.")),
    ];
    const lastPaid = [...delivered].reverse().find((c) => c.finish && c.finish.tx);
    return fig(inReview ? T("Round complete", "회차 완료") : T("Payments", "지급"), T("Payment timeline", "지급 내역"), body,
      [btn(T("Back to contribution", "기여로 돌아가기"), () => go("home")),
        lastPaid ? sub(T("View receipt", "영수증 보기"), () => { st.receipt = { kind: "finish", tx: lastPaid.finish, amount: lastPaid.amount_xrp, week: lastPaid.weeks[0] }; draw(); }) : null],
      { back: () => go("home") });
  }

  function extendedView(c, paid, inReview) {
    return fig(T("Review extended", "검토 연장"), T("Payment timeline", "지급 내역"), [
      pill("warn", T("Review extended", "검토 연장")),
      h1(T("A clarification is needed", "확인이 필요해요")),
      card("warn", T(`${won(inReview)} remains in review`, `${won(inReview)} 검토 중`), d(testnet),
        row(T("Paid", "지급됨"), won(paid), "ok"), row(T("Pending review", "검토 대기"), won(inReview), "warn")),
      card("", T("What needs review", "확인이 필요한 부분"), signalLines(c),
        n(T("A person reviews this. Nothing is decided automatically.", "사람이 직접 검토해요. 자동으로 결정하지 않아요."), true)),
      card("brand", T("Response window", "소명 기간"), d(T(`Respond by ${md(c.respond_by)} · review ends ${md(c.review_ends || c.respond_by)}`, `${md(c.respond_by)}까지 소명 · ${md(c.review_ends || c.respond_by)} 검토 종료`)),
        n(T("This notice does not expand study access or change your consent choices.", "이 알림은 연구 범위를 넓히거나 동의를 바꾸지 않아요."))),
    ], [btn(T("Open review notice", "검토 알림 열기"), () => go("review")), sub(T("Contact study team", "연구팀에 문의"), () => toast(T("The study team was notified.", "연구팀에 알렸어요.")))], { back: () => go("home") });
  }
  const signalLines = (c) => (c.signals || []).map((s) => d(SIGNAL_TEXT(s)));
  const SIGNAL_TEXT = (s) => {
    const w = KO ? `${s.week}주 차` : `Week ${s.week}`;
    if (s.code === "same_as_previous" || /same|repeat|dup/i.test(s.code || "")) return T(`${w} ${itemName(s.item).toLowerCase()} response matches the week before.`, `${w} ${itemName(s.item)} 응답이 지난주와 같아요.`);
    if (/range|outlier|impossible/i.test(s.code || "")) return T(`${w} ${itemName(s.item).toLowerCase()} value is outside the expected range.`, `${w} ${itemName(s.item)} 값이 예상 범위를 벗어났어요.`);
    return T(`${w} ${itemName(s.item)} needs a check.`, `${w} ${itemName(s.item)} 확인이 필요해요.`);
  };

  // ---------- P5 manage participation ----------
  function stopView() {
    const p = st.p;
    const paused = p.consent && p.consent.status === "paused";
    const revoked = p.consent && p.consent.status === "revoked";
    const rv = [...p.withdrawals].reverse().find((x) => x.kind === "revoke");
    if (revoked && rv) return withdrawnView(rv);
    const nextOpen = openReqs()[0];
    const option = (tone, title, desc, go2, onclick) => h("button", { class: `fg-card ${tone}`, onclick },
      h("p", { class: "t" }, title), d(desc), h("p", { class: "go" }, go2));
    const body = [
      h1(T("Choose only the change you want", "원하는 변경만 골라 주세요")),
      lead(T("These controls have different effects. Each action asks for confirmation.", "세 가지는 효과가 서로 달라요. 어느 것이든 한 번 더 확인해요.")),
      option("", T("Skip this round", "이번 회차 건너뛰기"), T("This request only. Earlier contributions, consent history and payments stay.", "이번 요청만 보내지 않아요. 이전 기여, 동의 이력, 지급액은 그대로예요."),
        T("Skip this round →", "이번 회차 건너뛰기 →"), (e) => (nextOpen ? skip(e, nextOpen) : toast(T("There is no open request to skip.", "건너뛸 요청이 없어요.")))),
      option("brand", paused ? T("Resume future rounds", "새 요청 다시 받기") : T("Stop future rounds", "이후 요청 중단"),
        T("New requests stop. Submitted data and payments stay; you can resume.", "새 요청을 받지 않아요. 보낸 기록과 지급액은 그대로이고, 다시 받을 수 있어요."),
        paused ? T("Resume future rounds →", "다시 받기 →") : T("Stop future rounds →", "이후 요청 중단 →"), async (e) => {
          const res = await busy(e.currentTarget.querySelector(".go"), T("Working", "처리 중"), () => (paused ? api.resume(pid) : api.pause(pid)));
          if (res) { st.p = res; toast(paused ? T("New requests resume.", "새 요청을 다시 받아요.") : T("Future rounds stopped.", "새 요청을 멈췄어요.")); draw(); }
        }),
      option("danger", T("Withdraw study access", "열람 권한 철회"),
        T("Future access is revoked. Eligible copies are requested for deletion; the study confirms the outcome separately. Retention exceptions may apply.",
          "앞으로의 열람 권한을 회수해요. 삭제 가능한 사본의 삭제를 요청하고, 결과는 연구 기관이 따로 확인해요. 보관 의무가 있는 자료는 남을 수 있어요."),
        T("Review withdrawal →", "철회 내용 보기 →"), () => openSheet(revokeSheet())),
      card("", T("Payment stays separate", "지급은 따로예요"), d(T("Changing access does not automatically reverse a confirmed payment.", "열람 권한을 바꿔도 이미 확정된 지급은 되돌리지 않아요."))),
    ];
    return fig(T("Three separate choices", "세 가지 선택"), T("Manage participation", "참여 관리"), body,
      [btn(T("Back to contribution", "기여로 돌아가기"), () => go("home"), { secondary: true })], { back: () => go("home") });
  }

  function withdrawnView(rv) {
    const p = st.p;
    const kept = sum(p.contributions.filter((c) => c.status === "delivered"), (c) => c.amount_xrp)
      + sum(p.payout.holdbacks.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const due = sum(p.payout.holdbacks.filter((x) => x.kind === "round" && (x.status === "held" || x.status === "suspected")), (x) => x.amount_xrp);
    const returned = sum(p.contributions.filter((c) => c.cancel && c.cancel.tx), (c) => c.amount_xrp)
      + sum(p.payout.holdbacks.filter((x) => x.status === "returned"), (x) => x.amount_xrp);
    const dl = rv.deletion || {};
    const hist = (p.consent ? p.consent.history : []).slice().reverse();
    const ST = { active: T("Active", "허용"), paused: T("Paused", "멈춤"), revoked: T("Withdrawn", "철회") };
    const body = [
      pill("danger", T("Access revoked", "열람 권한 회수됨")),
      h1(T("Withdrawal recorded", "철회가 기록됐어요")),
      lead(T(`Future study access was revoked on ${md(rv.ts)}. Deletion and retention evidence are tracked separately.`, `${md(rv.ts)}에 열람 권한을 회수했어요. 삭제와 보관 증빙은 따로 확인해요.`)),
      card("", T("Withdrawal evidence", "철회 증빙"),
        h("div", { class: "fg-row", style: { cursor: rv.clawback ? "pointer" : "default" }, onclick: () => { if (rv.clawback) { st.receipt = { kind: "clawback", tx: rv.clawback }; draw(); } } },
          h("span", { class: "l" }, T("Access revoked", "열람 권한 회수")), h("span", { class: "v danger" }, rv.clawback ? T(`Confirmed ${md(rv.ts)}`, `${md(rv.ts)} 확인`) : T("Pending", "대기"))),
        row(T("Deletion requested", "삭제 요청"), T("Sent to the study", "연구 기관에 보냄"), "brand"),
        row(T("Deletion confirmed by the study", "연구 기관 삭제 확인"), dl.confirmation_hash ? `${dl.bundles ? `${dl.bundles} ${T("bundles", "묶음")} · ` : ""}${short(dl.confirmation_hash, 4, 0)}` : T("Waiting for the study", "기관 확인 대기"), dl.confirmation_hash ? "ok" : "neutral"),
        row(T("Retention exception", "보관 예외"), dl.retained ? dl.retained : T("None reported by the study", "기관이 보고한 예외 없음"), "neutral")),
      card("", T("Payment outcome", "지급 결과"), d(testnet),
        row(T("Already paid · stays with you", "이미 받음 · 그대로"), won(kept), "ok"),
        row(T("Still due after review", "검토 후 받을 금액"), won(due), "brand"),
        row(T("Returns to study", "연구로 반환"), won(returned), "warn")),
      hist.length ? card("", T("Consent history", "동의 이력"), hist.map((x) => d(`v${x.version} · ${ST[x.status] || x.status} ${md(x.ts)}`))) : null,
    ];
    return fig(`${pid} · ${T("separate branch", "별도 절차")}`, T("Withdrawal status", "철회 상태"), body,
      [btn(T("Back to contribution", "기여로 돌아가기"), () => go("home")), sub(T("View payment status", "지급 상태 보기"), () => go("pay"))], { back: () => go("home") });
  }

  // ---------- P6 review notice ----------
  function reviewView() {
    const p = st.p;
    const c = p.payout.cases.find((x) => x.status === "suspected") || p.payout.cases[p.payout.cases.length - 1];
    if (!c) return homeView();
    const hb = p.payout.holdbacks.find((x) => x.kind === "round" && x.request_id === c.request_id);
    const amt = hb ? won(hb.amount_xrp) : "";
    if (c.status === "cleared") {
      return fig(T("Closed", "종료"), T("Review notice", "검토 알림"), [
        pill("ok", T("Cleared", "확인 완료")),
        h1(T("Review cleared", "검토가 끝났어요")),
        lead(T("Your response was accepted. The held part is now paid.", "소명이 받아들여져 검토 후 지급분이 지급됐어요.")),
        card("ok", T(`${amt} paid`, `${amt} 지급`), d(testnet), hb ? ledger(hb.release || hb.create, { kind: "release", amount: hb.amount_xrp }) : null),
        card("", T("Review timeline", "검토 경과"),
          row(md(c.opened_at || c.ts), T("Review opened", "검토 시작")),
          c.response ? row(md(c.responded_at || c.ts), T("Response sent", "소명 보냄")) : null,
          row(md(c.decided_at || c.respond_by), T("Cleared · payment released", "확인 · 지급"), "ok")),
        card("", T("Consent unchanged", "동의는 그대로예요"), d(T("The review decision did not expand the study scope or change your consent history.", "검토 결정은 연구 범위를 넓히거나 동의 이력을 바꾸지 않았어요."))),
      ], [btn(T("View payment timeline", "지급 내역 보기"), () => go("pay")), sub(T("Back to contribution", "기여로 돌아가기"), () => go("home"))], { back: () => go("home") });
    }
    if (c.status === "confirmed") {
      return fig(T("Closed", "종료"), T("Review notice", "검토 알림"), [
        pill("danger", T("Not paid", "미지급")),
        h1(T("The held part is not paid", "검토 후 지급분은 지급되지 않아요")),
        lead(T("A person reviewed your response. Amounts already paid stay with you.", "사람이 소명을 검토했어요. 이미 받은 금액은 그대로예요.")),
        card("", T("What the reviewer saw", "검토 내용"), signalLines(c)),
      ], [btn(T("Back to contribution", "기여로 돌아가기"), () => go("home"))], { back: () => go("home") });
    }
    const text = h("textarea", { maxlength: 500, placeholder: T("Add context for the reviewer…", "검토 담당자에게 상황을 알려 주세요…") });
    return fig(T(`Respond by ${md(c.respond_by)}`, `${md(c.respond_by)}까지 소명`), T("Review notice", "검토 알림"), [
      pill("warn", T("Action needed", "확인 필요")),
      h1(T("Your held part needs review", "검토 후 지급분 확인이 필요해요")),
      card("warn", T(`${amt} remains in review`, `${amt} 검토 중`), d(testnet)),
      card("", T("What the reviewer saw", "검토 담당자가 본 내용"), signalLines(c), n(T("A person reviews this. Nothing is decided automatically.", "사람이 직접 검토해요. 자동으로 결정하지 않아요."), true)),
      c.response ? card("", T("Your response", "보낸 소명"), d(c.response)) :
        card("", T("Tell the reviewer what happened", "상황을 알려 주세요"), d(T("Your response is shared with the study reviewer only.", "소명은 검토 담당자에게만 전달돼요.")), text),
      card("brand", T("Possible outcomes", "결과"), d(T(`If cleared, ${amt} is paid. If not cleared after human review, the held part is not paid and new requests pause for 180 days. Amounts already paid stay.`,
        `확인되면 ${amt}가 지급돼요. 사람이 검토한 뒤에도 확인되지 않으면 검토 후 지급분은 지급되지 않고 180일 동안 새 요청이 멈춰요. 이미 받은 금액은 그대로예요.`))),
    ], [btn(T("Send response", "소명 보내기"), async (e) => {
      if (c.response) return;
      const res = await busy(e.target, T("Sending", "보내는 중"), () => api.respond(pid, c.id, text.value.trim()));
      if (res && res.ok) load(); else toast(T("Could not send.", "보내지 못했어요."));
    }, { disabled: !!c.response }), sub(T("Contact study team", "연구팀에 문의"), () => toast(T("The study team was notified.", "연구팀에 알렸어요.")))], { back: () => go("home") });
  }

  // ---------- R3-M ledger receipt (bottom sheet) ----------
  function receiptView() {
    const rc = st.receipt;
    const close = () => { st.receipt = null; draw(); };
    const KINDS = {
      finish: ["EscrowFinish", T("Payment released", "지급 완료"), T("payment unlocked", "예치 해제")],
      release: ["EscrowFinish", T("Payment released", "지급 완료"), T("review part paid", "검토 후 지급분 지급")],
      escrow: ["EscrowCreate", T("Payment locked", "지급액 예치"), T("locked until delivery", "전달될 때까지 잠금")],
      holdback: ["EscrowCreate", T("Review part locked", "검토 후 지급분 예치"), T(`paid after review`, "검토 뒤 지급")],
      cancel: ["EscrowCancel", T("Returned to study", "연구로 반환"), T("undelivered week", "전달되지 않은 회차")],
      clawback: ["Clawback", T("Access revoked", "열람 권한 회수"), T("study licence taken back", "연구 라이선스 회수")],
      credential: ["Credential", T("Ethics credential", "IRB 자격 증명"), T("issued by the ethics board", "윤리위원회 발급")],
    };
    const [txType, title, note] = KINDS[rc.kind] || ["Transaction", rc.title || "", ""];
    const money = rc.amount != null;
    const r0 = st.p.requests[0];
    return h("div", { class: "fg-scrim", onclick: (e) => { if (e.target === e.currentTarget) close(); } },
      h("div", { class: "fg-sheet", role: "dialog", "aria-modal": "true", "aria-label": title },
        h("div", { class: "grab" }),
        h("div", { class: "hd" }, h("div", { class: "copy", style: { display: "flex", flexDirection: "column", gap: "1px" } },
          h("span", { class: "eb" }, T("LEDGER RECEIPT", "원장 영수증")), h("span", { class: "tt" }, title)),
          h("button", { onclick: close, "aria-label": T("Close", "닫기") }, "×")),
        pill("ok", T("Confirmed on XRPL Testnet", "XRPL Testnet에서 확인됨")),
        h("div", { class: "fg-card ok fg-sheet-body", style: { borderWidth: "1px" } },
          h("p", { class: "t" }, rc.week ? T(`Week ${rc.week} participation payment`, `${rc.week}주 차 참여 지급`) : title),
          h("p", { class: "d" }, `${txType} · ${note}`),
          money ? row(T("Amount", "금액"), won(rc.amount), "ok") : null,
          h("p", { class: "x c-brand" }, testnet)),
        h("div", { class: "fg-card fg-sheet-body" }, h("p", { class: "t" }, T("On the ledger", "원장에 남은 것")),
          row(T("From", "보낸 곳"), rc.kind === "credential" ? "org_ethics" : r0 ? lab(r0) : "—"),
          row(T("To", "받는 곳"), short(st.p.person.address, 4, 3)),
          rc.tx.ts ? row(T("Time", "시간"), when(rc.tx.ts)) : null,
          row(T("Network", "네트워크"), "XRPL Testnet", "brand"),
          h("button", { class: "fg-ledger", style: { fontSize: "10px", color: "var(--uqd-text-primary)" },
            onclick: async () => { try { await navigator.clipboard.writeText(rc.tx.tx); toast(T("Hash copied", "해시를 복사했어요")); } catch (e) { /* clipboard blocked */ } } },
            `${T("Hash", "해시")} ${short(rc.tx.tx, 8, 4)} · ${T("Copy", "복사")}`)),
        h("div", { class: "fg-card fg-sheet-body" }, h("p", { class: "t" }, T("Kept off the ledger", "원장에 올리지 않은 것")),
          h("p", { class: "d" }, T("Participant items · consent contents · review result", "참여자 항목 · 동의 내용 · 검토 결과"))),
        rc.tx.url ? h("a", { class: "fg-btn", href: rc.tx.url, target: "_blank", rel: "noopener", style: { display: "grid", placeItems: "center" } }, T("Open in explorer ↗", "탐색기에서 보기 ↗"))
          : btn(T("Close", "닫기"), close, { secondary: true })));
  }

  function toast(text) {
    st.toast = text;
    draw();
    setTimeout(() => { if (st.toast === text) { st.toast = null; draw(); } }, 4000);
  }

  load();
  return { reload: load, stop: () => watcher.stop() };
}
