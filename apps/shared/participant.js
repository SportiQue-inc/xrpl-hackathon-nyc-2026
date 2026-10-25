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
const SOURCE = { wearable: "웨어러블", survey_app: "설문 앱", clinic_export: "진료 기록" };
const PURPOSE = { sleep_research: "수면 연구" };
const EVENT = {
  passkey_registered: "패스키 등록", passkey_signed: "패스키로 승인", approval_bound: "승인과 결제 연결",
  approve: "승인", decline: "이번 회차 건너뜀", consent: "동의 변경", ask_person: "본인 확인 요청",
  provide: "데이터 준비", escrowed: "참여 지급액 예치", paid: "전달 완료 · 지급", holdback: "검토 후 지급분 예치",
  bonus: "완료 보너스 예치", licence: "열람 권한 발급", revoked: "철회", paused: "새 요청 멈춤", resumed: "새 요청 다시 받기",
  swap: "지급 통화 변환", deposit_auth: "입금 보호 설정", uniqdata_upload: "UniQdata에 저장", uniqdata_read: "UniQdata에서 읽음",
  released: "검토 후 지급", returned: "연구로 반환", clawback: "열람 권한 회수",
};
const CONSENT = { research: "연구 참여", third_party: "제3자 제공", sensitive: "민감정보", international: "국외 이전" };
const itemName = (i) => ITEM[i] || i;
const won = (x) => `${(Math.round((x || 0) * 100) / 100).toFixed(2)} ${UNIT}`;
const weeks = (ws) => {
  const s = [...new Set(ws)].sort((a, b) => a - b);
  if (!s.length) return "";
  const runs = [];
  for (const w of s) {
    const last = runs[runs.length - 1];
    if (last && w === last[1] + 1) last[1] = w; else runs.push([w, w]);
  }
  return runs.map(([a, b]) => (a === b ? `${a}주 차` : `${a}–${b}주 차`)).join(", ");
};
const when = (ts) => (ts ? new Date(ts * 1000).toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "");

function txA(tx) {
  if (!tx || !tx.tx) return null;
  const label = `${short(tx.tx, 6, 4)}`;
  return tx.url ? h("a", { class: "ar-hash", href: tx.url, target: "_blank", rel: "noopener" }, label, " ", icon("ext", 12))
    : h("span", { class: "ar-hash" }, label);
}

