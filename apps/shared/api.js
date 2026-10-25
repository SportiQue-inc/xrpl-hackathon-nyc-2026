// Engine client shared by the researcher console and the participant app (docs/API.md).
// `base` is "" when the page is served by the engine itself, or the engine origin when
// another app (UniQLab, the UniQdata WebView) mounts these modules.

export function engine(base = "") {
  const root = base.replace(/\/$/, "");

  async function call(method, path, body) {
    const res = await fetch(root + path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      const err = new Error(`${method} ${path} -> ${res.status}`);
      err.status = res.status;
      err.detail = text;
      throw err;
    }
    return res.json();
  }
  const get = (p) => call("GET", p);
  const post = (p, b) => call("POST", p, b || {});
  const P = (pid) => `/api/p/${encodeURIComponent(pid)}`;

  return {
    base: root,
    reset: (ledger) => post(`/api/reset${ledger ? `?ledger=${ledger}` : ""}`),
    events: (after = 0) => get(`/api/events?after=${after}`),
    study: () => get("/api/study"),
    setGoal: (goal) => post("/api/study/goal", { goal }),
    approveBudget: (signers) => post("/api/study/approve", { signers }),
    send: () => post("/api/study/send"),
    closeRound: () => post("/api/study/close-round"),
    sweep: () => post("/api/study/sweep"),
    releaseHeld: () => post("/api/study/payout/release"),
    decideCase: (id, reviewer_id, confirm) => post(`/api/study/cases/${id}/decide`, { reviewer_id, confirm }),
    bundle: (oid) => get(`/api/study/bundle/${oid}`),

    participant: (pid) => get(P(pid)),
    preview: (pid, rid) => get(`${P(pid)}/preview?request=${rid}`),
    approve: (pid, rid, items) => post(`${P(pid)}/requests/${rid}/approve`, { items }),
    decline: (pid, rid) => post(`${P(pid)}/requests/${rid}/decline`),
    pause: (pid) => post(`${P(pid)}/pause`),
    resume: (pid) => post(`${P(pid)}/resume`),
    revoke: (pid) => post(`${P(pid)}/revoke`),
    respond: (pid, caseId, text) => post(`${P(pid)}/cases/${caseId}/respond`, { text }),
    resumeRequests: (pid) => post(`${P(pid)}/resume-requests`),
    uniqdata: (pid, project) => get(`${P(pid)}/uniqdata${project ? `?project=${encodeURIComponent(project)}` : ""}`),
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
