"""Measure how the research-contract lane behaves as projects and participants grow, from real runs.

    python scripts/scale_run.py                               # in-process engine (LEDGER, AGENTRAIL_CONTRACTS_PAY from env)
    python scripts/scale_run.py --engine https://agentrail-try-production.up.railway.app   # the deployed engine
    python scripts/scale_run.py --steps 1x5,2x10,3x20         # projects x participants per project, one run per step

Each step posts that many research contracts (different institutions), joins that many participants to each with
their own Ed25519 keys and signed consent, stores generated test readings (labelled as such), and runs week 1.
The institution's agent asks, each participant's agent answers from its own consent, the engine pays (XRPL escrow
or AP4M, whatever the engine is set to). Nothing is estimated here: the engine records every timestamp and the
dashboard (/institutions) reads them. Each step carries its own run tag in the contract summary, so the dashboard
reports each step on its own and never mixes runs.

A share of participants keep "confirm each" (a person decides); the rest let their agent answer within the
consent. --confirm-share sets that share (default 0.2).

On the deployed engine, posting needs the posting code: AGENTRAIL_POSTING_CODE in the environment (never printed).
Budget: price per item 0.001 x 2 items = 0.002 RLUSD per participant-week, far under the AP4M 0.10 cap; the
default steps make 85 payments (0.17 RLUSD).
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentrail.security.devices import Device  # noqa: E402

INSTITUTIONS = ["Seoul Sleep Research Center", "NYC Fatigue Study Group", "Ulaanbaatar Cardio Institute",
                "Boston Activity Lab", "Busan Recovery Clinic", "Toronto Wearables Cohort",
                "Daejeon Circadian Lab", "Chicago Heart Rate Study"]
ITEMS = ["sleep.daily", "fatigue.survey"]
OUT = Path(__file__).resolve().parent.parent / "fixtures" / "scale-runs"


class Http:
    def __init__(self, base: str | None):
        if base:
            import httpx
            self.c = httpx.Client(base_url=base.rstrip("/"), timeout=900)
        else:
            os.environ.setdefault("AGENTRAIL_CONTRACTS_AUTORUN", "0")
            from fastapi.testclient import TestClient
            from agentrail import web
            self.c = TestClient(web.app)
        self.code = os.environ.get("AGENTRAIL_POSTING_CODE", "")

    def call(self, method: str, path: str, **kw):
        if path == "/api/contracts" and self.code:
            kw.setdefault("headers", {})["x-posting-code"] = self.code
        for attempt in range(4):
            r = self.c.request(method, path, **kw)
            if r.status_code != 429:
                break
            time.sleep(2 ** attempt)
        if r.status_code >= 400:
            raise SystemExit(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()


def token(h: Http, d: Device) -> dict:
    n = h.call("POST", "/api/auth/challenge", json={"sub": d.sub})["nonce"]
    t = h.call("POST", "/api/auth/token", json={"sub": d.sub, "nonce": n, "signature": d.sign_challenge(n)})
    return {"Authorization": "Bearer " + t["access_token"]}


def step(h: Http, run: str, projects: int, members: int, confirm_share: float, price: int) -> dict:
    t0 = time.time()
    posted = []
    for p in range(projects):
        inst = INSTITUTIONS[p % len(INSTITUTIONS)]
        r = Device(f"researcher-{run}-{p}")
        terms = {"title": f"Sleep and fatigue, week 1 ({inst})", "institution": inst, "irb_approval": f"IRB-{run}-{p + 1}",
                 "purpose": "sleep_research", "items": ITEMS, "weeks": [1, 1], "price_per_item_drops": price,
                 "budget_drops": price * len(ITEMS) * members, "capacity": max(members, 1),
                 "summary": f"[scale-run {run}] {projects} projects x {members} participants, synthetic test readings"}
        out = h.call("POST", "/api/contracts", json={"terms": terms, "researcher_key": r.public_hex})
        r.sub = out["researcher_sub"]
        posted.append((out["contract"]["id"], out["invite_code"], r))
    n_confirm = round(members * confirm_share)
    for cid, code, _ in posted:
        for i in range(members):
            d = Device(f"m-{run}-{cid}-{i}-{secrets.token_hex(2)}")
            auto = "confirm_each" if i < n_confirm else "auto_standard"
            s = h.call("POST", f"/api/contracts/{cid}/join/start",
                       json={"invite_code": code, "public_key": d.public_hex, "automation": auto})
            d.sub = s["pid"]
            h.call("POST", f"/api/contracts/{cid}/join/complete",
                   json={"pid": s["pid"], "signature": d.sign_consent(s["consent_hash"]), "generate_test_weeks": [1]})
    joined = time.time()
    rounds = [h.call("POST", f"/api/contracts/{cid}/rounds", json={"week": 1}, headers=token(h, r))
              for cid, _, r in posted]
    done = time.time()
    return {"run": run, "projects": projects, "members_per_project": members, "contracts": [c for c, _, _ in posted],
            "round_summaries": [r["summary"] for r in rounds], "setup_s": round(joined - t0, 2),
            "rounds_s": round(done - joined, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", help="engine base URL; default runs the engine in this process")
    ap.add_argument("--steps", default="1x5,2x10,3x20")
    ap.add_argument("--confirm-share", type=float, default=0.2)
    ap.add_argument("--price", type=int, default=1000, help="micro-units per item (1000 = 0.001)")
    a = ap.parse_args()
    h = Http(a.engine)
    stamp = time.strftime("%m%d%H%M", time.gmtime())
    results = []
    for s in a.steps.split(","):
        p, m = (int(x) for x in s.lower().split("x"))
        run = f"S-{stamp}-{p}x{m}"
        print(f"[scale] {run}: {p} projects x {m} participants ...", flush=True)
        results.append(step(h, run, p, m, a.confirm_share, a.price))
        print(f"[scale] {run}: done {results[-1]['round_summaries']}", flush=True)
    view = h.call("GET", "/api/institutions/overview")["research"]
    mine = [r for r in view["runs"] if r["run"] in {x["run"] for x in results}]
    rec = {"schema": "agentrail.scale-run.v1", "engine": a.engine or "in-process", "ledger": view["ledger"],
           "rail": view["rail"], "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "steps": results, "measured": mine}
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"scale-{stamp}.json"
    f.write_text(json.dumps(rec, indent=1))
    for r in mine:
        lat = r["request_to_paid"]
        print(f"{r['run']}: {r['contracts']} contracts, {r['members']} participants, {r['paid']} paid, "
              f"median request->paid {lat['median_s']} s, automated {r['automated_share']}")
    print(f"wrote {f}")


if __name__ == "__main__":
    main()
