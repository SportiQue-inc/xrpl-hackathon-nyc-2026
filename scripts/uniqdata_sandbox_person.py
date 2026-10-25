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
import uuid

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.uniqdata_live import SoftPasskey  # noqa: E402

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--container", default="uniqdata-hk-core-1")
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--out", default=".uniqdata_person.json")
    a = ap.parse_args()

    pid = uuid.uuid4()
    email = f"agentrail-{pid.hex[:8]}@synthetic.local"
    run = subprocess.run(["docker", "exec", "-i", "-w", "/app", "-e", "PYTHONPATH=/app", a.container,
                          "python", "-", str(pid), email], input=IN_CONTAINER, text=True,
                         capture_output=True, check=True)
    token = next(line[6:] for line in run.stdout.splitlines() if line.startswith("TOKEN="))

    api = a.base.rstrip("/") + "/api/v1"
    h = {"Authorization": f"Bearer {token}", "X-App-Id": "uniqdata-auth"}
    o = httpx.post(f"{api}/auth/passkey/register/options", json={"email": email}, headers=h, timeout=30)
    o.raise_for_status()
    o = o.json()
    pk = SoftPasskey.new()
    pk.rp_id = o["rp"]["id"]
    r = httpx.post(f"{api}/auth/passkey/register/complete", headers=h, timeout=30,
                   json={"challengeId": o.get("challengeId"), "device_name": "agentrail-person-agent",
                         **pk.attestation(o["challenge"])})
    r.raise_for_status()
    token = r.json()["access_token"]
    h["Authorization"] = f"Bearer {token}"

    c = httpx.post(f"{api}/consents/", headers=h, timeout=30, json={
        "scopes": ["health:*:write:all"], "consent_type": "sensitive_health_collection",
        "policy_id": "sensitive_health_collection_v1", "policy_version": 1})
    c.raise_for_status()
    cid = c.json()["consent_id"]
    ap_ = httpx.post(f"{api}/consents/{cid}/approve", headers=h, json={}, timeout=30)
    ap_.raise_for_status()

    pk_path = a.out + ".passkey"
    pk.save(pk_path)
    fd = os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"base_url": a.base, "person_id": str(pid), "email": email, "token": token,
                   "passkey": pk_path, "collection_consent_id": cid,
                   "collection_consent_status": ap_.json()["status"]}, f)
    print(f"synthetic person {pid} ready; collection consent {ap_.json()['status']}; saved {a.out}")


if __name__ == "__main__":
    main()
