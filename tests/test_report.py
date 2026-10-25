"""One HTML report per run."""
from fastapi.testclient import TestClient

from agentrail import report, web
from tests.test_security import login


def test_report_renders_contract_markets_and_engine_check():
    c = TestClient(web.app)
    c.post("/api/reset?ledger=mock", headers=login(c, "operator"))
    h = login(c, "operator")
    assert c.post("/api/market/run?act=2", headers=h).status_code == 200
    r = c.get("/api/report", headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    t = r.text
    assert "Engine check" in t and "Market act 2" in t and "org_genomics" in t and "법률 자문 아님" in t
    assert "<script" not in t


def test_projection_svg_and_escaping():
    ps = [{"after_window": w, "usable": w - 4, "target": 8, "expected_usable": w, "band_90": [w - 1, w + 1]}
          for w in (5, 6, 7, 8)]
    v = {"requirements": {"hash": "a" * 64, "windows": [5, 6, 7, 8], "tier": "A", "lowest_tier": "C",
                          "columns": [{"name": "<x>"}]}, "projections": ps, "contracts": [], "contributions": []}
    t = report.render(v)
    assert "<svg" in t and "&lt;x&gt;" in t and "<x>" not in t
