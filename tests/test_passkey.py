"""A participant with a passkey approves a request only by signing its statement; the signed
statement hash reaches the escrow memo, the event log and the participant's view."""
import base64
import hashlib
import json
import os

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from agentrail import study, web
from agentrail.cohort import HERO
from agentrail.security.http import reset_rate_limits
from tests.llm_doubles import capable_needs
from tests.test_security import login

R = f"researcher@{study.LAB}"
ORIGIN = "http://localhost:8000"


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def cbor(v) -> bytes:
    def head(major, n):
        if n < 24:
            return bytes([major << 5 | n])
        for ai, size in ((24, 1), (25, 2), (26, 4)):
            if n < 1 << (8 * size):
                return bytes([major << 5 | ai]) + n.to_bytes(size, "big")
    if isinstance(v, int):
        return head(0, v) if v >= 0 else head(1, -1 - v)
    if isinstance(v, bytes):
        return head(2, len(v)) + v
    if isinstance(v, str):
        return head(3, len(v.encode())) + v.encode()
    return head(5, len(v)) + b"".join(cbor(k) + cbor(x) for k, x in v.items())


class Authenticator:
    """What the browser and Touch ID return, for RP ID localhost."""

    def __init__(self, rp_id="localhost", origin=ORIGIN):
        self.key, self.cred, self.count = ec.generate_private_key(ec.SECP256R1()), os.urandom(16), 0
        self.rp, self.origin = hashlib.sha256(rp_id.encode()).digest(), origin

    def create(self, opts):
        n = self.key.public_key().public_numbers()
        cose = cbor({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")})
        auth = self.rp + bytes([0x45]) + (0).to_bytes(4, "big") + bytes(16) + len(self.cred).to_bytes(2, "big") \
            + self.cred + cose
        cdj = json.dumps({"type": "webauthn.create", "challenge": opts["challenge"], "origin": self.origin}).encode()
        return {"credentialId": b64u(self.cred), "rawId": b64u(self.cred), "clientDataJson": b64u(cdj),
                "attestationObject": b64u(cbor({"fmt": "none", "attStmt": {}, "authData": auth})),
                "transports": ["internal"]}

    def get(self, opts, flags=0x05):
        self.count += 1
        auth = self.rp + bytes([flags]) + self.count.to_bytes(4, "big")
        cdj = json.dumps({"type": "webauthn.get", "challenge": opts["challenge"], "origin": self.origin}).encode()
        sig = self.key.sign(auth + hashlib.sha256(cdj).digest(), ec.ECDSA(hashes.SHA256()))
        return {"credentialId": b64u(self.cred), "rawId": b64u(self.cred), "authenticatorData": b64u(auth),
                "clientDataJson": b64u(cdj), "signature": b64u(sig)}


@pytest.fixture
def c():
    reset_rate_limits()
    c = TestClient(web.app)
    c.post("/api/reset?ledger=mock", headers=login(c, "operator"))
    web._state["w"].robot_buyer.propose = capable_needs
    c.post("/api/study/goal", json={"goal": ""}, headers=login(c, R))
    a = c.post("/api/study/approvals", headers=login(c, R)).json()
    for sub in (f"approver:owner@{study.LAB}", f"approver:compliance@{study.LAB}"):
        sig = c.post(f"/api/dev/devices/{sub}/sign-approval/{a['id']}").json()
        c.post(f"/api/study/approvals/{a['id']}/signatures", json=sig, headers=login(c, sub))
    c.post("/api/study/send", headers=login(c, R))
    return c


def registered(c, me):
    key = Authenticator()
    opts = c.post(f"/api/p/{HERO}/passkey/register/options", headers=me).json()["publicKey"]
    assert opts["rp"]["id"] == "localhost" and opts["authenticatorSelection"]["userVerification"] == "required"
    r = c.post(f"/api/p/{HERO}/passkey/register/complete", json=key.create(opts), headers=me)
    assert r.status_code == 200, r.text
    assert c.get(f"/api/p/{HERO}/passkey", headers=me).json()["registered"]
    return key


def open_request(c, me):
    return c.get(f"/api/p/{HERO}", headers=me).json()["requests"][0]["id"]


def test_signed_approval_reaches_the_escrow_memo_and_the_log(c):
    me = login(c, HERO)
    key = registered(c, me)
    rid = open_request(c, me)
    ch = c.post(f"/api/p/{HERO}/requests/{rid}/challenge", json={"items": ["fatigue.survey"]}, headers=me).json()
    st = ch["statement"]
    assert st["items"] == ["fatigue.survey"] and st["request"] == rid and st["price_drops"] > 0
    assert unb64u(ch["publicKey"]["challenge"]).hex() == ch["statement_hash"]
    r = c.post(f"/api/p/{HERO}/requests/{rid}/approve",
               json={"items": ["fatigue.survey"], "assertion": key.get(ch["publicKey"])}, headers=me)
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["signed"]["statement_hash"] == ch["statement_hash"]
    bound = v["approvals"][-1]
    assert bound["status"] == "bound" and bound["orders"]
    w = web._state["w"]
    memos = [w.ledger.txs[o["escrow_tx"]]["Memo"] for o in bound["orders"]]
    assert all(f"consent:{ch['statement_hash'][:16]}" in m for m in memos)
    kinds = [e["kind"] for e in v["audit"]]
    assert kinds.index("passkey_signed") < kinds.index("approval_bound")
    assert all(e["hash"] for e in v["audit"])


def test_with_a_passkey_a_plain_approve_is_refused(c):
    me = login(c, HERO)
    registered(c, me)
    rid = open_request(c, me)
    r = c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey"]}, headers=me)
    assert r.status_code == 403
    assert not [x for x in c.get(f"/api/p/{HERO}", headers=me).json()["contributions"] if "fatigue.survey" in x["items"]
                and x["weeks"][0] in (3, 4, 5) and x["status"] == "delivered"]


def test_signature_over_other_items_or_reused_is_refused(c):
    me = login(c, HERO)
    key = registered(c, me)
    rid = open_request(c, me)
    ch = c.post(f"/api/p/{HERO}/requests/{rid}/challenge", json={"items": ["fatigue.survey"]}, headers=me).json()
    a = key.get(ch["publicKey"])
    wider = c.post(f"/api/p/{HERO}/requests/{rid}/approve",
                   json={"items": ["fatigue.survey", "heart_rate.daily"], "assertion": a}, headers=me)
    assert wider.status_code == 403
    ch = c.post(f"/api/p/{HERO}/requests/{rid}/challenge", json={"items": ["fatigue.survey"]}, headers=me).json()
    a = key.get(ch["publicKey"])
    assert c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey"], "assertion": a},
                  headers=me).status_code == 200
    again = c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey"], "assertion": a},
                   headers=me)
    assert again.status_code == 403


