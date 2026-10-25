"""Dashboard: one page, JSON state, buttons that run the scenes."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from . import scenario

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


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
