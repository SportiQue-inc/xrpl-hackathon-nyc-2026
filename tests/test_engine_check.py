from fastapi.testclient import TestClient

from agentrail import engine_check, scenario, study, web

LAB = study.LAB
R, O = f"researcher@{LAB}", "operator"


def test_one_trade_over_the_api_passes_every_flow_with_a_ledger_tx():
    c = TestClient(web.app)
    tok = lambda sub: {"Authorization": "Bearer " + c.post(f"/api/dev/login/{sub}").json()["access_token"]}
    c.post("/api/reset?ledger=mock", headers=tok(O))
    c.post("/api/study/goal", json={"goal": "back to 80% power"}, headers=tok(R))
    assert c.post("/api/study/approve", json={"signers": ["owner"]}, headers=tok(O)).json()["engine_result"] == "tefBAD_QUORUM"
    a = c.post("/api/study/approvals", headers=tok(R)).json()
    sub = f"approver:compliance@{LAB}"
    sig = c.post(f"/api/dev/devices/{sub}/sign-approval/{a['id']}").json()
    assert c.post(f"/api/study/approvals/{a['id']}/signatures", json=sig, headers=tok(sub)).json()["status"] == "executed"
    c.post("/api/study/send", headers=tok(R))
    c.post("/api/run/boundaries", headers=tok(O))
    flows = c.get("/api/engine/check", headers=tok(R)).json()["flows"]
    assert [f["flow"] for f in flows] == list(engine_check.FLOWS)
    assert all(f["ok"] for f in flows), [f for f in flows if not f["ok"]]
    assert all(f["result"] == "tesSUCCESS" for f in flows if f["tx"])


def test_a_world_with_no_trade_fails_every_ledger_flow():
    w = scenario.build_world("mock", ":memory:")
    rows = {f["flow"]: f for f in engine_check.flows(w)}
    for name in ("escrow", "key_reveal", "holdback", "withdrawal_clawback", "batch", "amm", "x402"):
        assert not rows[name]["ok"], name


def test_a_tx_the_ledger_does_not_know_does_not_pass():
    w = scenario.build_world("mock", ":memory:")
    study.ensure(w)
    study.approve(w, ["owner", "compliance"])
    study.send(w)
    w.store.conn.execute("UPDATE payments SET finish_tx='00'||substr(finish_tx,3) WHERE finish_tx IS NOT NULL")
    row = next(f for f in engine_check.flows(w) if f["flow"] == "key_reveal")
    assert not row["ok"] and row["result"] != "tesSUCCESS"
