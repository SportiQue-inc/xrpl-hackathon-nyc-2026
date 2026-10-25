"""HTTP API and the two sites: the market (/) and my DB (/vault)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import secrets
import threading
import time

from fastapi import Body, FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from . import agents, config, data, llm
from .data import KINDS
from .market import Market

app = FastAPI(title="Data Vault Market")
M = Market()
STATIC = os.path.join(os.path.dirname(__file__), "static")


@app.on_event("startup")
def _start():
    M.seed()
    threading.Thread(target=M.run_forever, daemon=True).start()


@app.get("/")
def market_page():
    return FileResponse(os.path.join(STATIC, "market.html"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#5b8cff"/><path d="M8 9h7a7 7 0 0 1 0 14H8z" fill="none" stroke="white" stroke-width="3"/></svg>', media_type="image/svg+xml")


@app.get("/vault")
def vault_page():
    return FileResponse(os.path.join(STATIC, "vault.html"))


@app.get("/static/{name}")
def static(name: str):
    path = os.path.join(STATIC, os.path.basename(name))
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path)


def _name(aid):
    a = M.s.one("SELECT name, type FROM accounts WHERE id = ?", (aid,))
    return a["name"] if a else aid


# ---------------- members ----------------
COOKIE = "vm_session"
_signups: dict[str, list[float]] = {}


def _hash(pw: str, salt: str) -> str:
    return hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1).hex()


def _me(request: Request) -> dict | None:
    tok = request.cookies.get(COOKIE)
    if not tok:
        return None
    demo=M.s.one("SELECT 1 FROM sessions WHERE token=? AND username='@demo'", (tok,))
    if demo:
        return {"username":"Demo","account":"demo-vault","demo":True,"wallet":None,"wallet_tx":None}
    s = M.s.one("SELECT u.* FROM sessions s JOIN users u ON u.username = s.username WHERE s.token = ?", (tok,))
    if s:
        s.pop("pw", None); s.pop("salt", None)
    return s


def _guard(request: Request, aid: str, write: bool = True):
    """Members act only on their own account. Demo accounts are open locally and read-only when public."""
    me = _me(request)
    if me and me.get("demo") and aid=="demo-vault":
        return me
    if aid.startswith("u-"):
        if not me or me["account"] != aid:
            raise HTTPException(403, "sign in as this member")
    elif write and config.PUBLIC:
        raise HTTPException(403, "Open your own vault to continue")
    return me


from .vaultfiles import register as register_vaultfiles
register_vaultfiles(app,M,_guard)
from .packages import register as register_packages
register_packages(app,M,_guard)


def _session(resp: Response, username: str):
    tok = secrets.token_urlsafe(32)
    M.s.insert("sessions", token=tok, username=username)
    resp.set_cookie(COOKIE, tok, httponly=True, samesite="lax", secure=config.PUBLIC, max_age=30 * 86400)


@app.post("/api/signup")
def signup(request: Request, response: Response, body: dict = Body(...)):
    name, pw = str(body.get("username", "")).strip().lower(), str(body.get("password", ""))
    if not re.fullmatch(r"[a-z0-9_]{3,20}", name):
        raise HTTPException(400, "username: 3 to 20 letters, digits or _")
    if len(pw) < 8:
        raise HTTPException(400, "password: at least 8 characters")
    ip = request.client.host if request.client else "?"
    recent = [t for t in _signups.get(ip, []) if t > time.time() - 3600]
    if len(recent) >= config.SIGNUPS_PER_HOUR:
        raise HTTPException(429, "too many signups from this address; try again later")
    _signups[ip] = recent + [time.time()]
    if M.s.one("SELECT 1 FROM users WHERE username = ?", (name,)):
        raise HTTPException(409, "that username is taken")
    salt = secrets.token_hex(16)
    aid = "u-" + name
    M.s.insert("users", username=name, pw=_hash(pw, salt), salt=salt, account=aid)
    M.add_user_account(aid, name)
    _session(response, name)
    return {"ok": True, "account": aid}


@app.post("/api/login")
def login(response: Response, body: dict = Body(...)):
    name, pw = str(body.get("username", "")).strip().lower(), str(body.get("password", ""))
    u = M.s.one("SELECT * FROM users WHERE username = ?", (name,))
    if not u or not secrets.compare_digest(u["pw"], _hash(pw, u["salt"])):
        raise HTTPException(401, "wrong username or password")
    _session(response, name)
    return {"ok": True, "account": u["account"]}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    M.s.x("DELETE FROM sessions WHERE token = ?", (request.cookies.get(COOKIE, ""),))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.post("/api/demo-session")
def demo_session(request: Request,response: Response):
    current=_me(request)
    if current:
        return {"ok":True,"account":current["account"]}
    if not M.s.one("SELECT id FROM accounts WHERE id='demo-vault'"):
        raise HTTPException(503,"The synthetic demo is starting. Please try again shortly.")
    _session(response,"@demo")
    return {"ok":True,"account":"demo-vault","demo":True}


@app.get("/api/me")
def me(request: Request):
    u = _me(request)
    if not u:
        return {"user": None, "public": config.PUBLIC}
    return {"user": u, "public": config.PUBLIC, "platform": getattr(M, "platform", None), "agent_wallet": M.addr.get(u["account"]),
            "chat_left": max(0, config.CHAT_DAILY - _chat_today(u["account"]))}


@app.post("/api/me/wallet")
def link_wallet(request: Request, body: dict = Body(...)):
    """Step 1: the member names their own wallet; we hand back a destination tag to prove control with."""
    u = _me(request)
    if not u:
        raise HTTPException(401)
    if u.get("demo"):
        raise HTTPException(403,"Sign in to your own vault before linking a personal wallet")
    from xrpl.core.addresscodec import is_valid_classic_address
    addr = str(body.get("address", "")).strip()
    if not is_valid_classic_address(addr):
        raise HTTPException(400, "not a valid XRPL address (starts with r)")
    tag = secrets.randbelow(9 * 10 ** 8) + 10 ** 8
    M.s.x("UPDATE users SET wallet = ?, wallet_tag = ?, wallet_tx = NULL WHERE username = ?", (addr, tag, u["username"]))
    M.s.x("UPDATE accounts SET payout = NULL WHERE id = ?", (u["account"],))
    return {"address": addr, "send_to": getattr(M, "platform", None), "destination_tag": tag, "drops": 1}


@app.post("/api/me/wallet/verify")
def verify_wallet(request: Request):
    """Step 2: find the member's 1-drop Payment with that tag on the ledger; then sales pay out to that wallet."""
    u = _me(request)
    if u and u.get("demo"):
        raise HTTPException(403,"Sign in to your own vault before linking a personal wallet")
    if not u or not u.get("wallet"):
        raise HTTPException(400, "link a wallet first")
    h = M.rail.find_link_payment(u["wallet"], M.platform, u["wallet_tag"])
    if not h:
        return {"ok": False, "why": "no validated payment with that destination tag yet; it can take a few seconds after you send it"}
    M.s.x("UPDATE users SET wallet_tx = ? WHERE username = ?", (h, u["username"]))
    M.s.x("UPDATE accounts SET payout = ? WHERE id = ?", (u["wallet"], u["account"]))
    M.chat(u["account"], "agent", f"Your wallet {u['wallet']} is linked. From now on buyers' escrows pay out straight to it.")
    return {"ok": True, "tx": h, "url": M.rail.explorer(h)}


