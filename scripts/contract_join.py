"""Join a research contract over HTTP, as one person or as a batch of test accounts.

Each joiner gets its own Ed25519 key, kept in a gitignored file on this machine (.contract_keys.json);
only the public half goes to the engine. The joiner signs the consent document the engine returns, then
signs in with the same key. Test accounts store generated test readings (labelled so) unless they join
with a UniQdata account the engine has in its UNIQDATA_ROSTER.

    # post a contract (localhost, or AGENTRAIL_POSTING_CODE in X-Posting-Code)
    python scripts/contract_join.py post --api http://localhost:8000 --terms terms.json
    # 50 test accounts, mixed automation, generated test readings for weeks 1-4
    python scripts/contract_join.py join --api URL --contract RC1-xxxxxx --invite CODE --count 50
    # the 50 sandbox UniQdata accounts the engine holds (UNIQDATA_ROSTER on the engine)
    python scripts/contract_join.py join --api URL --contract RC1-xxxxxx --invite CODE --roster .uniqdata_roster.json
    # one person (a teammate) with their own choice
    python scripts/contract_join.py join --api URL --contract RC1-xxxxxx --invite CODE --name daniel --automation confirm_each
    # researcher: run a week, see the console
    python scripts/contract_join.py round --api URL --contract RC1-xxxxxx --week 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx
from nacl.signing import SigningKey

KEYS = ".contract_keys.json"
MIX = ["auto_all"] * 6 + ["auto_standard"] * 3 + ["confirm_each"]   # what test accounts choose; people choose their own


def _keys() -> dict:
    return json.load(open(KEYS)) if os.path.exists(KEYS) else {}


def _save(k: dict):
    with open(KEYS, "w") as f:
        json.dump(k, f, indent=1)
    os.chmod(KEYS, 0o600)


def _key(name: str) -> SigningKey:
    k = _keys()
    if name not in k:
        k[name] = {"seed": SigningKey.generate().encode().hex()}
        _save(k)
    return SigningKey(bytes.fromhex(k[name]["seed"]))


def _sign(sk: SigningKey, msg: str) -> str:
    return sk.sign(msg.encode()).signature.hex()


def token(c: httpx.Client, sub: str, sk: SigningKey) -> dict:
    n = c.post("/api/auth/challenge", json={"sub": sub}).json()["nonce"]
    r = c.post("/api/auth/token", json={"sub": sub, "nonce": n,
                                        "signature": _sign(sk, f"agentrail-login|agentrail-api|{sub}|{n}")})
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def join_one(c, cid, invite, name, automation, weeks, uniqdata=None) -> str:
    sk = _key(name)
    body = {"invite_code": invite, "public_key": sk.verify_key.encode().hex(), "automation": automation}
    if uniqdata:
        body["uniqdata_account"] = uniqdata
    s = c.post(f"/api/contracts/{cid}/join/start", json=body)
    s.raise_for_status()
    s = s.json()
    gen = weeks if not uniqdata else []
    r = c.post(f"/api/contracts/{cid}/join/complete",
               json={"pid": s["pid"], "signature": _sign(sk, s["sign"]), "generate_test_weeks": gen})
    r.raise_for_status()
    k = _keys()
    k[name].update({"pid": s["pid"], "contract": cid})
    _save(k)
    return s["pid"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["post", "join", "round", "console"])
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--terms")
    ap.add_argument("--contract")
    ap.add_argument("--invite")
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--roster")
    ap.add_argument("--name")
    ap.add_argument("--automation", default="confirm_each", choices=["confirm_each", "auto_standard", "auto_all"])
    ap.add_argument("--weeks", default="1-4", help="weeks of generated test readings, e.g. 1-4 (test accounts)")
    ap.add_argument("--week", type=int)
    a = ap.parse_args()
    hdr = {"X-Posting-Code": os.environ["AGENTRAIL_POSTING_CODE"]} if os.environ.get("AGENTRAIL_POSTING_CODE") else {}
    c = httpx.Client(base_url=a.api.rstrip("/"), timeout=600, headers=hdr)
    w0, w1 = (int(x) for x in a.weeks.split("-"))
    weeks = list(range(w0, w1 + 1))

    if a.cmd == "post":
        sk = _key("researcher")
        r = c.post("/api/contracts", json={"terms": json.load(open(a.terms)), "researcher_key": sk.verify_key.encode().hex()})
        if r.status_code >= 400:
            sys.exit(f"{r.status_code}: {r.text}")
        out = r.json()
        k = _keys()
        k["researcher"].update({"sub": out["researcher_sub"], "contract": out["contract"]["id"]})
        _save(k)
        print(json.dumps({"contract": out["contract"]["id"], "invite_code": out["invite_code"],
                          "ethics_credential": out["ethics_credential"]}, indent=1))
        return
    if a.cmd == "join":
        done = []
        if a.name:
            done.append(join_one(c, a.contract, a.invite, a.name, a.automation, weeks if a.count == 0 else []))
        if a.roster:
            for i, rid in enumerate(sorted(json.load(open(a.roster)))):
                done.append(join_one(c, a.contract, a.invite, f"roster:{rid}", MIX[i % len(MIX)], [], uniqdata=rid))
        for i in range(a.count):
            done.append(join_one(c, a.contract, a.invite, f"test:{a.contract}:{i + 1:02d}", MIX[i % len(MIX)], weeks))
        print(f"joined {len(done)}: {', '.join(done[:5])}{' …' if len(done) > 5 else ''}")
        return
    r = _keys()["researcher"]
    h = token(c, r["sub"], _key("researcher"))
    if a.cmd == "round":
        out = c.post(f"/api/contracts/{a.contract}/rounds", json={"week": a.week}, headers=h).json()
        print(json.dumps({k: out[k] for k in ("week", "members", "summary")}, indent=1))
        for x in out["results"][:10]:
            print(x["person"], x["status"], (x.get("escrow_finish") or {}).get("url") or "")
    else:
        out = c.get(f"/api/contracts/{a.contract}/console", headers=h).json()
        print(json.dumps({k: out[k] for k in ("id", "members", "spent_drops", "budget_drops", "rounds")}, indent=1))


if __name__ == "__main__":
    main()
