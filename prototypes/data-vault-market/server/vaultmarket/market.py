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
from agentrail import ap4m_rail  # noqa: E402  (repo root is on sys.path via .rail)
from .store import Store

PEOPLE = ["Dana Park", "Minho Lee", "Sora Kim", "Jae Choi", "Lina Haddad", "Omar Farouk", "Priya Nair", "Ken Watanabe", "Ana Souza", "Tomas Novak",
          "Yuki Sato", "Bilal Khan", "Mei Lin", "Chris Doyle", "Nadia Petrova", "Leo Rossi", "Hana Jung", "Ravi Iyer", "Sofia Marin", "Ivan Horvat",
          "Zoe Carter", "Kofi Mensah", "Elif Demir", "Mateo Ruiz", "Aisha Bello", "Noah Fischer", "Jin Park", "Lucia Gomez", "Sam Taylor", "Amara Obi",
          "Theo Martin", "Rin Takahashi", "Diego Alvarez", "Maya Cohen", "Ola Nordmann", "Ethan Brooks", "Seo-yeon Han", "Farah Aziz", "Jonas Berg", "Bo Zhang",
          "Tara Singh", "Wen Chen"]
# more market personas, added to a running vault by VM_EXTRA_PEOPLE (seed() tops up; existing vaults are kept)
EXTRA_PEOPLE = ["Ines Duarte", "Kwame Asante", "Hye-jin Yoon", "Marco Bianchi", "Leila Rahimi", "Arjun Mehta", "Clara Weber", "Tunde Bakare",
                "Saki Mori", "Pablo Ortega", "Greta Lund", "Yusuf Kaya", "Nina Kowalski", "Dae-ho Kang", "Lea Dubois", "Kai Nakamura",
                "Rosa Silva", "Emre Aydin", "Ivy Tran", "Felix Huber", "Zara Malik", "Joon Seo", "Alma Torres", "Viktor Lindqvist",
                "Chloe Nguyen", "Hamza Idris", "Mina Choi", "Oskar Nilsson", "Freya Holm", "Rami Saleh", "Lily Evans", "Ji-ho Shin",
                "Paula Mendes", "Sven Aalto", "Nour Haddad", "Ryo Fujita", "Esme Clarke", "Adil Rahman", "Yara Costa", "Hugo Laurent"]
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
        self.events = 0
        self.lock = threading.Lock()
        self.wake = threading.Event()   # set when someone asks their agent to sell, so it runs now, not on the next tick
        if not self.s.stat("record_fingerprints_v2"):
            with self.s.transaction():
                for f in self.s.q("SELECT id,kind,raw,clean,fps FROM files"):
                    raw=json.loads(f["raw"] or "{}");clean=json.loads(f["clean"] or "{}")
                    payload=raw if "records" in raw else clean
                    fps=set(json.loads(f["fps"] or "[]")) | self.record_fps(f["kind"],payload)
                    self.s.x("UPDATE files SET fps=? WHERE id=?",(json.dumps(sorted(fps)),f["id"]))
                self.s.bump("record_fingerprints_v2")

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
                    self.s.insert("postings", buyer=o["id"], kind=k, offer=offer, max=mx, purpose=purpose, lot=1, min_trust=0.7, resale=resale, status="open", once=0)
                if o.get("sells") == "air":
                    for j in range(8):
                        body = data.make_record("air", rng, o["name"], j, (0, 0))
                        self.add_file(o["id"], "air", data.file_name("air", body, j), body, listed=True, source="kite-sensor-net")
        if not self.s.one("SELECT id FROM accounts WHERE id='demo-vault'"):
            self.s.insert("accounts",id="demo-vault",name="Demo vault",type="person",trust=.9,verified=0,
                          sell_agent={"mode":"auto","min":{k:v["price"] for k,v in KINDS.items()},"blocks":["insurance pricing"]},
                          buy_agent={"auto_limit":10,"min_trust":.7,"max_overlap":0})
            demo_rng=random.Random(101)
            for k in ("gps_track","sleep_log","purchase_receipts"):
                body=data.make_record(k,demo_rng,"Synthetic demo",0,(40.7,-74))
                self.add_file("demo-vault",k,data.file_name(k,body,0),body,listed=False,source="synthetic demo")
        if not self.s.stat("kinds_v2"):
            # newer everyday data kinds: give every vault a minimum for them and some records to sell
            rng2 = random.Random(303)
            for acc in self.s.q("SELECT id, name, type FROM accounts"):
                a = self.acct(acc["id"]); rules = a["sell_agent"]; mins = rules.setdefault("min", {})
                for k in data.NEW_KINDS:
                    mins.setdefault(k, round(KINDS[k]["price"] * (rng2.uniform(0.6, 1.25) if acc["type"] == "person" else 1.2), 1))
                self.s.x("UPDATE accounts SET sell_agent=? WHERE id=?", (json.dumps(rules), acc["id"]))
                if acc["type"] != "person" or acc["id"].startswith("u-"):
                    continue
                home = (round(40.66 + rng2.random() * 0.14, 5), round(-74.01 + rng2.random() * 0.1, 5))
                demo = acc["id"] == "demo-vault"
                for k in (list(KINDS) if demo else data.NEW_KINDS):
                    for j in range(6 if demo else rng2.randint(1, 3)):
                        body = data.make_record(k, rng2, acc["name"], j, home)
                        self.add_file(acc["id"], k, data.file_name(k, body, j), body, listed=acc["id"] == "demo-vault" or rng2.random() < 0.7, source="phone")
            self.s.bump("kinds_v2")
        if not self.s.stat("ap4m_tx_src_v1"):   # AP4M rows written before this used src = buyer; EscrowFinish rows use src = the seller paid
            self.s.x("UPDATE txs SET src = dst, dst = src WHERE type = 'AP4M VoucherRedeemed' AND src = (SELECT buyer FROM contracts WHERE contracts.id = txs.contract)")
            self.s.bump("ap4m_tx_src_v1")
        rng3 = random.Random(404)
        for name in EXTRA_PEOPLE[: max(0, config.EXTRA_PEOPLE)]:
            aid = name.split()[0].lower().replace("-", "")
            if not self.s.one("SELECT id FROM accounts WHERE id = ?", (aid,)):
                self._add_persona(aid, name, rng3)
        if not self.s.stat("demo_vault_auto_v1") and self.s.one("SELECT id FROM accounts WHERE id='demo-vault'"):
            # The demo vault's agent sells on its own within its minimums, like the market personas, with enough records to trade.
            rules=self.acct("demo-vault")["sell_agent"];rules["mode"]="auto"
            self.s.x("UPDATE accounts SET sell_agent=? WHERE id='demo-vault'",(json.dumps(rules),))
            self.s.x("UPDATE files SET status='listed' WHERE account='demo-vault' AND status='private'")
            demo_rng=random.Random(202)
            for k in ("gps_track","sleep_log","purchase_receipts"):
                for j in range(1,6):
                    body=data.make_record(k,demo_rng,"Synthetic demo",j,(40.7,-74))
                    self.add_file("demo-vault",k,data.file_name(k,body,j),body,listed=True,source="synthetic demo")
            self.chat("demo-vault","agent","I now sell automatically within your minimum prices and allowed purposes. Change this under Settings.")
            self.s.bump("demo_vault_auto_v1")
        legacy=self.s.q("SELECT DISTINCT account FROM chat WHERE done=0 AND actions IS NOT NULL AND text LIKE '%lot of at least % people%'")
        self.s.x("UPDATE chat SET done=1 WHERE done=0 AND actions IS NOT NULL AND text LIKE '%lot of at least % people%'")
        for a in legacy:
            self.chat(a["account"],"agent","The marketplace now settles one-to-one. Old group requests are archived. Ask what you can sell to review a fresh request.")
        # a negotiation a previous run left mid-flight has no money in it: close it. A contract left
        # 'settling' may have escrows on the ledger; recover() finishes or refunds them once wallets connect.
        self.s.x("UPDATE contracts SET status = 'rejected', reason = 'interrupted by a server restart' WHERE status = 'negotiating'")
        self.s.x("UPDATE contracts SET status = 'rejected', reason = 'interrupted by a server restart before any escrow' "
                 "WHERE status = 'settling' AND id NOT IN (SELECT contract FROM escrows) "
                 "AND id NOT IN (SELECT contract FROM txs WHERE type = 'EscrowCreate')")
        self.s.x("UPDATE sale_queue SET status=(SELECT status FROM contracts WHERE id=sale_queue.contract) WHERE contract IN (SELECT id FROM contracts WHERE status IN ('settled','rejected','recovery review'))")
        self.s.x("UPDATE sale_queue SET status='queued',contract=NULL,reason='Resuming your instruction after restart',updated=0 WHERE contract IN (SELECT id FROM contracts WHERE status='rejected' AND reason LIKE 'interrupted by a server restart%')")
        self.s.x("UPDATE contracts SET status='rejected',reason='This old pending purchase had no saved terms; request a new negotiation' WHERE status='awaiting buyer' AND terms IS NULL")
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

    def _add_persona(self, aid: str, name: str, rng: random.Random):
        """One simulated member whose agent sells on its own within its minimums, with records of every kind."""
        mins = {k: round(KINDS[k]["price"] * rng.uniform(0.6, 1.25), 1) for k in KINDS}
        blocks = (["insurance pricing"] if rng.random() < 0.55 else []) + (["speech model training"] if rng.random() < 0.2 else [])
        self.s.insert("accounts", id=aid, name=name, type="person", trust=round(rng.uniform(0.72, 0.97), 2), verified=0,
                      sell_agent={"mode": "auto", "min": mins, "blocks": blocks}, buy_agent={"auto_limit": 60, "min_trust": 0.7, "max_overlap": 0.3})
        home = (round(40.66 + rng.random() * 0.14, 5), round(-74.01 + rng.random() * 0.1, 5))
        counts = {"gps_track": rng.randint(1, 6), "sleep_log": rng.randint(0, 3), "purchase_receipts": rng.randint(0, 2), "audio": rng.randint(0, 1),
                  **{k: rng.randint(1, 3) for k in data.NEW_KINDS}}
        for k, c in counts.items():
            for j in range(c):
                body = data.make_record(k, rng, name, j, home)
                self.add_file(aid, k, data.file_name(k, body, j), body, listed=rng.random() < 0.7, source=body.get("device_serial", "phone"))

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
                    while not getattr(self, "asset_ready", False):
                        time.sleep(1)
                    if self.rail.token:
                        with self.lock:
                            self.rail.ensure_token_holder(addr)
                    self.addr[aid] = addr
                    self.s.x("UPDATE accounts SET address = ? WHERE id = ?", (addr, aid))
                    self.chat(aid, "agent", f"Welcome. Your agent's wallet on the ledger is {addr}. Upload data in My DB; I ask you before every sale.")
                    return
                except Exception:
                    time.sleep(3 * (attempt + 1))
        threading.Thread(target=connect, daemon=True).start()

    # ---------------- files ----------------
    @staticmethod
    def record_fps(kind: str, body: dict) -> set[str]:
        if "records" in body:
            return set().union(*(Market.record_fps(kind,row) for row in body["records"]))
        return {hashlib.sha256(leaf.encode()).hexdigest() for leaf in intake.leaves(kind,body)}

    def add_file(self, account: str, kind: str, name: str, body: dict, listed: bool, source: str, cleaned=False, checks=None) -> int:
        clean = data.pseudonymize(kind, body)
        att = intake.attest(kind, clean, checks or ["schema", "value ranges", "duplicates", "identifiers removed"], cleaned)
        clean["_attestation"] = att
        return self.s.insert("files", account=account, kind=kind, name=name, raw=data.dumps(body), clean=data.dumps(clean),
                             status="listed" if listed else "private", fps=sorted(self.record_fps(kind,clean)), source=source, bytes=len(data.dumps(clean)))

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
        fee_drops = round(sc["fee"] * config.MICRO_PER_UNIT)
        tx = self._fee(account, fee_drops, f"cleaning {name}")
        fid = self.add_file(account, sc["kind"], name, intake.clean(sc["kind"], body), listed=listed, source=body.get("device_serial", "upload"),
                            cleaned=True, checks=["schema", "value ranges", "duplicates", "identifiers removed"] + sc["issues"])
        self.s.x("UPDATE uploads SET file = ?, verdict = 'cleaned', fee_tx = ?, fee_micro = ? WHERE id = ?", (fid, tx, fee_drops, uid))
        self.s.bump("cleaned"); self.s.bump("fees", sc["fee"])
        return {"upload": uid, "file": fid, "verdict": "cleaned", "fee": sc["fee"], "tx": tx}

    def _fee(self, account: str, drops: int, memo: str) -> str | None:
        if config.AP4M and 0 < drops <= ap4m_rail.PER_PAYMENT_CAP_MICRO:
            r = ap4m_rail.pay(f"vm-fee-{account}-{int(time.time() * 1000)}", drops, pool="vault", memo={"account": account, "fee": memo})
            if r.get("ok"):
                self.s.insert("txs", contract=None, type="AP4M VoucherRedeemed (cleaning fee)", hash=r["voucher_redeemed_tx"], src=account, dst="platform",
                              drops=drops, result="verified" if r.get("verified") else "redeemed", asset="RLUSD (AP4M)")
                return r["voucher_redeemed_tx"]
            return None
        src, dst = self.addr.get(account), getattr(self, "platform", None)
        if not (src and dst):
            return None
        try:
            r = self.rail.pay(src, dst, drops, memo)
            self.s.insert("txs", contract=None, type="Payment (cleaning fee)", hash=r["hash"], src=account, dst="platform", drops=drops, result=r["result"], asset=self.rail.symbol())
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

    def describe_files(self, files: list[dict]) -> dict:
        fields, dates, count = set(), set(), 0
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.startswith("_") or key in data.DIRECT:
                        continue
                    fields.add(key)
                    if key in ("date", "night", "t") and isinstance(item, str) and len(item)>=10:
                        dates.add(item[:10])
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        for f in files:
            clean=json.loads(f["clean"])
            count+=len(self.record_fps(f["kind"],clean))
            walk(clean)
        return {"files":len(files),"records":count,"fields":sorted(fields),"start":min(dates) if dates else None,"end":max(dates) if dates else None}

    # ---------------- negotiation ----------------
    def enqueue_sale(self, aid: str, kind: str, posting: int | None = None) -> dict:
        with self.s.transaction():
            old = self.s.one("SELECT * FROM sale_queue WHERE account=? AND kind=? AND (? IS NULL OR posting IS ?) AND status IN ('queued','waiting','negotiating','settling','awaiting buyer')", (aid, kind, posting, posting))
            if old:
                return old
            qid = self.s.insert("sale_queue", account=aid, kind=kind, posting=posting, status="queued", reason="Waiting for your agent", updated=0)
            a = self.acct(aid)
            w = self.s.one("SELECT * FROM postings WHERE id=? AND status='open'", (posting,)) if posting else None
            count = self.s.one("SELECT count(*) n FROM files WHERE account=? AND kind=? AND status IN ('private','listed')", (aid, kind))["n"]
            reason = ""
            if not count:
                reason = "Upload this data in My DB before selling."
            elif w and w["purpose"] in a["sell_agent"].get("blocks", []):
                reason = "Your rules block this purpose."
            elif w and w["max"] < a["sell_agent"].get("min", {}).get(kind, 0):
                reason = "The buyer's budget is below your minimum."
            if reason:
                self.s.x("UPDATE sale_queue SET status='blocked',reason=? WHERE id=?", (reason, qid))
            else:
                self.s.x("UPDATE files SET status='listed' WHERE account=? AND kind=? AND status='private'", (aid, kind))
                if posting:
                    self.s.x("INSERT OR IGNORE INTO interests(account,posting,created) VALUES(?,?,?)", (aid, posting, time.time()))
            self.chat(aid, "agent", reason or f"Sale request #{qid} received. My agent is starting the negotiation now.")
        self.events += 1
        if not reason:
            self.wake.set()
        return self.s.one("SELECT * FROM sale_queue WHERE id=?", (qid,))

    def expire_sale_queue(self):
        """A sale instruction that found no buyer for 20 minutes is closed with that reason, so the list shows only live work."""
        self.s.x("UPDATE sale_queue SET status='rejected',reason='No buyer matched your terms within 20 minutes. Ask again any time, or lower your minimum.',updated=? "
                 "WHERE status='waiting' AND created<?", (time.time(), time.time() - 1200))

    def process_sale_queue(self) -> bool:
        # newest instruction first: on the shared demo vault a visitor's click shouldn't wait behind everyone else's
        q = self.s.one("SELECT * FROM sale_queue WHERE status IN ('queued','waiting') AND updated<? ORDER BY (status='queued') DESC, id DESC LIMIT 1", (time.time()-15,))
        if not q:
            return False
        a = self.acct(q["account"])
        if q["account"] not in self.addr:
            reason = "Your wallet is connecting; the request is saved."
        else:
            requests = self.s.q("SELECT * FROM postings WHERE status='open' AND kind=? AND buyer!=? ORDER BY max DESC", (q["kind"], q["account"]))
            own_fps=self.owned_fps(q["account"],q["kind"])
            requests=[w for w in requests if not (q["account"]=="demo-vault" and w["buyer"].startswith("u-")) and len(own_fps & self.owned_fps(w["buyer"],q["kind"])) == 0]
            w = next((w for w in requests if (q["posting"] is None or w["id"]==q["posting"]) and w["purpose"] not in a["sell_agent"].get("blocks", []) and w["max"]>=a["sell_agent"]["min"].get(q["kind"],0)), None)
            if w:
                self.s.x("INSERT OR IGNORE INTO interests(account,posting,created) VALUES(?,?,?)", (q["account"],w["id"],time.time()))
                cid = self.negotiate(w, seller_id=q["account"], queue_id=q["id"])
                c = self.s.one("SELECT status,reason,sellers FROM contracts WHERE id=?", (cid,)) if cid else None
                status = c["status"] if c else "waiting"
                reason = c["reason"] if c else "The buyer or wallet is not ready yet."
                self.s.x("UPDATE sale_queue SET status=?,reason=?,updated=? WHERE id=?", (status,reason,time.time(),q["id"]))
                self.events += 1
                return True
            reason = "Waiting for a buyer whose budget and purpose match your terms."
        self.s.x("UPDATE sale_queue SET status='waiting',reason=?,updated=? WHERE id=?", (reason,time.time(),q["id"]))
        return False

    def negotiate(self, w: dict, seller_id: str | None = None, queue_id: int | None = None) -> int | None:
        w = {**w, "lot": 1}  # Each contract is one buyer and one seller.

        # the LLM writes the buyer's opening, the first seller's answer and the buyer's decision when
        # three slots are free under the cap; otherwise the whole round runs on written rules
        llm.budget(3 if llm.free_slots() >= 3 else 0)
        try:
            return self._negotiate(w, seller_id, queue_id)
        finally:
            llm.budget(None)

    def quote(self, kind: str) -> dict:
        """The market price, formed by the agents themselves: the median of recent clearing prices on the
        shared ledger, nudged by supply (vaults listing it) against demand (people wanted in open requests)."""
        rows = [r["price"] for r in self.s.q("SELECT p.price FROM prices p JOIN contracts c ON c.id=p.contract WHERE p.kind=? AND c.asset=? AND c.unit_micro=? ORDER BY p.id DESC LIMIT 30", (kind,self.rail.symbol(),config.MICRO_PER_UNIT))]
        base = statistics.median(rows) if rows else KINDS[kind]["price"]
        supply = self.s.one("SELECT COUNT(DISTINCT account) n FROM files WHERE kind = ? AND status = 'listed'", (kind,))["n"]
        demand = self.s.one("SELECT COALESCE(SUM(lot), 0) n FROM postings WHERE kind = ? AND status = 'open'", (kind,))["n"]
        pressure = demand / max(1, supply)
        price = base * min(1.25, max(0.8, 1 + 0.12 * math.log(max(pressure, 0.05))))
        return {"price": round(price, 1), "median": round(base, 1), "n": len(rows), "lo": round(min(rows), 1) if rows else None,
                "hi": round(max(rows), 1) if rows else None, "supply": supply, "demand": demand, "pressure": round(pressure, 2)}

    def _negotiate(self, w: dict, seller_id=None, queue_id=None) -> int | None:
        buyer = self.acct(w["buyer"])
        if not buyer or w["buyer"] not in self.addr:
            return None
        personal = KINDS[w["kind"]]["personal"]
        owned = self.owned_fps(w["buyer"], w["kind"])
        # price discovery: the buyer opens under the market price, never above its owner's budget
        q = self.quote(w["kind"])
        if config.AP4M:   # one AP4M payment per seller, never above 0.10 RLUSD: the buyer's budget per seller is capped there
            cap_units = math.floor(ap4m_rail.PER_PAYMENT_CAP_MICRO / config.MICRO_PER_UNIT * 10) / 10
            w = {**w, "max": min(w["max"], cap_units), "offer": min(w["offer"], cap_units)}
        opening = round(min(w["max"], max(0.5, q["price"] * 0.92)), 1)
        w = {**w, "offer": opening, "quote": q}
        cid = self.s.insert("contracts", posting=w["id"], buyer=w["buyer"], kind=w["kind"], seller=seller_id, status="negotiating", reason="Buyer agent is preparing an offer", asset=self.rail.symbol(), unit_micro=config.MICRO_PER_UNIT)
        self.events += 1
        if queue_id:
            self.s.x("UPDATE sale_queue SET status='negotiating',contract=?,updated=? WHERE id=?", (cid,time.time(),queue_id))
        def say(who, side, text, thinking="", by=""):
            self.s.insert("messages", contract=cid, speaker=who, side=side, text=text, thinking=json.dumps({"t": thinking, "by": by}))
            self.events += 1
        op = agents.buyer_open(buyer["name"], w, len(owned))
        say(w["buyer"], "buyer", op["message"], op["thinking"], op["by"])
        trace = {"asset": self.rail.symbol(), "unit_micro": config.MICRO_PER_UNIT, "buyer_trace": [op["thinking"]], "seller_trace": [], "verdicts": {"sellers": {}}, "tx": [], "protocol": [], "model": llm.model_name()}
        def step(protocol, detail, ok=True, who=None, tx=None):
            trace["protocol"].append({"protocol": protocol, "detail": detail, "ok": ok, "who": who, "tx": tx})
        step("Price discovery (shared ledger)", f"market price {q['price']}: median {q['median']} of the last {q['n']} clearing prices"
             + (f" (range {q['lo']}–{q['hi']})" if q["n"] else " (no trades yet: list price)")
             + f", supply {q['supply']} vaults vs demand {q['demand']} people wanted (pressure {q['pressure']}). Buyer opens at {opening}, budget {w['max']}.")

        files = self.s.q("SELECT f.*, a.trust FROM files f JOIN accounts a ON a.id = f.account WHERE f.kind = ? AND f.status = 'listed' AND f.account != ?", (w["kind"], w["buyer"]))
        by_acct: dict[str, list] = {}
        skipped_owned = 0
        for f in files:
            if (w["buyer"]=="demo-vault" and f["account"].startswith("u-")) or (w["buyer"].startswith("u-") and f["account"]=="demo-vault"):
                continue  # The public demo never trades a real member's records.
            if f["account"] not in self.addr:      # wallet not funded yet: not in the market this round
                continue
            if not seller_id and owned and owned & set(json.loads(f["fps"] or "[]")):
                skipped_owned += 1                 # the buyer agent only asks for records it does not own yet
                continue
            by_acct.setdefault(f["account"], []).append(f)
        interested = {r["account"] for r in self.s.q("SELECT account FROM interests WHERE posting = ?", (w["id"],))}
        low_trust = [a for a, fs in by_acct.items() if fs[0]["trust"] < w["min_trust"]]
        cands = [a for a in by_acct if a not in low_trust and w["purpose"] not in self.acct(a)["sell_agent"].get("blocks", [])]
        self.rng.shuffle(cands)
        cands.sort(key=lambda a: a not in interested)
        if "demo-vault" in cands and self.rng.random() < 0.5:
            cands.remove("demo-vault");cands.insert(0,"demo-vault")  # the demo vault trades often so its history fills in
        cands = [seller_id] if seller_id in cands else [] if seller_id else cands[:1]
        trace["buyer_trace"].append(f"{len(by_acct)} vaults list this kind; {len(low_trust)} below trust {w['min_trust']} skipped; "
                                    + (f"{skipped_owned} listed files left out because the buyer already owns those records; " if skipped_owned else "")
                                    + f"asking {len(cands)}"
                                    + (f", {len(interested & set(cands))} marked interest so they go first." if interested & set(cands) else "."))
        if cands:
            self.s.x("UPDATE contracts SET seller=?,overview=? WHERE id=?", (cands[0],json.dumps(self.describe_files(by_acct[cands[0]])),cid))
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
            if ov > 0:
                say(w["buyer"], "buyer", f"Your lot overlaps {ov:.0%} with records I already own. I won't pay twice for the same data.",
                    f"Fingerprint check: {len(fps & owned)} of {len(fps)} records already in my vault.", "rules")
                trace["seller_trace"].append({"seller": a, "verdict": "refused by buyer: overlap", "price": None, "overlap": round(ov, 2)})
                step("Duplicate check (record fingerprints)", f"{ov:.0%} of this lot's record fingerprints are already in the buyer's DB; any overlap is refused. Refused before price talk.", False, a)
                overlap += 1
                continue
            # both agents check that what the buyer needs is what the seller holds, before any price talk
            need = agents.requirements(w)
            recs = [json.loads(x) for f in fs for x in intake.leaves(f["kind"], json.loads(f["clean"]))]
            present = set().union(*(r.keys() for r in recs if isinstance(r, dict))) if recs else set()
            if w["kind"] == "gps_track":
                present |= {k for r in recs for p in (r.get("points") or [])[:1] for k in p}
            missing = [x for x in need["fields"] if x not in present]
            fit = min(1.0, len(recs) / need["min_records"]) * (1 - 0.5 * len(missing) / max(1, len(need["fields"])))
            fit = round(fit if fit >= 0.2 else 0, 2)
            mt = agents.match_terms(buyer["name"], sa["name"], w, need, {"records": len(recs), "missing": missing, "fit": fit})
            say(w["buyer"], "buyer", mt["buyer"], f"Conditions for {w['purpose']}: at least {need['min_records']} {need['unit']}, fields {', '.join(need['fields'])}.", mt["by"])
            say(a, "seller", mt["seller"], f"I hold {len(recs)} {need['unit']}; missing {', '.join(missing) or 'nothing'}; fit {fit:.0%}.", mt["by"])
            step("Requirements match", f"buyer needs ≥{need['min_records']} {need['unit']} with {', '.join(need['fields'])}; seller has {len(recs)}"
                 + (f", missing {', '.join(missing)}" if missing else "") + f" → fit {fit:.0%}" + ("" if fit >= 1 else ", priced as a partial bundle" if fit else ", no trade"), fit > 0, a)
            if not fit:
                trace["seller_trace"].append({"seller": a, "verdict": "conditions not met", "price": None, "fit": fit})
                trace["verdicts"]["sellers"][a] = "conditions not met"
                declined += 1
                continue
            value = 0.5 + 0.5 * fit   # a partial bundle is still worth something to the buyer, just less
            w_fit = {**w, "max": round(w["max"] * value, 1), "offer": round(min(w["offer"], w["max"] * value * 0.92), 1)} if fit < 1 else w
            self.s.x("UPDATE contracts SET reason='Seller agent is reviewing the offer' WHERE id=?",(cid,));self.events += 1
            r = agents.seller_reply(sa["name"], sa["sell_agent"], w_fit, buyer["name"], len(fs))
            say(a, "seller", r["message"], r["thinking"], r["by"])
            final = r["verdict"]
            if r["verdict"] == "counter":
                if r["price"] <= w_fit["max"]:
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
        need = 1
        reason = ""
        if people_eff < need:
            reason = "The buyer already owns some of these records; no repeat payment." if overlap else "The seller did not accept within the buyer budget and owner terms."
        elif total * config.MICRO_PER_UNIT / 1e6 + (0 if self.rail.token else 0.2 * len(verified)) > bal:
            reason = f"not enough {self.rail.label()} for {len(verified)} escrows"
        if personal:
            step("One-to-one agreement", "One buyer negotiates with one seller for this record bundle.", len(verified) == 1)
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
            terms={"w":w,"verified":[{"seller":a,"files":[f["id"] for f in fs],"price":pr} for a,fs,pr in verified],"trace":trace,"total":total}
            self.s.x("UPDATE contracts SET terms=? WHERE id=?",(json.dumps(terms),cid))
            self.s.x("UPDATE contracts SET status='awaiting buyer', reason=?, trace=?, total=? WHERE id=?", (f"{total} is above the owner's auto-buy limit", json.dumps(trace), total, cid))
            self.chat(w["buyer"], "agent", f"I negotiated {people_eff} sellers for {KINDS[w['kind']]['label'].lower()} at {total} total, above your auto-buy limit. Buy?",
                      [{"t": f"Buy for {total}", "do": "buy", "contract": cid}, {"t": "Skip", "do": "skip_buy", "contract": cid}])
            return cid
        self.settle(cid, w, verified, trace, total)
        return cid

    def approve_buy(self, cid: int) -> bool:
        c=self.s.one("SELECT * FROM contracts WHERE id=? AND status='awaiting buyer'",(cid,))
        if not c or not c.get("terms"):
            return False
        p=json.loads(c["terms"]);verified=[]
        for leg in p["verified"]:
            fs=[self.s.one("SELECT * FROM files WHERE id=? AND account=? AND status='listed'",(fid,leg["seller"])) for fid in leg["files"]]
            if not all(fs):
                self.s.x("UPDATE contracts SET status='rejected',reason='The seller withdrew a file before buyer approval' WHERE id=?",(cid,))
                return False
            if any(set(json.loads(f["fps"])) & self.owned_fps(c["buyer"],c["kind"]) for f in fs):
                self.s.x("UPDATE contracts SET status='rejected',reason='The buyer already owns these records; no repeat payment' WHERE id=?",(cid,))
                return False
            verified.append((leg["seller"],fs,leg["price"]))
        self.settle(cid,p["w"],verified,p["trace"],p["total"])
        return True

    def _ask_owner(self, aid: str, w: dict, nfiles: int):
        if self.s.one("SELECT id FROM chat WHERE account = ? AND done = 0 AND actions LIKE ?", (aid, f'%"posting": {w["id"]}%')):
            return
        b = self.acct(w["buyer"])
        self.chat(aid, "agent", f"{b['name']} wants {KINDS[w['kind']]['label'].lower()} for {w['purpose']} at {w['offer'] * config.MICRO_PER_UNIT / 1e6:.6f} {self.rail.label()} for this purchase. "
                                f"You have {nfiles} listed file(s). Approve this one-to-one sale?",
                  [{"t": "OK, include me", "do": "interest", "posting": w["id"]}, {"t": "Not this one", "do": "noop", "posting": w["id"]}])

    def settle(self, cid: int, w: dict, verified: list, trace: dict, total: float):
        buyer_id = w["buyer"]
        self.s.x("UPDATE contracts SET status='settling', total=? WHERE id=?", (total, cid))
        self.events += 1
        legs, plain = [], {}
        for a, fs, price in verified:
            recs = [json.loads(f["clean"]) for f in fs]
            clear = data.dumps({"contract": cid, "seller": "p_" + data.fp(a, cid)[:10], "records": recs}).encode()
            sealed, K = self.rail.seal(buyer_id, clear)
            trace["protocol"].append({"protocol": "Sealed delivery (AES-256-GCM, key wrapped with X25519 + HKDF-SHA256)", "who": a, "ok": True, "tx": None,
                                      "detail": f"{len(clear)} bytes sealed to the buyer's X25519 key; bundle SHA-256 {hashlib.sha256(clear).hexdigest()[:16]}…; content key K stays with the seller's agent"})
            legs.append({"seller": a, "seller_addr": self.addr[a], "dst_addr": self.acct(a).get("payout") if self.rail.has_line(self.acct(a).get("payout") or "") else None, "drops": round(price * config.MICRO_PER_UNIT), "K": K, "sealed": sealed, "fs": fs, "price": price})
            plain[a] = clear
        self.s.x("UPDATE contracts SET trace=?,sellers=? WHERE id=?", (json.dumps(trace),json.dumps([l["seller"] for l in legs]),cid))
        use_ap4m = self._use_ap4m(buyer_id, [l["seller"] for l in legs])
        eids = {}
        def record(i, seq, create_hash, cancel_after, create_blob):
            l = legs[i]
            eids[i] = self.s.insert("escrows", contract=cid, buyer=buyer_id, seller=l["seller"], owner=self.addr[buyer_id], seq=seq,
                                    create_hash=create_hash, k=l["K"].hex(), cancel_after=cancel_after, drops=l["drops"], price=l["price"],
                                    files=[f["id"] for f in l["fs"]], sealed=l["sealed"], create_blob=create_blob, state="open")
        res = ([self._ap4m_leg(cid, buyer_id, l) for l in legs] if use_ap4m
               else self.rail.escrow_lot(self.addr[buyer_id], legs, f"vaultmarket/contract/{cid}", record=record))
        for i, r in enumerate(res):
            if i in eids:
                self.s.x("UPDATE escrows SET state = ?, finish_hash = ? WHERE id = ?",
                         ("finished" if r["finish"]["ok"] else "open", r["finish"]["hash"], eids[i]))
        with self.s.transaction():
            paid, items, fps, merged = [], 0, set(), []
            for leg, r in zip(legs, res):
                if use_ap4m:
                    if not self._record_ap4m(cid, buyer_id, leg, r, trace):
                        continue
                    K = r["K"]
                    raw_open = self.rail.open(buyer_id, leg["sealed"], K)
                    opened = json.loads(raw_open)
                    same = hashlib.sha256(raw_open).digest() == hashlib.sha256(plain[leg["seller"]]).digest()
                    trace["protocol"].append({"protocol": "Buyer opens the bundle", "who": leg["seller"], "ok": same, "tx": None,
                                              "detail": f"buyer agent got K back from the AP4M merchant for its redeemed Voucher, unwrapped and decrypted {len(opened['records'])} records; bundle SHA-256 {hashlib.sha256(raw_open).hexdigest()[:16]}… {'matches' if same else 'DOES NOT match'} the sealed bundle"})
                    merged.extend(opened["records"]); items += len(leg["fs"]); paid.append(leg)
                    for f in leg["fs"]:
                        self.s.x("UPDATE files SET sold = sold + 1 WHERE id = ?", (f["id"],)); fps.update(json.loads(f["fps"] or "[]"))
                    continue
                self.s.insert("txs", contract=cid, type="EscrowCreate", hash=r["create"]["hash"], src=buyer_id, dst=leg["seller"], drops=leg["drops"], result=r["create"]["result"], asset=self.rail.symbol())
                if r["finish"]["hash"]:
                    self.s.insert("txs", contract=cid, type="EscrowFinish (key released)", hash=r["finish"]["hash"], src=leg["seller"], dst=buyer_id, drops=leg["drops"], result=r["finish"]["result"], asset=self.rail.symbol())
                trace["tx"].append({"seller": leg["seller"], "create": r["create"]["hash"], "finish": r["finish"]["hash"], "ok": r["finish"]["ok"]})
                cond = condition_hex(leg["K"])
                trace["protocol"].append({"protocol": f"XRPL EscrowCreate ({'token escrow, ' if self.rail.token else ''}PREIMAGE-SHA-256 crypto-condition)", "who": leg["seller"], "ok": r["create"]["ok"], "tx": r["create"]["hash"],
                                          "detail": f"buyer locks {leg['drops'] / 1e6:.3f} {self.rail.label()}{(' (issuer ' + self.rail.issuer[:8] + '…)') if self.rail.token else ''} to the seller's {'own linked wallet ' + leg['dst_addr'][:8] + '…' if leg.get('dst_addr') else 'agent wallet'} under Condition {cond[:20]}… = SHA-256(K); CancelAfter 1 h; memo vaultmarket/contract/{cid}; {r['create']['result']}"})
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
            if not paid and use_ap4m:
                why = "; ".join(sorted({r.get("reason") or "AP4M payment failed" for r in res}))
                self.s.x("UPDATE contracts SET status='rejected',reason=?,trace=? WHERE id=?", (f"AP4M payment not made: {why}", json.dumps(trace), cid))
                self.s.bump("rejected")
                return
            if not paid:
                pending = bool(self.s.one("SELECT id FROM escrows WHERE contract=? AND state='open'", (cid,)))
                self.s.x("UPDATE contracts SET status=?,reason=?,trace=? WHERE id=?", ("settling" if pending else "rejected", "Waiting for validated ledger settlement; recovery will reconcile the saved escrow" if pending else "No escrow payment validated", json.dumps(trace),cid))
                if not pending:
                    self.s.bump("rejected")
                return
            paid_total = round(sum(l["price"] for l in paid), 2)
            people = sum(json.loads(l["fs"][0]["raw"]).get("_people", 1) for l in paid)
            raw = {"_people": people, "from_contract": cid, "records": merged}
            self.s.insert("files", account=buyer_id, kind=w["kind"], name=f"{w['kind']}_lot_{cid}.json", raw=data.dumps(raw), clean=data.dumps({"records": merged[:3], "_people": people}),
                          status="bought", fps=sorted(fps), source=f"contract {cid}", resale=w.get("resale", 0), bytes=sum(len(c) for c in plain.values()))
            self.s.x("UPDATE sale_queue SET status='settled',reason='Payment and delivery verified',updated=? WHERE contract=?", (time.time(),cid))
            self.s.x("UPDATE contracts SET status='settled', reason=NULL, total=?, items=?, sellers=?, trace=? WHERE id=?", (paid_total, items, json.dumps([l["seller"] for l in paid]), json.dumps(trace), cid))
            self.s.x("UPDATE postings SET settled = settled + 1 WHERE id = ?", (w["id"],))
            if w.get("once"):
                self.s.x("UPDATE postings SET status = 'filled' WHERE id = ?", (w["id"],))
            self.s.bump("settled"); self.s.bump("volume", paid_total); self.s.bump("volume:" + w["kind"], paid_total); self.s.bump("settled:" + w["kind"])
            self.s.bump("drops", sum(l["drops"] for l in paid))
            for l in paid:
                self.s.bump(f"earned:{l['seller']}:{w['kind']}", l["price"])
                self.s.insert("prices", kind=w["kind"], price=l["price"], contract=cid)
                if self.acct(l["seller"])["type"] == "person" and self.acct(l["seller"])["sell_agent"].get("mode") == "ask":
                    self.chat(l["seller"], "agent", f"Sale completed: {KINDS[w['kind']]['label']} to {self.acct(buyer_id)['name']}: +{l['drops'] / 1e6:.6f} {'RLUSD on AP4M' if use_ap4m else self.rail.label() + ' on the ledger'}. Contract #{cid}.")
            for a in {l["seller"] for l in paid}:
                self._bal.pop(a, None)
            self._bal.pop(buyer_id, None)

    # ---------------- AP4M (Mastercard) settlement ----------------
    def _use_ap4m(self, buyer_id: str, sellers: list[str]) -> bool:
        """Deals with a member or the demo vault on either side always pay on AP4M; deals between simulated
        agents only up to VM_AP4M_BOT_PER_HOUR, so the background market does not spend the shared budget."""
        if not config.AP4M:
            return False
        if any(a.startswith("u-") or a == "demo-vault" for a in [buyer_id, *sellers]):
            return True
        hour = f"ap4m_bot:{int(time.time() // 3600)}"
        if self.s.stat(hour) >= config.AP4M_BOT_PER_HOUR:
            return False
        self.s.bump(hour)
        return True

    def _ap4m_leg(self, cid: int, buyer_id: str, leg: dict) -> dict:
        """Pay one seller with one AP4M Voucher; its merchant response carries K. Negotiation caps every seller's
        price at 0.10 RLUSD, and a leg above it is refused here rather than split. A seller with an EVM wallet set
        (sell_agent.evm) gets the amount forwarded on-chain from the merchant payout wallet."""
        if leg["drops"] > ap4m_rail.PER_PAYMENT_CAP_MICRO:
            return {"ok": False, "receipts": [], "K": None, "reason": f"price {leg['drops'] / 1e6} RLUSD is above the AP4M per-payment cap 0.10"}
        evm = (self.acct(leg["seller"]).get("sell_agent") or {}).get("evm")
        evm = evm if isinstance(evm, str) and len(evm) == 42 and evm.startswith("0x") else None
        r = ap4m_rail.pay(f"vm-c{cid}-{leg['seller']}", leg["drops"], pool="vault",
                          memo={"contract": cid, "buyer": buyer_id, "seller": leg["seller"]},
                          content={"k": leg["K"].hex()}, forward_to=evm)
        if not r.get("ok"):
            return {"ok": False, "receipts": [r], "reason": r.get("reason"), "K": None}
        k_hex = (r.get("content") or {}).get("k")
        K = bytes.fromhex(k_hex) if k_hex else None
        ok = K is not None and K == leg["K"]
        return {"ok": ok, "receipts": [r], "K": K, "reason": None if ok else "the merchant did not return the data key"}

    def _record_ap4m(self, cid: int, buyer_id: str, leg: dict, r: dict, trace: dict) -> bool:
        paid = [x for x in r["receipts"] if x.get("ok")]
        for x in paid:
            self.s.insert("txs", contract=cid, type="AP4M VoucherRedeemed", hash=x["voucher_redeemed_tx"], src=leg["seller"], dst=buyer_id,   # like EscrowFinish: src is who is paid
                          drops=round(float(x["amount_rlusd"]) * 1e6), result="verified" if x.get("verified") else "redeemed", asset="RLUSD (AP4M)")
            if x.get("forward_tx"):
                self.s.insert("txs", contract=cid, type="RLUSD forward to seller", hash=x["forward_tx"], src="platform", dst=leg["seller"],
                              drops=round(float(x["amount_rlusd"]) * 1e6), result="ok" if x.get("forward_ok") else "failed", asset="RLUSD (AP4M)")
        trace["tx"].append({"seller": leg["seller"], "ap4m": [{k: x.get(k) for k in ("claim_id", "voucher_redeemed_tx", "voucher_url", "receipt_url",
                            "payout_tx", "payout_url", "forward_tx", "forward_url", "amount_rlusd", "verified")} for x in paid], "ok": r["ok"]})
        for x in paid:
            trace["protocol"].append({"protocol": "AP4M Voucher redeemed (Mastercard AP4M, XRPL EVM Testnet)", "who": leg["seller"], "ok": bool(x.get("verified")),
                                      "tx": x["voucher_redeemed_tx"], "url": x.get("voucher_url"), "receipt_url": x.get("receipt_url"),
                                      "detail": f"the market's AP4M agent paid {x['amount_rlusd']} RLUSD for {self.acct(buyer_id)['name']} with an EIP-712 Voucher on Channel {str(x.get('channel_id'))[:10]}…; "
                                                f"claim {str(x.get('claim_id'))[:10]}…; the AP4M service settled it to the market's Merchant payout wallet"
                                                + (f", then {x['amount_rlusd']} RLUSD was forwarded on-chain to the seller's wallet {x['forward_to'][:8]}…" if x.get("forward_tx") else ", where it is held for the seller")})
        if not r["ok"]:
            trace["protocol"].append({"protocol": "AP4M payment", "who": leg["seller"], "ok": False, "tx": None, "detail": r.get("reason") or "not paid"})
        return r["ok"]

    def backfill_ap4m_receipts(self, limit: int = 40) -> int:
        """AP4M settles in the background: fill receipt_url and the payout tx into recent deals paid without one."""
        if not config.AP4M:
            return 0
        n = 0
        for c in self.s.q("SELECT id, trace FROM contracts WHERE status = 'settled' AND trace LIKE '%\"ap4m\"%' AND trace LIKE '%\"receipt_url\": null%' ORDER BY id DESC LIMIT ?", (limit,)):
            trace = json.loads(c["trace"] or "{}"); changed = False
            for t in trace.get("tx", []):
                for x in t.get("ap4m") or []:
                    if x.get("receipt_url"):
                        continue
                    got = ap4m_rail.lookup(f"vm-c{c['id']}-{t['seller']}") or {}
                    if got.get("receipt_url"):
                        x.update({k: got.get(k) for k in ("receipt_url", "payout_tx", "payout_url")}); changed = True
                        for p in trace.get("protocol", []):
                            if p.get("tx") == x.get("voucher_redeemed_tx"):
                                p["receipt_url"] = got["receipt_url"]
                        self.s.x("UPDATE txs SET receipt = ? WHERE contract = ? AND hash = ?", (got["receipt_url"], c["id"], x.get("voucher_redeemed_tx")))
            if changed:
                self.s.x("UPDATE contracts SET trace = ? WHERE id = ?", (json.dumps(trace), c["id"])); n += 1; self.events += 1
        return n

    # ---------------- restart recovery ----------------
    def recover(self):
        self._adopt_legacy()
        for c in self.s.q("SELECT * FROM contracts WHERE status IN ('settling','interrupted') AND id IN (SELECT contract FROM escrows)"):
            for e in self.s.q("SELECT * FROM escrows WHERE contract=? AND state='open'", (c["id"],)):
                ok = self.rail.created_ok(e["create_hash"], e.get("create_blob"))
                if ok is None:
                    continue
                if not ok:
                    self.s.x("UPDATE escrows SET state='void' WHERE id=?", (e["id"],))
                    continue
                outcome, h = self.rail.escrow_outcome(e["owner"], e["seq"])
                if outcome == "open":
                    if e["k"] and e["seller"] in self.addr:
                        f = self.rail.finish_escrow(self.addr[e["seller"]], e["owner"], e["seq"], bytes.fromhex(e["k"]), f"vaultmarket/contract/{c['id']}")
                        if f["ok"]:
                            outcome, h = "finished", f["hash"]
                    if outcome == "open" and self.rail.led.now() > e["cancel_after"]:
                        f = self.rail.cancel_escrow(e["owner"], e["seq"])
                        if f["ok"]:
                            outcome, h = "refunded", f["hash"]
                if outcome in ("finished","refunded") and h:
                    self.s.x("UPDATE escrows SET state=?,finish_hash=? WHERE id=?", (outcome,h,e["id"]))
                    for typ, txh, src, dst in [("EscrowCreate",e["create_hash"],e["buyer"],e["seller"]),
                                               ("EscrowFinish (key released)" if outcome=="finished" else "EscrowCancel (refund)",h,e["seller"] if outcome=="finished" else e["buyer"],e["buyer"])]:
                        if not self.s.one("SELECT id FROM txs WHERE hash=?", (txh,)):
                            self.s.insert("txs",contract=c["id"],type=typ,hash=txh,src=src,dst=dst,drops=e["drops"],result="tesSUCCESS",asset=c.get("asset") or "XRP")
            if not self.s.one("SELECT id FROM escrows WHERE contract=? AND state='open'", (c["id"],)):
                self._close_recovered(c)

    def _adopt_legacy(self):
        """Contracts stranded before escrow legs were written down (status 'settling' or 'interrupted', with
        EscrowCreate rows in txs): read each escrow's sequence from the ledger so recover() can refund it."""
        for c in self.s.q("SELECT * FROM contracts WHERE status IN ('settling', 'interrupted') AND id NOT IN (SELECT contract FROM escrows)"):
            rows = []
            for t in self.s.q("SELECT * FROM txs WHERE contract = ? AND type = 'EscrowCreate'", (c["id"],)):
                owner = t["src"] if str(t["src"]).startswith("r") and len(t["src"]) > 24 else self.addr.get(t["src"])
                try:
                    st = self.rail.led.lookup(t["hash"])
                except Exception:
                    st = None
                if not owner or st is None or not st.found or not st.validated:
                    return                       # wallets still connecting or ledger unsure: try on a later pass
                if st.found and st.success:
                    rows.append(dict(contract=c["id"], buyer=t["src"], seller=t["dst"], owner=owner, seq=st.sequence, create_hash=t["hash"], k=None,
                                     cancel_after=self.rail.escrow_create_info(t["hash"]).get("CancelAfter", 2**63-1), drops=t["drops"], price=(t["drops"] or 0) / (c.get("unit_micro") or 10000), files=[], state="open"))
            for r in rows:
                self.s.insert("escrows", **r)
            if not rows:
                self.s.x("UPDATE contracts SET status = 'rejected', reason = 'interrupted by a server restart; no escrow validated' WHERE id = ?", (c["id"],))

    def _close_recovered(self, c: dict):
        with self.s.transaction():
            current = self.s.one("SELECT * FROM contracts WHERE id=?", (c["id"],))
            if current["status"] not in ("settling","interrupted"):
                return
            self._write_recovered(current)

    def _write_recovered(self, c: dict):
        cid, buyer_id = c["id"], c["buyer"]
        done = self.s.q("SELECT * FROM escrows WHERE contract = ? AND state = 'finished'", (cid,))
        trace = json.loads(c["trace"] or "null") or {"protocol": [], "tx": []}
        trace.setdefault("protocol", []).append({"protocol": "Restart recovery", "who": "platform", "ok": bool(done), "tx": None,
            "detail": f"the server restarted mid-settlement; {len(done)} escrow(s) finished from the saved key K, the rest void or refunded after CancelAfter"})
        if not done:
            n = self.s.one("SELECT COUNT(*) n FROM escrows WHERE contract = ? AND state = 'refunded'", (cid,))["n"]
            why = f"interrupted by a server restart; {n} escrow(s) refunded to the buyer by EscrowCancel" if n else "interrupted by a server restart; no escrow was left on the ledger"
            self.s.x("UPDATE contracts SET status = ?, reason = ?, trace = ? WHERE id = ?", ("refunded" if n else "rejected", why, json.dumps(trace), cid))
            self.s.x("UPDATE sale_queue SET status=?,reason=?,updated=? WHERE contract=?", ("refunded" if n else "rejected",why,time.time(),cid))
            return
        if any(not json.loads(e["files"]) for e in done):
            self.s.x("UPDATE contracts SET status='recovery review',reason='Ledger payment confirmed; original delivery manifest is missing' WHERE id=?", (cid,))
            return
        merged, fps, people, items = [], set(), 0, 0
        for e in done:
            for typ, txh, src, dst in [("EscrowCreate",e["create_hash"],buyer_id,e["seller"]),("EscrowFinish (key released)",e["finish_hash"],e["seller"],buyer_id)]:
                if not self.s.one("SELECT id FROM txs WHERE hash=?", (txh,)):
                    self.s.insert("txs",contract=cid,type=typ,hash=txh,src=src,dst=dst,drops=e["drops"],result="tesSUCCESS",asset=c.get("asset") or "XRP")
            sealed_records = None
            if e.get("sealed"):
                st = self.rail.led.lookup(e["finish_hash"])
                if not (st.validated and st.success and st.fulfillment):
                    raise RuntimeError("Recovery requires the validated key release")
                released = bytes.fromhex(st.fulfillment[8:])
                sealed_records = json.loads(self.rail.open(buyer_id, bytes(e["sealed"]), released))["records"]
            for fid in json.loads(e["files"]):
                f = self.s.one("SELECT * FROM files WHERE id = ?", (fid,))
                if not f:
                    continue
                merged.append(json.loads(f["clean"])); fps.update(json.loads(f["fps"] or "[]"))
                people += json.loads(f["raw"]).get("_people", 1); items += 1
                self.s.x("UPDATE files SET sold = sold + 1 WHERE id = ?", (fid,))
            if sealed_records is not None:
                merged[-len(json.loads(e["files"])):] = sealed_records
            self.s.insert("prices", kind=c["kind"], price=e["price"], contract=cid)
            self.s.bump(f"earned:{e['seller']}:{c['kind']}", e["price"])
            trace.setdefault("tx", []).append({"seller": e["seller"], "create": e["create_hash"], "finish": e["finish_hash"], "ok": True})
        total = round(sum(e["price"] for e in done), 2)
        self.s.insert("files", account=buyer_id, kind=c["kind"], name=f"{c['kind']}_lot_{cid}.json", raw=data.dumps({"_people": people, "from_contract": cid, "records": merged}),
                      clean=data.dumps({"records": merged[:3], "_people": people}), status="bought", fps=sorted(fps), source=f"contract {cid}", resale=self.s.one("SELECT resale FROM postings WHERE id=?", (c["posting"],))["resale"] or 0)
        self.s.x("UPDATE contracts SET status = 'settled', total = ?, items = ?, sellers = ?, reason = 'finished after a server restart', trace = ? WHERE id = ?",
                 (total, items, json.dumps([e["seller"] for e in done]), json.dumps(trace), cid))
        self.s.x("UPDATE postings SET settled = settled + 1 WHERE id = ?", (c["posting"],))
        self.s.bump("settled"); self.s.bump("volume", total); self.s.bump("volume:" + c["kind"], total); self.s.bump("settled:" + c["kind"])
        self.s.bump("drops", sum(e["drops"] for e in done))
        self.s.x("UPDATE postings SET status='filled' WHERE id=? AND once=1", (c["posting"],))
        self.s.x("UPDATE sale_queue SET status='settled',reason='Recovered after restart',updated=? WHERE contract=?", (time.time(),cid))
        self._bal.clear(); self.events += 1

    # ---------------- resale ----------------
    def bundle_files(self, aid: str, ids: list[int]) -> int:
        with self.s.transaction():
            lots=[self.s.one("SELECT * FROM files WHERE id=? AND account=? AND status='bought' AND resale=1",(fid,aid)) for fid in set(ids)]
            if not lots or not all(lots) or len({f["kind"] for f in lots})!=1:
                raise ValueError("Select purchased files of one category with resale rights")
            recs,fps,people,origins=[],set(),0,set()
            for f in lots:
                body=json.loads(f["raw"]);recs.extend(body["records"]);fps.update(json.loads(f["fps"]));people+=body.get("_people",1)
                origins.update(body.get("from_contracts",[]))
                if body.get("from_contract"):
                    origins.add(body["from_contract"])
            kind=lots[0]["kind"];body={"_people":people,"records":recs,"from_contracts":sorted(origins)}
            clean={"records":recs,"_people":people};clean["_attestation"]=intake.attest(kind,clean,["licensed purchases; original record fingerprints retained"],False)
            bid=self.s.insert("files",account=aid,kind=kind,name=f"{kind}_resale_bundle.json",raw=data.dumps(body),clean=data.dumps(clean),status="listed",fps=sorted(fps),source="licensed resale bundle",resale=1,derived_from=json.dumps(sorted(ids)),bytes=len(data.dumps(clean)))
            for f in lots:
                self.s.x("UPDATE files SET status='bundled' WHERE id=?",(f["id"],))
        self.events+=1
        return bid

    def resell(self):
        for kind in ("gps_track","sleep_log"):
            rows=self.s.q("SELECT id FROM files WHERE account=? AND kind=? AND status='bought' AND resale=1",(BROKER,kind))
            if len(rows)>=2:
                self.bundle_files(BROKER,[f["id"] for f in rows])

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
            kind = rng.choice(["gps_track", "gps_track", "sleep_log", "purchase_receipts", "audio", "step_count", "commute", "screen_time", "energy_use"])
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
        self.expire_sale_queue()
        # one negotiation: postings someone marked interest in first, then the rest
        open_ = self.s.q("SELECT p.*, (SELECT COUNT(*) FROM interests i WHERE i.posting = p.id) AS hot FROM postings p WHERE status = 'open' ORDER BY hot DESC, RANDOM()")
        if not self.process_sale_queue() and open_:
            w = open_[0] if open_[0]["hot"] and rng.random() < 0.6 else rng.choice(open_)
            self.negotiate(w)
        if rng.random() < 0.2:
            self.resell()
        if rng.random() < 0.3:
            for a in ["dana"] + [r["id"] for r in self.s.q("SELECT id FROM accounts WHERE id LIKE 'u-%'")]:
                self.scan(a)
        self.events += 1

    PURPOSES = {"step_count": ["fitness app benchmark", "city walkability study", "health insurer wellness program"],
                "commute": ["transit planning", "bike-lane planning", "office space planning"],
                "screen_time": ["digital wellbeing research", "app market study", "advertising"],
                "energy_use": ["utility demand forecasting", "solar sizing", "home insurance pricing"],
                "gps_track": ["running-route app", "city heat-map research", "shoe wear study", "bike-lane planning"],
                "sleep_log": ["sleep research", "mattress product study", "wearable calibration", "insurance pricing"],
                "purchase_receipts": ["basket research", "price index", "store layout study"],
                "audio": ["speech model training", "accent research", "voice assistant tuning"],
                "air": ["pollution alerts", "school air study", "asthma research"]}

    def new_request(self, rng) -> int:
        """A buyer agent posts a request on its own: someone in the market (company or person) wants the
        kind of data that has the least open demand right now, at a price near the going rate."""
        open_by = {k: self.s.one("SELECT COUNT(*) n FROM postings WHERE kind = ? AND status = 'open'", (k,))["n"] for k in KINDS}
        kind = min(open_by, key=lambda k: (open_by[k], rng.random()))
        buyer = rng.choice([a for a in self.s.q("SELECT id, type FROM accounts WHERE id NOT LIKE 'u-%' AND id!='demo-vault'") if a["id"] in self.addr] or [{"id": "atlas-maps", "type": "org"}])
        base = KINDS[kind]["price"] * rng.uniform(0.85, 1.3)
        offer = round(base, 1)
        pid = self.s.insert("postings", buyer=buyer["id"], kind=kind, offer=offer, max=round(offer * rng.uniform(1.15, 1.4), 1), purpose=rng.choice(self.PURPOSES[kind]),
                            lot=1, min_trust=0.7, resale=0, status="open", once=1)
        self.events += 1
        return pid

    def run_forever(self):
        # trade as soon as a handful of wallets are funded; the rest join as their faucet calls finish
        while sum(1 for a in self.addr if not a.startswith("u-")) < min(8, len(self.s.q("SELECT id FROM accounts"))):
            time.sleep(1)
        while self.rail.asset == "USD" and self.rail.name != "mock" and not getattr(self, "asset_ready", False):
            time.sleep(1)      # test USD trust lines are being set up
        last_recover = 0.0
        while True:
            t = time.time()
            try:
                with self.lock:
                    if t - last_recover > 60:     # settle() runs under this lock, so anything still 'settling' here is stranded
                        last_recover = t
                        self.recover()
                    self.tick()
                if t - getattr(self, "_last_backfill", 0.0) > 90:   # outside the lock: it only calls the rail and fills links
                    self._last_backfill = t
                    self.backfill_ap4m_receipts()
            except Exception:
                traceback.print_exc()
            # sleep until the next tick, but wake at once for a visitor's sale and negotiate only that
            while self.wake.wait(max(0.0, config.TICK_SECONDS - (time.time() - t))):
                self.wake.clear()
                try:
                    with self.lock:
                        self.process_sale_queue()
                except Exception:
                    traceback.print_exc()
            time.sleep(0.5)