def _chat_today(aid: str) -> int:
    return M.s.one("SELECT COUNT(*) n FROM chat WHERE account = ? AND role = 'me' AND created > ?", (aid, time.time() - 86400))["n"]


@app.get("/api/meta")
def meta():
    return {"ledger": M.rail.name, "model": llm.model_name(), "models": llm.models(), "llm": llm.USAGE, "kinds": {**KINDS, data.PACKAGE_KIND: data.PACKAGE_INFO}, "k_min": config.K_MIN,
            "revision": os.environ.get("APP_REVISION"), "unit_xrp": config.MICRO_PER_UNIT / 1e6, "asset": M.rail.symbol(), "asset_rlusd": False, "asset_label": M.rail.label(), "asset_footnote": config.ASSET_FOOTNOTE if M.rail.asset == "USD" else "", "asset_note": M.rail.asset_note, "issuer": M.rail.issuer, "connected": len(M.addr), "accounts": len(M.s.q("SELECT id FROM accounts")),
            "rpm_cap": config.LLM_RPM, "daily_cap": config.LLM_DAILY_CALLS, "engine_url": config.ENGINE_URL}


@app.get("/api/accounts")
def accounts(request: Request):
    me = _me(request)
    return M.s.q("SELECT id, name, type, online FROM accounts WHERE id NOT LIKE 'u-%' OR id = ? ORDER BY type DESC, name", (me["account"] if me else "",))


def _can_view_contract(c, account):
    participants={c.get("buyer"), c.get("seller"), *json.loads(c.get("sellers") or "[]")}
    return not config.PUBLIC or not any(str(a).startswith("u-") for a in participants) or (str(account).startswith("u-") and account in participants)


def _trade_summaries(contracts, account):
    s = M.s
    for c in contracts:
        c["buyer_name"] = _name(c["buyer"]); c["sellers"] = json.loads(c["sellers"] or "[]")
        c["mine"] = c["buyer"] == account or c.get("seller") == account or account in c["sellers"]
        c["seller_name"] = _name(c.get("seller") or c["sellers"][0]) if c.get("seller") or len(c["sellers"])==1 else None
        c["drops"] = M.s.one("SELECT COALESCE(SUM(drops),0) n FROM txs WHERE contract=? AND type LIKE 'EscrowFinish%' AND result='tesSUCCESS'", (c["id"],))["n"]
        c["asset"] = c.get("asset") or "XRP"
        t = s.one("SELECT hash FROM txs WHERE contract = ? AND hash IS NOT NULL ORDER BY id DESC LIMIT 1", (c["id"],))
        c["tx_url"] = M.rail.explorer(t["hash"]) if t else None
    return contracts


def _agent_styles(since=0):
    receipts=M.s.q("SELECT t.src,COALESCE(t.asset,'XRP') asset,COUNT(DISTINCT t.contract) sales,SUM(t.drops) micro FROM txs t JOIN contracts c ON c.id=t.contract WHERE t.type LIKE 'EscrowFinish%' AND t.result='tesSUCCESS' AND t.created>=? AND c.buyer NOT LIKE 'u-%' AND c.buyer!='demo-vault' AND COALESCE(c.seller,'') NOT LIKE 'u-%' AND COALESCE(c.seller,'')!='demo-vault' GROUP BY t.src,t.asset", (since,))
    styles=[]
    for row in M.s.q("SELECT id FROM accounts WHERE id NOT LIKE 'u-%' AND id!='demo-vault'"):
        a=M.acct(row['id']);rules=a['sell_agent'];mins=rules.get('min',{})
        ratio=sum(mins.get(k,v['price'])/v['price'] for k,v in KINDS.items())/len(KINDS)
        style='Approval first' if rules.get('mode')=='ask' else 'Price firm' if ratio>=1 else 'Flexible pricing'
        rs=[r for r in receipts if r['src']==a['id']]
        styles.append({'id':a['id'],'name':a['name'],'style':style,'blocked_purposes':rules.get('blocks',[]),'approval':rules.get('mode'),'minimums':mins,'floor_ratio':round(ratio,3),'budget':a['buy_agent'].get('auto_limit') if a.get('buy_agent') else None,'sales':sum(r['sales'] for r in rs),'income':[{'asset':r['asset'],'amount':r['micro']/1e6} for r in rs]})
    return sorted(styles,key=lambda a:(-a['sales'],a['name']))


@app.get("/demo")
def demo_page():
    return FileResponse(os.path.join(STATIC,"demo.html"))


