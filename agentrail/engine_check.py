"""Did one run carry a health trade all the way through? One row per flow, with the ledger transaction
that proves it (or the reason it is missing).

    proposal -> consent -> escrow -> key reveal -> holdback -> withdrawal + clawback -> Batch -> AMM -> 402
    -> data contract (negotiated per column, checked per contribution) -> per-contribution holdback

Read from the run's own database and checked against the ledger it ran on: a flow passes only when its
transaction is found on that ledger with tesSUCCESS (on Testnet, a validated ledger).
"""
from __future__ import annotations

import json

FLOWS = ("proposal", "consent", "co_signed_budget", "escrow", "key_reveal", "holdback", "withdrawal_clawback",
         "batch", "amm", "x402", "data_contract", "contribution_holdback")


def _ev(w, kind: str, like: str = "%"):
    r = w.store.one("SELECT message, data FROM events WHERE kind=? AND message LIKE ? ORDER BY id", kind, like)
    if not r:
        return None, None
    d = json.loads(r["data"] or "{}")
    h = d.get("tx_hash") or (d.get("tx") if isinstance(d.get("tx"), str) else None)
    return r["message"], h


def _on_ledger(w, h: str | None) -> str | None:
    if not h:
        return None
    try:
        return w.ledger.lookup(h).result
    except Exception as e:                      # unreachable node: reported, not passed
        return f"lookup failed ({type(e).__name__})"


def flows(w) -> list[dict]:
    st = w.store
    rows = []

    def add(flow, ok, detail, h=None, n=None):
        res = _on_ledger(w, h) if h else None
        if h:
            ok = ok and res == "tesSUCCESS"
        rows.append({"flow": flow, "ok": bool(ok), "detail": detail, "count": n, "tx": h, "result": res,
                     "url": w.ledger.explorer_url(h) if h else None})

    p = st.q("SELECT task, source, verdict FROM proposals WHERE task IN ('infer_needs','person_gaps')")
    add("proposal", bool(p), "; ".join(f"{r['task']} by {r['source']}: {r['verdict']}" for r in p)
        or "no gap reading recorded", n=len(p))

    c = st.one("SELECT COUNT(*) n FROM consents")["n"]
    add("consent", c > 0, f"{c} consent records; requests sent only inside them", n=c)

    msg, h = _ev(w, "top_up")
    add("co_signed_budget", bool(h), msg or "no co-signed treasury payment", h)

    e = st.one("SELECT COUNT(*) n, MIN(tx_hash) h FROM payments WHERE kind='escrow' AND tx_hash IS NOT NULL")
    add("escrow", e["n"] > 0, f"{e['n']} EscrowCreate (PREIMAGE-SHA-256 condition on the data key)", e["h"], e["n"])

    f = st.one("SELECT COUNT(*) n, MIN(finish_tx) h FROM payments WHERE kind='escrow' AND finish_tx IS NOT NULL")
    add("key_reveal", f["n"] > 0, f"{f['n']} EscrowFinish publishing the data key", f["h"], f["n"])

    hb = {r["status"]: r["n"] for r in st.q("SELECT status, COUNT(*) n FROM holdbacks GROUP BY status")}
    r = st.one("SELECT finish_tx FROM holdbacks WHERE status='released' AND finish_tx IS NOT NULL ORDER BY id")
    add("holdback", bool(r), "held parts: " + (", ".join(f"{k} {v}" for k, v in sorted(hb.items())) or "none"),
        r["finish_tx"] if r else None, sum(hb.values()))

    msg, h = _ev(w, "clawback")
    _, hc = _ev(w, "refunded")
    add("withdrawal_clawback", bool(h), (msg or "no clawback") + ("; escrow refunded" if hc else "; no refund yet"), h)

    n = st.one("SELECT COUNT(*) n FROM events WHERE kind='batch' AND message LIKE '%tesSUCCESS%'")["n"]
    msg, h = _ev(w, "batch", "%tesSUCCESS%")
    add("batch", n > 0, f"{n} Batch (all or nothing) of weekly escrows", h, n)

    msg, h = _ev(w, "swap")
    add("amm", bool(h), msg or "no AMM swap (nobody chose a stablecoin payout)", h)

    fees = [x for x in getattr(getattr(w, "study", None), "export_fees", []) if x.get("ok")]
    add("x402", bool(fees), (f"{len(fees)} clinic exports paid: HTTP {' -> '.join(map(str, fees[0]['http']))}, "
                             f"{fees[0]['rail']}") if fees else "no clinic export paid over HTTP 402",
        fees[0]["tx"] if fees else None, len(fees))
    o = st.one("SELECT COUNT(*) n, MIN(p.tx_hash) h FROM orders o JOIN payments p ON p.order_id=o.id "
               "WHERE o.product_id LIKE 'contract:%' AND p.finish_tx IS NOT NULL")
    caught = [x for x in getattr(getattr(w, "contract_round", None), "outcomes", []) if x["verdict"] == "fail"]
    add("data_contract", o["n"] > 0, f"{o['n']} contributions paid under a negotiated contract (contract hash in the "
        f"EscrowCreate memo and the sealed bundle); {len(caught)} unfit contributions caught", o["h"], o["n"])
    hb = st.one("SELECT COUNT(*) n, MIN(finish_tx) h FROM holdbacks WHERE kind='contribution' AND status='released'")
    wh = st.one("SELECT COUNT(*) n FROM holdbacks WHERE kind='contribution' AND status IN ('withheld','returned')")["n"]
    add("contribution_holdback", hb["n"] > 0, f"{hb['n']} held parts released after their contribution passed; "
        f"{wh} withheld by a reviewer after a failed check", hb["h"], hb["n"])
    return rows


def summary(rows: list[dict]) -> str:
    return "\n".join(f"{'PASS' if r['ok'] else 'FAIL'}  {r['flow']:<20} {r['detail']}"
                     + (f"  {r['url'] or r['tx']}" if r["tx"] else "") for r in rows)
