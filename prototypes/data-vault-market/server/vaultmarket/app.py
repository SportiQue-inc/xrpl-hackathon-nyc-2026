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
    s = M.s.one("SELECT u.* FROM sessions s JOIN users u ON u.username = s.username WHERE s.token = ?", (tok,))
    if s:
        s.pop("pw", None); s.pop("salt", None)
    return s


def _guard(request: Request, aid: str, write: bool = True):
    """Members act only on their own account. Demo accounts are open locally and read-only when public."""
    me = _me(request)
    if aid.startswith("u-"):
        if not me or me["account"] != aid:
            raise HTTPException(403, "sign in as this member")
    elif write and config.PUBLIC:
        raise HTTPException(403, "demo accounts are read-only here; sign up to use your own")
    return me


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
    return {"ledger": M.rail.name, "model": llm.model_name(), "llm": llm.USAGE, "kinds": KINDS, "k_min": config.K_MIN,
            "unit_xrp": config.DROPS_PER_XRP_UNIT / 1e6, "connected": len(M.addr), "accounts": len(M.s.q("SELECT id FROM accounts")),
            "rpm_cap": config.LLM_RPM, "daily_cap": config.LLM_DAILY_CALLS}


@app.get("/api/accounts")
def accounts(request: Request):
    me = _me(request)
    return M.s.q("SELECT id, name, type, online FROM accounts WHERE id NOT LIKE 'u-%' OR id = ? ORDER BY type DESC, name", (me["account"] if me else "",))


@app.get("/api/market")
def market(account: str = "dana", domain: str | None = None):
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
    contracts = s.q(f"SELECT id, posting, buyer, kind, status, reason, total, items, sellers, created FROM contracts WHERE status != 'negotiating' AND kind IN ({ph}) ORDER BY id DESC LIMIT 60", tuple(kinds))
    for c in contracts:
        c["buyer_name"] = _name(c["buyer"]); c["sellers"] = json.loads(c["sellers"] or "[]")
        c["mine"] = c["buyer"] == account or account in c["sellers"]
        c["drops"] = int((c["total"] or 0) * config.DROPS_PER_XRP_UNIT)
        t = s.one("SELECT hash FROM txs WHERE contract = ? AND hash IS NOT NULL ORDER BY id DESC LIMIT 1", (c["id"],))
        c["tx_url"] = M.rail.explorer(t["hash"]) if t else None
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
                         "volume": round(s.stat("volume"), 1), "xrp": round(s.stat("drops") / 1e6, 4), "uploads": s.stat("uploads"),
                         "blocked": s.stat("blocked"), "cleaned": s.stat("cleaned"), "fees": round(s.stat("fees"), 1),
                         "txs": s.one("SELECT COUNT(*) n FROM txs")["n"]},
            "domains": sorted(doms, key=lambda d: -(d["listed"] + 5 * d["settled"])), "postings": postings, "contracts": contracts, "listings": listings, "sell_now": _sell_now(account), "events": M.events}


def _sell_now(aid: str) -> list[dict]:
    """Open requests this account's data already qualifies for: it has files of the kind, the purpose is
    not one its rules refuse, and the offer meets its minimum. Sorted by what the owner would get."""
    a = M.acct(aid)
    if not a:
        return []
    out = []
    for w in M.s.q("SELECT p.*, a.name buyer_name, a.verified FROM postings p JOIN accounts a ON a.id = p.buyer WHERE p.status = 'open' AND p.buyer != ?", (aid,)):
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


def _consider(aid: str, a: dict, w: dict) -> str:
    """The owner pointed the agent at one request. Check it against the owner's rules, then act or say why not."""
    k = KINDS[w["kind"]]; floor = a["sell_agent"]["min"].get(w["kind"], 0)
    mine = M.s.q("SELECT status FROM files WHERE account = ? AND kind = ? AND status IN ('listed', 'private')", (aid, w["kind"]))
    buyer = _name(w["buyer"])
    if not mine:
        return f"You have no {k['label'].lower()} in your DB, so I can't sell to {buyer}. Upload some in My DB and I'll check again."
    if w["purpose"] in a["sell_agent"].get("blocks", []):
        return f"{buyer} wants it for {w['purpose']}, which your rules refuse. I'm leaving request #{w['id']} alone. Remove it from 'Never sell for' in Agent settings if you changed your mind."
    if w["max"] < floor:
        return f"{buyer} pays at most {w['max']} and your minimum is {floor}. I won't sell below it. Lower your minimum in Agent settings if you want this sale."
    M.s.x("UPDATE files SET status = 'listed' WHERE account = ? AND kind = ? AND status = 'private'", (aid, w["kind"]))
    M.s.x("INSERT OR IGNORE INTO interests (account, posting, created) VALUES (?, ?, ?)", (aid, w["id"], time.time()))
    price = max(floor, w["offer"])
    return (f"Fits your terms: {buyer} offers {w['offer']} (up to {w['max']}) for {w['purpose']}, and your minimum is {floor}. "
            f"I listed your {len(mine)} {k['label'].lower()} file(s) as pseudonymized copies and put you first in line for request #{w['id']}. "
            f"I'll ask for {price}" + (f" and it settles once a lot of at least {config.K_MIN} people is ready." if k["personal"] else "."))