@app.get("/report")
def research_report_page():
    return FileResponse(os.path.join(STATIC,"demo.html"))


@app.get("/api/research-report")
def research_report_data():
    return FileResponse(os.path.join(STATIC,"research-report.json"),media_type="application/json")


@app.get("/api/demo")
def demo(minutes: int = 60):
    if minutes not in (15,60,180,0):
        raise HTTPException(400,"Choose 15, 60, 180 minutes or all history")
    now=time.time();start=now-minutes*60 if minutes else M.s.one("SELECT COALESCE(MIN(created),?) t FROM txs",(now,))["t"]
    styles=_agent_styles(start);ids={a['id'] for a in styles}
    rows=M.s.q("SELECT t.src,COALESCE(t.asset,'XRP') asset,t.drops,t.created,t.contract,c.kind,b.name buyer_name FROM txs t LEFT JOIN contracts c ON c.id=t.contract LEFT JOIN accounts b ON b.id=c.buyer WHERE t.type LIKE 'EscrowFinish%' AND t.result='tesSUCCESS' AND t.created>=? AND c.buyer NOT LIKE 'u-%' AND c.buyer!='demo-vault' AND COALESCE(c.seller,'') NOT LIKE 'u-%' AND COALESCE(c.seller,'')!='demo-vault' ORDER BY t.created",(start,))
    for a in styles:
        a['receipts']=[{'asset':r['asset'],'amount':r['drops']/1e6,'at':r['created'],'contract':r['contract'],'kind':r['kind'],'buyer':r['buyer_name']} for r in rows if r['src']==a['id']]
    activity=[]
    for c in M.s.q("SELECT id,buyer,seller,kind,status,reason,total,created FROM contracts ORDER BY id DESC LIMIT 100"):
        if c['buyer'] not in ids or c['seller'] not in ids:
            continue
        sources=set()
        for m in M.s.q("SELECT thinking FROM messages WHERE contract=?",(c['id'],)):
            try:
                by=json.loads(m['thinking'] or '{}').get('by','rules')
                if by and by!='rules':sources.add(by)
            except (ValueError,TypeError):pass
        c['source']=', '.join(sorted(sources)) or 'rules'
        activity.append(c)
    return {'activity':activity[:20],'start':start,'end':now,'minutes':minutes,'agents':styles,'assets':sorted({r['asset'] for r in rows if r['src'] in ids} | {M.rail.symbol()}),'unit':config.MICRO_PER_UNIT/1e6,'note':'Simulated participants. Income is the gross amount from successful escrow finishes in the selected period; XRP network fees are separate.'}


@app.get("/api/market")
def market(request: Request, account: str = "", domain: str | None = None):
    if config.PUBLIC:
        u = _me(request)
        account = u["account"] if u else ""
    s = M.s
    kinds = [domain] if domain in KINDS else list(KINDS)
    doms = []
    for k in KINDS:
        if not (s.one("SELECT 1 FROM files WHERE kind = ? AND status = 'listed'", (k,)) or s.one("SELECT 1 FROM postings WHERE kind = ? AND status = 'open'", (k,))):
            continue      # categories come from what is actually in vaults and requests
        doms.append({"kind": k, "label": KINDS[k]["label"], "domain": KINDS[k]["domain"], "volume": s.stat("volume:" + k),
                     "settled": s.stat("settled:" + k), "rejected": s.stat("rejected:" + k),
                     "listed": s.one("SELECT COUNT(*) n FROM files WHERE kind = ? AND status = 'listed'", (k,))["n"],
                     "sellers": s.one("SELECT COUNT(DISTINCT account) n FROM files WHERE kind = ? AND status = 'listed'", (k,))["n"]})
    ph = ",".join("?" * len(kinds))
    postings = s.q(f"SELECT p.*, a.name AS buyer_name, a.verified, (SELECT COUNT(*) FROM interests i WHERE i.posting = p.id) AS interest, "
                   f"(SELECT COUNT(*) FROM interests i WHERE i.posting = p.id AND i.account = ?) AS mine "
                   f"FROM postings p JOIN accounts a ON a.id = p.buyer WHERE p.status = 'open' AND p.kind IN ({ph}) ORDER BY interest DESC, p.offer DESC", (account, *kinds))
    contracts = s.q(f"SELECT id, posting, buyer, seller, kind, status, reason, total, items, sellers, created, asset, unit_micro, overview FROM contracts WHERE kind IN ({ph}) ORDER BY id DESC LIMIT 60", tuple(kinds))
    contracts=[c for c in contracts if _can_view_contract(c,account)]
    _trade_summaries(contracts, account)
    people = s.q("SELECT COUNT(*) n, SUM(online) o FROM accounts")[0]
    # what is for sale: listed pseudonymized files per category, plus resale bundles
    listings = []
    for d in doms:
        if not d["listed"]:
            continue
        asks = [a["sell_agent"]["min"].get(d["kind"]) for a in (M.acct(r["account"]) for r in s.q("SELECT DISTINCT account FROM files WHERE kind = ? AND status = 'listed'", (d["kind"],))) if a]
        asks = [x for x in asks if x is not None]
        listings.append({"kind": d["kind"], "label": d["label"], "files": d["listed"], "vaults": d["sellers"],
                         "ask_min": min(asks) if asks else None, "ask_max": max(asks) if asks else None,
                         "bundles": s.one("SELECT COUNT(*) n FROM files WHERE kind = ? AND status = 'listed' AND derived_from IS NOT NULL", (d["kind"],))["n"]})
    return {"overview": {"online": people["o"], "accounts": people["n"], "settled": s.stat("settled"), "rejected": s.stat("rejected"),
                         "volume": round(_paid_now()["units"], 1), "xrp": round(_paid_now()["micro"] / 1e6, 4), "asset": M.rail.symbol(), "uploads": s.stat("uploads"),
                         "blocked": s.stat("blocked"), "cleaned": s.stat("cleaned"), "fees": round(s.stat("fees"), 1),
                         "txs": s.one("SELECT COUNT(*) n FROM txs")["n"]},
            "domains": sorted(doms, key=lambda d: -(d["listed"] + 5 * d["settled"])), "postings": postings, "contracts": contracts, "listings": listings, "sell_now": _sell_now(account), "prices": {k: M.quote(k) for k in KINDS}, "events": M.events}


