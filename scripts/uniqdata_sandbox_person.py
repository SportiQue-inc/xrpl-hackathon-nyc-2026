"""Create one synthetic person in a LOCAL UniQdata sandbox and save their session for the demo.

UniQdata's own sandbox (`docker-compose.sandbox.yml` in UniQdata/backend) must be running. Signup
needs email codes and identity providers that a laptop sandbox does not have, so two steps run
inside the sandbox container, as UniQdata's own sandbox scripts do: an account row for a
synthetic e-mail, and a first session token. Everything after that goes through UniQdata's public
API: first passkey (software key held by the person's agent), the sensitive-health collection
consent (create, then approve), and later the record writes and reads.

    python scripts/uniqdata_sandbox_person.py [--container uniqdata-hk-core-1] [--out .uniqdata_person.json]

The output file holds a local sandbox token and the software passkey: it is gitignored and only
ever describes a synthetic person.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.uniqdata_live import SoftPasskey, UniQdataClient  # noqa: E402

IN_CONTAINER = r'''
import asyncio, sys, uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import uniqdata_engine
from app.models.core_member import UserEmail
from app.core.security import create_access_token
pid, email = uuid.UUID(sys.argv[1]), sys.argv[2]
async def main():
    async with AsyncSession(uniqdata_engine) as s:
        s.add(UserEmail(person_id=pid, email=email, password_hash="!synthetic-no-login"))
        await s.commit()
asyncio.run(main())
print("TOKEN=" + create_access_token(pid, session_id=uuid.uuid4(), auth_level=2))
'''


def make_person(container: str, base: str, label: str) -> dict:
    """One synthetic UniQdata account: account row + first token (in the sandbox), then passkey and
    collection consent through UniQdata's API. Returns its session (token + software passkey)."""
    pid = uuid.uuid4()
    email = f"agentrail-{label.lower()}-{pid.hex[:6]}@synthetic.local"
    run = subprocess.run(["docker", "exec", "-i", "-w", "/app", "-e", "PYTHONPATH=/app", container,
                          "python", "-", str(pid), email], input=IN_CONTAINER, text=True,
                         capture_output=True, check=True)
    token = next(line[6:] for line in run.stdout.splitlines() if line.startswith("TOKEN="))
    api = base.rstrip("/") + "/api/v1"
    h = {"Authorization": f"Bearer {token}", "X-App-Id": "uniqdata-auth"}
    for wait in (20, 40, 60, 60, 0):              # the sandbox rate-limits passkey registration per client
        o = httpx.post(f"{api}/auth/passkey/register/options", json={"email": email}, headers=h, timeout=30)
        if o.status_code != 429 or not wait:
            break
        time.sleep(wait)
    o.raise_for_status()
    o = o.json()
    pk = SoftPasskey.new()
    pk.rp_id = o["rp"]["id"]
    r = httpx.post(f"{api}/auth/passkey/register/complete", headers=h, timeout=30,
                   json={"challengeId": o.get("challengeId"), "device_name": "agentrail-person-agent",
                         **pk.attestation(o["challenge"])})
    r.raise_for_status()
    client = UniQdataClient(base, r.json()["access_token"], pk)
    c = client._call("POST", "/consents/", {
        "scopes": ["health:*:write:all"], "consent_type": "sensitive_health_collection",
        "policy_id": "sensitive_health_collection_v1", "policy_version": 1})
    approved = client.approve_consent(c["consent_id"])
    return {"base_url": base, "person_id": str(pid), "email": email, "token": client.token,
            "passkey": pk.dump(), "collection_consent_id": c["consent_id"],
            "collection_consent_status": approved["status"]}


def _write_private(path: str, obj):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", default="uniqdata-hk-core-1")
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--out", default=".uniqdata_person.json")
    ap.add_argument("--cohort", action="store_true",
                    help="one account per cohort participant (fixtures), written as a roster to --out")
    ap.add_argument("--resume", action="store_true", help="keep accounts already in the roster")
    a = ap.parse_args()
    if not a.cohort:
        p = make_person(a.container, a.base, "p-017")
        _write_private(a.out, p)
        print(f"synthetic person {p['person_id']} ready; collection consent {p['collection_consent_status']}; saved {a.out}")
        return
    from agentrail.scenario import FIXTURE
    pids = [x["account_id"] for x in json.load(open(FIXTURE))["accounts"] if x["role"] == "participant"][:50]
    roster = json.load(open(a.out)) if os.path.exists(a.out) and a.resume else {}
    for i, pid in enumerate(pids):
        if pid in roster:
            continue
        roster[pid] = make_person(a.container, a.base, pid)
        _write_private(a.out, roster)                 # saved as it goes; a rerun starts a new roster
        print(f"[{i + 1}/{len(pids)}] {pid} ready", flush=True)
    print(f"{len(roster)} synthetic UniQdata accounts saved to {a.out}")


if __name__ == "__main__":
    main()
