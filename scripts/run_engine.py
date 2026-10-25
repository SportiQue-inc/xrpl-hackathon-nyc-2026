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
  researcher   buys per-column data under contracts the agents negotiate (profiles, substitutes, a
               shorter period), checks each contribution as it arrives and releases its held 20% only
               on a pass

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

    def call(self, method, path, body=None, who=None, allow=(), _retried=False):
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
            if e.code == 401 and who and not _retried:   # a Testnet run outlives the 15-minute token
                self.tokens.pop(who, None)
                return self.call(method, path, body, who, allow, _retried=True)
            if e.code in allow:
                return {"status": e.code, "detail": json.loads(e.read() or b"{}").get("detail")}
            sys.exit(f"{method} {path}: HTTP {e.code} {e.read()[:300]!r}")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--serve", action="store_true", help="keep the API and dashboard running after the trade")
    ap.add_argument("--uniqdata-server", help="UniQdata server whose dev lane holds the followed person's "
                    "records, e.g. https://api.kr.uniqdata.io; asks for the QA account password")
    ap.add_argument("--qa-fixture", default="core-authority-qa-v1")
    ap.add_argument("--goal", default="Bring the primary analysis back to 80% power before the interim report.")
    a = ap.parse_args()

    kind = os.environ.setdefault("LEDGER", "mock")
    if "AGENTRAIL_DB" not in os.environ:
        os.makedirs(os.path.join(ROOT, "runs"), exist_ok=True)
        os.environ["AGENTRAIL_DB"] = os.path.join(ROOT, "runs", f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.db")
    os.environ.setdefault("AGENTRAIL_ANCHOR_S", "0")

    uq = bool(os.environ.get("UNIQDATA_PERSON") or a.uniqdata_server)
    if a.uniqdata_server:
        import getpass
        from agentrail import uniqdata_live
        pw = getpass.getpass(f"UniQdata QA password for {a.qa_fixture} (dev lane, not shown or stored): ")
        uniqdata_live.CLIENT = uniqdata_live.server_login(a.uniqdata_server, a.qa_fixture, "subject", pw)
        del pw
        log(f"signed in to {a.uniqdata_server} dev lane as QA fixture {a.qa_fixture} (subject)")

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
    if uq:          # the followed person's records live in UniQdata
        d = api.call("GET", "/api/p/P-017/data", who="P-017")
        up = api.call("POST", "/api/p/P-017/data/upload", {}, who="P-017")
        log(f"P-017 uploaded {up['written']} records to UniQdata ({d['records']} before, {up['records']} now; "
            f"first record {up['receipts'][0]['record_hash'][:16] if up['receipts'] else '-'})")
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
    if uq:
        rid = api.call("GET", "/api/p/P-017", who="P-017")["requests"][0]["id"]
        pv = api.call("GET", f"/api/p/P-017/preview?request={rid}", who="P-017")
        log(f"P-017 preview: {pv['row_count']} rows from {pv['from']['records']} UniQdata records")
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

    k = api.call("POST", "/api/contract/round", who=R)
    log(f"data contracts: {k['providers_contracted']} providers, {k['usable']}/{k['target']} usable windows, "
        f"{k['unfit']} unfit caught ({', '.join(sorted(k['caught']))}); "
        f"{k['xrp_paid_for_unfit']} XRP paid for unfit")
    if kind == "testnet":          # held parts of passed contributions become releasable after the review time
        time.sleep(30)
        api.call("POST", "/api/study/payout/release", who=R)
    chk = api.call("GET", "/api/engine/check", who=R)
    print(summary(chk["flows"]))
    from agentrail.costs import line
    print(line(api.call("GET", "/api/costs", who=R)))
    from agentrail.binding import summary as proof_summary
    print(proof_summary(api.call("GET", "/api/proof", who=R)))
    from agentrail import report
    rp = os.path.join(os.path.dirname(os.environ["AGENTRAIL_DB"]) or ".", f"report-{kind}-{int(time.time())}.html")
    with open(rp, "w") as f:
        f.write(report.render(api.call("GET", "/api/contract/projection", who=R), None, chk, ledger=kind))
    log(f"run report written to {rp}")
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
