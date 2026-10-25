// Coach-mark guide: a spotlight box around a real element, the page dimmed, and a tooltip beside it.
// "click" steps advance only when the visitor clicks the highlighted element itself.
// The judge walkthrough runs across pages from the homepage; each page also has a short tour and a "?" help popup.
const T = (en, ko) => ({en, ko});
const JUDGE = [
  {page: "/", el: [".brand"], t: T(["Data Vault Market", "People keep their own records (sleep, steps, location, purchases) in a personal vault. Their AI agent sells one-to-one copies to buyers they allow, and every sale settles on the XRPL Testnet. You are in a shared demo vault with synthetic data, so nothing here needs a login."],
                                   ["데이터 금고 마켓", "사람들이 수면·걸음·위치·구매 기록을 개인 금고에 보관하고, AI 에이전트가 허락한 구매자에게만 1:1로 사본을 팔아요. 모든 판매는 XRPL Testnet에서 정산돼요. 지금은 합성 데이터의 공용 데모 금고라 로그인이 필요 없어요."])},
  {page: "/", el: ["#sellnow [data-sell].primary", "#sellnow [data-sell]"], click: true, base: () => tourMaxMine(),
    t: T(["Sell to a buyer", "Each card is an open buyer request your data already fits: who is buying, for what purpose, your minimum and their budget. Click “Ask agent to sell”: this queues a real sale."],
         ["구매자에게 팔기", "각 카드는 내 데이터가 맞는 구매 요청이에요: 누가, 어떤 용도로, 내 최저가와 구매자 예산. “Ask agent to sell”을 누르면 실제 판매가 대기열에 들어가요."])},
  {page: "/", el: ["#ledger"], wait: tourSaleDone,
    t: T(["Watch the agents negotiate", "This is live. Before any price talk the agents match conditions: enough records, the right fields and period, an allowed purpose. Then they trade offers; GPT talks, code enforces your floor and the buyer's budget. The guide moves on by itself when your deal settles on the ledger."],
         ["에이전트 협상 보기", "실시간이에요. 가격 전에 조건부터 맞춰요: 레코드 수, 필드, 기간, 허용 용도. 그다음 가격을 주고받아요. 말은 GPT, 규칙은 코드가 지켜요. 거래가 원장에서 정산되면 가이드가 자동으로 넘어가요."])},
  {page: "/", el: [".tx.mine.settled button", ".tx.settled button"], click: true,
    t: T(["Open your settled deal", "Your deal is the top purple row marked “You sold”. Click it to open its full record: the negotiation, the checks and the ledger transactions."],
         ["정산된 내 거래 열기", "맨 위 “You sold” 보라색 줄이 방금 거래예요. 눌러서 협상, 검증, 원장 트랜잭션 전체를 보세요."])},
  {page: "/", el: ["#dlgBody a[href*='xrpl.org']", "#dlgBody"], dialog: true,
    t: T(["Settled on the XRPL Testnet", "The buyer checked the intake signature and a Merkle proof of a sampled record, then locked the payment in an XRPL escrow whose condition is SHA-256(K), with CancelAfter of one hour. The seller's EscrowFinish reveals K: that releases the money and lets the buyer decrypt the data in the same transaction. Click a link to see it on the Testnet explorer."],
         ["XRPL Testnet 정산", "구매자가 인테이크 서명과 Merkle 샘플 증명을 확인하고, 조건 SHA-256(K)·CancelAfter 1시간인 에스크로에 돈을 잠가요. 판매자의 EscrowFinish가 K를 공개하면 같은 트랜잭션에서 돈이 풀리고 구매자는 데이터를 복호화해요. 링크를 누르면 Testnet 탐색기에서 보여요."])},
  {page: "/", el: ["#close"], click: true, dialog: true,
    t: T(["Close the deal", "Click Close to go back to the market."], ["닫기", "Close를 눌러 시장으로 돌아가세요."])},
  {page: "/", el: ["nav a[href='/assets']"], click: true,
    t: T(["Go to Assets", "Click Assets to see where the money landed."], ["Assets로 이동", "Assets를 눌러 돈이 어디로 들어왔는지 보세요."])},
  {page: "/assets", el: ["#activity", "#balance"],
    t: T(["Every payment, with its receipt", "Each escrow create, finish or refund is listed with its ledger result and an explorer link. Amounts show in RLUSD; on Testnet a test USD token issued by this app stands in for RLUSD (footnote at the bottom). A member links their own XRPL wallet so sales pay straight to it."],
         ["모든 결제와 영수증", "에스크로 생성·해제·환불이 원장 결과와 탐색기 링크와 함께 남아요. 금액은 RLUSD로 표시되고, Testnet에서는 이 앱이 발행한 test USD가 RLUSD를 대신해요(하단 주석). 회원은 자기 XRPL 지갑을 연결해 판매 대금을 바로 받아요."])},
  {page: "/assets", el: ["nav a[href='/vault']"], click: true,
    t: T(["Go to My DB", "Click My DB to see the data your agent sells."], ["My DB로 이동", "My DB를 눌러 에이전트가 파는 데이터를 보세요."])},
  {page: "/vault", el: [".sample-options summary"], click: true,
    t: T(["Add a file", "Open “Try a sample file”."], ["파일 추가", "“Try a sample file”을 여세요."])},
  {page: "/vault", el: ["#samples [data-s='1']", "#samples button"], click: true,
    t: T(["Upload a raw file", "Click “A run with strap spikes”. Intake classifies it, blocks sensitive data (diagnoses, ID numbers, data about minors), checks values and signs the Merkle root of its records."],
         ["원본 파일 올리기", "“A run with strap spikes”를 누르세요. 인테이크가 분류하고, 진단명·신분증 번호·미성년자 데이터는 막고, 값을 검사한 뒤 레코드 Merkle 루트에 서명해요."])},
  {page: "/vault", el: ["#uploads [data-u]"], click: true,
    t: T(["Needs cleaning", "Heart-rate spikes from a loose strap would fail buyers' quality checks. Click “Clean it” to pay the cleaning agent a small fee on the ledger; it filters the bad records."],
         ["정리 필요", "스트랩이 헐거워 생긴 심박수 튐은 구매자 품질 검사에서 떨어져요. “Clean it”을 눌러 원장에서 소액을 내면 정리 에이전트가 불량 레코드를 걸러요."])},
  {page: "/vault", el: ["#uploads .card"], wait: () => /cleaned|passed/.test(document.querySelector("#uploads .card .tag")?.textContent || ""),
    t: T(["Cleaned and listed", "The fee payment is a real ledger transaction (you'll find it in Assets), and the file now lists as cleaned, ready to sell."],
         ["정리 완료", "수수료 결제는 실제 원장 트랜잭션이고(Assets에서 확인), 파일은 이제 cleaned로 등록돼 판매할 수 있어요."])},
  {page: "/vault", el: [".buy-request summary"], click: true,
    t: T(["Buying works the same way", "Open “Buy data for my DB”."], ["구매도 같은 방식", "“Buy data for my DB”를 여세요."])},
  {page: "/vault", el: ["#buyForm"],
    t: T(["Post a buy request", "Pick a kind and an offer. Your buying agent finds sellers and runs the same steps: conditions, verification, price, escrow."],
         ["구매 요청", "종류와 가격을 고르면 구매 에이전트가 판매자를 찾아 조건 → 검증 → 가격 → 에스크로 순서로 협상해요."])},
  {page: "/vault", el: ["nav a[href='/']"], click: true,
    t: T(["Back to the Market", "Click Market."], ["마켓으로", "Market을 누르세요."])},
  {page: "/", el: ["#agentBtn"], click: true,
    t: T(["Your agent's rules", "Click Settings."], ["에이전트 규칙", "Settings를 누르세요."])},
  {page: "/", el: ["#agentDlg .agent-dlg-body", "#agents"], dialog: true,
    t: T(["Floor, purposes, approval", "Slide to set the minimum price your agent will accept, tap chips to switch off purposes you never sell to (insurance pricing, ads, resale), and choose whether it sells on its own or asks you first."],
         ["최저가 · 용도 · 승인", "슬라이더로 최저가를, 칩으로 팔지 않을 용도(보험료 산정, 광고, 재판매)를, 그리고 혼자 팔지 먼저 물어볼지를 정해요."])},
  {page: "/", el: ["#agentClose"], click: true, dialog: true, t: T(["Close Settings", "Click Close."], ["닫기", "Close를 누르세요."])},
  {page: "/", el: ["#chat"],
    t: T(["Talk to your agent", "Ask in plain words: “what can I sell?”, “set my sleep floor to 5”, “I need air-quality data”. The agent proposes; nothing happens until you press its button."],
         ["에이전트와 대화", "“뭘 팔 수 있어?”, “수면 최저가 5로”, “공기질 데이터 필요해”처럼 말해보세요. 에이전트는 제안만 하고, 버튼을 눌러야 실행돼요."])},
  {page: "/", el: [".help-btn"],
    t: T(["That's the whole loop", "Press ? on any screen for a short explanation of it. “Judge walkthrough ▶” replays this tour."],
         ["끝", "어느 화면에서든 ?를 누르면 그 화면 설명이 나와요. “Judge walkthrough ▶”로 이 투어를 다시 볼 수 있어요."])},
];
function tourMaxMine() { return Math.max(0, ...[...document.querySelectorAll(".tx.mine button[data-c]")].map(b => +b.dataset.c)); }
function tourSaleDone() {   // true once a deal of yours newer than the click has settled; a failed one shows why
  const base = +(tourGet("vm_tour_base") || 0);
  const row = [...document.querySelectorAll(".tx.mine button[data-c]")].find(b => +b.dataset.c > base)?.closest(".tx");
  if (!row) return false;
  if (row.classList.contains("settled")) return true;
  if (row.querySelector(".amt.failure")) return "fail";
  return false;
}
const PAGE = {
  "/": {help: T("The Market. Left: buyer requests your data already fits. Centre: the live market, one negotiation at a time, with recent outcomes. Right: your agent's chat. Settings holds the floor price, blocked purposes and approval mode. Purple rows are your deals.",
                "마켓 화면. 왼쪽은 내 데이터가 맞는 구매 요청, 가운데는 실시간 협상과 최근 결과, 오른쪽은 에이전트 채팅. Settings에 최저가·금지 용도·승인 방식이 있어요. 보라색이 내 거래예요."),
        steps: [{el: ["#sellnow"], t: T(["Requests you can fill", "Buyer requests that fit your data and terms. “Ask agent to sell” starts a negotiation."], ["팔 수 있는 요청", "내 데이터와 조건에 맞는 구매 요청이에요."])},
                {el: ["#ledger"], t: T(["Live market", "Negotiations update live; click any of your deals to see its checks and Testnet transactions."], ["실시간 시장", "협상이 실시간으로 바뀌어요. 내 거래를 누르면 검증과 Testnet 트랜잭션이 보여요."])},
                {el: ["#agentBtn"], t: T(["Settings", "Floor price, blocked purposes and approval mode."], ["설정", "최저가, 금지 용도, 승인 방식."])},
                {el: ["#chat"], t: T(["Your agent", "Ask it anything; it proposes, you press to approve."], ["내 에이전트", "무엇이든 물어보세요. 제안하면 내가 눌러 승인해요."])}]},
  "/vault": {help: T("My DB holds your files. Uploads go through intake: classification, screening of sensitive data, cleaning and a signed Merkle root. “Needs cleaning” means raw data that would fail buyers' quality checks (for example heart-rate spikes from a loose strap); pay the cleaning agent a small fee and it lists as passed. Bundles group files by domain or by who is asking. “Buy data for my DB” posts a purchase request.",
                     "My DB는 내 파일 보관소예요. 업로드는 분류·민감정보 차단·정리·Merkle 서명을 거쳐요. “Needs cleaning”은 구매자 품질 검사에서 떨어질 원본(예: 헐거운 스트랩의 심박수 튐)이라 소액을 내면 정리돼 passed로 등록돼요. 묶음은 도메인이나 요청자별로 정리돼요. “Buy data for my DB”로 구매 요청을 올려요."),
        steps: [{el: ["#drop", "#uploads"], t: T(["Upload", "Drop files here or try a sample. Intake explains each decision."], ["업로드", "파일을 놓거나 샘플을 써보세요."])},
                {el: ["#uploads"], t: T(["Intake results", "Passed, needs cleaning or refused, and why."], ["인테이크 결과", "통과·정리 필요·거부와 그 이유."])},
                {el: ["#bundles"], t: T(["Bundles", "Your files grouped by domain or demand, with the best current offer."], ["묶음", "도메인·수요별로 묶인 파일과 최고 제안가."])},
                {el: [".buy-request"], t: T(["Buy data", "Post a request; your buying agent negotiates it."], ["데이터 구매", "요청을 올리면 구매 에이전트가 협상해요."])}]},
  "/assets": {help: T("Assets shows your balance, income and spending, and every ledger transaction with an explorer link. Amounts are in RLUSD; on Testnet a test USD token stands in for it. Members can link their own XRPL wallet for payouts.",
                      "Assets는 잔액, 수입·지출, 모든 원장 트랜잭션(탐색기 링크 포함)을 보여요. 금액은 RLUSD이고 Testnet에서는 test USD가 대신해요. 회원은 자기 XRPL 지갑을 연결할 수 있어요."),
        steps: [{el: ["#balance", "#portfolio"], t: T(["Balance", "What your vault holds now, per asset."], ["잔액", "자산별 현재 잔액."])},
                {el: ["#activity"], t: T(["Transactions", "Every escrow and payment, with its ledger result and receipt."], ["트랜잭션", "모든 에스크로와 결제, 원장 결과와 영수증."])}]},
  "/demo": {help: T("Demo shows the live market's agents on one map. Click a participant to pin it and see its rules and each completed deal. Paths flash when a deal starts, settles or is rejected. These are real Testnet deals between synthetic participants.",
                    "Demo는 실시간 시장의 에이전트를 한 지도에 보여줘요. 참가자를 눌러 고정하면 규칙과 완료된 거래가 보여요. 거래가 시작·정산·거절될 때 선이 번쩍여요. 합성 참가자 간 실제 Testnet 거래예요."),
        steps: [{el: ["#network"], t: T(["Live map", "Each line is a deal; it flashes when the deal starts, settles or is rejected."], ["실시간 지도", "선 하나가 거래예요. 시작·정산·거절 때 번쩍여요."])},
                {el: ["#grid"], t: T(["Participants", "Click one to pin it; its rules and each completed deal appear on the right."], ["참가자", "하나를 눌러 고정하면 오른쪽에 규칙과 거래가 보여요."])}]},
  "/report": {help: T("Report is a practice simulation, not the live market: 50 made-up participants in one 8-week study, comparing approval policies. Nothing on this page touched the ledger.",
                      "Report는 실제 시장이 아닌 연습 시뮬레이션이에요: 가상 참가자 50명, 8주 연구, 승인 정책 비교. 이 페이지는 원장과 무관해요."),
        steps: [{el: [".demo-title"], t: T(["A simulation", "This page compares contribution policies in a recorded mock study."], ["시뮬레이션", "기록된 모의 연구로 정책을 비교해요."])}]},
};
const SETTINGS_HELP = T("Your agent's rules. The price slider sets the minimum it will ever accept for each kind of data. Chips switch off purposes it must refuse whatever the price. “Sell on its own” lets it close deals within these rules; “Ask me first” sends each sale to your chat for approval. The buying limit caps what it spends without asking.",
                        "에이전트 규칙이에요. 가격 슬라이더는 종류별 최저가, 칩은 가격과 상관없이 거절할 용도, “Sell on its own”은 규칙 안에서 자동 판매, “Ask me first”는 판매마다 채팅으로 승인 요청이에요. 구매 한도는 묻지 않고 쓸 수 있는 금액이에요.");

