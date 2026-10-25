"""Prepare a local engine so the UniQdata app demo has several pending requests for one participant.

Runs two study rounds of the synthetic sleep study (mock ledger) through the same HTTP calls the
console uses, then prints the participant's open requests. The UniQdata Flutter demo build
(UNIQDATA_RESEARCH_CONSENT_DEMO=true) loads them into its consent sheet and approves them all with
one passkey signature through POST /api/p/{pid}/consents/challenge and /consents/approve.

    LEDGER=mock AGENTRAIL_ANCHOR_S=0 python -m uvicorn agentrail.web:app --port 8000
    python scripts/prepare_uniqdata_app_demo.py [--base http://127.0.0.1:8000] [--pid P-017] [--rounds 2]

The demo harness (/api/dev/*) answers on localhost only. Synthetic data, no Testnet funds needed.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

LAB = "org_sleeplab"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--pid", default="P-017")
    ap.add_argument("--rounds", type=int, default=2)
    a = ap.parse_args()

    def call(method, path, body=None, token=None, ok=(200,)):
        req = urllib.request.Request(
            a.base + path, method=method, data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            if e.code in ok:
                return None
            raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:300]}")

    def login(sub):
        return call("POST", f"/api/dev/login/{sub}")["access_token"]

    call("POST", "/api/reset?ledger=mock", token=login("operator"))
    researcher = login(f"researcher@{LAB}")
    participant = login(a.pid)
    for n in range(a.rounds):
        if n:
            # The participant's agent answers the round first (opening the app does this),
            # then the week closes and the next request for the remaining items opens.
            call("GET", f"/api/p/{a.pid}", token=participant)
            call("POST", "/api/study/close-round", token=researcher)
        if n == 0:
            # One approved spec and budget; later rounds re-send it (a new goal would need new approvals).
            call("POST", "/api/study/goal", {"goal": ""}, researcher)
            approval = call("POST", "/api/study/approvals", token=researcher)
            for sub in (f"approver:owner@{LAB}", f"approver:compliance@{LAB}"):
                sig = call("POST", f"/api/dev/devices/{sub}/sign-approval/{approval['id']}")
                call("POST", f"/api/study/approvals/{approval['id']}/signatures", sig, login(sub))
        sent = call("POST", "/api/study/send", token=researcher)
        print(f"round {n + 1}: send ok={sent.get('ok', True)} status={sent.get('status')}", file=sys.stderr)
    view = call("GET", f"/api/p/{a.pid}", token=participant)
    open_ = [r for r in view["requests"] if r["status"] in ("open", "partly_open")]
    print(json.dumps([{"request": r["id"], "status": r["status"], "reward_xrp": r["reward_xrp"],
                       "items": [i["item"] for i in r["items"] if i["class"] == "approval"]} for r in open_]))


if __name__ == "__main__":
    main()
