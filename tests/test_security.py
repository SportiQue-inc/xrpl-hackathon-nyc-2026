"""Attack reproductions. Each test performs the attack and asserts it is blocked.

They also run against the code before the security layer (imports stay inside the tests, and the
login helper sends no token when the harness login does not exist), where they fail: see the
before/after table in docs/SECURITY.md.
"""
import base64
import json
import time

import pytest
from fastapi.testclient import TestClient

from agentrail import study, web
from agentrail.cohort import HERO
from tests.llm_doubles import capable_needs

LAB = study.LAB
OTHER = "P-001"


@pytest.fixture
def c():
    try:
        from agentrail.security.http import reset_rate_limits
        reset_rate_limits()
    except ImportError:
        pass
    c = TestClient(web.app)
    c.post("/api/reset?ledger=mock", headers=login(c, "operator"))
    web._state["w"].robot_buyer.propose = capable_needs
    return c


def login(c, sub) -> dict:
    r = c.post(f"/api/dev/login/{sub}")
    return {"Authorization": "Bearer " + r.json()["access_token"]} if r.status_code == 200 else {}


R, P, O = f"researcher@{LAB}", HERO, "operator"
OWNER, COMPLIANCE = f"approver:owner@{LAB}", f"approver:compliance@{LAB}"


def sent(c):
    c.post("/api/study/goal", json={"goal": "back to 80% power"}, headers=login(c, R))
    a = approve(c)
    assert a["status"] == "executed"
    c.post("/api/study/send", headers=login(c, R))
    return a


def approve(c, who=(OWNER, COMPLIANCE)):
    a = c.post("/api/study/approvals", headers=login(c, R)).json()
    out = a
    for sub in who:
        sig = c.post(f"/api/dev/devices/{sub}/sign-approval/{a['id']}").json()
        out = c.post(f"/api/study/approvals/{a['id']}/signatures", json=sig, headers=login(c, sub)).json()
    return out


def delivered_order(c):
    seen = c.get("/api/study", headers=login(c, R)).json()["contributions"]
    return next(x["order_id"] for x in seen if x["status"] == "delivered")


# ---------- 1. authentication and default deny ----------

def test_every_api_route_needs_a_token(c):
    from agentrail.security.rbac import POLICY
    for (method, path), rule in POLICY.items():
        if rule.public or not path.startswith("/api/"):
            continue
        url = path.replace("{pid}", HERO).replace("{rid}", "1").replace("{oid}", "1").replace(
            "{aid}", "1").replace("{case_id}", "1").replace("{scene}", "a")
        r = c.request(method, url, json={})
        assert r.status_code == 401, (method, path, r.status_code)


def test_every_route_has_an_access_rule():
    from agentrail.security.rbac import OPEN_PATHS, POLICY
    for route in web.app.routes:
        for m in getattr(route, "methods", None) or []:
            if m == "HEAD" or route.path in OPEN_PATHS:
                continue
            assert (m, route.path) in POLICY, f"{m} {route.path} has no rule (default deny would hide it)"


def test_unknown_route_is_denied_even_with_a_token(c):
    from fastapi import APIRouter
    router = APIRouter()
    router.add_api_route("/api/new-feature", lambda: {"secret": 1}, methods=["GET"])
    web.app.include_router(router)
    try:
        assert c.get("/api/new-feature", headers=login(c, O)).status_code == 403
    finally:
        web.app.router.routes = [r for r in web.app.router.routes if getattr(r, "path", "") != "/api/new-feature"]


def test_bundle_with_health_data_is_not_readable_without_the_study_team(c):
    sent(c)
    oid = delivered_order(c)
    assert c.get(f"/api/study/bundle/{oid}").status_code == 401
    for who in (P, O, OWNER):
        assert c.get(f"/api/study/bundle/{oid}", headers=login(c, who)).status_code == 403, who
    assert c.get(f"/api/study/bundle/{oid}", headers=login(c, R)).json()["hash_matches"]


def _forge(token: str, **changes) -> str:
    h, b, s = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(b + "=="))
    claims.update(changes)
    nb = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"{h}.{nb}.{s}"


