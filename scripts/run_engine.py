"""Bring up the engine with its API and run one full health trade through that API.

    python scripts/run_engine.py                    # mock ledger, about 5 s
    LEDGER=testnet python scripts/run_engine.py     # XRPL Testnet (faucet wallets), about 40 min
    python scripts/run_engine.py --serve            # keep the API and dashboard up afterwards

Everything goes over HTTP to the same API the dashboard uses, signed in as each party:

  researcher   sets the goal (gap reading), opens the budget approval
  approvers    one alone is refused by the ledger (tefBAD_QUORUM); both co-sign on their own devices
  researcher   sends the participation requests (consent checked per person, escrows in Batch)
  operator     runs the boundary checks: consent, refusals (incl. the clinic export over HTTP 402),
               payout review and holdbacks, the three withdrawals (clawback, refund)
  researcher   on Testnet: sweeps until the held escrow's deadline has passed and it is refunded

Then GET /api/engine/check prints one row per flow with its ledger transaction; the exit code is 0
only if every flow passed. The run's database is kept (runs/<ledger>-<time>.db) so that
scripts/open_bundle.py can open any EscrowFinish of the run.
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

LAB = "org_sleeplab"
R, O = f"researcher@{LAB}", "operator"
OWNER, COMPLIANCE = f"approver:owner@{LAB}", f"approver:compliance@{LAB}"


class Api:
    def __init__(self, base):
        self.base, self.tokens = base, {}

    def call(self, method, path, body=None, who=None, allow=()):
        h = {"Content-Type": "application/json"}
        if who:
            if who not in self.tokens:
                self.tokens[who] = self.call("POST", f"/api/dev/login/{who}")["access_token"]
            h["Authorization"] = "Bearer " + self.tokens[who]
        data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=3600) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            if e.code in allow:
                return {"status": e.code, "detail": json.loads(e.read() or b"{}").get("detail")}
            sys.exit(f"{method} {path}: HTTP {e.code} {e.read()[:300]!r}")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--serve", action="store_true", help="keep the API and dashboard running after the trade")
    ap.add_argument("--goal", default="Bring the primary analysis back to 80% power before the interim report.")
    a = ap.parse_args()

    kind = os.environ.setdefault("LEDGER", "mock")
    if "AGENTRAIL_DB" not in os.environ:
        os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
        os.environ["AGENTRAIL_DB"] = os.path.join(ROOT, "runs", f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.db")
    os.environ.setdefault("AGENTRAIL_ANCHOR_S", "0")

    import uvicorn
    from agentrail import web
    from agentrail.engine_check import summary

    server = uvicorn.Server(uvicorn.Config(web.app, host="127.0.0.1", port=a.port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.1)
    api = Api(f"http://127.0.0.1:{a.port}")
    t0 = time.time()
    log(f"engine up at {api.base} (ledger {kind}, db {os.environ['AGENTRAIL_DB']})")

    api.call("POST", "/api/reset", who=O)
    log("world built: parties, credentials, multisig treasury, cohort of 50 (synthetic)")
    g = api.call("POST", "/api/study/goal", {"goal": a.goal}, who=R)
    log(f"proposal: gaps {g.get('proposal', {}).get('gaps')} (source {g.get('proposal', {}).get('source')})")
    one = api.call("POST", "/api/study/approve", {"signers": ["owner"]}, who=O)
    log(f"one approver alone: {one.get('engine_result')}")
    ap_ = api.call("POST", "/api/study/approvals", who=R)     # the one the lone approver already signed
    res = ap_
    for sub in (OWNER, COMPLIANCE):
        sig = api.call("POST", f"/api/dev/devices/{sub}/sign-approval/{ap_['id']}")
        r = api.call("POST", f"/api/study/approvals/{ap_['id']}/signatures", sig, who=sub, allow=(409,))
        res = res if r.get("status") == 409 else r
    log(f"co-signed budget release: {res.get('status')}")
    s = api.call("POST", "/api/study/send", who=R)
    log(f"requests sent; power {s.get('heatmap', {}).get('power_before')} -> {s.get('heatmap', {}).get('power')}")
    api.call("POST", "/api/run/boundaries", who=O)
    log("boundary checks done (consent, refusals, payout review, withdrawals)")

    if kind == "testnet":
        end = time.time() + 300
        while time.time() < end:
            r = api.call("POST", "/api/study/sweep", who=R)
            if r.get("refunded"):
                log(f"held escrow refunded after its deadline: orders {r['refunded']}")
                break
            time.sleep(10)

    chk = api.call("GET", "/api/engine/check", who=R)
    print(summary(chk["flows"]))
    ok = all(f["ok"] for f in chk["flows"])
    log(f"{'ALL FLOWS PASSED' if ok else 'SOME FLOWS FAILED'} in {time.time() - t0:.0f} s; "
        f"db kept at {os.environ['AGENTRAIL_DB']}")
    if a.serve:
        log(f"serving: dashboard {api.base}/console, participant {api.base}/participant (Ctrl-C to stop)")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