def _paid_now() -> dict:
    """What settled deals in the current settlement asset paid on the ledger. Older counters mix in the XRP era."""
    r = M.s.one("SELECT COALESCE(SUM(t.drops), 0) micro FROM contracts c JOIN txs t ON t.contract = c.id "
                "AND t.type LIKE 'EscrowFinish%' AND t.result = 'tesSUCCESS' WHERE c.status = 'settled' AND c.asset = ?", (M.rail.symbol(),))
    return {"micro":r["micro"],"units":r["micro"]/config.MICRO_PER_UNIT}


def _sell_now(aid: str) -> list[dict]:
    """Open requests this account's data already qualifies for: it has files of the kind, the purpose is
    not one its rules refuse, and the offer meets its minimum. Sorted by what the owner would get."""
    a = M.acct(aid)
    if not a:
        return []
    out = []
    for w in M.s.q("SELECT p.*, a.name buyer_name, a.verified FROM postings p JOIN accounts a ON a.id = p.buyer WHERE p.status = 'open' AND p.buyer != ?", (aid,)):
        if aid=="demo-vault" and w["buyer"].startswith("u-"):
            continue
        mine = M.s.q("SELECT status FROM files WHERE account = ? AND kind = ? AND status IN ('listed', 'private')", (aid, w["kind"]))
        if not mine or w["purpose"] in a["sell_agent"].get("blocks", []):
            continue
        floor = a["sell_agent"]["min"].get(w["kind"], 0)
        if w["max"] < floor:
            continue
        others = M.s.one("SELECT COUNT(DISTINCT account) n FROM files WHERE kind = ? AND status = 'listed' AND account NOT IN (?, ?)", (w["kind"], aid, w["buyer"]))["n"]
        out.append({**w, "listed": sum(f["status"] == "listed" for f in mine), "private": sum(f["status"] == "private" for f in mine),
                    "expected": round(max(floor, w["offer"]), 1), "floor": floor, "others": others,
                    "interested": bool(M.s.one("SELECT 1 FROM interests WHERE account = ? AND posting = ?", (aid, w["id"])))})
    return sorted(out, key=lambda w: -w["expected"])


@app.post("/api/account/{aid}/sell-now/{pid}")
def sell_now(aid: str, pid: int, request: Request):
    """One tap: list my files of that kind as pseudonymized copies and put me first in line for this request."""
    _guard(request, aid)
    w = M.s.one("SELECT * FROM postings WHERE id = ? AND status = 'open'", (pid,))
    if not w:
        raise HTTPException(404)
    return {"ok": True, "request": M.enqueue_sale(aid, w["kind"], pid)}


@app.get("/api/contract/{cid}")
def contract(cid: int, request: Request):
    c = M.s.one("SELECT * FROM contracts WHERE id = ?", (cid,))
    if not c:
        raise HTTPException(404)
    me=_me(request)
    if not _can_view_contract(c, me["account"] if me else None):
        raise HTTPException(403, "This negotiation belongs to its buyer and seller")
    c["trace"] = json.loads(c["trace"] or "{}"); c["sellers"] = json.loads(c["sellers"] or "[]")
    c["buyer_name"] = _name(c["buyer"])
    p = M.s.one("SELECT * FROM postings WHERE id = ?", (c["posting"],))
    msgs = M.s.q("SELECT * FROM messages WHERE contract = ? ORDER BY id", (cid,))
    for m in msgs:
        th = json.loads(m["thinking"] or "{}"); m["thinking"] = th.get("t", ""); m["by"] = th.get("by", "")
        m["name"] = _name(m["speaker"])
    txs = M.s.q("SELECT * FROM txs WHERE contract = ? ORDER BY id", (cid,))
    for t in txs:
        t["reference"] = f"C{cid}-T{t['id']}"
        evidence = json.loads(t["receipt"]) if t.get("receipt") else None
        if not evidence and t.get("hash"):
            try:
                evidence = M.rail.receipt(t["hash"])
                if evidence.get("validated"):
                    M.s.x("UPDATE txs SET receipt=? WHERE id=?", (json.dumps(evidence), t["id"]))
            except Exception:
                evidence = None
        t["receipt"] = evidence
        t["url"] = M.rail.explorer(t["hash"]) if t["hash"] else None; t["src_name"] = _name(t["src"]); t["dst_name"] = _name(t["dst"])
    for st in c["trace"].get("protocol", []):
        st["url"] = M.rail.explorer(st["tx"]) if st.get("tx") else None; st["who_name"] = _name(st["who"]) if st.get("who") else None
    c["overview"] = json.loads(c.get("overview") or "null")
    c.pop("terms",None)
    c["seller_name"] = _name(c.get("seller")) if c.get("seller") else None
    c["reference"] = f"C{cid}"
    c["ledger_memo"] = f"vaultmarket/contract/{cid}"
    return {"contract": c, "posting": p, "messages": msgs, "txs": txs, "ledger": M.rail.name}


