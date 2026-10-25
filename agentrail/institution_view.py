"""What an institution (a research lab or a data buyer) sees of its agents' trades, measured from the records.

Three sources, each reported on its own with where it came from and when it was read, so numbers from different
runs never end up in one figure:

- research contracts on this engine (`Lane`): every contract, its members, each week's request and the payment;
  contracts posted by `scripts/scale_run.py` carry a run tag and are grouped by run
- the data vault market (VAULT_URL): every deal an organization's buyer agent made, refused or paid
- AP4M: the agent payment runs in `ap4m/receipts/` and the rail's pool budget (AP4M_RAIL_URL /health)

Times are seconds between two timestamps the systems wrote themselves (request -> payment recorded). Nothing here
is estimated; a figure with no data behind it is None and the page says so.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import ap4m_receipts

VAULT_URL = "https://data-vault-market-production.up.railway.app"
RUN_TAG = re.compile(r"\[scale-run (S-[0-9A-Za-z-]+)\]")
# Yale YODA Project dashboard, July 2026: median days from data request to access, and of those, to sign the DUA
BASELINE = {"request_to_access_days": 80, "contract_days": 35, "source": "Yale YODA Project dashboard, July 2026",
            "url": "https://yoda.yale.edu/wp-content/uploads/2026/07/YODA-Project-Dashboard-Metrics-July-2026.pdf"}
FOOTNOTE = "Testnet: test USD stands in for RLUSD"


def _stats(xs: list[float]) -> dict:
    xs = sorted(x for x in xs if x is not None and x >= 0)
    if not xs:
        return {"n": 0, "median_s": None, "p90_s": None, "max_s": None}
    p90 = xs[min(len(xs) - 1, int(round(0.9 * (len(xs) - 1))))]
    return {"n": len(xs), "median_s": round(statistics.median(xs), 2), "p90_s": round(p90, 2), "max_s": round(xs[-1], 2)}


def _share(a: int, b: int):
    return round(a / b, 4) if b else None


# ---------- research contracts on this engine ----------

def _contract_facts(lane, cid: str) -> dict:
    s = lane.store
    t = lane.terms(cid)
    iid = t["institution_id"]
    rail = t.get("payment_rail", "ledger")
    members = s.q("SELECT pid, automation, status FROM contract_members WHERE contract_id=?", cid)
    rounds = {r["week"]: r["started_at"] for r in s.q("SELECT week, started_at FROM contract_rounds WHERE contract_id=? "
                                                       "ORDER BY id", cid)}
    # the moment the institution's agent asked: the "round" event logged before any member is asked
    asked_at = {}
    for e in s.q("SELECT ts, message FROM events WHERE actor=? AND kind='round' ORDER BY id", iid):
        m = re.search(rf"^{re.escape(cid)} week (\d+):", e["message"])
        if m:
            asked_at.setdefault(int(m.group(1)), e["ts"])
    orders = s.q("SELECT o.id, o.status, o.price_drops, o.scope, o.created_at, p.status pstatus, p.updated_at pat "
                 "FROM orders o LEFT JOIN payments p ON p.order_id=o.id WHERE o.buyer_id=?", iid)
    cps = {r["order_id"]: r for r in s.q("SELECT order_id, ok, updated_at FROM contract_payments WHERE contract_id=?", cid)}
    asks = s.q("SELECT status, created_at FROM approval_requests WHERE buyer_id=?", iid)
    latencies, paid_n, paid_drops, delivered, withheld = [], 0, 0, 0, 0
    for o in orders:
        week = int(json.loads(o["scope"])["slot"].rsplit("week", 1)[-1])
        asked = asked_at.get(week, o["created_at"])
        if o["status"] == "withheld":
            withheld += 1
        if o["status"] != "delivered":
            continue
        delivered += 1
        if rail == "ap4m":
            cp = cps.get(o["id"])
            paid_at = cp["updated_at"] if cp and cp["ok"] else None
        else:
            paid_at = o["pat"] if o["pstatus"] == "validated" else None
        if paid_at:
            paid_n += 1
            paid_drops += o["price_drops"]
            latencies.append(paid_at - asked)
    human = len(asks)
    m = re.search(RUN_TAG, t.get("summary") or "")
    return {"contract": cid, "title": t["title"], "institution": t["institution"], "institution_id": iid,
            "run": m.group(1) if m else None, "rail": rail, "ledger": lane.ledger.name, "status": lane._row(cid)["status"],
            "items": t["items"], "price_per_item_micro": t["price_per_item_drops"],
            "members": sum(1 for x in members if x["status"] == "active"), "members_total": len(members),
            "auto_members": sum(1 for x in members if x["automation"] != "confirm_each"),
            "weeks_run": len(rounds), "requests": len(orders) + sum(1 for a in asks if a["status"] == "open"),
            "delivered": delivered, "withheld": withheld, "paid": paid_n, "paid_micro": paid_drops,
            "unpaid_delivered": delivered - paid_n, "human_approvals": human,
            "human_open": sum(1 for a in asks if a["status"] == "open"),
            "latencies": latencies, "posted_at": t.get("posted_at")}


def _roll(rows: list[dict]) -> dict:
    lat = [x for r in rows for x in r["latencies"]]
    paid = sum(r["paid"] for r in rows)
    micro = sum(r["paid_micro"] for r in rows)
    decisions = sum(r["requests"] for r in rows)
    human = sum(r["human_approvals"] for r in rows)
    return {"contracts": len(rows), "institutions": len({r["institution_id"] for r in rows}),
            "members": sum(r["members"] for r in rows), "requests": decisions,
            "delivered": sum(r["delivered"] for r in rows), "withheld": sum(r["withheld"] for r in rows),
            "paid": paid, "paid_micro": micro, "unpaid_delivered": sum(r["unpaid_delivered"] for r in rows),
            "human_approvals": human, "automated": max(decisions - human, 0),
            "automated_share": _share(max(decisions - human, 0), decisions),
            "request_to_paid": _stats(lat), "cost_per_payout_micro": round(micro / paid) if paid else None,
            "rails": sorted({r["rail"] for r in rows}), "ledgers": sorted({r["ledger"] for r in rows})}


def research(lane) -> dict:
    rows = [_contract_facts(lane, r["id"]) for r in
            lane.store.q("SELECT id FROM research_contracts ORDER BY created_at")]
    by_inst: dict[str, list] = {}
    for r in rows:
        by_inst.setdefault(r["institution"], []).append(r)
    runs: dict[str, list] = {}
    for r in rows:
        if r["run"]:
            runs.setdefault(r["run"], []).append(r)
    contracts = [{k: v for k, v in r.items() if k != "latencies"} | {"request_to_paid": _stats(r["latencies"])}
                 for r in rows]
    return {"source": "research contracts on this engine (/api/contracts)", "read_at": time.time(),
            "ledger": lane.ledger.name, "rail": lane.rail,
            "institutions": [{"institution": k, **_roll(v)} for k, v in sorted(by_inst.items())],
            "organic": _roll([r for r in rows if not r["run"]]),
            "runs": [{"run": k, **_roll(v), "started_at": min(r["posted_at"] or 0 for r in v)}
                     for k, v in sorted(runs.items(), key=lambda kv: min(r["posted_at"] or 0 for r in kv[1]))],
            "contracts": contracts}


# ---------- the data vault market ----------

_vault_cache: dict = {}


def _get(url: str, timeout: float = 8.0):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "agentrail-institutions"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _paid_tx(t: dict) -> bool:
    ty = t.get("type") or ""
    return (ty.startswith("AP4M VoucherRedeemed") and "cleaning" not in ty) or \
        (ty.startswith("EscrowFinish") and t.get("result") == "tesSUCCESS")


def vault(base: str | None = None, ttl: float = 20.0, get=_get) -> dict:
    base = (base or os.environ.get("VAULT_URL") or VAULT_URL).rstrip("/")
    hit = _vault_cache.get(base)
    if hit and time.time() - hit["read_at"] < ttl:
        return hit
    try:
        meta = get(f"{base}/api/meta")
        market = get(f"{base}/api/market")
    except Exception as e:
        return {"source": base, "read_at": time.time(), "ok": False, "why": f"{type(e).__name__}: {str(e)[:160]}"}
    ids = [c["id"] for c in market.get("contracts") or []]
    with ThreadPoolExecutor(8) as ex:
        details = list(ex.map(lambda i: _safe(get, f"{base}/api/contract/{i}"), ids))
    orgs: dict[str, dict] = {}
    deals = []
    for d in details:
        if not d or "contract" not in d:
            continue
        c, p, txs = d["contract"], d.get("posting") or {}, d.get("txs") or []
        paid = [t for t in txs if _paid_tx(t)]
        first_paid = min((t["created"] for t in paid if t.get("created")), default=None)
        asked = p.get("created") or c.get("created")
        rail = "ap4m" if any((t.get("type") or "").startswith("AP4M") for t in paid) else ("xrpl" if paid else None)
        deal = {"id": c["id"], "buyer": c.get("buyer_name") or c.get("buyer"), "kind": c.get("kind"),
                "status": c.get("status"), "reason": c.get("reason"), "sellers": len(c.get("sellers") or []) or 1,
                "items": c.get("items"), "paid_micro": sum(int(t.get("drops") or 0) for t in paid), "rail": rail,
                "asset": next((t.get("asset") for t in paid if t.get("asset")), None),
                "payments": len(paid), "request_to_paid_s": round(first_paid - asked, 2) if first_paid and asked else None,
                "created": c.get("created"),
                "tx_url": next((t.get("url") for t in paid if t.get("url")), None)}
        deals.append(deal)
        o = orgs.setdefault(deal["buyer"], {"buyer": deal["buyer"], "deals": 0, "settled": 0, "refused": 0,
                                            "reasons": {}, "paid_micro": 0, "payments": 0, "lat": [], "kinds": set()})
        o["deals"] += 1
        o["kinds"].add(deal["kind"])
        if deal["payments"]:
            o["settled"] += 1
            o["paid_micro"] += deal["paid_micro"]
            o["payments"] += deal["payments"]
            if deal["request_to_paid_s"] is not None:
                o["lat"].append(deal["request_to_paid_s"])
        elif deal["status"] == "rejected":
            o["refused"] += 1
            key = _reason(deal["reason"])
            o["reasons"][key] = o["reasons"].get(key, 0) + 1
    out_orgs = [{**{k: v for k, v in o.items() if k not in ("lat", "kinds")}, "kinds": sorted(o["kinds"]),
                 "request_to_paid": _stats(o["lat"]),
                 "cost_per_payout_micro": round(o["paid_micro"] / o["payments"]) if o["payments"] else None}
                for o in sorted(orgs.values(), key=lambda o: -o["deals"])]
    ov = market.get("overview") or {}
    lat = [d["request_to_paid_s"] for d in deals if d["request_to_paid_s"] is not None]
    paid_micro = sum(d["paid_micro"] for d in deals)
    payments = sum(d["payments"] for d in deals)
    res = {"source": base, "read_at": time.time(), "ok": True, "ledger": meta.get("ledger"),
           "asset": meta.get("asset_label") or meta.get("asset"), "revision": meta.get("revision"),
           "accounts": meta.get("accounts"), "window": f"latest {len(ids)} deals the vault lists",
           "intake": {"uploads": ov.get("uploads"), "blocked": ov.get("blocked"), "cleaned": ov.get("cleaned")},
           "totals": {"deals": len(deals), "settled": sum(1 for d in deals if d["payments"]),
                      "refused": sum(1 for d in deals if not d["payments"] and d["status"] == "rejected"),
                      "paid_micro": paid_micro, "payments": payments,
                      "ap4m_deals": sum(1 for d in deals if d["rail"] == "ap4m"),
                      "request_to_paid": _stats(lat),
                      "cost_per_payout_micro": round(paid_micro / payments) if payments else None},
           "orgs": out_orgs, "deals": deals}
    _vault_cache[base] = res
    return res


def _safe(get, url):
    try:
        return get(url)
    except Exception:
        return None


def _reason(r: str | None) -> str:
    r = (r or "no reason recorded").strip()
    return re.sub(r"\s*[\(#:].*$", "", r)[:60] if len(r) > 60 else r


# ---------- AP4M ----------

def ap4m() -> dict:
    v = ap4m_receipts.view(check=False)
    runs = []
    for r in v["runs"]:
        runs.append({"run_id": r["run_id"], "finished_at": r["finished_at"], "task": r["task"],
                     "paid": len(r["paid"]), "refused": len(r["refused"]),
                     "refusals": [x["reason"] for x in r["refused"]], "total_paid_rlusd": r["total_paid_rlusd"],
                     "hash_ok": sum(1 for p in r["paid"] if p.get("package_hash_ok")),
                     "receipt_url": (r.get("settlement") or {}).get("receipt_url"),
                     "txs": [p.get("url") for p in r["paid"] if p.get("url")]})
    health = None
    url = os.environ.get("AP4M_RAIL_URL")
    if url:
        try:
            h = _get(url.rstrip("/") + "/health", timeout=4)
            health = {"pools": h.get("pools"), "per_payment_cap_rlusd": h.get("per_payment_cap_rlusd")}
        except Exception as e:
            health = {"why": f"rail unreachable: {type(e).__name__}"}
    return {"source": "ap4m/receipts and the AP4M rail", "read_at": time.time(), "chain_id": v["chain_id"],
            "explorer": v["explorer"], "runs": runs, "rail": health}


def overview(lane, vault_url: str | None = None) -> dict:
    return {"baseline": BASELINE, "footnote": FOOTNOTE, "research": research(lane), "vault": vault(vault_url),
            "ap4m": ap4m(), "synthetic_data": True}
