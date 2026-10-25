"""The two app pages: served by the engine, mountable from UniQLab, and worded as research contribution."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentrail import study, web
from agentrail.security.http import reset_rate_limits
from agentrail.cohort import HERO
from tests.llm_doubles import capable_needs
from tests.test_security import login

APPS = Path(__file__).parent.parent / "apps"
R = f"researcher@{study.LAB}"
OWNER, COMPLIANCE = f"approver:owner@{study.LAB}", f"approver:compliance@{study.LAB}"

# Words the project never shows (designer brief, common rules). Engine field names the client
# reads (reward_xrp) are not UI copy and are stripped before the check.
BANNED = ["reward", "rlu", "sell", "sale", "anonymous", "fraud", "penalty", "fine",
          "데이터 판매", "리워드", "토큰 보상", "재식별 불가", "질병 예측", "의료 AI 진단"]
FIELDS = ["reward_xrp"]


def test_no_banned_words_in_the_apps():
    hits = []
    for f in APPS.rglob("*"):
        if f.suffix not in (".js", ".html", ".css", ".tsx", ".ts", ".dart"):   # page code, not READMEs
            continue
        text = f.read_text(encoding="utf-8")
        for name in FIELDS:
            text = text.replace(name, "")
        for w in BANNED:
            pat = re.escape(w) if not w.isascii() else rf"\b{re.escape(w)}\b"
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                hits.append(f"{f.relative_to(APPS)}: {w!r} near {text[max(0, m.start() - 30):m.end() + 30]!r}")
    assert not hits, "\n".join(hits)


def test_pages_and_shared_modules_are_served():
    c = TestClient(web.app)
    assert "mountResearcher" in c.get("/console").text
    assert "mountParticipant" in c.get("/participant").text
    for f in ("api.js", "ui.js", "ui.css", "researcher.js", "participant.js"):
        assert c.get(f"/apps/shared/{f}").status_code == 200


def test_before_after_demo_is_served_and_frames_only_itself():
    c = TestClient(web.app)
    r = c.get("/demo?mode=after", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/apps/demo/index.html?mode=after"
    for f in ("index.html", "lab.html", "phone.html", "lab.js", "phone.js", "common.js", "demo.css"):
        r = c.get(f"/apps/demo/{f}")
        assert r.status_code == 200
        assert r.headers["x-frame-options"] == "SAMEORIGIN" and "frame-ancestors 'self'" in r.headers["content-security-policy"]
    assert c.get("/console").headers["x-frame-options"] == "DENY"
    assert c.get("/try", follow_redirects=False).headers["location"] == "/apps/try/index.html"
    for f in ("try/index.html", "live/index.html", "live/live.js", "live/me.html", "live/me.js"):
        assert c.get(f"/apps/{f}").status_code == 200


def test_try_link_preserves_the_judges_access_code():
    c = TestClient(web.app)
    r = c.get("/try?code=judges-2026", follow_redirects=False)
    assert r.headers["location"] == "/apps/try/index.html?code=judges-2026"


@pytest.fixture
def c():
    reset_rate_limits()
    c = TestClient(web.app)
    c.post("/api/reset?ledger=mock", headers=login(c, "operator"))
    web._state["w"].robot_buyer.propose = capable_needs
    c.post("/api/study/goal", json={"goal": ""}, headers=login(c, R))
    a = c.post("/api/study/approvals", headers=login(c, R)).json()
    for sub in (OWNER, COMPLIANCE):
        sig = c.post(f"/api/dev/devices/{sub}/sign-approval/{a['id']}").json()
        c.post(f"/api/study/approvals/{a['id']}/signatures", json=sig, headers=login(c, sub))
    c.post("/api/study/send", headers=login(c, R))
    return c


def test_console_fields_the_pages_read(c):
    s = c.get("/api/study", headers=login(c, R)).json()
    assert s["study"]["irb"] == "IRB-SYN-2026-014" and s["withdrawals"] == []
    me = login(c, HERO)
    p = c.get(f"/api/p/{HERO}", headers=me).json()
    items = {i["item"]: i for i in p["requests"][0]["items"]}
    assert items["blood_pressure.daily"]["sensitive"] and not items["fatigue.survey"]["sensitive"]
    c.post(f"/api/p/{HERO}/requests/{p['requests'][0]['id']}/approve", json={"items": ["fatigue.survey"]}, headers=me)
    mine = [x for x in c.get("/api/study", headers=login(c, R)).json()["contributions"]
            if x["pseudonym"] == p["person"]["study_pseudonym"]]
    assert mine and all(x["items"] for x in mine)
    assert all("ts" in e for e in c.get("/api/events", headers=login(c, R)).json()["events"])
    c.post(f"/api/p/{HERO}/revoke", headers=me)
    w = c.get("/api/study", headers=login(c, R)).json()["withdrawals"]
    assert [x["kind"] for x in w] == ["revoke"] and HERO not in str(w)


def test_uniqdata_records_for_one_participant(c):
    me = login(c, HERO)
    rid = c.get(f"/api/p/{HERO}", headers=me).json()["requests"][0]["id"]
    c.post(f"/api/p/{HERO}/requests/{rid}/approve", json={"items": ["fatigue.survey"]}, headers=me)
    before = c.get(f"/api/p/{HERO}/uniqdata", headers=me).json()
    assert [g["consent_type"] for g in before["consent_grants"]] == ["research_participation"]
    assert before["payout_receipts"] and before["withdrawal"] is None
    assert c.get(f"/api/p/{HERO}/uniqdata", headers=login(c, "P-001")).status_code == 403
    c.post(f"/api/p/{HERO}/revoke", headers=me)
    after = c.get(f"/api/p/{HERO}/uniqdata", params={"privacy_epoch": 2}, headers=me).json()
    assert after["withdrawal"]["boundary"]["superseding_epoch"] == 3
    assert HERO not in str(after)


def test_demo_devices_answer_remote_visitors_only_with_the_access_code(monkeypatch):
    remote = TestClient(web.app, client=("203.0.113.5", 4000))
    sub = f"researcher@{study.LAB}"
    assert remote.post(f"/api/dev/login/{sub}").status_code == 403
    monkeypatch.setenv("AGENTRAIL_SANDBOX_CODE", "judges-2026")
    assert remote.post(f"/api/dev/login/{sub}", headers={"X-Sandbox-Code": "wrong"}).status_code == 403
    assert remote.post(f"/api/dev/login/{sub}", headers={"X-Sandbox-Code": "judges-2026"}).status_code == 200
    assert remote.post("/api/dev/login/operator", headers={"X-Sandbox-Code": "judges-2026"}).status_code == 403
    monkeypatch.setenv("AGENTRAIL_SANDBOX_CODE", "short")    # too short to count as a code
    assert remote.post(f"/api/dev/login/{sub}", headers={"X-Sandbox-Code": "short"}).status_code == 403
    v = remote.get("/api/public/live").json()
    assert {"study", "heatmap", "institution", "events"} <= set(v) and all(e["kind"] != "access" for e in v["events"])