def _bundles(aid: str):
    files = M.s.q("SELECT id, kind, name, status, sold, bytes, source, derived_from, resale, created, clean FROM files WHERE account = ? ORDER BY created DESC", (aid,))
    for f in files:
        c = json.loads(f.pop("clean") or "{}")
        att = c.pop("_attestation", None)
        f["attestation"] = {k: att[k] for k in ("records", "merkle_root", "checks", "cleaned")} if att else None
        f["preview"] = data.dumps({'name': f['name'], 'note': 'Complete package contents and source rights are in your private download.'}) if f['kind'] == data.PACKAGE_KIND else data.dumps(c)[:900]
    by_domain = {}
    for f in files:
        if f["status"] in ("bought", "bundled"):
            continue
        info = data.kind_info(f['kind'])
        b = by_domain.setdefault(f["kind"], {"kind": f["kind"], "domain": info["domain"], "label": info["label"], "files": []})
        b["files"].append(f)
    out = []
    for k, b in by_domain.items():
        st = {"offers": 0, "agreed": 0, "declined": 0}
        for c in M.s.q("SELECT trace FROM contracts WHERE kind = ? AND trace LIKE ?", (k, f'%"seller": "{aid}"%')):
            for s in json.loads(c["trace"] or "{}").get("seller_trace", []):
                if s["seller"] == aid:
                    st["offers"] += 1
                    st["agreed" if s["verdict"] == "agree" else "declined"] += 1
        best = M.s.one("SELECT MAX(offer) m FROM postings WHERE kind = ? AND status = 'open' AND buyer != ?", (k, aid))["m"]
        b.update(listed=sum(f["status"] == "listed" for f in b["files"]), earned=round(M.s.stat(f"earned:{aid}:{k}"), 1), best_offer=best, **st)
        out.append(b)
    demand = []
    for w in M.s.q("SELECT p.*, a.name buyer_name FROM postings p JOIN accounts a ON a.id = p.buyer WHERE p.status = 'open' AND p.buyer != ?", (aid,)):
        mine = [f for f in files if f["kind"] == w["kind"] and f["status"] in ("listed", "private")]
        if mine:
            demand.append({**w, "listed": sum(f["status"] == "listed" for f in mine), "private": sum(f["status"] == "private" for f in mine),
                           "interested": bool(M.s.one("SELECT 1 FROM interests WHERE account = ? AND posting = ?", (aid, w["id"])))})
    demand.sort(key=lambda w: (-(w["offer"] or 0), -(w["max"] or 0)))
    return files, out, demand


@app.get("/assets")
def assets_page():
    return FileResponse(os.path.join(STATIC,"assets.html"))


@app.get("/api/account/{aid}/portfolio")
def portfolio(aid: str, request: Request):
    _guard(request,aid,write=False)
    a=M.acct(aid)
    if not a:
        raise HTTPException(404)
    addr=a.get("payout") if a.get("payout") and M.rail.has_line(a["payout"]) else M.addr.get(aid)
    income=M.s.q("SELECT asset,SUM(drops)/1000000.0 amount FROM txs WHERE src=? AND type LIKE 'EscrowFinish%' AND result='tesSUCCESS' GROUP BY asset",(aid,))
    spending=M.s.q("SELECT t.asset,SUM(t.drops)/1000000.0 amount FROM txs t JOIN contracts c ON c.id=t.contract WHERE c.buyer=? AND t.type LIKE 'EscrowFinish%' AND t.result='tesSUCCESS' GROUP BY t.asset",(aid,))
    transactions=[]
    rows=M.s.q("SELECT t.*,c.buyer FROM txs t LEFT JOIN contracts c ON c.id=t.contract WHERE (t.src=? OR c.buyer=?) AND t.result='tesSUCCESS' AND (t.type LIKE 'EscrowFinish%' OR t.type LIKE 'Payment%' OR t.type LIKE 'EscrowCancel%') ORDER BY t.id DESC",(aid,aid))
    for t in rows:
        transactions.append({**{k:t[k] for k in ['id','contract','created','type','asset','hash','result']},"amount":t["drops"]/1000000.0,"direction":"in" if t["src"]==aid and t["type"].startswith("EscrowFinish") or t["type"].startswith("EscrowCancel") else "out","url":M.rail.explorer(t["hash"]) if t["hash"] else None})
    note="Recorded market transfers"
    if addr and M.rail.name!="mock":
        try:
            chain=M.rail.wallet_activity(addr)
            refs={t["hash"]:t["contract"] for t in rows}
            transactions=[{**t,"contract":refs.get(t["hash"])} for t in chain]
            note="Latest 200 wallet transactions, validated on the ledger"
        except Exception:
            note="Wallet history unavailable; showing recorded market transfers"
    return {"asset":M.rail.symbol(),"balance":M.rail.balance(addr) if addr else None,"address":addr,"budget":a["buy_agent"],"income":income,"spending":spending,"roi_percent":None,"roi_note":"A return requires purchase costs matched to the resold records; gross proceeds are not a return rate.","transactions":transactions,"history_note":note,"ledger":M.rail.name}