def test_wrong_origin_missing_verification_or_forged_signature_is_refused(c):
    me = login(c, HERO)
    key = registered(c, me)
    rid = open_request(c, me)

    def attempt(assertion_of):
        ch = c.post(f"/api/p/{HERO}/requests/{rid}/challenge", json={"items": ["fatigue.survey"]}, headers=me).json()
        return c.post(f"/api/p/{HERO}/requests/{rid}/approve",
                      json={"items": ["fatigue.survey"], "assertion": assertion_of(ch["publicKey"])}, headers=me)

    phish = Authenticator(origin="https://uniqdata-login.example")
    phish.key, phish.cred = key.key, key.cred
    assert attempt(phish.get).status_code == 403
    assert attempt(lambda o: key.get(o, flags=0x01)).status_code == 403          # no user verification
    other = Authenticator()
    other.cred = key.cred
    assert attempt(other.get).status_code == 403                                  # not the registered key
    assert attempt(key.get).status_code == 200


def test_another_participant_cannot_ask_for_my_challenge(c):
    me = login(c, HERO)
    registered(c, me)
    rid = open_request(c, me)
    r = c.post(f"/api/p/{HERO}/requests/{rid}/challenge", json={"items": ["fatigue.survey"]},
               headers=login(c, "P-001"))
    assert r.status_code == 403
