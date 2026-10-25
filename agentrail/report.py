"""One end-to-end HTML report per run: the contract, the negotiation, every contribution's checks,
the projection over time, payments, holdbacks and transaction links; plus the market acts and the
engine check if they ran. A single self-contained file (inline CSS and SVG, no scripts)."""
from __future__ import annotations

import html
import json
import time

CSS = """body{font:14px/1.45 system-ui,-apple-system,sans-serif;margin:24px auto;max-width:1100px;padding:0 16px;color:#1d1d1f;background:#fff}
h1{font-size:22px}h2{font-size:17px;margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0}td,th{border-bottom:1px solid #eee;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#f6f6f7}.ok{color:#18794e}.bad{color:#b42318}.muted{color:#666}code{font-size:12px}
.pill{display:inline-block;border-radius:9px;padding:0 7px;font-size:11.5px;background:#eef}.foot{margin-top:32px;color:#666;font-size:12px}
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}th{background:#222}td,th{border-color:#333}.muted,.foot{color:#aaa}}"""


def e(x) -> str:
    return html.escape(str(x))


def link(url, text) -> str:
    return f'<a href="{e(url)}">{e(text)}</a>' if url else e(text)


def projection_svg(ps: list[dict]) -> str:
    if not ps:
        return ""
    W, H, P = 640, 200, 36
    xs = [p["after_window"] for p in ps]
    top = max(max(p.get("target", 1) for p in ps), max(p["band_90"][1] for p in ps), 1)
    sx = lambda x: P + (x - min(xs)) / max(1, max(xs) - min(xs)) * (W - 2 * P)
    sy = lambda y: H - P - y / top * (H - 2 * P)
    band = " ".join(f"{sx(p['after_window']):.1f},{sy(p['band_90'][1]):.1f}" for p in ps) + " " + \
        " ".join(f"{sx(p['after_window']):.1f},{sy(p['band_90'][0]):.1f}" for p in reversed(ps))
    exp = " ".join(f"{sx(p['after_window']):.1f},{sy(p['expected_usable']):.1f}" for p in ps)
    use = " ".join(f"{sx(p['after_window']):.1f},{sy(p['usable']):.1f}" for p in ps)
    t = ps[-1].get("target", 0)
    return (f'<svg width="{W}" height="{H}" role="img" aria-label="projection over time">'
            f'<polygon points="{band}" fill="#2a6fdb22"/><polyline points="{exp}" fill="none" stroke="#2a6fdb" stroke-width="2"/>'
            f'<polyline points="{use}" fill="none" stroke="#18794e" stroke-width="2"/>'
            f'<line x1="{P}" x2="{W - P}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" stroke="#b42318" stroke-dasharray="4 3"/>'
            f'<text x="{W - P}" y="{sy(t) - 4:.1f}" font-size="11" text-anchor="end" fill="#b42318">target {t}</text>'
            + "".join(f'<text x="{sx(x):.1f}" y="{H - 12}" font-size="11" text-anchor="middle">w{x}</text>' for x in xs)
            + f'<text x="{P}" y="14" font-size="11">blue: expected usable (90% band), green: usable so far</text></svg>')