const tourGet = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
const tourSet = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} };
let tourLang = tourGet("vm_tour_lang") || "en";
let tourTimer = null, tourClick = null;
const tourState = () => { try { return JSON.parse(tourGet("vm_tour") || "null"); } catch { return null; } };
const tourSteps = (st) => st?.seq === "judge" ? JUDGE : (PAGE[st?.seq]?.steps || []).map(s => ({...s, page: st.seq}));
const tx = (o) => o[tourLang] || o.en;

function tourStart(seq) { tourSet("vm_tour", JSON.stringify({seq, i: 0})); tourShow(); }
function tourEnd() {
  const st = tourState(); if (st?.seq === "judge") tourSet("vm_tour_done", "1");
  tourSet("vm_tour", null); tourClear();
}
function tourClear() {
  clearInterval(tourTimer); tourTimer = null;
  if (tourClick) document.removeEventListener("click", tourClick, true), tourClick = null;
  document.querySelectorAll(".coach,.coach-box").forEach(e => e.remove());
}
function tourGo(i) {
  const st = tourState(); if (!st) return;
  const steps = tourSteps(st);
  if (i < 0) return;
  if (i >= steps.length) return tourEnd();
  tourSet("vm_tour", JSON.stringify({...st, i}));
  if (location.pathname !== steps[i].page) location.href = steps[i].page; else tourShow();
}
function tourFind(s) {
  const root = s.dialog ? document.querySelector("dialog[open]") : document;
  if (!root) return null;
  return s.el.map(q => root.querySelector(q)).find(e => e && e.getClientRects().length);
}
function tourShow() {
  tourClear();
  const st = tourState(); if (!st) return;
  const steps = tourSteps(st), s = steps[st.i];
  if (!s) return tourEnd();
  if (location.pathname !== s.page) { location.href = s.page; return; }
  s.prep?.();
  const [title, body] = tx(s.t);
  const host = document.querySelector("dialog[open]") || document.body;   // inside an open modal, or it would be inert
  host.insertAdjacentHTML("beforeend", `<div class="coach-box" aria-hidden="true"></div><div class="coach" role="dialog" aria-label="Guide">
    <div class="coach-row"><span class="coach-n">Step ${st.i + 1} / ${steps.length}</span><button type="button" class="coach-lang">${tourLang === "ko" ? "EN" : "한국어"}</button></div>
    <h3>${esc(title)}</h3><p>${esc(body)}</p>
    <div class="coach-row"><button type="button" class="coach-skip">${tourLang === "ko" ? "건너뛰기" : "Skip"}</button><span>${st.i ? `<button type="button" class="coach-back">${tourLang === "ko" ? "이전" : "Back"}</button>` : ""}${s.wait ? `<span class="coach-wait">${tourLang === "ko" ? "실제 이벤트를 기다리는 중…" : "Waiting for the real event…"}</span>` : s.click ? `<span class="coach-hint">${tourLang === "ko" ? "강조된 버튼을 누르세요 ↗" : "Click the highlighted element"}</span>` : `<button type="button" class="primary coach-next">${st.i === steps.length - 1 ? (tourLang === "ko" ? "완료" : "Done") : (tourLang === "ko" ? "다음" : "Next")}</button>`}</span></div></div>`);
  const card = host.querySelector(".coach"), box = host.querySelector(".coach-box");
  card.querySelector(".coach-skip").onclick = tourEnd;
  card.querySelector(".coach-next")?.addEventListener("click", () => tourGo(st.i + 1));
  card.querySelector(".coach-back")?.addEventListener("click", () => tourGo(st.i - 1));
  card.querySelector(".coach-lang").onclick = () => { tourLang = tourLang === "ko" ? "en" : "ko"; tourSet("vm_tour_lang", tourLang); tourShow(); };
  let scrolled = false, missing = 0;
  const place = () => {
    const t = tourFind(s);
    if (!t) {   // not drawn yet (lists load live); after a few seconds let the visitor move on
      box.hidden = true; card.classList.add("coach-float");
      if (++missing === 6 && s.click) card.querySelector(".coach-hint")?.replaceWith(Object.assign(document.createElement("button"), {type: "button", className: "primary", textContent: tourLang === "ko" ? "다음" : "Next", onclick: () => tourGo(st.i + 1)}));
      return;
    }
    if (!scrolled) { t.scrollIntoView({block: "center"}); scrolled = true; }
    const r = t.getBoundingClientRect(), pad = 6;
    box.hidden = false; card.classList.remove("coach-float");
    Object.assign(box.style, {left: `${r.left - pad}px`, top: `${r.top - pad}px`, width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px`});
    const cw = card.offsetWidth, ch = card.offsetHeight, vw = innerWidth, vh = innerHeight;
    let top = r.bottom + 14, left = Math.min(Math.max(12, r.left), vw - cw - 12);
    if (top + ch > vh - 12) top = r.top - ch - 14;
    if (top < 12) { top = Math.min(Math.max(12, r.top), vh - ch - 12); left = r.right + 14 + cw < vw ? r.right + 14 : Math.max(12, r.left - cw - 14); }
    Object.assign(card.style, {left: `${left}px`, top: `${top}px`});
  };
  let waited = 0;
  const tick = () => {
    if ((document.querySelector("dialog[open]") || document.body) !== host) return tourShow();   // a dialog opened or closed under us
    place();
    if (!s.wait) return;
    const done = s.wait(); waited++;
    const w = card.querySelector(".coach-wait"); if (!w) return;
    if (done === true) { clearInterval(tourTimer); w.textContent = tourLang === "ko" ? "완료 ✓" : "Done ✓"; setTimeout(() => tourGo(st.i + 1), 900); }
    else if (done === "fail" || waited === 450) {   // not sold this time, or three minutes passed: let the visitor go on
      w.replaceWith(Object.assign(document.createElement("button"), {type: "button", className: "primary", textContent: done === "fail" ? (tourLang === "ko" ? "이번엔 거절됨 · 다음" : "Not sold this time · Next") : (tourLang === "ko" ? "다음" : "Next"), onclick: () => tourGo(st.i + 1)}));
    }
  };
  tick(); tourTimer = setInterval(tick, 400);
  addEventListener("resize", place, {once: true});
  if (s.click) {
    tourClick = (e) => {
      const t = tourFind(s);
      if (!t || !t.contains(e.target)) return;
      if (s.base) tourSet("vm_tour_base", String(s.base()));
      const steps2 = tourSteps(st), next = st.i + 1;
      if (next >= steps2.length) { tourEnd(); return; }
      tourSet("vm_tour", JSON.stringify({...st, i: next}));
      if (steps2[next].page === location.pathname) setTimeout(tourShow, 700);   // let the click open its dialog or list first
      else tourClear();   // the click itself navigates
    };
    document.addEventListener("click", tourClick, true);
  }
}
function helpPopup() {
  document.querySelector(".help-pop")?.remove();
  const p = PAGE[location.pathname] || PAGE["/"], ko = tourLang === "ko";
  document.body.insertAdjacentHTML("beforeend", `<div class="help-pop" role="dialog" aria-label="Help"><div class="coach-row"><b>${ko ? "이 화면은" : "This screen"}</b><button type="button" class="coach-skip help-x">${ko ? "닫기" : "Close"}</button></div><p>${esc(tx(p.help))}</p>
    <div class="help-acts"><button type="button" class="primary help-page">${ko ? "이 화면 둘러보기" : "Show me around"}</button><button type="button" class="help-judge">Judge walkthrough ▶</button></div></div>`);
  const h = document.querySelector(".help-pop");
  h.querySelector(".help-x").onclick = () => h.remove();
  h.querySelector(".help-page").onclick = () => { h.remove(); tourStart(PAGE[location.pathname] ? location.pathname : "/"); };
  h.querySelector(".help-judge").onclick = () => { h.remove(); tourSet("vm_tour", JSON.stringify({seq: "judge", i: 0})); tourGo(0); };
}
function settingsHelp(dlg) {   // the "?" inside the Settings dialog
  if (!dlg || dlg.querySelector(".set-help")) return;
  const head = dlg.querySelector(".row"); if (!head) return;
  head.insertAdjacentHTML("beforeend", '<button type="button" class="help-btn set-help" aria-label="Help for Settings">?</button>');
  head.after(Object.assign(document.createElement("p"), {className: "small muted set-help-text", hidden: true}));
  dlg.querySelector(".set-help").onclick = () => { const p = dlg.querySelector(".set-help-text"); p.textContent = tx(SETTINGS_HELP); p.hidden = !p.hidden; };
}
function tourInit() {
  const nav = document.querySelector(".top nav");
  if (nav && !nav.querySelector(".judge-link")) {
    nav.insertAdjacentHTML("beforeend", '<button type="button" class="judge-link">Judge walkthrough ▶</button><button type="button" class="help-btn" aria-label="Help for this screen">?</button>');
    nav.querySelector(".judge-link").onclick = () => { tourSet("vm_tour", JSON.stringify({seq: "judge", i: 0})); tourGo(0); };
    nav.querySelector(".help-btn").onclick = helpPopup;
  }
  settingsHelp(document.getElementById("agentDlg"));
  const path = location.pathname, st = tourState();
  if (!st) {
    if (path === "/" && !tourGet("vm_tour_done")) tourSet("vm_tour", JSON.stringify({seq: "judge", i: 0}));   // a first visit lands in the judge walkthrough
    else if (PAGE[path] && path !== "/" && !tourGet("vm_seen_" + path)) tourSet("vm_tour", JSON.stringify({seq: path, i: 0}));
  }
  tourSet("vm_seen_" + path, "1");
  setTimeout(tourShow, 900);   // let the page draw its lists first
}
