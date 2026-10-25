// First-visit guided tour: seller and buyer paths across the pages, skippable and replayable from the nav.
const tourOpen = (q) => () => { const d = document.querySelector(q); if (d) d.open = true; };
async function tourLatestSale() {   // the signed-in (or demo) vault's newest settled deal, with its real Testnet transactions
  const ko = tourLang === "ko";
  const rows = [...document.querySelectorAll(".tx.mine.settled button[data-c]")];
  if (!rows.length) return `<p class="small muted">${ko ? "아직 정산된 내 거래가 없어요. 데모 에이전트가 스스로 거래하니 잠시 뒤 다시 보세요." : "No settled deal of yours yet. The demo agent trades on its own; check back in a minute."}</p>`;
  try {
    const d = await api(`/api/contract/${rows[0].dataset.c}`), c = d.contract;
    const txs = d.txs.filter(t => t.url && /^Escrow/.test(t.type)).slice(0, 4);
    return `<div class="tour-live"><b>C${c.id} · ${esc(META.kinds[c.kind]?.label || c.kind)} · ${esc(c.status)}</b>${txs.map(t => `<a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(t.type)} · ${micro(t.drops, c.asset)} ↗</a>`).join("")}</div>`;
  } catch { return ""; }
}
const TOUR = [
  // ---- the idea ----
  {page: "/", el: [".brand"],
    ko: ["1. 데이터 금고란?", "건강·위치·구매 같은 내 기록은 내 금고에만 있어요. 내 AI 에이전트가 대신 나서서, 내가 허락한 구매자에게 허락한 용도로만 사본을 1:1로 팔아요. 지금은 데모 금고(합성 데이터)지만 결제는 진짜 XRPL Testnet에서 일어나요."],
    en: ["1. What is the data vault?", "Your health, location and purchase records live only in your vault. Your AI agent acts for you and sells a copy one-to-one, only to buyers and purposes you allow. This is the demo vault (synthetic data), but payments are real XRPL Testnet transactions."]},
  // ---- seller path: your data ----
  {page: "/vault", el: ["#uploads", "#drop"],
    ko: ["2. 내 데이터 넣기 (인테이크)", "파일을 올리면 ① 종류를 분류하고 ② 진단명·신분증 번호·미성년자 데이터는 아예 막고 ③ 중복·불가능한 값은 정리(소액 수수료)한 뒤 ④ 레코드의 Merkle 루트에 서명해요. 구매자는 이 서명으로 데이터가 진짜인지 확인해요."],
    en: ["2. Bring in your data (intake)", "Each upload is (1) classified, (2) screened: diagnoses, ID numbers and data about minors are never listed, (3) cleaned of duplicates and impossible values for a small fee, and (4) signed over the Merkle root of its records, so a buyer can check it is genuine."]},
  {page: "/vault", el: [".sample-options", "#samples"], prep: tourOpen(".sample-options"),
    ko: ["3. 샘플로 바로 해보기", "내 파일이 없으면 샘플 파일을 눌러보세요. 인테이크 결과가 바로 위 목록에 쌓여요. 수면, 걸음 수, 출퇴근, 스크린타임, 전력 사용 등 9가지 종류가 있어요."],
    en: ["3. Try it with a sample", "No files of your own? Tap a sample file and its intake result appears in the list. There are 9 kinds, from sleep and steps to commute, screen time and energy use."]},
  {page: "/vault", el: ["#collections", "#collectionForm"],
    ko: ["4. 동의 범위 정하기", "어떤 파일을 시장에 내놓을지는 내가 정해요. 컬렉션으로 묶은 파일만 팔 수 있고, 판매 전에는 아무것도 금고 밖으로 나가지 않아요. 직접 식별자(이름·이메일 등)는 인테이크에서 이미 지워져요."],
    en: ["4. Choose your consent scope", "You decide which files are on the market. Only what you include can be sold, and nothing leaves the vault before a sale. Direct identifiers like names and emails are already stripped at intake."]},
  {page: "/", el: ["#agentBtn"],
    ko: ["5. 최저가 · 용도 · 승인 방식", "Settings에서 ① '가격 고집' 슬라이더로 최저가를 정해요. 에이전트는 이 아래로 절대 안 팔아요. ② 보험료 산정·광고·재판매처럼 팔지 않을 용도를 칩으로 꺼요. ③ '혼자 판매' 또는 '먼저 물어보기'를 골라요."],
    en: ["5. Floor, purposes and approval", "In Settings: (1) the 'How firm on price' slider sets your floor, and your agent never sells below it; (2) chips switch off purposes you never sell to, like insurance pricing, ads or resale; (3) pick 'Sell on its own' or 'Ask me first'."]},
  // ---- the negotiation ----
  {page: "/", el: ["#ledger"],
    ko: ["6. 구매 요청이 들어와요", "가운데 목록이 실시간 시장이에요. 구매자 에이전트가 '어떤 데이터를, 무슨 용도로, 얼마에' 원하는지 올리면 내 에이전트가 먼저 용도가 내가 막은 것인지 확인해요. 막힌 용도면 가격과 상관없이 거절해요."],
    en: ["6. A buyer request arrives", "The centre list is the live market. A buyer agent posts what it wants, for what purpose, at what price. Your agent checks the purpose against your blocked list first; a blocked purpose is refused whatever the price."]},
  {page: "/", el: ["#ledger"],
    ko: ["7. 조건 맞추기 (대변인 협상)", "두 에이전트가 서로를 대변해 조건을 맞춰요: 필요한 레코드 수, 필드, 기간을 내 데이터가 얼마나 채우는지 '적합도'를 계산해요. 일부만 맞으면 가격이 내려가고, 20% 미만이면 '조건 불충족'으로 거래가 안 돼요."],
    en: ["7. Matching conditions", "Each agent speaks for its owner and they match conditions first: how well your data meets the records, fields and period the buyer needs. A partial fit lowers the price; under 20% fit there is no deal ('conditions not met')."]},
  {page: "/", el: ["#ledger"],
    ko: ["8. 가격 협상", "조건이 맞으면 가격을 주고받아요. GPT가 말을 하지만 규칙은 코드가 지켜요: 최저가 아래, 구매자 예산 위로는 절대 합의되지 않아요. 보라색으로 표시된 줄이 내 거래예요. 눌러서 대화 전체를 볼 수 있어요."],
    en: ["8. Negotiating price", "With conditions matched, they trade offers. GPT does the talking, but code enforces the rules: never below your floor, never above the buyer's budget. Purple rows are your deals; click one to read the whole exchange."]},
  {page: "/", el: ["#ledger"],
    ko: ["9. 사기 전에 검증", "구매자 에이전트는 돈을 걸기 전에 인테이크 서명을 확인하고, 레코드 하나를 뽑아 Merkle 증명으로 루트와 맞는지 검사해요. 하나라도 틀리면 결제 없이 끝나요."],
    en: ["9. Verify before paying", "Before locking any money, the buyer agent checks the intake signature and samples one record, proving it against the Merkle root. If either fails, the deal ends with no payment."]},
  // ---- settlement on the ledger ----
  {page: "/", el: [".tx.mine.settled", "#ledger"], live: tourLatestSale,
    ko: ["10. 에스크로에 잠그기", "합의되면 구매자가 RLUSD를 XRPL 에스크로에 잠가요. 조건은 SHA-256(K)이고 CancelAfter는 1시간이에요. 판매자가 1시간 안에 키를 내지 않으면 돈은 구매자에게 돌아가요. 아래는 내 금고의 실제 Testnet 거래예요."],
    en: ["10. Locked in escrow", "Once agreed, the buyer locks RLUSD in an XRPL escrow with condition SHA-256(K) and CancelAfter of 1 hour. If the seller doesn't reveal the key within the hour, the money returns to the buyer. Below are your vault's real Testnet transactions."]},
  {page: "/", el: [".tx.mine.settled", "#ledger"], live: tourLatestSale,
    ko: ["11. 키 공개 = 결제 완료", "판매자가 EscrowFinish로 K를 공개하는 순간 돈이 판매자에게 가고, 같은 K로 구매자가 데이터를 풀어요. 결제와 데이터 전달이 한 트랜잭션에서 같이 일어나서 어느 쪽도 먹튀할 수 없어요."],
    en: ["11. Key reveal = payment", "When the seller reveals K with EscrowFinish, the money moves to the seller and the buyer uses the same K to decrypt the data. Payment and delivery happen in one transaction, so neither side can walk away with both."]},
  {page: "/", el: ["#chat"],
    ko: ["12. 에이전트와 대화", "오른쪽 챗봇에 '뭘 팔 수 있어?', '수면 데이터 최저가 5로 해줘', '공기질 데이터 사고 싶어'처럼 말해보세요. 에이전트는 제안만 하고, 실제 실행은 내가 버튼을 눌러야 해요."],
    en: ["12. Talk to your agent", "Try the chat: 'what can I sell?', 'set my sleep floor to 5', 'I want air-quality data'. The agent only proposes; nothing happens until you press its button."]},
  // ---- buyer path ----
  {page: "/vault", el: [".buy-request", "#buyForm"], prep: tourOpen(".buy-request"),
    ko: ["13. 데이터 사기 (구매자)", "필요한 데이터 종류와 예산을 적어 요청을 올리면, 내 구매 에이전트가 판매자들을 찾아 같은 순서(조건 → 검증 → 가격 → 에스크로)로 협상해요. 산 파일은 내 DB에 들어와요."],
    en: ["13. Buying data", "Post a request with the kind and your budget. Your buying agent finds sellers and runs the same steps (conditions, verification, price, escrow). Purchased files land in your DB."]},
  {page: "/vault", el: ["#bundles", "#discoverData"],
    ko: ["14. 여러 명 묶음 구매", "연구처럼 많은 사람의 데이터가 필요하면 묶음을 사요. 각 판매자와 따로 에스크로를 만들어서, 한 명이 빠져도 나머지는 정상 정산돼요."],
    en: ["14. Buying from many people", "For research that needs many people, buy a bundle. Each seller gets their own escrow, so if one drops out the rest still settle."]},
  // ---- money ----
  {page: "/assets", el: ["#balance", "#portfolio"],
    ko: ["15. 잔액과 화폐 단위", "판매 대금은 RLUSD로 보여요. Testnet에서는 이 앱이 발행한 test USD가 RLUSD를 대신해요(페이지 하단 주석). 실제 돈이 아니에요."],
    en: ["15. Balance and unit", "Sales show in RLUSD. On Testnet, a test USD token issued by this app stands in for RLUSD (see the footnote at the bottom). It is not real money."]},
  {page: "/assets", el: ["#activity"],
    ko: ["16. 모든 거래 기록과 출금", "에스크로 생성·해제·환불이 전부 탐색기 링크와 함께 남아요. 내 금고로 로그인해 '내 지갑 연결'을 하면 판매 대금이 내 XRPL 지갑으로 바로 가요. 데모 금고는 공용이라 출금은 안 돼요."],
    en: ["16. Every transaction, and withdrawal", "Every escrow create, finish and refund is listed with an explorer link. Sign in to your own vault and use 'Link my wallet' so sale proceeds go straight to your XRPL wallet. The shared demo vault can't withdraw."]},
  {page: "/", el: [".tour-link"],
    ko: ["끝! 다시 보려면", "이 가이드는 상단의 Guide 버튼으로 언제든 다시 볼 수 있어요. Demo 페이지에서는 50명의 에이전트가 거래하는 모습을 실시간 지도로 볼 수 있어요."],
    en: ["That's it", "Replay this guide anytime from Guide at the top. The Demo page shows 50 agents trading on a live map."]},
];
const tourGet = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
const tourSet = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch {} };
let tourTimer = null;
let tourLang = tourGet("vm_tour_lang") || ((navigator.language || "").startsWith("ko") ? "ko" : "en");
function tourStart() { tourSet("vm_tour_step", "0"); tourShow(); }
function tourEnd() { tourSet("vm_tour_step", null); tourSet("vm_tour_done", "1"); document.querySelector(".tour")?.remove(); document.querySelectorAll(".tour-hi").forEach(e => e.classList.remove("tour-hi")); }
function tourGo(i) {
  if (i < 0) return;
  if (i >= TOUR.length) return tourEnd();
  tourSet("vm_tour_step", String(i));
  if (location.pathname !== TOUR[i].page) location.href = TOUR[i].page; else tourShow();
}
function tourShow() {
  const i = +tourGet("vm_tour_step");
  if (tourGet("vm_tour_step") == null || !TOUR[i]) return;
  const s = TOUR[i];
  if (location.pathname !== s.page) { location.href = s.page; return; }
  document.querySelectorAll(".tour-hi").forEach(e => e.classList.remove("tour-hi"));
  s.prep?.();
  const find = () => s.el.map(q => document.querySelector(q)).find(e => e && e.offsetParent !== null);
  const target = find();
  if (target) { target.classList.add("tour-hi"); target.scrollIntoView({block: "center", behavior: "smooth"}); }
  clearInterval(tourTimer);   // live lists redraw every few seconds; keep the spotlight on
  tourTimer = setInterval(() => { if (!document.querySelector(".tour")) return clearInterval(tourTimer); if (!document.querySelector(".tour-hi")) find()?.classList.add("tour-hi"); }, 1000);
  const [title, body] = s[tourLang];
  document.querySelector(".tour")?.remove();
  document.body.insertAdjacentHTML("beforeend", `<div class="tour" role="dialog" aria-label="Guide"><div class="row"><span class="small muted">${i + 1} / ${TOUR.length}</span><button type="button" class="tour-lang">${tourLang === "ko" ? "EN" : "한국어"}</button></div><h3>${esc(title)}</h3><p>${esc(body)}</p><div class="tour-extra"></div><div class="row"><button type="button" class="tour-skip">${tourLang === "ko" ? "건너뛰기" : "Skip"}</button><span>${i ? `<button type="button" class="tour-back">${tourLang === "ko" ? "이전" : "Back"}</button> ` : ""}<button type="button" class="primary tour-next">${i === TOUR.length - 1 ? (tourLang === "ko" ? "완료" : "Done") : (tourLang === "ko" ? "다음" : "Next")}</button></span></div></div>`);
  const t = document.querySelector(".tour");
  t.querySelector(".tour-skip").onclick = tourEnd;
  t.querySelector(".tour-next").onclick = () => tourGo(i + 1);
  t.querySelector(".tour-back")?.addEventListener("click", () => tourGo(i - 1));
  if (s.live) s.live().then(h => { const x = t.querySelector(".tour-extra"); if (x && document.contains(t)) x.innerHTML = h; });
  t.querySelector(".tour-lang").onclick = () => { tourLang = tourLang === "ko" ? "en" : "ko"; tourSet("vm_tour_lang", tourLang); tourShow(); };
}
function tourInit() {
  const nav = document.querySelector(".top nav");
  if (nav && !nav.querySelector(".tour-link")) {
    nav.insertAdjacentHTML("beforeend", '<button type="button" class="tour-link">Guide</button>');
    nav.querySelector(".tour-link").onclick = tourStart;
  }
  if (tourGet("vm_tour_step") == null && !tourGet("vm_tour_done") && location.pathname === "/") tourSet("vm_tour_step", "0");
  setTimeout(tourShow, 1200);   // let the page draw its lists first
}
