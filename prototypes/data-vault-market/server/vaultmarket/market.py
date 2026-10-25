"""The market: 50 accounts, their vaults, postings, negotiations and settlement, running continuously."""
from __future__ import annotations

import json
import math
import random
import statistics
import threading
import time
import traceback

from . import agents, config, data, intake, llm
from .data import KINDS
import hashlib

from .rail import Rail, condition_hex, merkle_proof, merkle_verify
from .store import Store

PEOPLE = ["Dana Park", "Minho Lee", "Sora Kim", "Jae Choi", "Lina Haddad", "Omar Farouk", "Priya Nair", "Ken Watanabe", "Ana Souza", "Tomas Novak",
          "Yuki Sato", "Bilal Khan", "Mei Lin", "Chris Doyle", "Nadia Petrova", "Leo Rossi", "Hana Jung", "Ravi Iyer", "Sofia Marin", "Ivan Horvat",
          "Zoe Carter", "Kofi Mensah", "Elif Demir", "Mateo Ruiz", "Aisha Bello", "Noah Fischer", "Jin Park", "Lucia Gomez", "Sam Taylor", "Amara Obi",
          "Theo Martin", "Rin Takahashi", "Diego Alvarez", "Maya Cohen", "Ola Nordmann", "Ethan Brooks", "Seo-yeon Han", "Farah Aziz", "Jonas Berg", "Bo Zhang",
          "Tara Singh", "Wen Chen"]
ORGS = [
    {"id": "atlas-maps", "name": "Atlas Maps", "buys": [("gps_track", 11, 14, "route-safety model", 6, 0)]},
    {"id": "restwell", "name": "Restwell App", "buys": [("sleep_log", 7, 9, "sleep coaching feature", 6, 0)]},
    {"id": "murmur", "name": "Murmur Speech Lab", "buys": [("audio", 5, 7, "speech model training", 5, 0)]},
    {"id": "northwind", "name": "Northwind Grocers", "buys": [("purchase_receipts", 2, 3.5, "basket research", 6, 0)]},
    {"id": "orbit-insure", "name": "Orbit Insure R&D", "buys": [("sleep_log", 9, 12, "insurance pricing", 5, 0)]},
    {"id": "city-health", "name": "City Health Dept", "buys": [("air", 4, 5, "pollution alerts", 2, 0)]},
    {"id": "kite-robotics", "name": "Kite Robotics", "buys": [("gps_track", 9, 11, "delivery robot routing", 5, 0)], "sells": "air"},
    {"id": "coop-broker", "name": "DataCo-op Broker", "buys": [("gps_track", 10, 13, "aggregation and resale", 5, 1), ("sleep_log", 6, 8, "aggregation and resale", 5, 1)]},
]
BROKER = "coop-broker"