@app.get("/api/account/{aid}")
def account(aid: str, request: Request):
    _guard(request, aid, write=False)
    a = M.acct(aid)
    if not a:
        raise HTTPException(404)
    files, bundles, demand = _bundles(aid)
    growth = M.s.q("SELECT CAST((created - (SELECT MIN(created) FROM files)) / 60 AS INT) m, COUNT(*) n FROM files WHERE account = ? GROUP BY m ORDER BY m", (aid,))
    fees = M.s.q("SELECT asset,SUM(drops)/1000000.0 amount FROM txs WHERE src=? AND contract IS NULL AND result='tesSUCCESS' GROUP BY asset", (aid,))
    balances = M.s.q("SELECT asset,SUM(drops)/1000000.0 amount FROM txs WHERE src=? AND type LIKE 'EscrowFinish%' AND result='tesSUCCESS' GROUP BY asset", (aid,))
    stats = {"fees_by_asset":fees, "earned_by_asset": balances, "agreed": sum(b["agreed"] for b in bundles), "declined": sum(b["declined"] for b in bundles),
             "earned_xrp": next((b["amount"] for b in balances if b["asset"]=="XRP"),0), "fees_xrp": next((b["amount"] for b in fees if b["asset"]=="XRP"),0)}
    trade_rows=M.s.q("SELECT id,buyer,seller,kind,status,reason,total,items,sellers,asset,unit_micro,created FROM contracts WHERE buyer=? OR seller=? OR sellers LIKE ? ORDER BY id DESC", (aid,aid,'%'+json.dumps(aid)+'%'))
    trades = _trade_summaries([c for c in trade_rows if _can_view_contract(c,aid)],aid)
    payout=a.get("payout")
    display_address=payout if payout and M.rail.has_line(payout) else M.addr.get(aid)
    display_balance=M.rail.balance(payout) if payout and display_address==payout else M.balance(aid)
    return {"balance_address":display_address,"trades":trades,"agent_queue": M.s.q("SELECT q.*,p.purpose,p.buyer,c.status contract_status,c.reason contract_reason FROM sale_queue q LEFT JOIN postings p ON p.id=q.posting LEFT JOIN contracts c ON c.id=q.contract WHERE q.account=? ORDER BY q.id DESC", (aid,)),
            "account": a, "balance": display_balance, "address": M.addr.get(aid), "stats": stats, "bundles": bundles, "demand": demand,
            "bought": [f for f in files if f["status"] in ("bought", "bundled")], "files": len(files), "growth": growth,
            "uploads": M.s.q("SELECT * FROM uploads WHERE account = ? ORDER BY id DESC LIMIT 10", (aid,)),
            "recs": M.s.q("SELECT * FROM recs WHERE account = ? AND status = 'open' ORDER BY id DESC", (aid,)),
            "chat": [{**c, "actions": json.loads(c["actions"]) if c["actions"] else None} for c in M.s.q("SELECT * FROM chat WHERE account = ? ORDER BY id DESC", (aid,))][::-1]}