export function mountParticipant(root, { base = "", pid = "P-017", embedded = false, token } = {}) {
  const api = engine(base, { token });
  const st = { p: null, view: "home", rid: null, picked: null, sheet: null, flow: null, batch: new Set(), error: null, toast: null,
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
    if ((!st.sheet || st.sheet.phase !== "busy") && !st.flow) { st.p = v; st.error = null; draw(); }
  });

  const go = (view) => { st.view = view; st.sheet = null; st.flow = null; draw(); window.scrollTo(0, 0); };
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
          tabBtn("home", "요청", "list"), tabBtn("data", "내 데이터", "data"), tabBtn("record", "기록", "history"),
          tabBtn("pay", "지급", "wallet")),
      st.sheet ? sheetView() : null,
      st.flow ? flowView() : null,
      st.toast && h("div", { class: "ar-toast" }, st.toast));
  }
  function tabBtn(view, label, ic) {
    const on = st.view === view || (view === "home" && ["request", "done", "stop", "review"].includes(st.view));
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
      out = v === "request" ? requestView() : v === "done" ? doneView() : v === "data" ? dataView()
        : v === "record" ? recordView() : v === "pay" ? payView() : v === "stop" ? stopView()
        : v === "review" ? reviewView() : homeView();
    }
    render(root, out);
    if (st.flow) afterFlowDraw();
  }

  // ---------- 요청 목록 ----------
  function homeView() {
    const p = st.p;
    const revoked = p.consent && p.consent.status === "revoked";
    const paused = p.consent && p.consent.status === "paused";
    const openCase = p.payout.cases.find((c) => c.status === "suspected");
    const pending = openReqs();
    const done = p.requests.filter((r) => !pending.includes(r)).slice().reverse();
    const card = (r) => {
      const asks = r.items.filter((i) => i.class === "approval");
      const sent = r.items.filter((i) => i.class === "auto");
      const state = r.status === "declined" ? tag("건너뜀", "gray") : r.status === "contributed" ? tag("승인함", "green")
        : tag("승인 대기", "amber");
      const pick = pending.includes(r) && defaultSend(r).length
        ? h("input", { type: "checkbox", class: "ar-pick", checked: st.batch.has(r.id), "aria-label": `${lab(r)} 선택`,
            onclick: (e) => e.stopPropagation(),
            onchange: (e) => { e.target.checked ? st.batch.add(r.id) : st.batch.delete(r.id); draw(); } }) : null;
      return h("div", { class: "ar-card col ar-req", role: "button", tabindex: 0,
          onclick: () => { st.rid = r.id; st.picked = null; go("request"); } },
        h("div", { class: "spread" }, h("div", { class: "row", style: { gap: "10px" } }, pick, h("b", {}, lab(r))), state),
        h("span", { class: "small" }, `${PURPOSE[r.purpose] || "연구"} · ${asks.map((i) => itemName(i.item)).join(", ") || "요청 항목 없음"}`),
        sent.length ? h("span", { class: "small muted" }, `${sent.map((i) => itemName(i.item)).join(", ")}은 동의 범위 안이라 에이전트가 보냈어요`) : null,
        h("span", { class: "small muted" }, `참여 지급액 최대 ${won(r.reward_xrp)}`));
    };
    const body = [
      revoked ? banner("gray", "이 연구에서 철회했어요.") : null,
      paused ? banner("amber", "새 요청을 멈춘 상태예요. ", h("button", { class: "ar-link", onclick: () => go("stop") }, "다시 받기")) : null,
      openCase ? h("button", { class: "ar-banner amber", style: { border: 0, textAlign: "left" }, onclick: () => go("review") },
        icon("clock", 16), h("span", {}, "검토 후 지급분 확인이 길어지고 있어요. 눌러서 확인해 주세요.")) : null,
      h("h3", {}, "승인 대기"),
      pending.length ? pending.map(card) : h("p", { class: "muted small" }, "지금 승인할 요청이 없어요. 동의 범위 밖의 요청이 오면 알려 드려요."),
      done.length ? [h("h3", {}, "지난 요청"), done.map(card)] : null,
      h("button", { class: "ar-row-link", onclick: () => go("stop") }, h("span", {}, "참여 중단 · 철회"), icon("chevron", 16)),
    ];
    const chosen = pending.filter((r) => st.batch.has(r.id));
    const foot = chosen.length ? [h("button", { class: "ar-btn primary block",
      onclick: () => startFlow(chosen.map((r) => ({ r, send: defaultSend(r) }))) },
      `선택한 ${chosen.length}건 동의서 보기 · ${won(sum(chosen, (r) => cellPrice(r) * sum(defaultSend(r), (i) => i.weeks.length)))}`)] : null;
    return frame("연구 참여", body, foot);
  }
  const defaultSend = (r) => r.items.filter((i) => i.class === "approval" && !i.sensitive);

  // ---------- 요청 상세와 승인 ----------
  function requestView() {
    const r = current();
    if (!r) return homeView();
    const open = r.status === "open" || r.status === "partly_open";
    if (!st.picked || st.picked.rid !== r.id) {
      st.picked = { rid: r.id, items: new Set(r.items.filter((i) => i.class === "approval" && !i.sensitive).map((i) => i.item)) };
    }
    const picked = st.picked.items;
    const asks = r.items.filter((i) => i.class === "approval");
    const blocked = r.items.filter((i) => i.class === "blocked");
    const credentialOk = r.institution.badges.some((b) => b.kind === "ethics_review" && b.on_ledger);
    const send = asks.filter((i) => picked.has(i.item));
    const price = cellPrice(r) * sum(send, (i) => i.weeks.length);
    const allWeeks = send.flatMap((i) => i.weeks);
    const pk = st.p.passkey || { registered: false };

    const head = h("div", { class: "ar-card col ar-statement" },
      h("div", { class: "spread" }, h("b", {}, lab(r)), credentialOk ? tag("IRB 승인 확인", "green") : tag("IRB 확인 안 됨", "red")),
      h("dl", { class: "ar-kv left" },
        h("dt", {}, "목적"), h("dd", {}, PURPOSE[r.purpose] || r.purpose),
        h("dt", {}, "기간"), h("dd", {}, weeks(asks.flatMap((i) => i.weeks)) || "—"),
        h("dt", {}, "참여 지급액"), h("dd", {}, `최대 ${won(r.reward_xrp)}`)));

    const items = asks.map((i) => h("label", { class: "ar-item row", style: { alignItems: "center" } },
      h("input", { type: "checkbox", checked: picked.has(i.item), disabled: !open || !credentialOk,
        onchange: (e) => { e.target.checked ? picked.add(i.item) : picked.delete(i.item); draw(); } }),
      h("div", { class: "grow col", style: { gap: "2px" } }, h("b", {}, itemName(i.item)),
        h("span", { class: "small muted" }, `${weeks(i.weeks)} · ${SOURCE[i.source] || i.source || ""}`)),
      i.sensitive ? tag("민감 정보", "red") : null));

    const body = [
      !credentialOk ? banner("red", "이 기관의 IRB 승인을 원장에서 확인할 수 없어 승인할 수 없어요.") : null,
      head,
      h("h3", {}, "보낼 항목"),
      items,
      blocked.length ? h("p", { class: "small muted" }, `${blocked.map((i) => itemName(i.item)).join(", ")}은 허용한 목적 밖이라 보내지 않아요.`) : null,
      h("button", { class: "ar-link small", style: { alignSelf: "flex-start" }, onclick: () => { st.details = !st.details; draw(); } },
        st.details ? "자세히 접기" : "자세히"),
      st.details ? h("div", { class: "ar-card col small" },
        h("p", {}, "연구 기관은 참여 번호와 승인한 항목만 받아요. 이름이나 연락처는 받지 않아요."),
        h("p", {}, "참여 지급액은 보내기 전에 원장에 예치되고, 데이터가 전달되면 지급돼요."),
        h("p", {}, "언제든 철회할 수 있어요. 철회하면 아직 전달되지 않은 회차는 멈추고 예치금은 연구로 돌아가요. 이미 받은 지급액은 그대로예요."),
        h("p", {}, r.international_transfer && r.international_transfer.planned ? "국외 이전이 예정되어 있어 별도 동의가 필요해요." : "국외 이전은 없어요."),
        h("p", { class: "muted" }, "접근 기록은 2년, 권한 변경 기록은 3년 보관해요.")) : null,
    ];
    let foot = null;
    if (open && credentialOk) {
      foot = [
        h("button", { class: "ar-btn primary block", disabled: !send.length, onclick: () => startFlow([{ r, send }]) },
          send.length ? `동의서 보기 · ${won(price)}` : "보낼 항목을 골라 주세요"),
        h("button", { class: "ar-btn block", onclick: (e) => skip(e, r) }, "이번 회차 건너뛰기"),
      ];
    }
    return frame(lab(r), body, foot, { back: () => go("home") });
  }

  // ---------- 동의 시트: 서명이 필요한 곳은 모두 이 시트 하나로 확인합니다 ----------
  // 승인, 민감 정보 동의, 철회, 패스키 만들기. 패스키가 없으면 같은 시트에서 먼저 만들고 이어서 서명해요.
  function openSheet(spec) { st.sheet = { ...spec, phase: "review", error: null }; draw(); }
  function closeSheet() { if (st.sheet && st.sheet.phase !== "busy") { st.sheet = null; draw(); } }

  // 시트 모양과 문구는 UniQdata 앱의 동의·패스키 시트를 따릅니다(/mnt/project-files/uniqdata-consent-sheet.md):
  // 핸들, 제목, 부제, 공시 카드(아이콘 + 라벨 + 값), 패스키 안내 박스, 전체 폭 버튼 두 개.
  function revokeSheet() {
    const p = st.p;
    const locked = p.contributions.filter((c) => c.status === "escrowed");
    const kept = sum(p.contributions.filter((c) => c.status === "delivered"), (c) => c.amount_xrp);
    const r = p.requests[p.requests.length - 1];
    return {
      title: "연구 참여 철회", danger: true,
      sub: `${r ? lab(r) : "연구 기관"}의 열람 권한을 회수하고, 아직 보내지 않은 회차를 멈춥니다.`,
      rows: [
        { icon: "unlock", label: "열람 권한", value: "원장에서 바로 회수합니다." },
        locked.length ? { icon: "coin", label: "예치금", value: `아직 전달 전인 ${locked.length}회차 ${won(sum(locked, (c) => c.amount_xrp))}는 연구로 돌아갑니다.` } : null,
        { icon: "timer", label: "보관·삭제", value: "연구 기관은 개인 단위 사본을 지우고 확인해야 합니다. 이미 만들어진 집계 통계만 남습니다." },
        { icon: "shield", label: "받은 지급액", value: `이미 받은 ${won(kept)}는 그대로예요.` },
        { icon: "ban", label: "다시 참여하려면", value: "새로 동의해야 합니다." },
      ].filter(Boolean),
      passkeyNote: "계속하면 이 기기의 패스키(생체·PIN) 인증 창이 열립니다.",
      confirm: "철회하고 패스키로 인증", cancel: "취소",
      sign: async () => {
        const ch = await api.revokeChallenge(pid);
        return api.revoke(pid, await signWithPasskey(ch.publicKey, pid));
      },
      unsigned: () => api.revoke(pid),
      done: (res) => { st.p = res; draw(); },
      cancelled: "철회를 취소했어요. 바뀐 것은 없어요.",
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
          sh.step = "패스키 만드는 중";
          draw();
          const { publicKey } = await api.passkeyOptions(pid);
          const { prf, ...body } = await createPasskey(publicKey);
          await api.passkeyComplete(pid, body);
          st.p = { ...st.p, passkey: { ...pk, registered: true } };
        }
        sh.step = "본인 확인 중";
        draw();
        res = await sh.sign();
      }
      st.sheet = null;
      sh.done(res);
    } catch (err) {
      sh.phase = "review"; sh.step = null;
      sh.error = err && err.name === "NotAllowedError" ? sh.cancelled : "확인하지 못했어요. 아무것도 바뀌지 않았어요.";
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
          h("span", {}, firstTime ? "처음 한 번 이 기기에 패스키를 만든 뒤, 이어서 패스키(생체·PIN) 인증 창이 열립니다." : sh.passkeyNote)),
        sh.error ? h("div", { role: "status", "aria-live": "polite" }, banner("red", sh.error)) : null,
        h("div", { class: "act" },
          h("button", { class: `ar-fill${sh.danger ? " danger" : ""}`, disabled: busyNow, onclick: confirmSheet },
            icon("unlock", 18), busyNow ? (sh.step || "확인 중") : sh.confirm),
          h("button", { class: "ar-text-btn", disabled: busyNow, onclick: closeSheet }, sh.cancel || "취소"))));
  }

  // ---------- 동의서: 금액·기간·기관·항목은 위에 고정, 조항은 한 장씩 끝까지 읽어야 체크돼요 ----------
  // 여러 건을 골라도 장은 요청마다, 동의마다 따로 넘기고, 패스키 서명은 마지막에 한 번만 해요.
  function startFlow(list) {
    const entries = list.map(({ r, send }) => {
      const price = cellPrice(r) * sum(send, (i) => i.weeks.length);
      return { r, send, price, pages: consentPages(r, send, price,
        { org: lab(r), purpose: PURPOSE[r.purpose] || r.purpose, item: itemName, weeks }) };
    });
    const steps = entries.flatMap((e, n) => e.pages.map((p) => ({ e, n, p, key: `${e.r.id}:${p.kind}` })));
    st.flow = { entries, steps, idx: 0, read: new Set(), checked: new Set(), scroll: {}, phase: "read", error: null };
    draw();
  }
  function closeFlow() { if (st.flow && st.flow.phase !== "busy") { st.flow = null; draw(); } }

  function afterFlowDraw() {
    const f = st.flow;
    const box = root.querySelector(".ar-clause:not(.signing)");
    if (!box || f.idx >= f.steps.length) return;
    const step = f.steps[f.idx];
    box.scrollTop = f.scroll[step.key] || 0;
    const atEnd = () => box.scrollTop + box.clientHeight >= box.scrollHeight - 8;
    if (!f.read.has(step.key) && atEnd()) { f.read.add(step.key); requestAnimationFrame(draw); }
    box.addEventListener("scroll", () => {
      f.scroll[step.key] = box.scrollTop;
      if (!f.read.has(step.key) && atEnd()) { f.read.add(step.key); draw(); }
    }, { passive: true });
  }

  function flowView() {
    const f = st.flow;
    const signing = f.idx >= f.steps.length;
    const step = signing ? null : f.steps[f.idx];
    const e = signing ? null : step.e;
    const total = sum(f.entries, (x) => x.price);
    const back = () => { if (f.phase === "busy") return; if (f.idx === 0) closeFlow(); else { f.idx -= 1; draw(); } };

    const pin = signing
      ? h("div", { class: "ar-pin" },
          h("div", { class: "spread" }, h("span", { class: "small muted" }, `${f.entries.length}건 · 동의 ${f.steps.length}개`),
            h("span", { class: "small muted" }, "참여 지급액 합계")),
          h("div", { class: "spread" }, h("b", { class: "org" }, f.entries.map((x) => lab(x.r)).filter((v, i, a) => a.indexOf(v) === i).join(", ")),
            h("b", { class: "amt" }, won(total))))
      : h("div", { class: "ar-pin" },
          f.entries.length > 1 ? h("div", { class: "spread small muted" }, h("span", {}, `${f.entries.length}건 중 ${step.n + 1}번째`),
            h("span", {}, `합계 ${won(total)}`)) : null,
          h("div", { class: "spread" }, h("b", { class: "org" }, lab(e.r)), tag("IRB 승인 확인", "green")),
          h("div", { class: "spread", style: { alignItems: "flex-end" } },
            h("div", { class: "col", style: { gap: "2px" } }, h("span", { class: "small muted" }, "참여 지급액"),
              h("b", { class: "amt" }, won(e.price))),
            h("span", { class: "small muted", style: { textAlign: "right" } },
              `전달 시 ${e.r.payment.immediate_pct}% · 검토 후 ${e.r.payment.held_pct}%`)),
          h("dl", { class: "ar-kv left small" },
            h("dt", {}, "기간"), h("dd", {}, weeks(e.send.flatMap((i) => i.weeks))),
            h("dt", {}, "항목"), h("dd", {}, e.send.map((i) => itemName(i.item)).join(", ")),
            h("dt", {}, "목적"), h("dd", {}, PURPOSE[e.r.purpose] || e.r.purpose)));

    const progress = h("div", { class: "ar-flowstep" },
      h("div", { class: "track" }, h("span", { style: { width: `${Math.round(100 * Math.min(f.idx, f.steps.length) / f.steps.length)}%` } })),
      h("div", { class: "spread small" },
        h("b", {}, signing ? "서명" : step.p.title),
        h("span", { class: "muted" }, signing ? `${f.steps.length}/${f.steps.length} 확인` : `${f.idx + 1} / ${f.steps.length}`)));

    let main, foot;
    if (!signing) {
      const p = step.p;
      const read = f.read.has(step.key);
      const checked = f.checked.has(step.key);
      main = [
        h("div", { class: "ar-clause", tabindex: 0, "aria-label": p.title },
          h("p", { class: "basis" }, p.basis),
          p.sections.map(([hd, v]) => h("section", {}, h("h4", {}, hd),
            Array.isArray(v) ? v.map((x) => h("p", {}, x)) : h("p", {}, v))),
          h("p", { class: "end" }, "— 끝 —")),
        h("label", { class: `ar-agree${read ? "" : " locked"}` },
          h("input", { type: "checkbox", checked, disabled: !read,
            onchange: (ev) => { ev.target.checked ? f.checked.add(step.key) : f.checked.delete(step.key); draw(); } }),
          h("span", {}, p.agree, h("span", { class: "req" }, " (필수)"))),
        !read ? h("p", { class: "tiny muted", style: { margin: "0", textAlign: "center" } }, "끝까지 읽으면 체크할 수 있어요.") : null,
      ];
      foot = [h("button", { class: "ar-fill", disabled: !checked, onclick: () => { f.idx += 1; draw(); } },
        f.idx + 1 === f.steps.length ? "서명으로" : "다음")];
    } else {
      const pk = st.p.passkey || { registered: false };
      main = [h("div", { class: "ar-clause signing" },
        f.entries.map((x) => h("div", { class: "ar-signlist" },
          h("div", { class: "spread" }, h("b", {}, lab(x.r)), h("b", {}, won(x.price))),
          h("span", { class: "small muted" }, `${x.send.map((i) => itemName(i.item)).join(", ")} · ${weeks(x.send.flatMap((i) => i.weeks))}`),
          x.pages.map((p) => h("div", { class: "row small" }, h("span", { class: "ok" }, icon("check", 14)), h("span", {}, p.title))))),
        h("div", { class: "ar-pkbox" }, h("span", { class: "ic" }, icon("fingerprint", 22)),
          h("span", {}, `패스키 서명 한 번으로 체크한 동의 ${f.steps.length}개가 각각 따로 기록됩니다. `,
            !pk.registered && passkeySupported() ? "처음 한 번 이 기기에 패스키를 만든 뒤 인증 창이 열립니다." : "계속하면 이 기기의 패스키(생체·PIN) 인증 창이 열립니다.")),
        f.error ? banner("red", f.error) : null)];
      foot = [h("button", { class: "ar-fill", disabled: f.phase === "busy", onclick: signFlow },
        icon("unlock", 18), f.phase === "busy" ? (f.step || "확인 중") : "동의하고 패스키로 인증")];
    }
    return h("div", { class: "ar-sheet-wrap", onclick: (ev) => { if (ev.target === ev.currentTarget) closeFlow(); } },
      h("div", { class: "ar-flow", role: "dialog", "aria-modal": "true", "aria-label": "연구 참여 동의서" },
      h("div", { class: "grab" }),
      h("div", { class: "bar" },
        h("button", { class: "ar-iconbtn", style: { border: 0 }, onclick: back, "aria-label": "이전" }, icon("back")),
        h("span", { class: "title" }, "연구 참여 동의서"),
        h("button", { class: "ar-iconbtn", style: { border: 0 }, onclick: closeFlow, "aria-label": "닫기" }, icon("x"))),
      pin, progress,
      h("div", { class: "main" }, main),
      h("div", { class: "foot" }, foot)));
  }

  async function signFlow() {
    const f = st.flow;
    const pk = st.p.passkey || { registered: false };
    f.phase = "busy"; f.error = null; draw();
    try {
      const entries = [];
      for (const x of f.entries) {
        entries.push({ request: x.r.id, items: x.send.map((i) => i.item),
          consents: await Promise.all(x.pages.map(async (p) => ({ kind: p.kind, text_hash: await textHash(p.text) }))) });
      }
      if (!pk.registered) {
        f.step = "패스키 만드는 중"; draw();
        const { publicKey } = await api.passkeyOptions(pid);
        const { prf, ...body } = await createPasskey(publicKey);
        await api.passkeyComplete(pid, body);
        st.p = { ...st.p, passkey: { ...pk, registered: true } };
      }
      f.step = "본인 확인 중"; draw();
      const ch = await api.consentChallenge(pid, entries);
      const res = await api.consentApprove(pid, entries, await signWithPasskey(ch.publicKey, pid));
      st.flow = null; st.batch.clear();
      st.p = res; st.lastBatch = res.signed_batch;
      go("done");
    } catch (err) {
      f.phase = "read"; f.step = null;
      f.error = err && err.name === "NotAllowedError" ? "인증을 취소했어요. 아무것도 보내지 않았어요." : "확인하지 못했어요. 아무것도 보내지 않았어요.";
      draw();
    }
  }

  async function skip(e, r) {
    const res = await busy(e.target, "처리 중", () => api.decline(pid, r.id), () => toast("연결할 수 없어요. 바뀐 것은 없어요."));
    if (res) { st.p = res; toast("이번 회차를 건너뛰었어요. 아무것도 보내지 않았어요."); go("home"); }
  }

  // ---------- 승인 완료 ----------
  function doneView() {
    const hashes = new Set((st.lastBatch || []).map((x) => x.statement_hash));
    const list = st.p.approvals.filter((x) => hashes.has(x.statement_hash));
    if (!list.length && st.p.approvals.length) list.push(st.p.approvals[st.p.approvals.length - 1]);
    if (!list.length) return homeView();
    if (list.length > 1) return doneMany(list);
    const a = list[0];
    const r = st.p.requests.find((x) => x.id === a.request);
    const body = [
      h("div", { class: "ar-card col", style: { alignItems: "center", textAlign: "center", padding: "28px 16px" } },
        h("span", { class: "ar-okmark" }, icon("check", 28)),
        h("h2", {}, "동의했어요"),
        h("p", { class: "small muted" }, `${lab(r)}에 ${a.statement.items.map(itemName).join(", ")} · ${weeks(Object.keys(a.statement.weeks).map(Number))}`)),
      h("div", { class: "ar-card col" },
        h("div", { class: "spread" }, h("span", { class: "small muted" }, "참여 지급액 예치"), h("b", {}, won(a.statement.price_drops / 1e6))),
        a.orders.map((o) => h("div", { class: "spread small" }, h("span", {}, `${o.weeks.join(", ")}주 차 · ${o.items.map(itemName).join(", ")}`), txA(o.escrow)))),
      h("button", { class: "ar-btn block", onclick: () => { st.tab = "trade"; go("record"); } }, "기록에서 보기"),
    ];
    return frame("동의 완료", body, null, { back: () => go("home") });
  }

  function doneMany(list) {
    const reqName = (a) => lab(st.p.requests.find((r) => r.id === a.request));
    const body = [
      h("div", { class: "ar-card col", style: { alignItems: "center", textAlign: "center", padding: "28px 16px" } },
        h("span", { class: "ar-okmark" }, icon("check", 28)),
        h("h2", {}, `${list.length}건에 동의했어요`),
        h("p", { class: "small muted" }, "패스키 서명 한 번으로, 요청마다 동의가 따로 기록됐어요.")),
      list.map((a) => h("div", { class: "ar-card col" },
        h("div", { class: "spread" }, h("b", {}, reqName(a)), h("b", {}, won(a.statement.price_drops / 1e6))),
        h("span", { class: "small muted" }, `${a.statement.items.map(itemName).join(", ")} · 동의 ${(a.statement.consents || []).length}개`),
        a.orders.map((o) => h("div", { class: "spread small" }, h("span", {}, `${o.weeks.join(", ")}주 차 예치`), txA(o.escrow))))),
      h("button", { class: "ar-btn block", onclick: () => { st.tab = "trade"; go("record"); } }, "기록에서 보기"),
    ];
    return frame("동의 완료", body, null, { back: () => go("home") });
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

  // ---------- 지급 ----------
  function payView() {
    const p = st.p;
    const hbs = p.payout.holdbacks;
    const delivered = p.contributions.filter((c) => c.status === "delivered");
    const paid = sum(delivered, (c) => c.amount_xrp) + sum(hbs.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const inReview = sum(hbs.filter((x) => x.kind === "round" && (x.status === "held" || x.status === "suspected")), (x) => x.amount_xrp);
    const locked = sum(p.contributions.filter((c) => c.status === "escrowed"), (c) => c.amount_xrp);
    const rows = [];
    for (const c of p.contributions) {
      const w = `${c.weeks.join(", ")}주 차`;
      if (c.status === "delivered") rows.push([c.order_id, `${w} 지급`, `+${won(c.amount_xrp)}`, "", c.finish]);
      else if (c.cancel && c.cancel.tx) rows.push([c.order_id, `${w} 연구로 반환`, won(c.amount_xrp), "gray", c.cancel]);
      else rows.push([c.order_id, `${w} 예치`, won(c.amount_xrp), "blue", c.escrow]);
    }
    for (const x of hbs) {
      const label = x.kind === "bonus" ? "완료 보너스" : "검토 후 지급분";
      const stt = x.status === "released" ? "지급" : x.status === "returned" ? "반환" : x.status === "withheld" ? "미지급" : "검토 중";
      rows.push([1e6 + x.id, `${label} · ${stt}`, `${x.status === "released" ? "+" : ""}${won(x.amount_xrp)}`,
        x.status === "released" ? "" : "blue", x.release || x.return || x.create]);
    }
    rows.sort((a, b) => b[0] - a[0]);
    const kpi = (label, v) => h("div", { class: "col", style: { gap: "2px" } }, h("span", { class: "small muted" }, label), h("b", {}, won(v)));
    const body = [
      h("div", { class: "ar-card ar-grid k3" }, kpi("받음", paid), kpi("검토 중", inReview), kpi("예치됨", locked)),
      h("p", { class: "small muted" }, "회차마다 전달되면 80%를 바로 받고, 20%는 짧은 검토 뒤에 받아요. 중단해도 받은 금액은 그대로예요."),
      rows.length ? h("div", { class: "ar-card ar-vline" }, rows.map(([, l, a, tone, t]) => h("div", { class: "e" },
        h("span", { class: `d ${tone}` }), h("div", { class: "col", style: { gap: "2px" } }, h("span", {}, l), txA(t)), h("b", {}, a))))
        : h("p", { class: "muted small" }, "아직 지급 내역이 없어요."),
    ];
    return frame("참여 지급", body);
  }

  // ---------- 중단 · 철회 ----------
  function stopView() {
    const p = st.p;
    const paused = p.consent && p.consent.status === "paused";
    const revoked = p.consent && p.consent.status === "revoked";
    const rv = [...p.withdrawals].reverse().find((x) => x.kind === "revoke");
    if (revoked && rv) return withdrawnView(rv);
    const option = (title, desc, btn) => h("div", { class: "ar-card col" }, h("b", {}, title), h("span", { class: "small muted" }, desc), btn);
    const body = [
      option(paused ? "새 요청 다시 받기" : "새 요청 멈추기", "이미 보낸 데이터와 받은 지급액은 그대로예요. 언제든 다시 받을 수 있어요.",
        h("button", { class: "ar-btn", onclick: async (e) => {
          const res = await busy(e.target, "처리 중", () => (paused ? api.resume(pid) : api.pause(pid)));
          if (res) { st.p = res; toast(paused ? "새 요청을 다시 받아요." : "새 요청을 멈췄어요."); draw(); }
        } }, paused ? "다시 받기" : "멈추기")),
      option("이 연구에서 철회", "연구 기관의 열람 권한을 원장에서 회수하고, 아직 전달되지 않은 회차는 멈춰요. 이미 받은 지급액은 그대로예요.",
        h("button", { class: "ar-btn danger", onclick: () => openSheet(revokeSheet()) }, "철회")),
    ];
    return frame("참여 중단 · 철회", body, null, { back: () => go("home") });
  }

  function withdrawnView(rv) {
    const p = st.p;
    const kept = sum(p.contributions.filter((c) => c.status === "delivered"), (c) => c.amount_xrp)
      + sum(p.payout.holdbacks.filter((x) => x.status === "released"), (x) => x.amount_xrp);
    const refunded = p.contributions.filter((c) => c.cancel && c.cancel.tx);
    const d = rv.deletion || {};
    const check = (ok, text, extra) => h("div", { class: "ar-check" }, h("span", { class: `ic ${ok ? "ok" : "wait"}` }, icon(ok ? "check" : "clock", 12)),
      h("span", { class: "grow small" }, text), extra);
    const body = [
      banner("green", icon("check", 16), "철회했어요."),
      h("div", { class: "ar-card" },
        check(!!rv.clawback, "열람 권한 회수", rv.clawback ? txA(rv.clawback) : null),
        refunded.map((c) => check(true, `${c.weeks.join(", ")}주 차 예치금 연구로 반환`, txA(c.cancel))),
        check(!!d.confirmation_hash, `연구 기관 삭제 확인${d.confirmation_hash ? ` · ${short(d.confirmation_hash, 6, 0)}` : ""}`)),
      h("p", { class: "small" }, `이미 받은 ${won(kept)}는 그대로예요.`),
    ];
    return frame("철회 완료", body, null, { back: () => go("home") });
  }

  // ---------- 검토 알림 ----------
  function reviewView() {
    const p = st.p;
    const c = p.payout.cases.find((x) => x.status === "suspected") || p.payout.cases[p.payout.cases.length - 1];
    if (!c) return homeView();
    const hb = p.payout.holdbacks.find((x) => x.kind === "round" && x.request_id === c.request_id);
    const text = h("textarea", { class: "ar-textarea", maxlength: 500, placeholder: "검토 담당자에게 상황을 알려 주세요" });
    const closed = c.status === "cleared" || c.status === "confirmed";
    const body = [
      c.status === "cleared" ? banner("green", "검토가 끝나 지급됐어요.")
        : c.status === "confirmed" ? banner("gray", "검토 결과 검토 후 지급분은 지급되지 않아요. 이미 받은 금액은 그대로예요.")
        : banner("amber", `검토 후 지급분 ${hb ? won(hb.amount_xrp) : ""} 확인이 길어지고 있어요.`),
      h("div", { class: "ar-card col" }, h("b", {}, "확인이 필요한 부분"),
        c.signals.map((s) => h("span", { class: "small" }, `${s.week}주 차 ${itemName(s.item)}`)),
        h("span", { class: "tiny muted" }, "사람이 직접 검토해요. 자동으로 결정하지 않아요.")),
      !closed ? (c.response ? h("div", { class: "ar-card small" }, c.response)
        : h("div", { class: "col", style: { gap: "8px" } }, text, h("button", { class: "ar-btn primary", onclick: async (e) => {
          const res = await busy(e.target, "보내는 중", () => api.respond(pid, c.id, text.value.trim()));
          if (res && res.ok) load(); else toast("보내지 못했어요.");
        } }, "보내기"))) : null,
    ];
    return frame("검토 알림", body, null, { back: () => go("home") });
  }

  function toast(text) {
    st.toast = text;
    draw();
    setTimeout(() => { if (st.toast === text) { st.toast = null; draw(); } }, 4000);
  }

  load();
  return { reload: load, stop: () => watcher.stop() };
}