@app.post("/api/account/{aid}/sell-now/{pid}")
def sell_now(aid: str, pid: int, request: Request):
    """One tap: list my files of that kind as pseudonymized copies and put me first in line for this request."""
    _guard(request, aid)
    w = M.s.one("SELECT * FROM postings WHERE id = ? AND status = 'open'", (pid,))
    if not w:
        raise HTTPException(404)
    M.s.x("UPDATE files SET status = 'listed' WHERE account = ? AND kind = ? AND status = 'private'", (aid, w["kind"]))
    M.s.x("INSERT OR IGNORE INTO interests (account, posting, created) VALUES (?, ?, ?)", (aid, pid, time.time()))
    M.chat(aid, "agent", f"Listed your {KINDS[w['kind']]['label'].lower()} and put you first in line for request #{pid} from {_name(w['buyer'])}. "
                         f"The sale goes through once a lot of at least {config.K_MIN if KINDS[w['kind']]['personal'] else 1} is ready.")
    return {"ok": True}


@app.get("/api/contract/{cid}")
def contract(cid: int):
    c = M.s.one("SELECT * FROM contracts WHERE id = ?", (cid,))
    if not c:
        raise HTTPException(404)
    c["trace"] = json.loads(c["trace"] or "{}"); c["sellers"] = json.loads(c["sellers"] or "[]")
    c["buyer_name"] = _name(c["buyer"])
    p = M.s.one("SELECT * FROM postings WHERE id = ?", (c["posting"],))
    msgs = M.s.q("SELECT * FROM messages WHERE contract = ? ORDER BY id", (cid,))
    for m in msgs:
        th = json.loads(m["thinking"] or "{}"); m["thinking"] = th.get("t", ""); m["by"] = th.get("by", "")
        m["name"] = _name(m["speaker"])
    txs = M.s.q("SELECT * FROM txs WHERE contract = ? ORDER BY id", (cid,))
    for t in txs:
        t["url"] = M.rail.explorer(t["hash"]) if t["hash"] else None; t["src_name"] = _name(t["src"]); t["dst_name"] = _name(t["dst"])
    for st in c["trace"].get("protocol", []):
        st["url"] = M.rail.explorer(st["tx"]) if st.get("tx") else None; st["who_name"] = _name(st["who"]) if st.get("who") else None
    return {"contract": c, "posting": p, "messages": msgs, "txs": txs, "ledger": M.rail.name}


def _bundles(aid: str):
    files = M.s.q("SELECT id, kind, name, status, sold, bytes, source, derived_from, created, clean FROM files WHERE account = ? ORDER BY created DESC", (aid,))
    for f in files:
        c = json.loads(f.pop("clean") or "{}")
        att = c.pop("_attestation", None)
        f["attestation"] = {k: att[k] for k in ("records", "merkle_root", "checks", "cleaned")} if att else None
        f["preview"] = data.dumps(c)[:900]
    by_domain = {}
    for f in files:
        if f["status"] in ("bought", "bundled"):
            continue
        b = by_domain.setdefault(f["kind"], {"kind": f["kind"], "domain": KINDS[f["kind"]]["domain"], "label": KINDS[f["kind"]]["label"], "files": []})
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
    return files, out, demand


@app.get("/api/account/{aid}")
def account(aid: str, request: Request):
    _guard(request, aid, write=False)
    a = M.acct(aid)
    if not a:
        raise HTTPException(404)
    files, bundles, demand = _bundles(aid)
    growth = M.s.q("SELECT CAST((created - (SELECT MIN(created) FROM files)) / 60 AS INT) m, COUNT(*) n FROM files WHERE account = ? GROUP BY m ORDER BY m", (aid,))
    return {"account": a, "balance": M.balance(aid), "address": M.addr.get(aid), "bundles": bundles, "demand": demand,
            "bought": [f for f in files if f["status"] in ("bought", "bundled")], "files": len(files), "growth": growth,
            "uploads": M.s.q("SELECT * FROM uploads WHERE account = ? ORDER BY id DESC LIMIT 10", (aid,)),
            "recs": M.s.q("SELECT * FROM recs WHERE account = ? AND status = 'open' ORDER BY id DESC", (aid,)),
            "chat": [{**c, "actions": json.loads(c["actions"]) if c["actions"] else None} for c in M.s.q("SELECT * FROM chat WHERE account = ? ORDER BY id DESC LIMIT 40", (aid,))][::-1]}