def test_forged_tokens_are_refused(c):
    tok = login(c, P)["Authorization"][7:]
    none_head = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    for bad in (_forge(tok, role="researcher", scope=LAB),          # privilege escalation in the payload
                _forge(tok, sub=OTHER, scope=OTHER),                 # someone else's identity
                _forge(tok, exp=int(time.time()) - 10),              # expired
                none_head + "." + tok.split(".")[1] + ".",           # alg=none
                "garbage"):
        assert c.get(f"/api/p/{HERO}", headers={"Authorization": "Bearer " + bad}).status_code == 401


def test_login_needs_the_enrolled_device_and_a_fresh_nonce(c):
    from agentrail.security.devices import Device
    ch = c.post("/api/auth/challenge", json={"sub": HERO}).json()
    attacker = Device("attacker")
    r = c.post("/api/auth/token", json={"sub": HERO, "nonce": ch["nonce"], "signature": attacker.sign_challenge(ch["nonce"])})
    assert r.status_code == 401
    dev = web._state["w"].security.devices[HERO]
    ch = c.post("/api/auth/challenge", json={"sub": HERO}).json()
    good = {"sub": HERO, "nonce": ch["nonce"], "signature": dev.sign_challenge(ch["nonce"])}
    assert c.post("/api/auth/token", json=good).status_code == 200
    assert c.post("/api/auth/token", json=good).status_code == 401          # replayed challenge


def test_logout_revokes_the_token(c):
    h = login(c, P)
    assert c.post("/api/auth/logout", headers=h).status_code == 200
    assert c.get(f"/api/p/{HERO}", headers=h).status_code == 401


# ---------- 4. participants act only on their own record ----------

def test_participant_cannot_read_or_act_for_someone_else(c):
    sent(c)
    h = login(c, P)
    assert c.get(f"/api/p/{OTHER}", headers=h).status_code == 403
    w = web._state["w"]
    other_rid = next(r["id"] for r in w.study.requests.values() if r["person"] == OTHER)
    for path in (f"/api/p/{OTHER}/requests/{other_rid}/decline", f"/api/p/{OTHER}/revoke", f"/api/p/{OTHER}/pause"):
        assert c.post(path, headers=h).status_code == 403, path
    # Own path, someone else's request id: still refused
    assert c.post(f"/api/p/{HERO}/requests/{other_rid}/decline", headers=h).status_code == 404
    assert w.study.requests[other_rid]["status"] != "declined"


def test_other_roles_cannot_act_for_a_participant(c):
    sent(c)
    for who in (R, O, OWNER):
        assert c.post(f"/api/p/{HERO}/revoke", headers=login(c, who)).status_code == 403, who


def test_revoke_is_undone_only_by_a_consent_signed_on_the_participants_device(c):
    sent(c)
    h = login(c, P)
    assert c.post(f"/api/p/{HERO}/revoke", headers=h).status_code == 200
    assert c.post(f"/api/p/{HERO}/resume", headers=h).status_code == 409
    body = {"items": ["sleep.daily"], "automation": "confirm_each"}
    draft = c.post(f"/api/p/{HERO}/consent", json=body, headers=h).json()
    from agentrail.security.devices import Device
    forged = Device("not-the-phone").sign_consent(draft["doc_hash"])
    assert c.post(f"/api/p/{HERO}/consent", json={**body, "signature": forged}, headers=h).status_code == 403
    w = web._state["w"]
    assert w.store.one("SELECT status FROM consents WHERE person_id=? AND buyer_id=?", HERO, LAB)["status"] == "revoked"
    sig = w.security.devices[HERO].sign_consent(draft["doc_hash"])
    r = c.post(f"/api/p/{HERO}/consent", json={**body, "signature": sig}, headers=h).json()
    assert r["ok"] and r["doc_hash"] == draft["doc_hash"]


# ---------- 3. co-signing ----------

