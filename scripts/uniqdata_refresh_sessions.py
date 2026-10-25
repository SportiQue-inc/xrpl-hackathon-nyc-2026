"""Issue fresh sandbox sessions for every account in a roster (local UniQdata sandbox only).

Sandbox accounts have no password, so their session is re-issued inside the sandbox container, as
the first one was; passkeys and consents stay as they are.
    python scripts/uniqdata_refresh_sessions.py [--roster .uniqdata_roster.json]
"""
import argparse
import json
import os
import subprocess

IN_CONTAINER = r'''
import sys, uuid, json
from app.core.security import create_access_token
for pid in json.loads(sys.stdin.read()):
    print(pid + "=" + create_access_token(uuid.UUID(pid), session_id=uuid.uuid4(), auth_level=2))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default=".uniqdata_roster.json")
    ap.add_argument("--container", default="uniqdata-hk-core-1")
    a = ap.parse_args()
    roster = json.load(open(a.roster))
    ids = [s["person_id"] for s in roster.values()]
    run = subprocess.run(["docker", "exec", "-i", "-w", "/app", "-e", "PYTHONPATH=/app", a.container, "python", "-c",
                          IN_CONTAINER], input=json.dumps(ids), text=True, capture_output=True, check=True)
    tokens = dict(line.split("=", 1) for line in run.stdout.splitlines() if len(line) > 37 and line[36] == "=")
    for s in roster.values():
        s["token"] = tokens[s["person_id"]]
    fd = os.open(a.roster + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(roster, f)
    os.replace(a.roster + ".tmp", a.roster)
    print(f"{len(tokens)} sessions refreshed")


if __name__ == "__main__":
    main()
