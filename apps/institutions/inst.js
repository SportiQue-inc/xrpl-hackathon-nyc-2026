// Institution dashboard: reads /api/institutions/overview (research contracts, vault deals, AP4M runs) and shows each
// source on its own. Nothing is computed here that the engine did not record; a missing figure shows as "no data".

const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const DAY = 86400;
let data = null;

function dur(s) {
  if (s == null) return "no data";
  if (s < 1) return `${(s * 1000).toFixed(0)} ms`;
  if (s < 90) return `${s.toFixed(1)} s`;
  if (s < 5400) return `${(s / 60).toFixed(1)} min`;
  if (s < 2 * DAY) return `${(s / 3600).toFixed(1)} h`;
  return `${(s / DAY).toFixed(1)} days`;
}
const usd = (micro) => (micro == null ? "no data" : `${(micro / 1e6).toLocaleString(undefined, { maximumFractionDigits: 6 })} RLUSD*`);
const pct = (x) => (x == null ? "no data" : `${(x * 100).toFixed(0)}%`);
const when = (t) => (t ? new Date(t * 1000).toLocaleString() : "");
const faster = (s) => (s ? `${Math.round((data.baseline.request_to_access_days * DAY) / s).toLocaleString()}× shorter than the ${data.baseline.request_to_access_days}-day median` : "");

function table(el, cols, rows, empty = "No records yet.") {
  if (!rows.length) { el.innerHTML = `<tr><td class="empty">${esc(empty)}</td></tr>`; return; }
  el.innerHTML = `<thead><tr>${cols.map((c) => `<th class="${c.n ? "n" : ""}">${esc(c.h)}</th>`).join("")}</tr></thead><tbody>` +
    rows.map((r) => `<tr>${cols.map((c) => `<td class="${c.n ? "n" : ""} ${c.wrap ? "w" : ""}">${c.html ? c.f(r) : esc(c.f(r))}</td>`).join("")}</tr>`).join("") + "</tbody>";
}

function kpi(label, value, sub, vs = "") {
  return `<div class="kpi"><span class="l">${esc(label)}</span><span class="v">${value}</span>${vs ? `<span class="vs">${esc(vs)}</span>` : ""}<span class="s">${esc(sub)}</span></div>`;
}

function chosen() { return $("#inst").value; }