@app.post("/api/account/{aid}/settings")
def settings(aid: str, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    a = M.acct(aid)
    if not a:
        raise HTTPException(404, "account not found")
    if any(not isinstance(body.get(side, {}), dict) for side in ("sell_agent", "buy_agent")):
        raise HTTPException(400, "Agent settings must be objects")
    sell = {**a["sell_agent"], **body.get("sell_agent", {})}; buy = {**a["buy_agent"], **body.get("buy_agent", {})}
    if any(not isinstance(rules.get("model", "auto"), str) or rules.get("model", "auto") not in llm.models() for rules in (sell, buy)):
        raise HTTPException(400, "Choose auto or a model allowed by this service")
    import math
    try:
        values=list(sell.get("min",{}).values())+[buy.get("auto_limit",0)]
        if sell.get("mode") not in ("ask","auto") or any(not math.isfinite(float(v)) or float(v)<0 for v in values):
            raise ValueError()
        if any(not 0<=float(buy.get(k,0))<=1 for k in ("min_trust","max_overlap")):
            raise ValueError()
    except (ValueError,TypeError):
        raise HTTPException(400,"Prices and budgets must be finite, non-negative numbers; thresholds must be between 0 and 1")
    M.s.x("UPDATE accounts SET sell_agent = ?, buy_agent = ? WHERE id = ?", (json.dumps(sell), json.dumps(buy), aid))
    return {"ok": True}


@app.post("/api/account/{aid}/file/{fid}")
def file_list(aid: str, fid: int, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    M.set_listed(aid, fid, bool(body.get("listed")))
    return {"ok": True}


@app.post("/api/interest")
def interest(request: Request, body: dict = Body(...)):
    aid, pid = body["account"], int(body["posting"])
    _guard(request, aid)
    if body.get("on", True):
        M.s.x("INSERT OR IGNORE INTO interests (account, posting, created) VALUES (?, ?, ?)", (aid, pid, time.time()))
    else:
        M.s.x("DELETE FROM interests WHERE account = ? AND posting = ?", (aid, pid))
    return {"ok": True}


@app.post("/api/account/{aid}/bundle")
def bundle(aid: str,request: Request,body: dict=Body(...)):
    _guard(request,aid)
    try:
        return {"ok":True,"file":M.bundle_files(aid,[int(x) for x in body.get("files",[])])}
    except (ValueError,TypeError) as e:
        raise HTTPException(400,str(e))


@app.post("/api/account/{aid}/upload")
async def upload(aid: str, request: Request, file: UploadFile):
    user=_guard(request, aid)
    if user and user.get("demo"):
        raise HTTPException(403,"The shared demo accepts synthetic samples only. Sign in to upload your own files.")
    raw = await file.read()
    try:
        body = json.loads(raw)
    except Exception:
        return {"verdict": "block", "why": "the file is not JSON in one of the market's schemas (see the sample files), so it stays private"}
    with M.lock:
        return M.upload(aid, file.filename, body)


@app.post("/api/account/{aid}/upload-sample")
def upload_sample(aid: str, request: Request, body: dict = Body(...)):
    """Pick a file from the demo phone: a realistic record, sometimes with problems the intake must catch."""
    _guard(request, aid)
    import random
    rng = random.Random()
    a = M.acct(aid)
    kind, flaw = body.get("kind", "gps_track"), body.get("flaw")
    rec = data.make_record(kind, rng, a["name"], rng.randint(10, 80), (40.72, -73.98))
    if flaw == "diagnosis":
        rec["diagnosis"] = "obstructive sleep apnea"; rec["icd10"] = "G47.33"
    elif flaw == "duplicates" and kind == "sleep_log":
        rec["nights"] += [dict(rec["nights"][0]), dict(rec["nights"][1])]
    elif flaw == "spikes" and kind == "gps_track":
        rec["points"][4]["hr"] = 251; rec["points"][9]["hr"] = 12
    elif flaw == "minor":
        rec["subject_age"] = 12
    with M.lock:
        return M.upload(aid, data.file_name(kind, rec, 0), rec)


@app.post("/api/account/{aid}/upload/{uid}/clean")
def upload_clean(aid: str, uid: int, request: Request):
    _guard(request, aid)
    if not M.s.one("SELECT 1 FROM uploads WHERE id = ? AND account = ?", (uid, aid)):
        raise HTTPException(404)
    with M.lock:
        return M.clean_upload(uid)


@app.post("/api/account/{aid}/rec/{rid}")
def rec(aid: str, rid: int, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    r = M.s.one("SELECT * FROM recs WHERE id = ? AND account = ?", (rid, aid))
    if not r:
        raise HTTPException(404)
    if body.get("accept"):
        M.s.x("UPDATE files SET status = 'listed' WHERE account = ? AND kind = ? AND status = 'private'", (aid, r["kind"]))
    M.s.x("UPDATE recs SET status = ? WHERE id = ?", ("accepted" if body.get("accept") else "dismissed", rid))
    return {"ok": True}


@app.post("/api/account/{aid}/chat")
def chat(aid: str, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    if aid.startswith("u-") and _chat_today(aid) >= config.CHAT_DAILY:
        raise HTTPException(429, f"your agent answers {config.CHAT_DAILY} messages a day; try again tomorrow")
    if aid == "demo-vault" and _chat_today(aid) >= config.DEMO_CHAT_DAILY:
        raise HTTPException(429, "the shared demo has used today's agent messages; use your own vault or try again tomorrow")
    text = body["text"].strip()[:500]
    M.chat(aid, "me", text)
    a = M.acct(aid)
    discovery = body.get("intent")=="discover" or bool(re.search(r"^(?:what|which|how|where)\b|\bcan i\b|뭘|무엇|어떤|뭐|팔\s*수\s*있",text,re.I))
    ref = re.search(r"#(\d+)", text) if not discovery else None
    w = M.s.one("SELECT * FROM postings WHERE id = ? AND status = 'open'", (int(ref.group(1)),)) if ref else None
    if w and w["buyer"] != aid:
        M.enqueue_sale(aid, w["kind"], w["id"])
        return {"ok": True}
    if llm.enabled():
        threading.Thread(target=_converse, args=(aid, text, body, discovery), daemon=True).start()
    else:
        _rules_chat(aid, text, body, discovery)
    return {"ok": True}


def _amt(w) -> str:
    return f"{w['expected']*config.MICRO_PER_UNIT/1000000:.2f} {M.rail.label()}"


def _offer_buttons(offers) -> list[dict]:
    return [{"t":f"{KINDS[w['kind']]['label']} · {w['purpose']} · ~{_amt(w)}","do":"interest","posting":w["id"]} for w in offers]


def _set_min(aid: str, kind: str, price: float):
    floor=float(price)/(config.MICRO_PER_UNIT/1000000)
    if not 0<=floor<1000000:
        raise HTTPException(400,"Enter a finite non-negative minimum")
    rules=M.acct(aid)["sell_agent"];rules.setdefault("min",{})[kind]=floor
    M.s.x("UPDATE accounts SET sell_agent=? WHERE id=?",(json.dumps(rules),aid))


def _post_buy(aid: str, kind: str, offer: float, resale=False) -> int:
    a = M.acct(aid)
    if not 0<offer<1000000:
        raise HTTPException(400,"Enter a positive purchase budget")
    pid = M.s.insert("postings", buyer=aid, kind=kind, offer=offer, max=round(offer * 1.25, 1), purpose="aggregation and resale" if resale else f"{a['name']}'s own use", lot=1,
                     min_trust=a["buy_agent"].get("min_trust", 0.7), resale=int(bool(resale)), status="open", once=1)
    def run():
        with M.lock:          # released even if the negotiation raises, or the market loop would stall
            M.negotiate(M.s.one("SELECT * FROM postings WHERE id = ?", (pid,)))
    threading.Thread(target=run, daemon=True).start()
    return pid


def _rules_chat(aid: str, text: str, body: dict, discovery: bool):
    """The written-rules agent, used when no model is configured or the model does not answer."""
    a = M.acct(aid)
    p = {"kind":None,"intent":"discover","price":None} if discovery else agents.parse_chat(text, sell_model=a["sell_agent"].get("model", "auto"), buy_model=a["buy_agent"].get("model", "auto"))
    if p["intent"] == "other":
        M.chat(aid, "agent", "Tell me what to sell or what you need, for example 'sell my sleep logs' or 'I need air-quality data'.")
    elif not p["kind"]:
        offers=_sell_now(aid)[:3]
        if offers:
            M.chat(aid,"agent",f"{len(offers)} buyer request{'s' if len(offers)>1 else ''} fit your data and your minimums: "+"; ".join(f"{KINDS[w['kind']]['label']} for {w['purpose']} (~{_amt(w)})" for w in offers)+". Pick one and I'll negotiate it for you. The price is an estimate until the deal settles.",
                   _offer_buttons(offers))
        else:
            M.chat(aid,"agent","I found no matching sale yet. Add records in My DB; I will classify them and compare them with buyers' requests. Your files stay private until you choose to sell.")
    elif p["intent"] == "sell":
        if p.get("price") is not None:
            _set_min(aid, p["kind"], p["price"])
            M.chat(aid,"agent",f"Your minimum is now {p['price']:g} {M.rail.label()} for this data category.")
        M.enqueue_sale(aid, p["kind"])
    elif p["intent"] == "buy":
        offer = float(body["price"]) if body.get("price") is not None else float(p["price"])/(config.MICRO_PER_UNIT/1000000) if p["price"] is not None else KINDS[p["kind"]]["price"]
        pid = _post_buy(aid, p["kind"], offer, body.get("resale"))
        M.chat(aid, "agent", f"Posted request #{pid}: {KINDS[p['kind']]['label'].lower()} at {offer}, up to {round(offer * 1.25, 1)}. I will negotiate it next and buy on my own up to {a['buy_agent'].get('auto_limit')} total.")


def _converse(aid: str, text: str, body: dict, discovery: bool):
    """The model holds the conversation, off the request path so a slow provider never times the request out.
    It proposes; code checks every action against the owner's rules before anything happens."""
    try:
        a = M.acct(aid); u = config.MICRO_PER_UNIT/1000000
        files = M.s.q("SELECT kind, status, COUNT(*) n FROM files WHERE account = ? AND status IN ('listed','private') GROUP BY kind, status", (aid,))
        sold = M.s.one("SELECT COUNT(*) n, COALESCE(SUM(total*unit_micro),0)/1000000.0 t FROM contracts WHERE seller = ? AND status = 'settled' AND asset = ?", (aid, M.rail.symbol()))
        offers = _sell_now(aid)[:12]
        demand = [{"kind": d["kind"], "n": d["n"], "best": d["best"]} for d in M.s.q("SELECT kind, COUNT(*) n, MAX(max) best FROM postings WHERE status='open' AND buyer != ? GROUP BY kind", (aid,))]
        history = [{"who": c["role"], "text": c["text"][:300]} for c in M.s.q("SELECT role, text FROM chat WHERE account = ? ORDER BY id DESC LIMIT 8", (aid,))][::-1]
        ctx = {"asset": M.rail.label(), "my_files": [dict(f) for f in files], "deals_sold": sold["n"], "sold_total": sold["t"],
               "selling_mode": a["sell_agent"].get("mode"), "my_minimums": {k: round(v*u, 2) for k, v in (a["sell_agent"].get("min") or {}).items()},
               "blocked_purposes": a["sell_agent"].get("blocks", []), "auto_buy_limit": round(a["buy_agent"].get("auto_limit", 0)*u, 2),
               "matching_offers": [{"id": w["id"], "kind": w["kind"], "buyer": w["buyer_name"], "purpose": w["purpose"], "you_would_get": round(w["expected"]*u, 2), "buyer_budget": round(w["max"]*u, 2)} for w in offers],
               "open_demand_by_kind": demand, "kinds": {k: v["label"] for k, v in KINDS.items()}}
        side = "buy_agent" if agents.parse_chat(text)["intent"] == "buy" else "sell_agent"
        out = agents.chat_reply(text, ctx, history, model=a[side].get("model", "auto"))
        reply = str((out or {}).get("reply") or "").strip()
        if not reply:
            raise ValueError("no model answer")
        by_id = {w["id"]: w for w in offers}
        picks = [by_id[i] for i in (out.get("offer_ids") or []) if isinstance(i, int) and i in by_id][:3]
        # the model only proposes: each change or trade becomes a button the owner presses, checked again when pressed
        acts = _offer_buttons(picks)
        sm = out.get("set_min") or {}
        if sm.get("kind") in KINDS and isinstance(sm.get("price"), (int, float)) and 0 <= sm["price"] < 1e6:
            acts.append({"t": f"Set {KINDS[sm['kind']]['label'].lower()} minimum to {sm['price']:g} {M.rail.label()}", "do": "set_min", "kind": sm["kind"], "price": float(sm["price"])})
        if out.get("sell_kind") in KINDS:
            acts.append({"t": f"Sell my {KINDS[out['sell_kind']]['label'].lower()}", "do": "sell_kind", "kind": out["sell_kind"]})
        buy = out.get("buy") or {}
        if buy.get("kind") in KINDS and isinstance(buy.get("budget"), (int, float)) and 0 < buy["budget"] < 1e6:
            acts.append({"t": f"Post a request: {KINDS[buy['kind']]['label'].lower()} up to {buy['budget']:g} {M.rail.label()}", "do": "post_buy", "kind": buy["kind"], "budget": float(buy["budget"])})
        M.chat(aid, "agent", reply[:800], acts or None)
    except Exception:
        try:
            _rules_chat(aid, text, body, discovery)
        except HTTPException as e:
            M.chat(aid, "agent", str(e.detail))
    M.events += 1


@app.post("/api/account/{aid}/chat/{cid}/act")
def chat_act(aid: str, cid: int, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    c = M.s.one("SELECT * FROM chat WHERE id = ? AND account = ? AND done = 0", (cid, aid))
    if not c:
        return {"ok": False}
    act = json.loads(c["actions"])[int(body["i"])]
    M.s.x("UPDATE chat SET done = 1 WHERE id = ?", (cid,))
    if act["do"] == "interest":
        w = M.s.one("SELECT * FROM postings WHERE id=?", (act["posting"],))
        if w:
            M.enqueue_sale(aid, w["kind"], w["id"])
    elif act["do"] == "buy":
        def go():
            with M.lock:
                M.approve_buy(act["contract"])
                state=M.s.one("SELECT status FROM contracts WHERE id=?",(act["contract"],))
            M.chat(aid,"agent",f"Purchase #{act['contract']}: {state['status']}. Open its receipts for the payment and delivery result.")
            M.events+=1
        threading.Thread(target=go,daemon=True).start()
    elif act["do"] == "sell_kind" and act.get("kind") in KINDS:
        M.enqueue_sale(aid, act["kind"])
    elif act["do"] == "set_min" and act.get("kind") in KINDS:
        _set_min(aid, act["kind"], act["price"])
        M.chat(aid, "agent", f"Your minimum for {KINDS[act['kind']]['label'].lower()} is now {act['price']:g} {M.rail.label()}.")
    elif act["do"] == "post_buy" and act.get("kind") in KINDS:
        pid = _post_buy(aid, act["kind"], act["budget"]/(config.MICRO_PER_UNIT/1000000))
        M.chat(aid, "agent", f"Posted request #{pid} for {KINDS[act['kind']]['label'].lower()}, up to {act['budget']:g} {M.rail.label()}. I'll negotiate it next.")
    elif act["do"] == "skip_buy":
        M.s.x("UPDATE contracts SET status='rejected',reason='Owner skipped this purchase' WHERE id=? AND buyer=? AND status='awaiting buyer'",(act.get("contract"),aid))
    return {"ok": True}


@app.get("/api/stream")
async def stream():
    async def gen():
        last = -1
        while True:
            if M.events != last:
                last = M.events
                yield f"data: {json.dumps({'events': last, 'connected': len(M.addr)})}\n\n"
            await asyncio.sleep(1.5)
    return StreamingResponse(gen(), media_type="text/event-stream")