@app.post("/api/account/{aid}/settings")
def settings(aid: str, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    a = M.acct(aid)
    sell = {**a["sell_agent"], **body.get("sell_agent", {})}; buy = {**a["buy_agent"], **body.get("buy_agent", {})}
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


@app.post("/api/account/{aid}/upload")
async def upload(aid: str, request: Request, file: UploadFile):
    _guard(request, aid)
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
    text = body["text"].strip()[:500]
    M.chat(aid, "me", text)
    a = M.acct(aid)
    ref = re.search(r"#(\d+)", text)
    w = M.s.one("SELECT * FROM postings WHERE id = ? AND status = 'open'", (int(ref.group(1)),)) if ref else None
    if w and w["buyer"] != aid:
        M.chat(aid, "agent", _consider(aid, a, w))
        return {"ok": True}
    p = agents.parse_chat(text)
    if not p["kind"]:
        M.chat(aid, "agent", "Which data do you mean? Running tracks, sleep logs, receipts, voice clips or air-quality sensors.")
    elif p["intent"] == "sell":
        n = M.s.x("UPDATE files SET status = 'listed' WHERE account = ? AND kind = ? AND status = 'private'", (aid, p["kind"]))
        cnt = M.s.one("SELECT COUNT(*) n FROM files WHERE account = ? AND kind = ? AND status = 'listed'", (aid, p["kind"]))["n"]
        ws = M.s.q("SELECT id FROM postings WHERE kind = ? AND status = 'open' AND buyer != ?", (p["kind"], aid))
        for w in ws:
            M.s.x("INSERT OR IGNORE INTO interests (account, posting, created) VALUES (?, ?, ?)", (aid, w["id"], time.time()))
        M.chat(aid, "agent", f"{cnt} {KINDS[p['kind']]['label'].lower()} file(s) are listed as pseudonymized copies. I marked interest in {len(ws)} open request(s), "
                             f"so I negotiate those first, within your minimum of {a['sell_agent']['min'].get(p['kind'])}.")
    elif p["intent"] == "buy":
        offer = p["price"] or KINDS[p["kind"]]["price"]
        pid = M.s.insert("postings", buyer=aid, kind=p["kind"], offer=offer, max=round(offer * 1.25, 1), purpose=f"{a['name']}'s own use", lot=6 if KINDS[p["kind"]]["personal"] else 2,
                         min_trust=a["buy_agent"].get("min_trust", 0.7), resale=0, status="open", once=1)
        M.chat(aid, "agent", f"Posted request #{pid}: {KINDS[p['kind']]['label'].lower()} at {offer}, up to {round(offer * 1.25, 1)}. I will negotiate it next and buy on my own up to {a['buy_agent'].get('auto_limit')} total.")
        threading.Thread(target=lambda: (M.lock.acquire(), M.negotiate(M.s.one("SELECT * FROM postings WHERE id = ?", (pid,))), M.lock.release()), daemon=True).start()
    else:
        M.chat(aid, "agent", "Tell me what to sell or what you need, for example 'sell my sleep logs' or 'I need air-quality data'.")
    return {"ok": True}


@app.post("/api/account/{aid}/chat/{cid}/act")
def chat_act(aid: str, cid: int, request: Request, body: dict = Body(...)):
    _guard(request, aid)
    c = M.s.one("SELECT * FROM chat WHERE id = ? AND account = ? AND done = 0", (cid, aid))
    if not c:
        return {"ok": False}
    act = json.loads(c["actions"])[int(body["i"])]
    M.s.x("UPDATE chat SET done = 1 WHERE id = ?", (cid,))
    if act["do"] == "interest":
        M.s.x("INSERT OR IGNORE INTO interests (account, posting, created) VALUES (?, ?, ?)", (aid, act["posting"], time.time()))
        M.chat(aid, "agent", "Okay. I will include you in the next lot for that request, within your rules.")
    elif act["do"] == "buy" and act["contract"] in M.pending_buys:
        pb = M.pending_buys.pop(act["contract"])
        def go():
            with M.lock:
                M.settle(act["contract"], pb["w"], pb["verified"], pb["trace"], pb["total"])
            M.chat(aid, "agent", f"Bought. Contract #{act['contract']} settled on the ledger; the data is in your DB.")
        threading.Thread(target=go, daemon=True).start()
    elif act["do"] == "skip_buy":
        M.pending_buys.pop(act.get("contract"), None)
        M.s.x("UPDATE contracts SET status = 'rejected', reason = 'owner skipped' WHERE id = ?", (act.get("contract"),))
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