def render(contract: dict | None = None, markets: list[dict] | None = None, engine_check: dict | None = None,
           title: str = "AgentRail run report", ledger: str = "", products: dict | None = None) -> str:
    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{e(title)}</title><style>{CSS}</style></head><body><h1>{e(title)}</h1>"
           f"<p class=muted>Generated {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
           f"{' · ledger ' + e(ledger) if ledger else ''} · 법률 자문 아님 · 합성 데이터 · Testnet</p>"]
    if engine_check:
        out.append("<h2>Engine check</h2><table><tr><th>flow</th><th>result</th><th>tx</th></tr>")
        for f in engine_check.get("flows", []):
            ok = f.get("ok")
            out.append(f"<tr><td>{e(f.get('flow'))}</td><td class={'ok' if ok else 'bad'}>{'PASS' if ok else 'FAIL'} "
                       f"{e(f.get('detail', ''))}</td><td>{link(f.get('url'), (f.get('tx') or '')[:16])}</td></tr>")
        out.append("</table>")
    if contract and contract.get("requirements"):
        r = contract["requirements"]
        out.append(f"<h2>Contract requirements</h2><p>hash <code>{e(r['hash'][:16])}</code> · windows {e(r['windows'])} · "
                   f"tier {e(r['tier'])} (lowest {e(r['lowest_tier'])})</p><table><tr><th>column</th><th>spec</th></tr>")
        for c in r["columns"]:
            out.append(f"<tr><td>{e(c.get('name', c.get('column', '')))}</td><td><code>{e(json.dumps(c))}</code></td></tr>")
        out.append("</table><h2>Projection over time</h2>" + projection_svg(contract.get("projections", [])))
        out.append("<h2>Contracts and negotiation</h2>")
        for k in contract.get("contracts", []):
            out.append(f"<details><summary><b>{e(k['provider'])}</b> · tier {e(k['tier'])} · windows {e(k['windows'])} · "
                       f"{e(k['price_xrp_per_window'])} XRP/window · <code>{e(k['hash'][:16])}</code></summary><table>")
            for m in k.get("transcript") or []:
                out.append(f"<tr><td>{e(m.get('from'))} → {e(m.get('to'))}</td><td>{e(m.get('kind'))}</td>"
                           f"<td><code>{e(json.dumps({x: y for x, y in m.items() if x not in ('from', 'to', 'kind')})[:400])}</code></td></tr>")
            out.append("</table></details>")
        out.append("<h2>Contributions, checks, payments, holdback</h2><table><tr><th>provider</th><th>window</th><th>verdict</th>"
                   "<th>stage</th><th>signals</th><th>paid</th><th>held</th><th>released</th><th>tx</th></tr>")
        for c in contract.get("contributions", []):
            sig = ", ".join(s["code"] for s in c.get("signals", []))
            txs = " ".join(link(u, n) for n, u in (c.get("urls") or {}).items()) or \
                " ".join(e(f"{n}:{(h or '')[:10]}") for n, h in (c.get("txs") or {}).items() if h)
            out.append(f"<tr><td>{e(c['provider'])}</td><td>{e(c['window'])}</td><td class={'ok' if c['verdict'] == 'pass' else 'bad'}>"
                       f"{e(c['verdict'])}</td><td>{e(c['stage'])}</td><td>{e(sig)}</td><td>{c['paid_drops'] / 1e6:g}</td>"
                       f"<td>{c['held_drops'] / 1e6:g}</td><td>{c['released_drops'] / 1e6:g}</td><td>{txs}</td></tr>")
        out.append("</table>")
    for m in markets or []:
        a = m.get("activity", {})
        out.append(f"<h2>Market act {e(m.get('act'))}</h2><p>{e(a.get('trades'))} trades · "
                   f"{e(json.dumps(a.get('by_status', {})))} · volume {e(a.get('volume_xrp'))} XRP · withheld "
                   f"{e(a.get('withheld_xrp'))} XRP · waiting for an owner {e(a.get('awaiting_owner'))}</p>")
        if m.get("buyer_grades"):
            out.append("<table><tr><th>buyer</th><th>grade</th><th>reasons</th></tr>" + "".join(
                f"<tr><td>{e(k)}</td><td>{e(v['grade'])}</td><td>{e('; '.join(v['reasons']))}</td></tr>"
                for k, v in m["buyer_grades"].items()) + "</table>")
        out.append("<table><tr><th>need</th><th>seller → buyer</th><th>columns</th><th>status</th><th>why</th><th>XRP</th><th>tx</th></tr>")
        for t in a.get("recent", []):
            txs = " ".join(link(u, n) for n, u in (t.get("urls") or {}).items())
            out.append(f"<tr><td>{e(t['need'])}</td><td>{e(t['seller'])} → {e(t['buyer'])}</td><td>{e(', '.join(t.get('columns', [])))}</td>"
                       f"<td>{e(t['status'])}</td><td>{e(t.get('why', ''))}</td><td>{t.get('paid_drops', 0) / 1e6:g}</td><td>{txs}</td></tr>")
        out.append("</table>")
    if products:
        pr = products
        out.append(f"<h2>Person's agent: products ({e(pr['person'])})</h2><p>collected from connected sources: "
                   f"{e(', '.join(c['column'] for c in pr['collected'] if c['collected']) or 'nothing')} · "
                   f"re-identification check: {e('; '.join(pr['k_anonymity']))}</p>"
                   "<table><tr><th>direction</th><th>domain</th><th>columns</th><th>tier</th><th>grade</th><th>XRP</th>"
                   "<th>review</th><th>de-identification</th><th>sale</th></tr>")
        for c in pr["candidates"]:
            sale = c.get("sale") or {}
            sold = (f"sealed push to {sale.get('institution')}, paid" if sale.get("sold") else sale.get("why", "not listed"))
            out.append(f"<tr><td>{e(c['direction'])}</td><td>{e(c['domain'])}</td><td>{e(', '.join(c['columns']))}</td>"
                       f"<td>{e(c['tier'])}</td><td>{e(c['grade'])}</td><td>{c['price_drops'] / 1e6:g}</td>"
                       f"<td>{e(c['review']['how'])}: {e(c['review']['why'])}</td><td>{e('; '.join(c.get('deid', [])))}</td>"
                       f"<td class={'ok' if sale.get('sold') else 'muted'}>{e(sold)}</td></tr>")
        out.append("</table><table><tr><th>study posting</th><th>institution</th><th>matched</th><th>why</th></tr>" + "".join(
            f"<tr><td>{e(x['posting'])}</td><td>{e(x['institution'])}</td><td>{e(', '.join(x['matched']))}</td>"
            f"<td>{e(x['why'])}</td></tr>" for x in pr["postings_searched"]) + "</table>")
    out.append("<p class=foot>Synthetic data, XRPL Testnet. Legal requirements are reflected in the design; this is not a compliance claim.</p></body></html>")
    return "".join(out)
