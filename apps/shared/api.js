// Engine client shared by the researcher console and the participant app (docs/API.md).
// `base` is "" when the page is served by the engine itself, or the engine origin when
// another app (UniQLab, the UniQdata WebView) mounts these modules.
//
// Every /api route needs a bearer token for one subject (agentrail/security/rbac.py).
// `token(sub)` returns one; the default asks the engine's demo devices (/api/dev/login/{sub}),
// which only answers on a local dev engine. A host app passes its own `token` instead.

import { setSettlementAsset } from "./ui.js";

export const STUDY = "org_sleeplab";
export const RESEARCHER = `researcher@${STUDY}`;
export const approverSub = (signer) => `approver:${signer}@${STUDY}`;

// Access code for a public demo deploy (AGENTRAIL_SANDBOX_CODE): taken from ?code= once and kept per browser.
export function storedSandboxCode() {
  try {
    const q = new URLSearchParams(location.search).get("code");
    if (q) localStorage.setItem("ar-code", q);
    return q || localStorage.getItem("ar-code") || "";
  } catch { return ""; }
}

export function engine(base = "", { token, sandboxCode = storedSandboxCode() } = {}) {
  const root = base.replace(/\/$/, "");
  const tokens = new Map();

  async function devToken(sub) {
    const res = await fetch(`${root}/api/dev/login/${encodeURIComponent(sub)}`, { method: "POST", headers: sandboxCode ? { "X-Sandbox-Code": sandboxCode } : {} });
    if (!res.ok) throw Object.assign(new Error(`sign-in for ${sub} -> ${res.status}`), { status: res.status });
    return (await res.json()).access_token;
  }
  async function bearer(sub, fresh) {
    if (!sub) return null;
    if (fresh || !tokens.has(sub)) tokens.set(sub, await (token || devToken)(sub));
    return tokens.get(sub);
  }

  async function call(method, path, body, sub, retried = false) {
    const t = await bearer(sub, retried);
    const headers = {};
    if (sandboxCode) headers["X-Sandbox-Code"] = sandboxCode;
    if (body) headers["Content-Type"] = "application/json";
    if (t) headers.Authorization = `Bearer ${t}`;
    const res = await fetch(root + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    if (res.status === 401 && sub && !retried) return call(method, path, body, sub, true);   // token expired
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      const err = new Error(`${method} ${path} -> ${res.status}`);
      err.status = res.status;
      err.detail = text;
      throw err;
    }
    const data = await res.json();
    setSettlementAsset(data.study?.asset ?? data.asset);
    return data;
  }
  const get = (p, sub = RESEARCHER) => call("GET", p, null, sub);
  const post = (p, b, sub = RESEARCHER) => call("POST", p, b || {}, sub);
  const P = (pid) => `/api/p/${encodeURIComponent(pid)}`;

  return {
    base: root,
    reset: (ledger) => { tokens.clear(); return post(`/api/reset${ledger ? `?ledger=${ledger}` : ""}`, {}, "operator"); },
    events: (after = 0) => get(`/api/events?after=${after}`),
    study: () => get("/api/study"),
    setGoal: (goal) => post("/api/study/goal", { goal }),
    // Budget approval: the researcher opens it, each approver signs on their own device.
    openApproval: () => post("/api/study/approvals"),
    approval: (aid) => get(`/api/study/approvals/${aid}`),
    signApproval: async (signer, aid) => {
      const sub = approverSub(signer);
      const sig = await call("POST", `/api/dev/devices/${encodeURIComponent(sub)}/sign-approval/${aid}`, {}, null);
      return post(`/api/study/approvals/${aid}/signatures`, sig, sub);
    },
    send: () => post("/api/study/send"),
    closeRound: () => post("/api/study/close-round"),
    sweep: () => post("/api/study/sweep"),
    releaseHeld: () => post("/api/study/payout/release"),
    decideCase: (id, reviewer_id, confirm) => post(`/api/study/cases/${id}/decide`, { reviewer_id, confirm }, `reviewer@${STUDY}`),
    bundle: (oid) => get(`/api/study/bundle/${oid}`),

    participant: (pid) => get(P(pid), pid),
    preview: (pid, rid) => get(`${P(pid)}/preview?request=${rid}`, pid),
    approve: (pid, rid, items) => post(`${P(pid)}/requests/${rid}/approve`, { items }, pid),
    decline: (pid, rid) => post(`${P(pid)}/requests/${rid}/decline`, {}, pid),
    pause: (pid) => post(`${P(pid)}/pause`, {}, pid),
    resume: (pid) => post(`${P(pid)}/resume`, {}, pid),
    revoke: (pid) => post(`${P(pid)}/revoke`, {}, pid),
    respond: (pid, caseId, text) => post(`${P(pid)}/cases/${caseId}/respond`, { text }, pid),
    resumeRequests: (pid) => post(`${P(pid)}/resume-requests`, {}, pid),
    uniqdata: (pid, project) => get(`${P(pid)}/uniqdata${project ? `?project=${encodeURIComponent(project)}` : ""}`, pid),
  };
}

// Poll /api/events once a second and call onChange(events, first) when anything new arrives.
// Both pages watch the same event stream, so an action on one shows on the other within a second.
// A full refresh also runs every `refreshEvery` ticks, so a page notices an engine reset made
// from the other page (event ids start again from 1 after a reset).
export function watch(api, onChange, { interval = 1000, refreshEvery = 5 } = {}) {
  let last = 0;
  let first = true;
  let n = 0;
  let stopped = false;
  let timer;
  async function tick() {
    try {
      let got = [];
      for (;;) {
        const r = await api.events(last);
        r.events = r.events.filter((e) => e.kind !== "access");   // request log, not study activity
        got = got.concat(r.events);
        last = r.last;
        if (r.events.length < 500) break;
      }
      n += 1;
      if (first || got.length || n % refreshEvery === 0) {
        if (!first && !got.length && last > 0) {
          const probe = await api.events(last - 1);   // the last event we saw is gone after a reset
          if (!probe.events.length) {
            last = 0;
            first = true;
            return tick();
          }
        }
        onChange(got, first);
        first = false;
      }
    } catch (_) {
      // engine restarting; keep polling
    }
    if (!stopped) timer = setTimeout(tick, interval);
  }
  tick();
  return {
    stop() { stopped = true; clearTimeout(timer); },
    restart() { last = 0; first = true; },
  };
}

// The participant app cannot read the study's event stream (that needs a researcher token), so it
// polls its own view and calls onChange(view) when anything in it changed.
export function watchSelf(api, pid, onChange, { interval = 1500 } = {}) {
  let seen = "";
  let stopped = false;
  let timer;
  async function tick() {
    try {
      const v = await api.participant(pid);
      const key = JSON.stringify(v);
      if (key !== seen) { seen = key; onChange(v); }
    } catch (_) {
      // engine restarting; keep polling
    }
    if (!stopped) timer = setTimeout(tick, interval);
  }
  tick();
  return { stop() { stopped = true; clearTimeout(timer); } };
}