function render() {
  const d = data, R = d.research, V = d.vault, A = d.ap4m, pick = chosen();
  $("#read").textContent = `read ${new Date().toLocaleTimeString()}`;
  $("#baseline").innerHTML = `Baseline: research data takes a median of <b>${d.baseline.request_to_access_days} days</b> from request to access, ${d.baseline.contract_days} of them to sign the data use agreement (<a href="${esc(d.baseline.url)}" target="_blank" rel="noopener">${esc(d.baseline.source)}</a>). That is one major data platform's figure, not every data deal.`;

  // institution filter
  const names = [...new Set([...R.institutions.map((i) => i.institution), ...(V.ok ? V.orgs.map((o) => o.buyer) : [])])].sort();
  const sel = $("#inst"), keep = sel.value;
  sel.innerHTML = `<option value="">All institutions</option>` + names.map((n) => `<option>${esc(n)}</option>`).join("");
  sel.value = names.includes(keep) ? keep : "";

  const resRow = pick ? R.institutions.find((i) => i.institution === pick) : null;
  const vRow = pick && V.ok ? V.orgs.find((o) => o.buyer === pick) : null;
  const org = R.organic, latestRun = R.runs[R.runs.length - 1];
  const rr = resRow || org;
  const vt = vRow ? { ...vRow, request_to_paid: vRow.request_to_paid } : V.ok ? V.totals : null;
  const research = pick ? `${pick}, research contracts on this engine` : `research contracts people posted on this engine (scale runs not included)`;
  const k = [];
  k.push(kpi("Request → paid, research", dur(rr.request_to_paid.median_s), `median of ${rr.request_to_paid.n} payments · p90 ${dur(rr.request_to_paid.p90_s)} · ${research} · ${R.ledger}, ${rr.rails.join("/") || R.rail}`, faster(rr.request_to_paid.median_s)));
  if (vt) k.push(kpi("Request → paid, data market", dur(vt.request_to_paid.median_s), `median of ${vt.request_to_paid.n} paid deals · p90 ${dur(vt.request_to_paid.p90_s)} · ${pick ? pick + ", " : ""}${V.window} · ${V.ledger}`, faster(vt.request_to_paid.median_s)));
  if (vt) k.push(kpi("Refused before any payment", pct(vt.deals ? vt.refused / vt.deals : null), `${vt.refused} of ${vt.deals} deals in the data market ended unpaid with a recorded reason${!pick && V.intake.blocked != null ? ` · ${V.intake.blocked} uploads blocked at intake by the cleaning checks, ${V.intake.cleaned} cleaned` : ""}`));
  const a0 = A.runs[0];
  if (a0 && !pick) k.push(kpi("AP4M offers refused by the agent", `${a0.refused} <small>of ${a0.paid + a0.refused}</small>`, `AP4M run ${a0.run_id}: ${a0.paid} paid, package hash checked on ${a0.hash_ok}; refused: ${a0.refusals.join("; ") || "none"}`));
  k.push(kpi("Decided by agents, no person needed", pct(rr.automated_share), `${rr.automated} of ${rr.requests} requests answered within consent; ${rr.human_approvals} sent to the person · ${research}`));
  k.push(kpi("Cost per payout", usd(rr.cost_per_payout_micro), `${rr.paid} payouts, ${usd(rr.paid_micro)} in total · ${research}`));
  if (vt) k.push(kpi("Cost per payout, data market", usd(vt.cost_per_payout_micro), `${vt.payments} payments, ${usd(vt.paid_micro)} in total · ${pick ? pick + ", " : ""}${V.window}`));
  if (latestRun && !pick) k.push(kpi("Largest measured run", `${latestRun.members} <small>participants · ${latestRun.contracts} projects</small>`, `run ${latestRun.run}: ${latestRun.paid} paid, median request → paid ${dur(latestRun.request_to_paid.median_s)}, ${pct(latestRun.automated_share)} decided by agents · ${latestRun.ledgers.join("/")}, ${latestRun.rails.join("/")}`));
  $("#kpis").innerHTML = k.join("");

  // scale runs
  chart(R.runs);
  table($("#runs"), [
    { h: "Run", f: (r) => r.run }, { h: "Started", f: (r) => when(r.started_at) },
    { h: "Projects", n: 1, f: (r) => r.contracts }, { h: "Participants", n: 1, f: (r) => r.members },
    { h: "Requests", n: 1, f: (r) => r.requests }, { h: "Paid", n: 1, f: (r) => r.paid },
    { h: "Median request → paid", n: 1, f: (r) => dur(r.request_to_paid.median_s) }, { h: "p90", n: 1, f: (r) => dur(r.request_to_paid.p90_s) },
    { h: "By agents", n: 1, f: (r) => pct(r.automated_share) }, { h: "To a person", n: 1, f: (r) => r.human_approvals },
    { h: "Cost / payout", n: 1, f: (r) => usd(r.cost_per_payout_micro) }, { h: "Ledger · rail", f: (r) => `${r.ledgers.join("/")} · ${r.rails.join("/")}` },
  ], R.runs, "No scale run yet. Run scripts/scale_run.py against this engine.");

  // research
  $("#res-src").textContent = `Source: ${R.source} · ledger ${R.ledger} · payment rail ${R.rail} · read ${when(R.read_at)}. Scale-run contracts are counted under their institution here too; the efficiency figures above leave them out.`;
  const inst = R.institutions.filter((i) => !pick || i.institution === pick);
  table($("#res-inst"), [
    { h: "Institution", f: (r) => r.institution }, { h: "Contracts", n: 1, f: (r) => r.contracts },
    { h: "Participants", n: 1, f: (r) => r.members }, { h: "Requests", n: 1, f: (r) => r.requests },
    { h: "Delivered", n: 1, f: (r) => r.delivered }, { h: "Withheld", n: 1, f: (r) => r.withheld },
    { h: "Paid", n: 1, f: (r) => r.paid }, { h: "Spent", n: 1, f: (r) => usd(r.paid_micro) },
    { h: "Median request → paid", n: 1, f: (r) => dur(r.request_to_paid.median_s) },
    { h: "By agents", n: 1, f: (r) => pct(r.automated_share) }, { h: "Unpaid", n: 1, f: (r) => r.unpaid_delivered },
  ], inst, "No research contract on this engine yet.");
  table($("#res-c"), [
    { h: "Contract", f: (r) => r.contract }, { h: "Institution", f: (r) => r.institution }, { h: "Title", wrap: 1, f: (r) => r.title },
    { h: "Run", f: (r) => r.run || "posted by a person" }, { h: "Status", f: (r) => r.status },
    { h: "Participants", n: 1, f: (r) => r.members }, { h: "Weeks run", n: 1, f: (r) => r.weeks_run },
    { h: "Paid", n: 1, f: (r) => r.paid }, { h: "Spent", n: 1, f: (r) => usd(r.paid_micro) },
    { h: "Median request → paid", n: 1, f: (r) => dur(r.request_to_paid.median_s) }, { h: "Rail", f: (r) => r.rail },
  ], R.contracts.filter((c) => !pick || c.institution === pick).slice().reverse());

  // vault
  if (!V.ok) {
    $("#v-src").textContent = `Data market not reachable from this engine (${V.source}): ${V.why}`;
    table($("#v-org"), [], []); table($("#v-deals"), [], []);
  } else {
    $("#v-src").textContent = `Source: ${V.source} · ${V.window} · ledger ${V.ledger} · ${V.accounts} accounts · read ${when(V.read_at)}. Members are simulated agents unless a person signed up.`;
    table($("#v-org"), [
      { h: "Buyer organization", f: (r) => r.buyer }, { h: "Deals", n: 1, f: (r) => r.deals },
      { h: "Paid", n: 1, f: (r) => r.settled }, { h: "Refused", n: 1, f: (r) => r.refused },
      { h: "Why refused", wrap: 1, f: (r) => Object.entries(r.reasons).map(([k, n]) => `${k} (${n})`).join(", ") || "none" },
      { h: "Data kinds", wrap: 1, f: (r) => r.kinds.join(", ") }, { h: "Payments", n: 1, f: (r) => r.payments },
      { h: "Spent", n: 1, f: (r) => usd(r.paid_micro) }, { h: "Median request → paid", n: 1, f: (r) => dur(r.request_to_paid.median_s) },
      { h: "Cost / payout", n: 1, f: (r) => usd(r.cost_per_payout_micro) },
    ], V.orgs.filter((o) => !pick || o.buyer === pick));
    table($("#v-deals"), [
      { h: "Deal", f: (r) => `C${r.id}` }, { h: "When", f: (r) => when(r.created) }, { h: "Buyer", f: (r) => r.buyer },
      { h: "Data", f: (r) => r.kind }, { h: "Owners", n: 1, f: (r) => r.sellers }, { h: "Status", f: (r) => r.status },
      { h: "Reason", wrap: 1, f: (r) => r.payments ? "" : (r.reason || "") }, { h: "Paid", n: 1, f: (r) => r.payments ? usd(r.paid_micro) : "not paid" },
      { h: "Rail", f: (r) => r.rail === "ap4m" ? "AP4M" : r.rail === "xrpl" ? "XRPL escrow" : "" },
      { h: "Request → paid", n: 1, f: (r) => r.request_to_paid_s == null ? "" : dur(r.request_to_paid_s) },
      { h: "Receipt", html: 1, f: (r) => r.tx_url ? `<a href="${esc(r.tx_url)}" target="_blank" rel="noopener">tx ↗</a>` : "" },
    ], V.deals.filter((x) => !pick || x.buyer === pick));
  }

  // AP4M
  const rail = A.rail && A.rail.pools ? Object.entries(A.rail.pools).map(([k, p]) => `${k} pool ${p.spent_rlusd}/${p.cap_rlusd} RLUSD* spent`).join(" · ") : (A.rail && A.rail.why) || "rail budget not read (AP4M_RAIL_URL not set on this engine)";
  $("#a-src").textContent = `Source: ${A.source} · XRPL EVM Testnet (chain ${A.chain_id}) · ${rail}`;
  table($("#a-runs"), [
    { h: "Run", f: (r) => r.run_id }, { h: "Task", wrap: 1, f: (r) => r.task }, { h: "Paid", n: 1, f: (r) => r.paid },
    { h: "Refused", n: 1, f: (r) => r.refused }, { h: "Why refused", wrap: 1, f: (r) => r.refusals.join("; ") || "none" },
    { h: "Total", n: 1, f: (r) => `${r.total_paid_rlusd} RLUSD*` },
    { h: "Vouchers", html: 1, f: (r) => r.txs.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">${i + 1}↗</a>`).join(" ") },
    { h: "Receipt", html: 1, f: (r) => r.receipt_url ? `<a href="${esc(r.receipt_url)}" target="_blank" rel="noopener">receipt ↗</a>` : "" },
  ], A.runs, "No AP4M run record in ap4m/receipts.");

  $("#foot").innerHTML = `* ${esc(d.footnote)}. All participants and readings are synthetic. Times are differences between timestamps the systems wrote themselves (request recorded → payment recorded).`;
}

function chart(runs) {
  const el = $("#chart");
  if (!runs.length) { el.innerHTML = `<p class="empty">No scale run measured yet.</p>`; return; }
  const W = 900, H = 240, L = 60, B = 46, T = 20, bw = Math.min(70, (W - L - 20) / runs.length - 18);
  const max = Math.max(...runs.map((r) => r.request_to_paid.p90_s || r.request_to_paid.median_s || 0), 0.001);
  const y = (v) => T + (H - T - B) * (1 - v / max);
  const step = (W - L - 20) / runs.length;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Median time from request to payment per run">`;
  for (const f of [0, 0.5, 1]) s += `<line x1="${L}" x2="${W - 10}" y1="${y(max * f)}" y2="${y(max * f)}" stroke="var(--border)"/><text x="${L - 6}" y="${y(max * f) + 4}" font-size="11" text-anchor="end" fill="var(--text-2)">${esc(dur(max * f))}</text>`;
  runs.forEach((r, i) => {
    const x = L + i * step + (step - bw) / 2, m = r.request_to_paid.median_s || 0, p = r.request_to_paid.p90_s || 0;
    s += `<rect x="${x}" y="${y(m)}" width="${bw}" height="${H - B - y(m)}" rx="4" fill="var(--brand)"><title>${esc(r.run)}: median ${dur(m)}, p90 ${dur(p)}</title></rect>`;
    s += `<line x1="${x + bw / 2}" x2="${x + bw / 2}" y1="${y(p)}" y2="${y(m)}" stroke="var(--text-2)" stroke-dasharray="3 3"/><line x1="${x + bw / 4}" x2="${x + 3 * bw / 4}" y1="${y(p)}" y2="${y(p)}" stroke="var(--text-2)"/>`;
    s += `<text x="${x + bw / 2}" y="${y(m) - 6}" font-size="11" text-anchor="middle" fill="var(--text)">${esc(dur(m))}</text>`;
    s += `<text x="${x + bw / 2}" y="${H - B + 16}" font-size="11" text-anchor="middle" fill="var(--text)">${r.contracts}×${Math.round(r.members / r.contracts)}</text>`;
    s += `<text x="${x + bw / 2}" y="${H - B + 30}" font-size="10" text-anchor="middle" fill="var(--text-2)">${r.paid} paid</text>`;
  });
  s += `</svg><p class="small muted">Bars: median request → paid per run; dashed tick: p90. Under each bar: projects × participants per project, and payments made.</p>`;
  el.innerHTML = s;
}

async function load() {
  $("#read").textContent = "reading…";
  try {
    const r = await fetch("/api/institutions/overview", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    data = await r.json();
    render();
  } catch (e) {
    $("#read").textContent = `could not read the engine: ${e.message}`;
  }
}

$("#reload").addEventListener("click", load);
$("#inst").addEventListener("change", () => data && render());
load();
setInterval(load, 30000);
