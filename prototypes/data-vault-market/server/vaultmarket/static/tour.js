// Coach-mark guide: a spotlight box around a real element, the page dimmed, and a tooltip beside it.
// "click" steps advance only when the visitor clicks the highlighted element itself.
// The judge walkthrough runs across pages from the homepage; each page also has a short tour and a "?" help popup.
const T = (en, ko) => ({en, ko});
const JUDGE = [
  {page: "/", el: [".brand"], t: T(["Data Vault Market", "People keep their own data in a private vault, and an AI agent sells copies only to buyers they allow. Every sale is paid on the XRPL Testnet. This is a shared demo vault with made-up data, so no login is needed."],
                                   ["데이터 금고 마켓", "사람들이 자기 데이터를 개인 금고에 두고, AI 에이전트가 허락한 구매자에게만 사본을 팔아요. 모든 판매는 XRPL Testnet에서 결제돼요. 합성 데이터의 공용 데모 금고라 로그인이 필요 없어요."])},
  {page: "/", el: ["#sellnow [data-sell].primary", "#sellnow [data-sell]"], click: true, base: () => tourMaxMine(),
    t: T(["Sell to a buyer", "Each card is a buyer who wants data you have, with their purpose and budget. Click “Ask agent to sell” to start a real sale."],
         ["구매자에게 팔기", "각 카드는 내 데이터를 원하는 구매자예요. 용도와 예산이 적혀 있어요. “Ask agent to sell”을 눌러 실제 판매를 시작하세요."])},
  {page: "/", el: () => tourMine() || document.querySelector("#agentQueue"), wait: tourSaleDone,
    t: T(["Your agent is negotiating", "This is your sale, live. The two agents first check the data fits, then agree on a price. The guide moves on when it's paid, or tells you why it wasn't.",
          "Before any price talk the agents match conditions: enough records, the right fields and period, an allowed purpose. GPT writes the messages; code enforces your floor price and the buyer's budget."],
         ["에이전트가 협상 중", "지금 진행 중인 내 판매예요. 두 에이전트가 데이터가 맞는지 확인하고 가격을 정해요. 결제되면 다음으로 넘어가고, 안 되면 이유를 알려줘요.",
          "가격 전에 레코드 수, 필드, 기간, 허용 용도를 먼저 맞춰요. 말은 GPT가, 최저가와 예산은 코드가 지켜요."])},
  {page: "/", el: [".tx.mine.settled button", ".tx.settled button"], click: true,
    t: T(["Open the receipt", "Click a purple “You sold” row to open the deal's receipt."],
         ["영수증 열기", "보라색 “You sold” 줄을 눌러 거래 영수증을 여세요."])},
  {page: "/", el: ["#dlgBody .receipt-tx", "#dlgBody a[href*='xrpl.org']", "#dlgBody .settlement-summary"], dialog: true,
    t: () => (typeof META !== "undefined" && META?.ap4m) ? T(["Paid through Mastercard AP4M", "The buyer's agent paid with an AP4M voucher on the XRPL EVM Testnet; redeeming it released the data key. Click a link to see the real payment and its receipt.",
          "The buyer checked the intake signature and a Merkle proof of a sampled record first. Each payment is a small AP4M voucher (at most 0.10 RLUSD); when the merchant redeems it, the seller's key K is released so the buyer can decrypt the data, and the RLUSD is forwarded to the seller."],
         ["Mastercard AP4M로 결제", "구매자 에이전트가 XRPL EVM Testnet에서 AP4M 바우처로 결제했고, 바우처가 사용되면서 데이터 키가 풀렸어요. 링크를 눌러 실제 결제와 영수증을 보세요.",
          "구매자는 먼저 인테이크 서명과 샘플 레코드의 Merkle 증명을 확인해요. 결제는 건당 0.10 RLUSD 이하의 AP4M 바우처이고, 가맹점이 바우처를 사용하면 판매자의 키 K가 공개되어 구매자가 복호화하고, RLUSD는 판매자에게 전달돼요."])
      : T(["Paid on XRPL", "The payment was locked on XRPL until the seller handed over the data key. Click a link to see the real transaction.",
          "The buyer checked the intake signature and a Merkle proof of a sampled record, then locked the payment in an escrow whose condition is SHA-256(K), cancelling after one hour. The seller's EscrowFinish reveals K, which releases the money and lets the buyer decrypt the data in the same transaction."],
         ["XRPL에서 결제", "판매자가 데이터 키를 넘길 때까지 돈이 XRPL에 잠겨 있었어요. 링크를 눌러 실제 트랜잭션을 보세요.",
          "구매자는 인테이크 서명과 샘플 레코드의 Merkle 증명을 확인한 뒤, 조건 SHA-256(K)·1시간 후 취소인 에스크로에 돈을 잠가요. 판매자의 EscrowFinish가 K를 공개하면 같은 트랜잭션에서 돈이 풀리고 구매자는 복호화해요."])},
  {page: "/", el: ["#close"], click: true, dialog: true,
    t: T(["Close the receipt", "Click Close."], ["닫기", "Close를 누르세요."])},
  {page: "/", el: ["nav a[href='/assets']"], click: true,
    t: T(["Where the money went", "Click Assets."], ["돈이 간 곳", "Assets를 누르세요."])},
  {page: "/assets", el: ["#activity", "#balance"],
    t: T(["Every payment has a receipt", "Each payment and refund is listed with a link to the ledger.",
          "Amounts show in RLUSD. On Testnet a test USD token issued by this app stands in for RLUSD (see the footnote). Members link their own XRPL wallet so sales pay straight to it."],
         ["모든 결제에 영수증", "결제와 환불마다 원장 링크가 붙어 있어요.",
          "금액은 RLUSD로 보여요. Testnet에서는 이 앱이 발행한 test USD가 RLUSD를 대신해요(하단 주석). 회원은 자기 XRPL 지갑을 연결해 대금을 바로 받아요."])},
  {page: "/assets", el: ["nav a[href='/vault']"], click: true,
    t: T(["Your data", "Click My DB."], ["내 데이터", "My DB를 누르세요."])},
  {page: "/vault", el: [".sample-options summary"], click: true,
    t: T(["Add a file", "Open “Try a sample file”."], ["파일 추가", "“Try a sample file”을 여세요."])},
  {page: "/vault", el: ["#samples [data-s='1']", "#samples button"], click: true,
    t: T(["Upload a messy file", "Click “A run with strap spikes”. The app checks it and blocks anything too sensitive to sell.",
          "Intake classifies the file, blocks sensitive data (diagnoses, ID numbers, data about minors), checks values and signs the Merkle root of its records."],
         ["지저분한 파일 올리기", "“A run with strap spikes”를 누르세요. 앱이 검사하고 팔면 안 되는 민감한 데이터는 막아요.",
          "인테이크가 분류하고, 진단명·신분증 번호·미성년자 데이터를 막고, 값을 검사한 뒤 레코드 Merkle 루트에 서명해요."])},
  {page: "/vault", el: ["#uploads [data-u]"], click: true,
    t: T(["Clean it", "A loose strap left bad heart-rate spikes, so buyers would reject it. Click “Clean it” to pay a small fee and fix it."],
         ["정리하기", "스트랩이 헐거워 심박수가 튀어서 구매자가 거절할 거예요. “Clean it”을 눌러 소액을 내고 고치세요."])},
  {page: "/vault", el: ["#uploads .card"], wait: () => /cleaned|passed/.test(document.querySelector("#uploads .card .tag")?.textContent || ""),
    t: T(["Cleaned and ready", "The fee went from your vault wallet to the platform on the ledger; the receipt link is on the file. It's now ready to sell."],
         ["정리 완료", "수수료는 내 금고 지갑에서 플랫폼으로 원장 결제됐고, 파일에 영수증 링크가 있어요. 이제 팔 수 있어요."])},
  {page: "/vault", el: [".buy-request summary"], click: true,
    t: T(["Buying works too", "Open “Buy data for my DB”."], ["구매도 가능", "“Buy data for my DB”를 여세요."])},
  {page: "/vault", el: ["#buyForm"],
    t: T(["Post a buy request", "Pick a kind of data and a price. Your agent finds sellers and pays the same safe way."],
         ["구매 요청", "데이터 종류와 가격을 고르면 에이전트가 판매자를 찾아 같은 안전한 방식으로 결제해요."])},
  {page: "/vault", el: ["nav a[href='/']"], click: true,
    t: T(["Back to the Market", "Click Market."], ["마켓으로", "Market을 누르세요."])},
  {page: "/", el: ["#agentBtn"], click: true,
    t: T(["Your agent's rules", "Click Settings."], ["에이전트 규칙", "Settings를 누르세요."])},
  {page: "/", el: ["#agentDlg .agent-dlg-body", "#agents"], dialog: true,
    t: T(["You set the rules", "Set the lowest price you accept, turn off purposes you never sell to, and choose whether it asks you first."],
         ["규칙은 내가", "받을 최저가, 절대 팔지 않을 용도, 먼저 물어볼지를 정해요."])},
  {page: "/", el: ["#agentClose"], click: true, dialog: true, t: T(["Close Settings", "Click Close."], ["닫기", "Close를 누르세요."])},
  {page: "/", el: ["#chat"],
    t: T(["Talk to your agent", "Ask in plain words, like “what can I sell?”. It suggests; nothing happens until you press its button."],
         ["에이전트와 대화", "“뭘 팔 수 있어?”처럼 말해보세요. 제안만 하고, 버튼을 눌러야 실행돼요."])},
  {page: "/", el: [".help-btn"],
    t: T(["That's it", "Press ? on any screen for help. “Judge walkthrough ▶” replays this tour."],
         ["끝", "어느 화면에서든 ?를 누르면 도움말이 나와요. “Judge walkthrough ▶”로 다시 볼 수 있어요."])},
];
function tourMaxMine() {   // the newest of your sale instructions (R…) before the click, so the guide follows the one you just started
  return Math.max(0, ...[...document.querySelectorAll("#agentQueue .queue-item time")].map(t => +(t.textContent.match(/R(\d+)/) || [0, 0])[1]));
}
let tourIdle = 0;
function tourMine() {
  const base = +(tourGet("vm_tour_base") || 0);
  return [...document.querySelectorAll("#agentQueue .queue-item")].find(q => +(q.querySelector("time")?.textContent.match(/R(\d+)/) || [0, 0])[1] > base);
}
function tourSaleDone() {   // the real outcome of your instruction: true when settled, {reason} when not sold, {live} while it runs
  const item = tourMine();
  if (!item) return {live: tourLang === "ko" ? "판매 요청을 대기열에 넣는 중…" : "Queuing your sale…"};
  const tag = item.querySelector(".tag")?.textContent || "", why = item.querySelector("p")?.textContent || "";
  if (tag === "Settled") return true;
  if (tag === "Not sold" || tag === "Blocked by your terms") return {reason: why || tag};
  if (tag === "Waiting for a buyer") {   // no buyer fits right now: that is the outcome, say so after a short look
    tourIdle = (tourIdle || 0) + 1;
    if (tourIdle > 25) { tourIdle = 0; return {reason: why || tag}; }
  } else tourIdle = 0;
  return {live: `${tag}${why ? " · " + why : ""}`};
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
function tourPlace(el, left, top) {   // position:fixed, corrected for a transformed ancestor (an open dialog) that shifts it
  Object.assign(el.style, {left: `${left}px`, top: `${top}px`});
  const r = el.getBoundingClientRect();
  if (Math.abs(r.left - left) > 1 || Math.abs(r.top - top) > 1) Object.assign(el.style, {left: `${2 * left - r.left}px`, top: `${2 * top - r.top}px`});
}
function tourRect(el) {   // the part of el actually on screen: clipped by every scrolling ancestor and the viewport
  let {left, top, right, bottom} = el.getBoundingClientRect();
  for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
    if (!/(auto|scroll|hidden)/.test(getComputedStyle(p).overflow + getComputedStyle(p).overflowY)) continue;
    const q = p.getBoundingClientRect();
    left = Math.max(left, q.left); top = Math.max(top, q.top); right = Math.min(right, q.right); bottom = Math.min(bottom, q.bottom);
  }
  left = Math.max(left, 0); top = Math.max(top, 0); right = Math.min(right, innerWidth); bottom = Math.min(bottom, innerHeight);
  return {left, top, right, bottom, width: Math.max(0, right - left), height: Math.max(0, bottom - top)};
}
function tourFind(s) {
  const root = s.dialog ? document.querySelector("dialog[open]") : document;
  if (!root) return null;
  if (typeof s.el === "function") { const e = s.el(); return e && e.getClientRects().length ? e : null; }
  return s.el.map(q => root.querySelector(q)).find(e => e && e.getClientRects().length);
}
function tourShow() {
  tourClear();
  const st = tourState(); if (!st) return;
  const steps = tourSteps(st), s = steps[st.i];
  if (!s) return tourEnd();
  if (location.pathname !== s.page) { location.href = s.page; return; }
  s.prep?.();
  const [title, body, more] = tx(typeof s.t === "function" ? s.t() : s.t);
  const host = document.querySelector("dialog[open]") || document.body;   // inside an open modal, or it would be inert
  host.insertAdjacentHTML("beforeend", `<div class="coach-box" aria-hidden="true"></div><div class="coach" role="dialog" aria-label="Guide">
    <div class="coach-row"><span class="coach-n">Step ${st.i + 1} / ${steps.length}</span><button type="button" class="coach-lang">${tourLang === "ko" ? "EN" : "한국어"}</button></div>
    <h3>${esc(title)}</h3><p>${esc(body)}</p>${more ? `<details class="coach-more"><summary>${tourLang === "ko" ? "작동 방식" : "How it works"}</summary><p>${esc(more)}</p></details>` : ""}
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
    let r = tourRect(t);
    if (!scrolled || r.height < 4) {   // bring the target to the middle of the screen (inside its own scroller too)
      t.scrollIntoView({block: t.offsetHeight > innerHeight * 0.8 ? "start" : "center", inline: "nearest"}); scrolled = true; r = tourRect(t);
    }
    const pad = 6, vw = innerWidth, vh = innerHeight, m = 12;
    box.hidden = false; card.classList.remove("coach-float");
    tourPlace(box, r.left - pad, r.top - pad); Object.assign(box.style, {width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px`});
    const cw = card.offsetWidth, ch = card.offsetHeight;
    let left, top;
    if (vh < 560 || ch > vh - 2 * m) { left = (vw - cw) / 2; top = vh - ch - m; }                     // short screen: dock at the bottom
    else if (r.right + 14 + cw <= vw - m) { left = r.right + 14; top = r.top + r.height / 2 - ch / 2; }   // beside, right
    else if (r.left - 14 - cw >= m) { left = r.left - 14 - cw; top = r.top + r.height / 2 - ch / 2; }     // beside, left
    else if (r.bottom + 14 + ch <= vh - m) { left = r.left + r.width / 2 - cw / 2; top = r.bottom + 14; } // below
    else if (r.top - 14 - ch >= m) { left = r.left + r.width / 2 - cw / 2; top = r.top - 14 - ch; }       // above
    else { left = (vw - cw) / 2; top = vh - ch - m; }
    tourPlace(card, Math.min(Math.max(m, left), vw - cw - m), Math.min(Math.max(m, top), vh - ch - m));
  };
  let waited = 0;
  const tick = () => {
    if ((document.querySelector("dialog[open]") || document.body) !== host) return tourShow();   // a dialog opened or closed under us
    place();
    if (!s.wait) return;
    const done = s.wait(); waited++;
    const w = card.querySelector(".coach-wait"); if (!w) return;
    if (done && done.live) { w.textContent = done.live; w.classList.add("coach-live"); box.classList.add("coach-pulse"); return; }
    if (done === true) { clearInterval(tourTimer); w.textContent = tourLang === "ko" ? "완료 ✓" : "Done ✓"; setTimeout(() => tourGo(st.i + 1), 900); }
    else if (done && done.reason) {   // not sold: say why, from the recorded reason, and let the judge retry or go on
      clearInterval(tourTimer);
      const ko = tourLang === "ko", box = document.createElement("div");
      box.className = "coach-fail";
      const b = document.createElement("p"); b.innerHTML = `<b>${ko ? "이번엔 안 팔렸어요" : "Not sold this time"}</b>: `; b.append(done.reason);
      const h = Object.assign(document.createElement("p"), {className: "small", textContent: ko ? "실제 협상이라 거절도 결과예요. Settings에서 최저가를 낮추거나 다른 요청으로 다시 해보세요." : "This is a real negotiation, so a refusal is a real outcome. Lower your floor in Settings, or try another request."});
      const row = document.createElement("span");
      row.append(Object.assign(document.createElement("button"), {type: "button", textContent: ko ? "다른 요청으로 다시" : "Try another request", onclick: () => tourGo(st.i - 1)}),
                 Object.assign(document.createElement("button"), {type: "button", className: "primary", textContent: ko ? "계속" : "Continue", onclick: () => tourGo(st.i + 1)}));
      box.append(b, h, row); w.replaceWith(box); place();
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