def test_one_person_cannot_release_the_budget(c):
    c.post("/api/study/goal", json={"goal": "x"}, headers=login(c, R))
    a = c.post("/api/study/approvals", headers=login(c, R)).json()
    owner_sig = c.post(f"/api/dev/devices/{OWNER}/sign-approval/{a['id']}").json()
    url = f"/api/study/approvals/{a['id']}/signatures"
    assert c.post(url, json=owner_sig, headers=login(c, OWNER)).json()["status"] == "open"
    assert c.post(url, json=owner_sig, headers=login(c, OWNER)).status_code == 409         # same approver twice
    assert c.post(url, json=owner_sig, headers=login(c, COMPLIANCE)).status_code == 400    # owner's key, other name
    assert c.post(url, json=owner_sig, headers=login(c, R)).status_code == 403             # not an approver
    assert c.post("/api/study/approve", json={"signers": ["owner", "compliance"]},
                  headers=login(c, R)).status_code == 403                                   # harness is not for staff
    assert c.get("/api/study", headers=login(c, R)).json()["study"]["budget_xrp"] == 0


def test_signature_cannot_be_replayed_on_another_approval_or_after_expiry(c, monkeypatch):
    from agentrail.security import cosign
    c.post("/api/study/goal", json={"goal": "x"}, headers=login(c, R))
    a = c.post("/api/study/approvals", headers=login(c, R)).json()
    old = c.post(f"/api/dev/devices/{OWNER}/sign-approval/{a['id']}").json()
    w = web._state["w"]
    with w.store.tx() as x:
        x.execute("UPDATE approvals SET expires_at=? WHERE id=?", (time.time() - 1, a["id"]))
    r = c.post(f"/api/study/approvals/{a['id']}/signatures", json=old, headers=login(c, OWNER))
    assert r.status_code == 410
    b = c.post("/api/study/approvals", headers=login(c, R)).json()                          # fresh nonce
    assert b["nonce"] != a["nonce"]
    r = c.post(f"/api/study/approvals/{b['id']}/signatures", json=old, headers=login(c, OWNER))
    assert r.status_code == 400


def test_the_treasury_cannot_be_drained_by_repeating_goal_and_approval(c):
    first = sent(c)
    w = web._state["w"]
    old = [json.loads(r["payload"]) for r in w.store.q("SELECT payload FROM approval_signatures WHERE approval_id=?",
                                                         first["id"])]
    before = c.get("/api/study", headers=login(c, R)).json()["study"]["budget_xrp"]
    for _ in range(3):                                       # the researcher alone, over and over
        c.post("/api/study/goal", json={"goal": "x"}, headers=login(c, R))
        a = c.post("/api/study/approvals", headers=login(c, R)).json()
        for sub, sig in zip((OWNER, COMPLIANCE), sorted(old, key=lambda x: x["signer"] != w.study.signers["owner"])):
            r = c.post(f"/api/study/approvals/{a['id']}/signatures", json=sig, headers=login(c, sub))
            assert r.status_code == 400                      # yesterday's signatures do not sign today's approval
    assert c.get("/api/study", headers=login(c, R)).json()["study"]["budget_xrp"] == before


def test_reviewer_decides_only_under_their_own_name(c):
    h = login(c, f"reviewer@{LAB}")
    r = c.post("/api/study/cases/1/decide", json={"reviewer_id": "someone-else", "confirm": True}, headers=h)
    assert r.status_code == 403
    assert c.post("/api/study/cases/1/decide", json={"reviewer_id": R, "confirm": True},
                  headers=login(c, R)).status_code == 403


# ---------- 2. key separation ----------

def test_engine_and_ledger_hold_no_private_keys_of_other_parties(c):
    sent(c)
    p = login(c, P)
    rid = c.get(f"/api/p/{HERO}", headers=p).json()["requests"][0]["id"]
    c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey", "heart_rate.daily"]}, headers=p)
    w = web._state["w"]
    assert LAB not in w.engine.box_keys                                      # institution keeps its box key
    assert w.store.one("SELECT COUNT(*) n FROM escrow_keys")["n"] == 0       # K never stored by the engine
    for addr in w.study.signers.values():                                    # approver keys stay on devices
        assert addr not in getattr(w.ledger, "wallets", {})
    held = w.store.one("SELECT o.order_key FROM orders o JOIN payments p ON p.order_id=o.id "
                       "WHERE o.seller_id=? AND p.condition IS NOT NULL AND p.finish_blob IS NULL", HERO)
    assert held, "the held round of the followed participant"
    k = w.cohort_people[HERO].keyring.fulfillment(held["order_key"])[8:].lower()
    dump = "\n".join(str(tuple(r)) for t in ("orders", "payments", "bundles", "events", "outbox", "escrow_keys")
                     for r in w.store.q(f"SELECT * FROM {t}")).lower()
    assert k not in dump                                                     # K of an unpublished round: nowhere


