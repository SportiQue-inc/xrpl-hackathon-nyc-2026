// 참여자 앱: 연구 참여 요청, 패스키 승인, 내 데이터, 기록(거래 · 나간 데이터 · 공유 이력 · 감사 기록),
// 참여 지급, 중단과 철회, 검토 알림. GET /api/p/{pid}와 그 하위 경로만 씁니다.

import { engine, watchSelf } from "./api.js";
import { createPasskey, passkeySupported, signWithPasskey } from "./passkey.js";
import { h, render, tag, icon, short, sum, banner, busy } from "./ui.js";

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
const itemName = (i) => ITEM[i] || i;
const won = (x) => `${(Math.round((x || 0) * 100) / 100).toFixed(2)} XRP`;
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
  const st = { p: null, view: "home", rid: null, picked: null, sensitiveOk: false, sign: null, error: null, toast: null,
               data: undefined, from: {}, tab: "trade", confirmWithdraw: false, details: false };
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
    if (!st.sign) { st.p = v; st.error = null; draw(); }
  });

  const go = (view) => { st.view = view; st.confirmWithdraw = false; draw(); window.scrollTo(0, 0); };
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
      return h("button", { class: "ar-card col ar-req", onclick: () => { st.rid = r.id; st.picked = null; go("request"); } },
        h("div", { class: "spread" }, h("b", {}, lab(r)), state),
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
    return frame("연구 참여", body);
  }

  // ---------- 요청 상세와 승인 ----------
  function requestView() {
    const r = current();
    if (!r) return homeView();
    const open = r.status === "open" || r.status === "partly_open";
    if (!st.picked || st.picked.rid !== r.id) {
      st.picked = { rid: r.id, items: new Set(r.items.filter((i) => i.class === "approval" && !i.sensitive).map((i) => i.item)) };
      st.sensitiveOk = false;
    }
    const picked = st.picked.items;
    const asks = r.items.filter((i) => i.class === "approval");
    const blocked = r.items.filter((i) => i.class === "blocked");
    const credentialOk = r.institution.badges.some((b) => b.kind === "ethics_review" && b.on_ledger);
    const send = asks.filter((i) => picked.has(i.item) && (!i.sensitive || st.sensitiveOk));
    const price = cellPrice(r) * sum(send, (i) => i.weeks.length);
    const allWeeks = send.flatMap((i) => i.weeks);
    const pk = st.p.passkey || { registered: false };

    const statement = h("div", { class: "ar-card col ar-statement" },
      h("span", { class: "small muted" }, "승인하는 내용"),
      h("dl", { class: "ar-kv left" },
        h("dt", {}, "요청 기관"), h("dd", {}, lab(r), " ", credentialOk ? tag("IRB 승인 확인", "green") : tag("IRB 확인 안 됨", "red")),
        h("dt", {}, "목적"), h("dd", {}, PURPOSE[r.purpose] || r.purpose),
        h("dt", {}, "항목"), h("dd", {}, send.map((i) => itemName(i.item)).join(", ") || "선택한 항목 없음"),
        h("dt", {}, "기간"), h("dd", {}, weeks(allWeeks) || "—"),
        h("dt", {}, "참여 지급액"), h("dd", {}, h("b", {}, won(price)), h("span", { class: "small muted" }, ` · 전달 시 ${r.payment.immediate_pct}%, 검토 후 ${r.payment.held_pct}%`))));

    const items = asks.map((i) => h("label", { class: "ar-item row", style: { alignItems: "center" } },
      h("input", { type: "checkbox", checked: picked.has(i.item), disabled: !open || !credentialOk,
        onchange: (e) => { e.target.checked ? picked.add(i.item) : picked.delete(i.item); draw(); } }),
      h("div", { class: "grow col", style: { gap: "2px" } }, h("b", {}, itemName(i.item)),
        h("span", { class: "small muted" }, `${weeks(i.weeks)} · ${SOURCE[i.source] || i.source || ""}`)),
      i.sensitive ? tag("민감 정보", "red") : null));
    const sensitive = asks.filter((i) => i.sensitive && picked.has(i.item));

    const body = [
      !credentialOk ? banner("red", "이 기관의 IRB 승인을 원장에서 확인할 수 없어 승인할 수 없어요.") : null,
      statement,
      h("h3", {}, "보낼 항목"),
      items,
      sensitive.length ? h("label", { class: "ar-item row", style: { alignItems: "center" } },
        h("input", { type: "checkbox", checked: st.sensitiveOk, onchange: (e) => { st.sensitiveOk = e.target.checked; draw(); } }),
        h("span", { class: "small" }, `${sensitive.map((i) => itemName(i.item)).join(", ")}은 민감 정보예요. 이 연구에 보내는 데 따로 동의해요.`)) : null,
      blocked.length ? h("p", { class: "small muted" }, `${blocked.map((i) => itemName(i.item)).join(", ")}은 허용한 목적 밖이라 보내지 않아요.`) : null,
      h("button", { class: "ar-link small", style: { alignSelf: "flex-start" }, onclick: () => { st.details = !st.details; draw(); } },
        st.details ? "자세히 접기" : "자세히"),
      st.details ? h("div", { class: "ar-card col small" },
        h("p", {}, "연구 기관은 참여 번호와 승인한 항목만 받아요. 이름이나 연락처는 받지 않아요."),
        h("p", {}, "참여 지급액은 보내기 전에 원장에 예치되고, 데이터가 전달되면 지급돼요."),
        h("p", {}, "언제든 철회할 수 있어요. 철회하면 아직 전달되지 않은 회차는 멈추고 예치금은 연구로 돌아가요. 이미 받은 지급액은 그대로예요."),
        h("p", {}, r.international_transfer && r.international_transfer.planned ? "국외 이전이 예정되어 있어 별도 동의가 필요해요." : "국외 이전은 없어요."),
        h("p", { class: "muted" }, "접근 기록은 2년, 권한 변경 기록은 3년 보관해요.")) : null,
      st.sign && st.sign.error ? banner("red", st.sign.error) : null,
    ];
    let foot = null;
    if (open && credentialOk) {
      const primary = !pk.registered
        ? h("button", { class: "ar-btn primary block", disabled: !passkeySupported(), onclick: (e) => register(e) },
          icon("key", 16), " 이 기기에 패스키 만들기")
        : h("button", { class: "ar-btn primary block", disabled: !send.length, onclick: (e) => approve(e, r, send.map((i) => i.item)) },
          icon("key", 16), send.length ? ` 패스키로 승인 · ${won(price)}` : " 보낼 항목을 골라 주세요");
      foot = [
        !pk.registered ? h("p", { class: "tiny muted", style: { margin: "0 0 4px" } }, "승인은 본인 기기의 패스키로만 할 수 있어요. 처음 한 번 만들어 주세요.") : null,
        primary,
        h("button", { class: "ar-btn block", onclick: (e) => skip(e, r) }, "이번 회차 건너뛰기"),
      ];
    }
    return frame(lab(r), body, foot, { back: () => go("home") });
  }

  async function register(e) {
    st.sign = null;
    const res = await busy(e.target, "패스키 만드는 중", async () => {
      const { publicKey } = await api.passkeyOptions(pid);
      return api.passkeyComplete(pid, await createPasskey(publicKey));
    }, (err) => { st.sign = { error: err.name === "NotAllowedError" ? "패스키 만들기를 취소했어요." : "패스키를 만들지 못했어요." }; });
    if (res) { st.p = await api.participant(pid); toast("패스키를 만들었어요. 이제 승인할 수 있어요."); }
    draw();
  }

  async function approve(e, r, items) {
    st.sign = { pending: true };
    const res = await busy(e.target, "본인 확인 중", async () => {
      const ch = await api.challenge(pid, r.id, items);
      const assertion = await signWithPasskey(ch.publicKey);
      return api.approve(pid, r.id, items, assertion);
    }, (err) => {
      st.sign = { error: err.name === "NotAllowedError" ? "승인을 취소했어요. 아무것도 보내지 않았어요."
        : "승인하지 못했어요. 아무것도 보내지 않았어요." };
    });
    if (res) { st.p = res; st.sign = null; st.lastSigned = res.signed; go("done"); return; }
    draw();
  }

  async function skip(e, r) {
    const res = await busy(e.target, "처리 중", () => api.decline(pid, r.id), () => toast("연결할 수 없어요. 바뀐 것은 없어요."));
    if (res) { st.p = res; toast("이번 회차를 건너뛰었어요. 아무것도 보내지 않았어요."); go("home"); }
  }

  // ---------- 승인 완료 ----------
  function doneView() {
    const r = current();
    const a = st.p.approvals.find((x) => st.lastSigned && x.statement_hash === st.lastSigned.statement_hash)
      || st.p.approvals[st.p.approvals.length - 1];
    if (!a) return homeView();
    const body = [
      h("div", { class: "ar-card col", style: { alignItems: "center", textAlign: "center", padding: "28px 16px" } },
        h("span", { class: "ar-okmark" }, icon("check", 28)),
        h("h2", {}, "승인했어요"),
        h("p", { class: "small muted" }, `${lab(r)}에 ${a.statement.items.map(itemName).join(", ")} · ${weeks(Object.keys(a.statement.weeks).map(Number))}`)),
      h("div", { class: "ar-card col" },
        h("div", { class: "spread" }, h("span", { class: "small muted" }, "참여 지급액 예치"), h("b", {}, won(a.statement.price_drops / 1e6))),
        a.orders.map((o) => h("div", { class: "spread small" }, h("span", {}, `${o.weeks.join(", ")}주 차 · ${o.items.map(itemName).join(", ")}`), txA(o.escrow)))),
      h("button", { class: "ar-btn block", onclick: () => { st.tab = "trade"; go("record"); } }, "기록에서 보기"),
    ];
    return frame("승인 완료", body, null, { back: () => go("home") });
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
    const locked = p.contributions.filter((c) => c.status === "escrowed");
    const option = (title, desc, btn) => h("div", { class: "ar-card col" }, h("b", {}, title), h("span", { class: "small muted" }, desc), btn);
    const body = [
      option(paused ? "새 요청 다시 받기" : "새 요청 멈추기", "이미 보낸 데이터와 받은 지급액은 그대로예요. 언제든 다시 받을 수 있어요.",
        h("button", { class: "ar-btn", onclick: async (e) => {
          const res = await busy(e.target, "처리 중", () => (paused ? api.resume(pid) : api.pause(pid)));
          if (res) { st.p = res; toast(paused ? "새 요청을 다시 받아요." : "새 요청을 멈췄어요."); draw(); }
        } }, paused ? "다시 받기" : "멈추기")),
      option("이 연구에서 철회", "연구 기관의 열람 권한을 원장에서 회수하고, 아직 전달되지 않은 회차는 멈춰요. 이미 받은 지급액은 그대로예요.",
        st.confirmWithdraw
          ? h("div", { class: "col", style: { gap: "8px" } },
            h("ul", { class: "small", style: { margin: 0, paddingLeft: "18px" } },
              h("li", {}, "열람 권한을 원장에서 회수해요."),
              locked.length ? h("li", {}, `예치된 ${locked.length}회차 ${won(sum(locked, (c) => c.amount_xrp))}는 연구로 돌아가요.`) : null,
              h("li", {}, "연구 기관은 개인 단위 사본을 지우고 확인해야 해요."),
              h("li", {}, "이미 만들어진 집계 통계만 남아요.")),
            h("button", { class: "ar-btn danger block", onclick: async (e) => {
              const res = await busy(e.target, "원장에서 확인 중", () => api.revoke(pid), () => toast("원장 확인이 늦어지고 있어요. 철회는 기록됐고 다시 시도해요."));
              if (res) { st.p = res; draw(); }
            } }, "철회하기"),
            h("button", { class: "ar-btn block", onclick: () => { st.confirmWithdraw = false; draw(); } }, "취소"))
          : h("button", { class: "ar-btn danger", onclick: () => { st.confirmWithdraw = true; draw(); } }, "철회")),
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