class Market:
    def __init__(self):
        self.s = Store(config.DB_PATH)
        self.rail = Rail()
        self.rng = random.Random()
        self.ready = 0                 # accounts connected to the ledger so far
        self.addr: dict[str, str] = {}
        self._bal: dict[str, tuple[float, float]] = {}
        self.pending_buys: dict[int, dict] = {}
        self.events = 0
        self.lock = threading.Lock()

    # ---------------- setup ----------------
    def seed(self):
        if not self.s.one("SELECT id FROM accounts LIMIT 1"):
            rng = random.Random(7)
            for i, name in enumerate(PEOPLE[: max(0, config.AGENTS - len(ORGS))]):
                aid = name.split()[0].lower().replace("-", "")
                mins = {k: round(KINDS[k]["price"] * rng.uniform(0.6, 1.25), 1) for k in KINDS}
                blocks = (["insurance pricing"] if rng.random() < 0.55 else []) + (["speech model training"] if rng.random() < 0.2 else [])
                mode = "ask" if aid == "dana" else "auto"
                if aid == "dana":
                    mins.update(gps_track=10, sleep_log=7, purchase_receipts=2, audio=5); blocks = ["insurance pricing"]
                self.s.insert("accounts", id=aid, name=name, type="person", trust=round(rng.uniform(0.72, 0.97), 2), verified=0,
                              sell_agent={"mode": mode, "min": mins, "blocks": blocks}, buy_agent={"auto_limit": 60, "min_trust": 0.7, "max_overlap": 0.3})
                home = (round(40.66 + rng.random() * 0.14, 5), round(-74.01 + rng.random() * 0.1, 5))
                counts = {"gps_track": rng.randint(1, 6), "sleep_log": rng.randint(0, 3), "purchase_receipts": rng.randint(0, 2), "audio": rng.randint(0, 1)}
                if aid == "dana":
                    counts = {"gps_track": 5, "sleep_log": 3, "purchase_receipts": 2, "audio": 1}
                for k, c in counts.items():
                    for j in range(c):
                        body = data.make_record(k, rng, name, j, home)
                        listed = rng.random() < 0.7 if aid != "dana" else k == "gps_track" and j < 2
                        self.add_file(aid, k, data.file_name(k, body, j), body, listed=listed, source=body.get("device_serial", "phone"))
            for o in ORGS:
                self.s.insert("accounts", id=o["id"], name=o["name"], type="org", trust=0.95, verified=1,
                              sell_agent={"mode": "auto", "min": {"air": 3.5, "gps_track": 12, "sleep_log": 8}, "blocks": []},
                              buy_agent={"auto_limit": 10_000, "min_trust": 0.7, "max_overlap": 0.3})
                for (k, offer, mx, purpose, lot, resale) in o["buys"]:
                    self.s.insert("postings", buyer=o["id"], kind=k, offer=offer, max=mx, purpose=purpose, lot=lot, min_trust=0.7, resale=resale, status="open", once=0)
                if o.get("sells") == "air":
                    for j in range(8):
                        body = data.make_record("air", rng, o["name"], j, (0, 0))
                        self.add_file(o["id"], "air", data.file_name("air", body, j), body, listed=True, source="kite-sensor-net")
        # contracts a previous run left mid-flight never settle; close them honestly
        self.s.x("UPDATE contracts SET status = 'rejected', reason = 'interrupted by a server restart' WHERE status IN ('negotiating', 'settling')")
        threading.Thread(target=self._connect_all, daemon=True).start()

    def _connect_all(self):
        """Every account gets its own XRPL wallet (Testnet faucet on first run, reused after)."""
        from concurrent.futures import ThreadPoolExecutor
        def one(aid):
            for attempt in range(4):
                try:
                    addr = self.rail.ensure_account(aid)
                    self.addr[aid] = addr
                    self.s.x("UPDATE accounts SET address = ? WHERE id = ?", (addr, aid))
                    break
                except Exception:
                    time.sleep(4 * (attempt + 1))
            self.ready += 1
            self.events += 1
        self.platform = self.rail.ensure_account("platform")
        # orgs first (they post the demand), then people; a few faucet calls at a time
        with ThreadPoolExecutor(max_workers=6) as ex:
            list(ex.map(one, [a["id"] for a in self.s.q("SELECT id FROM accounts ORDER BY type DESC, id")]))
        self.setup_asset()

    def setup_asset(self):
        """Trust lines and starting test USD: companies get budgets for many lots, people a small float
        for buying and cleaning fees. Trading waits for this, so no lot settles in the wrong asset."""
        holders = {self.platform: 10}
        for a in self.s.q("SELECT id, type FROM accounts"):
            if a["id"] in self.addr:
                holders[self.addr[a["id"]]] = 20000 if a["type"] == "org" else 300
        self.rail.setup_token(holders, funder=self.addr.get("coop-broker") or self.platform)
        self.asset_ready = True
        self._bal.clear(); self.events += 1

    def add_user_account(self, aid: str, name: str):
        """A signed-up member: an empty vault, an agent that asks before every sale, and its own XRPL wallet."""
        mins = {k: KINDS[k]["price"] for k in KINDS}
        self.s.insert("accounts", id=aid, name=name, type="person", trust=0.8, verified=0,
                      sell_agent={"mode": "ask", "min": mins, "blocks": ["insurance pricing"]},
                      buy_agent={"auto_limit": 10, "min_trust": 0.7, "max_overlap": 0.3})
        def connect():
            for attempt in range(3):
                try:
                    addr = self.rail.ensure_account(aid)
                    self.addr[aid] = addr
                    self.s.x("UPDATE accounts SET address = ? WHERE id = ?", (addr, aid))
                    self.chat(aid, "agent", f"Welcome. Your agent's wallet on the ledger is {addr}. Upload data in My DB; I ask you before every sale.")
                    return
                except Exception:
                    time.sleep(3 * (attempt + 1))
        threading.Thread(target=connect, daemon=True).start()

    # ---------------- files ----------------
    def add_file(self, account: str, kind: str, name: str, body: dict, listed: bool, source: str, cleaned=False, checks=None) -> int:
        clean = data.pseudonymize(kind, body)
        att = intake.attest(kind, clean, checks or ["schema", "value ranges", "duplicates", "identifiers removed"], cleaned)
        clean["_attestation"] = att
        return self.s.insert("files", account=account, kind=kind, name=name, raw=data.dumps(body), clean=data.dumps(clean),
                             status="listed" if listed else "private", fps=data.fingerprints(body), source=source, bytes=len(data.dumps(clean)))

    def upload(self, account: str, name: str, body: dict, auto: bool = False) -> dict:
        """Intake for one uploaded file. auto=True: a demo account's agent pays the cleaning fee itself."""
        self.s.bump("uploads")
        sc = intake.screen(body)
        uid = self.s.insert("uploads", account=account, name=name, verdict=sc["verdict"], why=sc["why"], fee=sc.get("fee"))
        if sc["verdict"] == "block":
            self.s.bump("blocked")
            return {"upload": uid, **sc}
        if sc["verdict"] == "clean" and not auto:
            self.s.x("UPDATE uploads SET file = -1 WHERE id = ?", (uid,))
            self._held = getattr(self, "_held", {}); self._held[uid] = (account, name, body, sc)
            return {"upload": uid, **sc}
        if sc["verdict"] == "clean":
            return self.clean_upload(uid, (account, name, body, sc), listed=True)
        fid = self.add_file(account, sc["kind"], name, body, listed=auto, source=body.get("device_serial", "upload"))
        self.s.x("UPDATE uploads SET file = ? WHERE id = ?", (fid, uid))
        return {"upload": uid, "file": fid, **sc}

    def clean_upload(self, uid: int, held=None, listed=False) -> dict:
        held = held or getattr(self, "_held", {}).pop(uid, None)
        if not held:
            return {"error": "nothing to clean"}
        account, name, body, sc = held
        fee_drops = int(sc["fee"] * config.MICRO_PER_UNIT)
        tx = self._fee(account, fee_drops, f"cleaning {name}")
        fid = self.add_file(account, sc["kind"], name, intake.clean(sc["kind"], body), listed=listed, source=body.get("device_serial", "upload"),
                            cleaned=True, checks=["schema", "value ranges", "duplicates", "identifiers removed"] + sc["issues"])
        self.s.x("UPDATE uploads SET file = ?, verdict = 'cleaned' WHERE id = ?", (fid, uid))
        self.s.bump("cleaned"); self.s.bump("fees", sc["fee"])
        return {"upload": uid, "file": fid, "verdict": "cleaned", "fee": sc["fee"], "tx": tx}

    def _fee(self, account: str, drops: int, memo: str) -> str | None:
        src, dst = self.addr.get(account), getattr(self, "platform", None)
        if not (src and dst):
            return None
        try:
            r = self.rail.pay(src, dst, drops, memo)
            self.s.insert("txs", contract=None, type="Payment (cleaning fee)", hash=r["hash"], src=account, dst="platform", drops=drops, result=r["result"])
            return r["hash"]
        except Exception:
            return None

    def set_listed(self, account: str, fid: int, on: bool):
        self.s.x("UPDATE files SET status = ? WHERE id = ? AND account = ? AND status IN ('private','listed')", ("listed" if on else "private", fid, account))

    # ---------------- helpers ----------------
    def acct(self, aid: str) -> dict:
        a = self.s.one("SELECT * FROM accounts WHERE id = ?", (aid,))
        if a:
            a["sell_agent"] = json.loads(a["sell_agent"]); a["buy_agent"] = json.loads(a["buy_agent"])
        return a

    def balance(self, aid: str) -> float | None:
        addr = self.addr.get(aid)
        if not addr:
            return None
        v, t = self._bal.get(aid, (None, 0))
        if time.time() - t > 20:
            v = self.rail.balance(addr)
            self._bal[aid] = (v, time.time())
        return v

    def owned_fps(self, aid: str, kind: str) -> set:
        fps = set()
        for f in self.s.q("SELECT fps FROM files WHERE account = ? AND kind = ?", (aid, kind)):
            fps.update(json.loads(f["fps"] or "[]"))
        return fps

    def chat(self, aid: str, role: str, text: str, actions=None):
        self.s.insert("chat", account=aid, role=role, text=text, actions=actions or None)

    # ---------------- negotiation ----------------
    def negotiate(self, w: dict) -> int | None:
        # the LLM writes the buyer's opening, the first seller's answer and the buyer's decision when
        # three slots are free under the cap; otherwise the whole round runs on written rules
        llm.budget(3 if llm.free_slots() >= 3 else 0)
        try:
            return self._negotiate(w)
        finally:
            llm.budget(None)

    def quote(self, kind: str) -> dict:
        """The market price, formed by the agents themselves: the median of recent clearing prices on the
        shared ledger, nudged by supply (vaults listing it) against demand (people wanted in open requests)."""
        rows = [r["price"] for r in self.s.q("SELECT price FROM prices WHERE kind = ? ORDER BY id DESC LIMIT 30", (kind,))]
        base = statistics.median(rows) if rows else KINDS[kind]["price"]
        supply = self.s.one("SELECT COUNT(DISTINCT account) n FROM files WHERE kind = ? AND status = 'listed'", (kind,))["n"]
        demand = self.s.one("SELECT COALESCE(SUM(lot), 0) n FROM postings WHERE kind = ? AND status = 'open'", (kind,))["n"]
        pressure = demand / max(1, supply)
        price = base * min(1.25, max(0.8, 1 + 0.12 * math.log(max(pressure, 0.05))))
        return {"price": round(price, 1), "median": round(base, 1), "n": len(rows), "lo": round(min(rows), 1) if rows else None,
                "hi": round(max(rows), 1) if rows else None, "supply": supply, "demand": demand, "pressure": round(pressure, 2)}

    def _negotiate(self, w: dict) -> int | None:
        buyer = self.acct(w["buyer"])
        if not buyer or w["buyer"] not in self.addr:
            return None
        personal = KINDS[w["kind"]]["personal"]
        owned = self.owned_fps(w["buyer"], w["kind"])
        # price discovery: the buyer opens under the market price, never above its owner's budget
        q = self.quote(w["kind"])
        opening = round(min(w["max"], max(0.5, q["price"] * 0.92)), 1)
        w = {**w, "offer": opening, "quote": q}
        cid = self.s.insert("contracts", posting=w["id"], buyer=w["buyer"], kind=w["kind"], status="negotiating")
        say = lambda who, side, text, thinking="", by="": self.s.insert("messages", contract=cid, speaker=who, side=side, text=text, thinking=json.dumps({"t": thinking, "by": by}))
        op = agents.buyer_open(buyer["name"], w, len(owned))
        say(w["buyer"], "buyer", op["message"], op["thinking"], op["by"])
        trace = {"buyer_trace": [op["thinking"]], "seller_trace": [], "verdicts": {"sellers": {}}, "tx": [], "protocol": [], "model": llm.model_name()}
        def step(protocol, detail, ok=True, who=None, tx=None):
            trace["protocol"].append({"protocol": protocol, "detail": detail, "ok": ok, "who": who, "tx": tx})
        step("Price discovery (shared ledger)", f"market price {q['price']}: median {q['median']} of the last {q['n']} clearing prices"
             + (f" (range {q['lo']}–{q['hi']})" if q["n"] else " (no trades yet: list price)")
             + f", supply {q['supply']} vaults vs demand {q['demand']} people wanted (pressure {q['pressure']}). Buyer opens at {opening}, budget {w['max']}.")

        files = self.s.q("SELECT f.*, a.trust FROM files f JOIN accounts a ON a.id = f.account WHERE f.kind = ? AND f.status = 'listed' AND f.account != ?", (w["kind"], w["buyer"]))
        by_acct: dict[str, list] = {}
        for f in files:
            if f["account"] not in self.addr:      # wallet not funded yet: not in the market this round
                continue
            by_acct.setdefault(f["account"], []).append(f)
        interested = {r["account"] for r in self.s.q("SELECT account FROM interests WHERE posting = ?", (w["id"],))}
        low_trust = [a for a, fs in by_acct.items() if fs[0]["trust"] < w["min_trust"]]
        cands = [a for a in by_acct if a not in low_trust]
        self.rng.shuffle(cands)
        cands.sort(key=lambda a: a not in interested)
        cands = cands[: w["lot"] + 3]
        trace["buyer_trace"].append(f"{len(by_acct)} vaults list this kind; {len(low_trust)} below trust {w['min_trust']} skipped; asking {len(cands)}"
                                    + (f", {len(interested & set(cands))} marked interest so they go first." if interested & set(cands) else "."))
        agreed, declined, overlap = [], 0, 0
        for a in cands:
            sa = self.acct(a)
            fs = by_acct[a]
            if sa["sell_agent"].get("mode") == "ask" and a not in interested:
                say(a, "seller", "My owner reviews each sale. I have asked them; count me in once they approve.", "Owner set 'ask me first' and has not marked this posting.", "rules")
                trace["seller_trace"].append({"seller": a, "verdict": "waiting for owner", "price": None})
                self._ask_owner(a, w, len(fs))
                declined += 1
                continue
            # buyer agent: duplicate or overlapping data is refused before any price talk
            fps = set().union(*(json.loads(f["fps"] or "[]") for f in fs))
            ov = len(fps & owned) / max(1, len(fps))
            if ov >= buyer["buy_agent"].get("max_overlap", 0.3):
                say(w["buyer"], "buyer", f"Your lot overlaps {ov:.0%} with records I already own. I won't pay twice for the same data.",
                    f"Fingerprint check: {len(fps & owned)} of {len(fps)} records already in my vault.", "rules")
                trace["seller_trace"].append({"seller": a, "verdict": "refused by buyer: overlap", "price": None, "overlap": round(ov, 2)})
                step("Duplicate check (record fingerprints)", f"{ov:.0%} of this lot's record fingerprints are already in the buyer's DB; limit {buyer['buy_agent'].get('max_overlap', 0.3):.0%}. Refused before price talk.", False, a)
                overlap += 1
                continue
            r = agents.seller_reply(sa["name"], sa["sell_agent"], w, buyer["name"], len(fs))
            say(a, "seller", r["message"], r["thinking"], r["by"])
            final = r["verdict"]
            if r["verdict"] == "counter":
                if r["price"] <= w["max"]:
                    say(w["buyer"], "buyer", f"{r['price']} accepted.", f"Counter {r['price']} is within my max.", "rules"); final = "agree"
                else:
                    say(w["buyer"], "buyer", f"{r['price']} is more than I can pay. Pass.", f"Counter {r['price']} exceeds my max.", "rules"); final = "decline"
            trace["seller_trace"].append({"seller": a, "thinking": r["thinking"], "verdict": final, "price": r["price"], "by": r["by"]})
            trace["verdicts"]["sellers"][a] = final
            if final == "agree":
                agreed.append((a, fs, r["price"]))
            else:
                declined += 1
        # the buyer fills the lot at the lowest prices on offer
        agreed.sort(key=lambda x: x[2])
        if len(agreed) > w["lot"]:
            dropped = agreed[w["lot"]:]
            agreed = agreed[: w["lot"]]
            trace["buyer_trace"].append(f"{len(agreed) + len(dropped)} sellers agreed; I keep the {len(agreed)} cheapest "
                                        f"({agreed[0][2]}–{agreed[-1][2]}) and pass on {len(dropped)} asking up to {dropped[-1][2]}.")
            for a, _, pr in dropped:
                trace["verdicts"]["sellers"][a] = "outbid"

        # buyer agent: verify each seller's attestation and a sampled record against its Merkle root
        verified = []
        for a, fs, price in agreed:
            ok = True
            for f in fs:
                c = json.loads(f["clean"]); att = c.get("_attestation", {})
                recs = intake.leaves(f["kind"], c)
                i = self.rng.randrange(len(recs)) if recs else 0
                sig_ok = bool(att) and intake.verify_attestation(att)
                mk_ok = bool(recs) and sig_ok and merkle_verify(recs[i], merkle_proof(recs, i), att["merkle_root"])
                step("Intake attestation (Ed25519)", f"{f['name']}: schema {att.get('schema', '?')}, {att.get('records', 0)} records, checks: {', '.join(att.get('checks', [])) or 'none'}; signature {'valid' if sig_ok else 'INVALID'} (intake key {str(att.get('pubkey', ''))[:12]}…)", sig_ok, a)
                step("Merkle sample proof (SHA-256)", f"record {i + 1} of {len(recs)} proven against root {str(att.get('merkle_root', ''))[:16]}… with {len(merkle_proof(recs, i)) if recs else 0} sibling hashes", mk_ok, a)
                if not (sig_ok and mk_ok):
                    ok = False
            if ok:
                verified.append((a, fs, price))
        people = len(verified) if personal else len(verified)
        people_eff = sum(json.loads(fs[0]["raw"]).get("_people", 1) for _, fs, _ in verified) if personal else people
        total = round(sum(p for _, _, p in verified), 2)
        bal = self.balance(w["buyer"]) or 0
        need = config.K_MIN if personal else 1
        reason = ""
        if people_eff < need:
            reason = f"only {people_eff} people agreed; a lot of personal data needs at least {config.K_MIN}" if personal else "no seller agreed"
        elif total * config.MICRO_PER_UNIT / 1e6 + (0 if self.rail.token else 0.2 * len(verified)) > bal:
            reason = f"not enough {self.rail.symbol()} for {len(verified)} escrows"
        if personal:
            step(f"k-anonymity (k >= {config.K_MIN})", f"{people_eff} people in the lot", people_eff >= config.K_MIN)
        outcome = {"agreed": len(agreed), "declined": declined, "overlap": overlap, "people": people_eff, "total": total, "ok": not reason, "reason": reason}
        cl = agents.buyer_close(buyer["name"], w, outcome)
        say(w["buyer"], "buyer", cl["message"], cl["thinking"], cl["by"])
        trace["buyer_trace"].append(cl["thinking"])
        trace["verdicts"]["buyer"] = "agree" if not reason else "reject"
        if reason:
            self.s.x("UPDATE contracts SET status='rejected', reason=?, trace=?, sellers=? WHERE id=?", (reason, json.dumps(trace), json.dumps([a for a, *_ in verified]), cid))
            self.s.x("UPDATE postings SET rejected = rejected + 1 WHERE id = ?", (w["id"],))
            self.s.bump("rejected"); self.s.bump("rejected:" + w["kind"])
            return cid
        if buyer["type"] == "person" and total > buyer["buy_agent"].get("auto_limit", 60):
            self.pending_buys[cid] = {"w": w, "verified": verified, "trace": trace, "total": total}
            self.s.x("UPDATE contracts SET status='awaiting buyer', reason=?, trace=?, total=? WHERE id=?", (f"{total} is above the owner's auto-buy limit", json.dumps(trace), total, cid))
            self.chat(w["buyer"], "agent", f"I negotiated {people_eff} sellers for {KINDS[w['kind']]['label'].lower()} at {total} total, above your auto-buy limit. Buy?",
                      [{"t": f"Buy for {total}", "do": "buy", "contract": cid}, {"t": "Skip", "do": "skip_buy", "contract": cid}])
            return cid
        self.settle(cid, w, verified, trace, total)
        return cid

    def _ask_owner(self, aid: str, w: dict, nfiles: int):
        if self.s.one("SELECT id FROM chat WHERE account = ? AND done = 0 AND actions LIKE ?", (aid, f'%"posting": {w["id"]}%')):
            return
        b = self.acct(w["buyer"])
        self.chat(aid, "agent", f"{b['name']} wants {KINDS[w['kind']]['label'].lower()} for {w['purpose']} at {w['offer']} per person. "
                                f"You have {nfiles} listed file(s). Sell them inside a lot of at least {config.K_MIN} people?",
                  [{"t": "OK, include me", "do": "interest", "posting": w["id"]}, {"t": "Not this one", "do": "noop", "posting": w["id"]}])

    def settle(self, cid: int, w: dict, verified: list, trace: dict, total: float):
        buyer_id = w["buyer"]
        self.s.x("UPDATE contracts SET status='settling', total=? WHERE id=?", (total, cid))
        legs, plain = [], {}
        for a, fs, price in verified:
            recs = [json.loads(f["clean"]) for f in fs]
            clear = data.dumps({"contract": cid, "seller": "p_" + data.fp(a, cid)[:10], "records": recs}).encode()
            sealed, K = self.rail.seal(buyer_id, clear)
            trace["protocol"].append({"protocol": "Sealed delivery (AES-256-GCM, key wrapped with X25519 + HKDF-SHA256)", "who": a, "ok": True, "tx": None,
                                      "detail": f"{len(clear)} bytes sealed to the buyer's X25519 key; bundle SHA-256 {hashlib.sha256(clear).hexdigest()[:16]}…; content key K stays with the seller's agent"})
            legs.append({"seller": a, "seller_addr": self.addr[a], "dst_addr": self.acct(a).get("payout") if self.rail.has_line(self.acct(a).get("payout") or "") else None, "drops": int(price * config.MICRO_PER_UNIT), "K": K, "sealed": sealed, "fs": fs, "price": price})
            plain[a] = clear
        res = self.rail.escrow_lot(self.addr[buyer_id], legs, f"vaultmarket/contract/{cid}")
        paid, items, fps, merged = [], 0, set(), []
        for leg, r in zip(legs, res):
            self.s.insert("txs", contract=cid, type="EscrowCreate", hash=r["create"]["hash"], src=buyer_id, dst=leg["seller"], drops=leg["drops"], result=r["create"]["result"])
            if r["finish"]["hash"]:
                self.s.insert("txs", contract=cid, type="EscrowFinish (key released)", hash=r["finish"]["hash"], src=leg["seller"], dst=buyer_id, drops=leg["drops"], result=r["finish"]["result"])
            trace["tx"].append({"seller": leg["seller"], "create": r["create"]["hash"], "finish": r["finish"]["hash"], "ok": r["finish"]["ok"]})
            cond = condition_hex(leg["K"])
            trace["protocol"].append({"protocol": f"XRPL EscrowCreate ({'token escrow, ' if self.rail.token else ''}PREIMAGE-SHA-256 crypto-condition)", "who": leg["seller"], "ok": r["create"]["ok"], "tx": r["create"]["hash"],
                                      "detail": f"buyer locks {leg['drops'] / 1e6:.3f} {self.rail.symbol()}{(' (issuer ' + self.rail.issuer[:8] + '…)') if self.rail.token else ''} to the seller's {'own linked wallet ' + leg['dst_addr'][:8] + '…' if leg.get('dst_addr') else 'agent wallet'} under Condition {cond[:20]}… = SHA-256(K); CancelAfter 1 h; memo vaultmarket/contract/{cid}; {r['create']['result']}"})
            trace["protocol"].append({"protocol": "XRPL EscrowFinish (fulfillment reveals K)", "who": leg["seller"], "ok": r["finish"]["ok"], "tx": r["finish"]["hash"],
                                      "detail": f"seller's agent submits the fulfillment (the preimage K); the ledger checks SHA-256(K) against the condition and pays; {r['finish']['result']}"})
            if not r["finish"]["ok"]:
                continue
            # the buyer reads K from the ledger's EscrowFinish and opens what it already holds
            st = self.rail.led.lookup(r["finish"]["hash"])
            K = bytes.fromhex(st.fulfillment[8:]) if st.fulfillment else leg["K"]
            raw_open = self.rail.open(buyer_id, leg["sealed"], K)
            opened = json.loads(raw_open)
            same = hashlib.sha256(raw_open).digest() == hashlib.sha256(plain[leg["seller"]]).digest()
            trace["protocol"].append({"protocol": "Buyer opens the bundle", "who": leg["seller"], "ok": same, "tx": None,
                                      "detail": f"buyer agent read K from the validated EscrowFinish on the ledger, unwrapped and decrypted {len(opened['records'])} records; bundle SHA-256 {hashlib.sha256(raw_open).hexdigest()[:16]}… {'matches' if same else 'DOES NOT match'} the sealed bundle"})
            merged.extend(opened["records"]); items += len(leg["fs"]); paid.append(leg)
            for f in leg["fs"]:
                self.s.x("UPDATE files SET sold = sold + 1 WHERE id = ?", (f["id"],)); fps.update(json.loads(f["fps"] or "[]"))
        if not paid:
            self.s.x("UPDATE contracts SET status='rejected', reason='ledger did not settle', trace=? WHERE id=?", (json.dumps(trace), cid))
            self.s.bump("rejected"); return
        paid_total = round(sum(l["price"] for l in paid), 2)
        people = sum(json.loads(l["fs"][0]["raw"]).get("_people", 1) for l in paid)
        raw = {"_people": people, "from_contract": cid, "records": merged}
        self.s.insert("files", account=buyer_id, kind=w["kind"], name=f"{w['kind']}_lot_{cid}.json", raw=data.dumps(raw), clean=data.dumps({"records": merged[:3], "_people": people}),
                      status="bought", fps=sorted(fps), source=f"contract {cid}", resale=w.get("resale", 0), bytes=sum(len(c) for c in plain.values()))
        self.s.x("UPDATE contracts SET status='settled', total=?, items=?, sellers=?, trace=? WHERE id=?", (paid_total, items, json.dumps([l["seller"] for l in paid]), json.dumps(trace), cid))
        self.s.x("UPDATE postings SET settled = settled + 1 WHERE id = ?", (w["id"],))
        if w.get("once"):
            self.s.x("UPDATE postings SET status = 'filled' WHERE id = ?", (w["id"],))
        self.s.bump("settled"); self.s.bump("volume", paid_total); self.s.bump("volume:" + w["kind"], paid_total); self.s.bump("settled:" + w["kind"])
        self.s.bump("drops", sum(l["drops"] for l in paid))
        for l in paid:
            self.s.bump(f"earned:{l['seller']}:{w['kind']}", l["price"])
            self.s.insert("prices", kind=w["kind"], price=l["price"], contract=cid)
            if self.acct(l["seller"])["type"] == "person" and self.acct(l["seller"])["sell_agent"].get("mode") == "ask":
                self.chat(l["seller"], "agent", f"Sold to {self.acct(buyer_id)['name']} in a lot of {people} people: +{l['drops'] / 1e6:.2f} {self.rail.symbol()} on the ledger. Contract #{cid}.")
        for a in {l["seller"] for l in paid}:
            self._bal.pop(a, None)
        self._bal.pop(buyer_id, None)

    # ---------------- resale ----------------
    def resell(self):
        """The broker combines lots it bought (with resale rights) into one bigger bundle and lists it."""
        for kind in ("gps_track", "sleep_log"):
            lots = self.s.q("SELECT * FROM files WHERE account = ? AND kind = ? AND status = 'bought' AND resale = 1", (BROKER, kind))
            if len(lots) < 2:
                continue
            recs, fps, people = [], set(), 0
            for l in lots:
                r = json.loads(l["raw"]); recs.extend(r["records"]); fps.update(json.loads(l["fps"])); people += r.get("_people", 1)
            body = {"_people": people, "bundle_of": [l["id"] for l in lots], "records": recs}
            clean = {"records": recs, "_people": people}
            a = intake.attest(kind, clean, ["bundle of attested lots"], False)
            clean["_attestation"] = a
            self.s.insert("files", account=BROKER, kind=kind, name=f"{kind}_bundle_{people}people.json", raw=data.dumps(body), clean=data.dumps(clean),
                          status="listed", fps=sorted(fps), source="bundle", derived_from=json.dumps([l["id"] for l in lots]), bytes=len(data.dumps(clean)))
            for l in lots:
                self.s.x("UPDATE files SET status = 'bundled' WHERE id = ?", (l["id"],))

    # ---------------- recommendations (ontology scan) ----------------
    def scan(self, aid: str):
        """The ontology scan: private files whose kind has open demand get a recommendation to list them."""
        a = self.acct(aid)
        for p in self.s.q("SELECT kind, COUNT(*) n FROM files WHERE account = ? AND status = 'private' GROUP BY kind", (aid,)):
            demand = [{"buyer": self.acct(w["buyer"])["name"], "offer": w["offer"], "purpose": w["purpose"]}
                      for w in self.s.q("SELECT * FROM postings WHERE kind = ? AND status = 'open' AND buyer != ?", (p["kind"], aid))
                      if w["purpose"] not in a["sell_agent"].get("blocks", [])]
            if demand and not self.s.one("SELECT id FROM recs WHERE account = ? AND kind = ? AND status = 'open'", (aid, p["kind"])):
                self.s.insert("recs", account=aid, kind=p["kind"], text=agents.recommend(a["name"], p["kind"], p["n"], demand), status="open")

    # ---------------- the loop ----------------
    def tick(self):
        rng = self.rng
        # people come and go
        for a in rng.sample(self.s.q("SELECT id FROM accounts WHERE type = 'person' AND id NOT LIKE 'u-%'"), 3):
            self.s.x("UPDATE accounts SET online = 1 - online WHERE id = ? AND id != 'dana'", (a["id"],))
        # someone uploads something new; their agent runs it through intake
        if rng.random() < 0.7:
            a = rng.choice(self.s.q("SELECT id, name FROM accounts WHERE type = 'person' AND id != 'dana' AND id NOT LIKE 'u-%'"))
            kind = rng.choice(["gps_track", "gps_track", "sleep_log", "purchase_receipts", "audio"])
            body = data.make_record(kind, rng, a["name"], rng.randint(5, 60), (40.7 + rng.random() * 0.1, -73.95 - rng.random() * 0.05))
            roll = rng.random()
            if roll < 0.08:
                body["diagnosis"] = "sleep apnea, moderate"
            elif roll < 0.3 and kind == "sleep_log":
                body["nights"].append(dict(body["nights"][0]))
            elif roll < 0.3 and kind == "gps_track":
                body["points"][5]["hr"] = 255
            self.upload(a["id"], data.file_name(kind, body, 0), body, auto=True)
        # demand keeps coming: an agent posts a new request, for the kind of data with the least demand
        if rng.random() < 0.35:
            self.new_request(rng)
        self.s.x("UPDATE postings SET status = 'expired' WHERE status = 'open' AND once = 1 AND created < ?", (time.time() - 1800,))
        # one negotiation: postings someone marked interest in first, then the rest
        open_ = self.s.q("SELECT p.*, (SELECT COUNT(*) FROM interests i WHERE i.posting = p.id) AS hot FROM postings p WHERE status = 'open' ORDER BY hot DESC, RANDOM()")
        if open_:
            w = open_[0] if open_[0]["hot"] and rng.random() < 0.6 else rng.choice(open_)
            self.negotiate(w)
        if rng.random() < 0.2:
            self.resell()
        if rng.random() < 0.3:
            for a in ["dana"] + [r["id"] for r in self.s.q("SELECT id FROM accounts WHERE id LIKE 'u-%'")]:
                self.scan(a)
        self.events += 1

    PURPOSES = {"gps_track": ["running-route app", "city heat-map research", "shoe wear study", "bike-lane planning"],
                "sleep_log": ["sleep research", "mattress product study", "wearable calibration", "insurance pricing"],
                "purchase_receipts": ["basket research", "price index", "store layout study"],
                "audio": ["speech model training", "accent research", "voice assistant tuning"],
                "air": ["pollution alerts", "school air study", "asthma research"]}

    def new_request(self, rng) -> int:
        """A buyer agent posts a request on its own: someone in the market (company or person) wants the
        kind of data that has the least open demand right now, at a price near the going rate."""
        open_by = {k: self.s.one("SELECT COUNT(*) n FROM postings WHERE kind = ? AND status = 'open'", (k,))["n"] for k in KINDS}
        kind = min(open_by, key=lambda k: (open_by[k], rng.random()))
        buyer = rng.choice([a for a in self.s.q("SELECT id, type FROM accounts WHERE id NOT LIKE 'u-%'") if a["id"] in self.addr] or [{"id": "atlas-maps", "type": "org"}])
        base = KINDS[kind]["price"] * rng.uniform(0.85, 1.3)
        offer = round(base, 1)
        pid = self.s.insert("postings", buyer=buyer["id"], kind=kind, offer=offer, max=round(offer * rng.uniform(1.15, 1.4), 1), purpose=rng.choice(self.PURPOSES[kind]),
                            lot=rng.choice([5, 6, 8]) if KINDS[kind]["personal"] else 2, min_trust=0.7, resale=0, status="open", once=1)
        self.events += 1
        return pid

    def run_forever(self):
        # trade as soon as a handful of wallets are funded; the rest join as their faucet calls finish
        while sum(1 for a in self.addr if not a.startswith("u-")) < min(8, len(self.s.q("SELECT id FROM accounts"))):
            time.sleep(1)
        while self.rail.asset == "USD" and self.rail.name != "mock" and not getattr(self, "asset_ready", False):
            time.sleep(1)      # test USD trust lines are being set up
        while True:
            t = time.time()
            try:
                with self.lock:
                    self.tick()
            except Exception:
                traceback.print_exc()
            time.sleep(max(1.0, config.TICK_SECONDS - (time.time() - t)))