# ---------- 6. audit log ----------

def test_edited_or_deleted_log_rows_are_detected(c):
    sent(c)
    h = login(c, O)
    assert c.get("/api/ops/audit/verify", headers=h).json()["ok"]
    assert c.post("/api/ops/audit/anchor", headers=h).json()["ok"]
    w = web._state["w"]
    mid = w.store.one("SELECT id FROM events ORDER BY id LIMIT 1 OFFSET 20")["id"]
    w.store.conn.execute("UPDATE events SET message='nothing happened' WHERE id=?", (mid,))
    v = c.get("/api/ops/audit/verify", headers=h).json()
    assert not v["ok"] and v["broken_at"] == mid
    c.post("/api/reset?ledger=mock", headers=h)
    sent(c)
    w = web._state["w"]
    mid = w.store.one("SELECT id FROM events ORDER BY id LIMIT 1 OFFSET 20")["id"]
    w.store.conn.execute("DELETE FROM events WHERE id=?", (mid,))
    assert not c.get("/api/ops/audit/verify", headers=login(c, O)).json()["ok"]


def test_every_state_change_is_recorded_with_its_actor(c):
    sent(c)
    rows = web._state["w"].store.q("SELECT actor, message FROM events WHERE kind='access'")
    assert any(r["actor"] == R and "/api/study/send" in r["message"] for r in rows)


# ---------- 7. HTTP basics ----------

def test_other_origins_get_no_cors_grant(c):
    r = c.options("/api/study", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET",
                                         "Access-Control-Request-Headers": "authorization"})
    assert "access-control-allow-origin" not in r.headers
    assert c.post(f"/api/p/{HERO}/revoke", headers={"Origin": "https://evil.example"}).status_code == 401


def test_security_headers(c):
    r = c.get("/api/study", headers=login(c, R))
    for h in ("content-security-policy", "x-content-type-options", "x-frame-options", "referrer-policy"):
        assert h in r.headers
    assert r.headers["cache-control"] == "no-store"


def test_request_bodies_are_strict(c):
    h = login(c, R)
    assert c.post("/api/study/goal", json={"goal": "x" * 501}, headers=h).status_code == 422
    assert c.post("/api/study/goal", json={"goal": "x", "budget_xrp": 999}, headers=h).status_code == 422
    sent(c)
    p = login(c, P)
    rid = c.get(f"/api/p/{HERO}", headers=p).json()["requests"][0]["id"]
    bad = c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["x'; DROP TABLE consents;--"]}, headers=p)
    assert bad.status_code == 422


def test_login_is_rate_limited(c):
    from agentrail.security.http import reset_rate_limits
    reset_rate_limits()
    codes = [c.post("/api/auth/challenge", json={"sub": HERO}).status_code for _ in range(40)]
    assert 429 in codes


def test_secrets_are_masked_in_the_event_log(c):
    from xrpl.wallet import Wallet
    seed = Wallet.create().seed
    w = web._state["w"]
    w.store.log("engine", "error", f"failed with seed {seed} and key sk-proj-abcdefghijklmnopqrstuvwx")
    msg = w.store.one("SELECT message FROM events ORDER BY id DESC LIMIT 1")["message"]
    assert seed not in msg and "sk-proj-abc" not in msg


def test_prod_mode_closes_the_demo_harness(c, monkeypatch):
    from agentrail.security.http import reset_rate_limits
    reset_rate_limits()
    monkeypatch.setenv("AGENTRAIL_ENV", "prod")
    assert c.post(f"/api/dev/login/{HERO}").status_code == 404
    assert c.post("/api/run/a", headers={"Authorization": "Bearer x"}).status_code == 404
    from agentrail.security.auth import Authority
    monkeypatch.delenv("AGENTRAIL_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        Authority()
