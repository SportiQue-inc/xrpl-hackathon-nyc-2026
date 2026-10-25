"""Dashboard: one page, JSON state, buttons that run the scenes."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import scenario, study
from .llm import voice

app = FastAPI(title="AgentRail")
_lock = threading.Lock()
_state: dict = {}


def world() -> scenario.World:
    if "w" not in _state:
        reset()
    return _state["w"]


@app.post("/api/reset")
def reset(ledger: str | None = None):
    with _lock:
        kind = ledger or os.environ.get("LEDGER", "mock")
        _state["w"] = scenario.build_world(kind, os.environ.get("AGENTRAIL_DB", ":memory:"))
        _state["results"] = {}
    return {"ok": True, "ledger": kind}


@app.post("/api/run/{scene}")
def run(scene: str, budget: float | None = None):
    w = world()
    with _lock:
        if scene == "a":
            r = scenario.scene_a(w, budget)
        elif scene == "a-guarded":
            r = scenario.scene_a_guarded(w)
            scene = "a"
        elif scene == "b":
            r = scenario.scene_b(w)
        elif scene == "c":
            r = scenario.scene_c(w)
        elif scene == "d":
            r = scenario.scene_d(w)
        elif scene == "h":
            r = scenario.scene_h(w)
        elif scene == "boundaries":
            from . import boundaries
            r = boundaries.run(w)
        else:
            return {"error": "unknown scene"}
        _state["results"][scene] = r
    return r


@app.get("/api/state")
def state():
    w = world()
    s = w.store
    rows = lambda sql, *a: [dict(r) for r in s.q(sql, *a)]
    orders = rows("""SELECT o.id, o.buyer_id, o.seller_id, o.payee_id, o.product_id, o.scope, o.purpose,
                     o.price_drops, o.status, o.note, o.bundle_hash, o.policy_snapshot,
                     p.tx_hash, p.status AS pay_status, p.ledger_index
                     FROM orders o LEFT JOIN payments p ON p.order_id=o.id ORDER BY o.id""")
    for o in orders:
        o["url"] = w.ledger.explorer_url(o["tx_hash"]) if o["tx_hash"] else None
        o["scope"] = json.loads(o["scope"])
        o["policy_snapshot"] = json.loads(o["policy_snapshot"])
    accounts = {}
    named = {pid: w.engine.party(pid)["address"] for pid in ("org_robodev", "org_sleeplab")}
    named["org_robodev treasury"] = w.treasury
    for pid, address in named.items():
        p = {"address": address}
        try:
            accounts[pid] = {"address": p["address"], **w.ledger.account_settings(p["address"])}
        except Exception as e:  # network hiccup should not break the page
            accounts[pid] = {"address": p["address"], "error": str(e)}
    return {
        "ledger": w.ledger.name,
        "voice": voice().label(),
        "mandates": rows("SELECT * FROM mandates"),
        "orders": orders,
        "events": rows("SELECT id, scene, actor, kind, message, data FROM events ORDER BY id"),
        "consents": rows("SELECT person_id, buyer_id, purpose, items, automation, status, version, doc_hash "
                         "FROM consents ORDER BY person_id"),
        "approvals": rows("SELECT * FROM approval_requests ORDER BY id"),
        "exceptions": rows("SELECT * FROM exceptions ORDER BY id"),
        "accounts": accounts,
        "results": _state.get("results", {}),
    }


# ---------- participant app and researcher console (docs/API.md) ----------

def _call(fn, *a, **k):
    w = world()
    with _lock:
        try:
            return fn(w, *a, **k)
        except KeyError as e:
            raise HTTPException(404, f"not found: {e}")


@app.get("/api/events")
def events(after: int = 0):
    return _call(study.events, after)


@app.get("/api/boundaries")
def boundaries_view():
    from . import boundaries
    return _call(boundaries.view)


@app.get("/api/p/{pid}")
def participant(pid: str):
    return _call(study.participant_view, pid)


@app.get("/api/p/{pid}/preview")
def participant_preview(pid: str, request: int):
    return _call(study.preview, pid, request)


@app.post("/api/p/{pid}/requests/{rid}/approve")
def participant_approve(pid: str, rid: int, body: dict = Body(default={})):
    return _call(study.participant_approve, pid, rid, list(body.get("items") or []))


@app.post("/api/p/{pid}/requests/{rid}/decline")
def participant_decline(pid: str, rid: int):
    return _call(study.participant_decline, pid, rid)


@app.post("/api/p/{pid}/pause")
def participant_pause(pid: str):
    return _call(study.participant_pause, pid)


@app.post("/api/p/{pid}/resume")
def participant_resume(pid: str):
    return _call(study.participant_pause, pid, True)


@app.post("/api/p/{pid}/revoke")
def participant_revoke(pid: str):
    return _call(study.participant_revoke, pid)


@app.get("/api/study")
def study_state():
    return _call(study.study_view)


@app.post("/api/study/goal")
def study_goal(body: dict = Body(default={})):
    return _call(study.set_goal, body.get("goal") or "")


@app.post("/api/study/approve")
def study_approve(body: dict = Body(default={})):
    return _call(study.approve, list(body.get("signers") or []))


@app.post("/api/study/send")
def study_send():
    return _call(study.send)


@app.post("/api/study/close-round")
def study_close_round():
    return _call(study.close_round)


@app.post("/api/study/sweep")
def study_sweep():
    return _call(study.sweep)


@app.get("/api/study/bundle/{oid}")
def study_bundle(oid: int):
    return _call(study.open_bundle, oid)


def _page(*parts):
    p = Path(__file__).parent.parent.joinpath(*parts)
    if not p.exists():
        raise HTTPException(404, "page not built yet")
    return FileResponse(p)


def _card(name, desc, url, skills):
    return {"name": name, "description": desc, "version": "0.1.0",
            "supportedInterfaces": [{"url": url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
            "capabilities": {"streaming": False, "pushNotifications": False,
                             "extensions": [{"uri": "https://github.com/google-agentic-commerce/ap2", "required": False},
                                            {"uri": "https://x402.org", "required": False}]},
            "defaultInputModes": ["application/json"], "defaultOutputModes": ["application/json"],
            "skills": skills}


@app.get("/.well-known/agent-card.json")
def research_agent_card():
    """A2A v1.0 Agent Card for the study's research agent (static; demo only)."""
    return _card("Sleep study research agent (synthetic)",
                 "Finds missing person-weeks in a study and sends participation requests; rewards by XRPL escrow.",
                 "/api/study", [{"id": "research_request", "name": "Participation request",
                                 "description": "Ask a participant's agent for protocol items and weeks.",
                                 "tags": ["research", "consent", "xrpl"]}])


@app.get("/agents/{pid}/.well-known/agent-card.json")
def personal_agent_card(pid: str):
    return _card(f"Personal agent of {pid} (synthetic)",
                 "Answers research participation requests within the person's consent; asks the person otherwise.",
                 f"/api/p/{pid}", [{"id": "answer_research_request", "name": "Answer participation request",
                                    "description": "auto / ask the person / blocked, then sealed contribution.",
                                    "tags": ["consent", "health-record", "xrpl-escrow"]}])


@app.get("/participant")
def participant_page():
    return _page("apps", "participant", "index.html")


@app.get("/console")
def console_page():
    return _page("apps", "researcher", "index.html")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
