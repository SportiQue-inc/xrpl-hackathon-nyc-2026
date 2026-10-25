"""Research contracts as records: a researcher posts one, people join it themselves, agents trade on it.

Nothing about a contract is in the code. The institution, ethics approval number, purpose, items, weeks,
price per item, budget and capacity come from the posting; the members are whoever joined it with their
own key; the rows a member's agent offers are what that member's vault holds (their UniQdata account,
or records they stored here). The lane keeps its own store (AGENTRAIL_CONTRACTS_DB), so resetting the
demo world does not touch it.

  researcher  POST /api/contracts                       terms + researcher key -> contract id, invite code (once)
  anyone      POST /api/contracts/{cid}/join/start      invite code + key + items + automation -> pid, consent doc
              POST /api/contracts/{cid}/join/complete   pid + signature over the consent doc -> member
  researcher  POST /api/contracts/{cid}/rounds          week -> each member's agent decides; escrow, delivery, key
  member      POST /api/p/{pid}/contracts/{cid}/requests/{rid}/approve | /withdraw

The member's agent and keyring run in this service, as in the rest of the engine. The member's login and
consent key does not: only its public half is enrolled.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time

from . import units
from .agents import PersonalAgent, consent_document
from .connectors import Person, PersonalVaultConnector
from .db import Store
from .engine import BudgetExceeded, Engine, NeedsHumanApproval, OrderRequest, canonical, sha256_hex
from .policy import AUTOMATION_LEVELS, PURPOSE_DUO, SENSITIVITY, BuyerMandate, ComplianceRules
from .security.auth import Identity
from .security.devices import InstitutionVault, ParticipantKeyring, consent_message, verify_ed25519
from .security.keystore import LocalKeyStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS research_contracts (
  id TEXT PRIMARY KEY, institution_id TEXT NOT NULL, terms TEXT NOT NULL, terms_hash TEXT NOT NULL,
  invite_hash TEXT NOT NULL, researcher_key TEXT NOT NULL, status TEXT NOT NULL,
  created_at REAL NOT NULL, closed_at REAL
);
CREATE TABLE IF NOT EXISTS contract_members (
  contract_id TEXT NOT NULL, pid TEXT NOT NULL, joined_via TEXT NOT NULL, public_hex TEXT NOT NULL,
  items TEXT NOT NULL, automation TEXT NOT NULL, consent_hash TEXT NOT NULL, consent_signature TEXT NOT NULL,
  data_source TEXT NOT NULL, status TEXT NOT NULL, joined_at REAL NOT NULL, withdrawn_at REAL,
  payout_address TEXT,
  PRIMARY KEY (contract_id, pid)
);
CREATE TABLE IF NOT EXISTS contract_rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT, contract_id TEXT NOT NULL, week INTEGER NOT NULL,
  started_at REAL NOT NULL, result TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contract_payments (
  order_id INTEGER PRIMARY KEY, contract_id TEXT NOT NULL, pid TEXT NOT NULL, rail TEXT NOT NULL, ref TEXT NOT NULL,
  amount_micro INTEGER NOT NULL, ok INTEGER NOT NULL, result TEXT NOT NULL, attempts INTEGER NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS member_records (
  pid TEXT NOT NULL, item TEXT NOT NULL, day INTEGER NOT NULL, value TEXT NOT NULL,
  source TEXT NOT NULL, record_hash TEXT NOT NULL, stored_at REAL NOT NULL,
  PRIMARY KEY (pid, item, day)
);
"""

ITEMS = PersonalVaultConnector.ITEMS
# T3 kinds trade only through the T3 lane, with a fresh approval each time; a contract cannot ask for them.
T3_PREFIXES = ("imaging.", "genome.", "genomic.", "mri", "ct.")
REGISTRY = "contracts_registry"
ETHICS = "ETHICS_REVIEW"
JOIN_TTL_S = 900
MAX_MEMBERS = 500
# AGENTRAIL_CONTRACTS_PAY=ap4m: each delivered member-week is paid through the AP4M rail (ap4m_rail.pay),
# one payment of at most 0.10, into the team's AP4M merchant wallet (AP4M has one merchant per team).
RAILS = ("ledger", "ap4m")
AP4M_MAX_MICRO = 100_000
AP4M_PAYEE = "the team's AP4M merchant wallet (AP4M has one merchant per team), credited to this member here"


class ContractError(ValueError):
    pass


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:24] or "institution"


def _hash_code(code: str) -> str:
    return hashlib.sha256(f"agentrail-invite|{code}".encode()).hexdigest()


class StoredSource:
    """One of a member's sources, read from records the member stored in this service."""

    def __init__(self, original, store: Store, pid: str):
        self.name, self.items, self.original = original.name, list(original.items), original
        self.store, self.pid = store, pid

    def read(self, pid, item, day, rng):
        r = self.store.one("SELECT value FROM member_records WHERE pid=? AND item=? AND day=?", self.pid, item, day)
        return json.loads(r["value"]) if r else None


class Lane:
    def __init__(self, path: str | None = None, ledger=None):
        from .ledger import make_ledger
        vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")      # a deploy's volume: contracts outlive redeploys
        self.store = Store(path or os.environ.get("AGENTRAIL_CONTRACTS_DB")
                           or (os.path.join(vol, "contracts.db") if vol else ":memory:"))
        self.store._keepalive.executescript(SCHEMA)
        cols = {r[1] for r in self.store._keepalive.execute("PRAGMA table_info(contract_members)")}
        if "payout_address" not in cols:        # a store from before payouts were forwarded
            self.store._keepalive.execute("ALTER TABLE contract_members ADD COLUMN payout_address TEXT")
        self.ledger = ledger or make_ledger(os.environ.get("LEDGER", "mock"))
        wallets = os.environ.get("AGENTRAIL_CONTRACTS_WALLETS") or (os.path.join(vol, "contracts.wallets.json") if vol else None)
        if wallets and hasattr(self.ledger, "_labels"):
            # the institution's and members' Testnet wallets, so a restart signs with the same accounts
            self.ledger.wallet_file = wallets
            if os.path.exists(wallets):
                self.ledger._labels = json.load(open(wallets))
        self.engine = Engine(self.store, self.ledger)
        self.engine.relay = self.ledger.new_account("contracts_relay")
        self.root = os.environ.get("AGENTRAIL_KEYSTORE") or (os.path.join(vol, "keystore") if vol else None)
        self.rail = os.environ.get("AGENTRAIL_CONTRACTS_PAY", "ledger")
        if self.rail not in RAILS:
            raise ValueError(f"AGENTRAIL_CONTRACTS_PAY must be one of {RAILS}")
        self.people: dict[str, PersonalAgent] = {}
        self.uniqdata: dict = {}                      # roster id -> UniQdataClient (UNIQDATA_ROSTER)
        self._pending: dict[str, dict] = {}           # pid -> join waiting for its signature
        self._lock = threading.RLock()
        if os.environ.get("UNIQDATA_ROSTER"):
            from . import uniqdata_live
            self.uniqdata = uniqdata_live.load_roster(os.environ["UNIQDATA_ROSTER"])
        if self.engine.party(REGISTRY) is None:
            self.engine.add_party(REGISTRY, "AgentRail contract registry", "organization",
                                  self.ledger.new_account(REGISTRY))
        self._load()
        if os.environ.get("AGENTRAIL_CONTRACTS_AUTORUN", "1") != "0":
            threading.Thread(target=self._autorun, name="contract-rounds", daemon=True).start()

    # ---------- the researcher's agent: each week on its own ----------

    def _autorun(self):
        while True:
            time.sleep(5)
            try:
                self.tick()
            except Exception as e:              # a bad round never stops the next one
                self.store.log(REGISTRY, "round_failed", f"automatic round failed: {str(e)[:200]}")

    def tick(self, now: float | None = None) -> list[dict]:
        """Run every round that is due: a contract posted with round_every_s gets its next week that many
        seconds after the last one (the first one that long after posting). No one presses anything: the
        institution's agent asks, each member's agent answers from that member's consent, the rail pays."""
        now = time.time() if now is None else now
        out = []
        for c in self.store.q("SELECT id, terms, created_at FROM research_contracts WHERE status='open'"):
            t = json.loads(c["terms"])
            every = t.get("round_every_s")
            if not every:
                continue
            last = self.store.one("SELECT week, started_at FROM contract_rounds WHERE contract_id=? "
                                  "ORDER BY id DESC LIMIT 1", c["id"])
            week = last["week"] + 1 if last else t["weeks"][0]
            if week > t["weeks"][1]:
                self.retry_payments(c["id"])
                self.close(c["id"])
                self.store.log(t["institution_id"], "contract_done", f"{c['id']}: last week done, contract closed")
                continue
            if now >= (last["started_at"] if last else c["created_at"]) + every and self._members(c["id"]):
                r = self.run_round(c["id"], week)
                out.append({k: r[k] for k in ("contract", "week", "members", "summary")})
        return out

    # ---------- startup: rebuild agents from the records ----------

    def _load(self):
        for c in self.store.q("SELECT * FROM research_contracts"):
            self._open_institution(c["institution_id"])
            self._rewallet(c["institution_id"])
            if self.ledger.name == "mock":     # mock credentials live in memory: issue the ethics one again
                self.ledger.issue_credential(self.engine.party(REGISTRY)["address"],
                                             self.engine.party(c["institution_id"])["address"], ETHICS)
        for m in self.store.q("SELECT * FROM contract_members"):
            if m["pid"] not in self.people:
                try:
                    self._agent(m["pid"], m["data_source"])
                except ContractError:          # their UniQdata account is not connected here any more
                    self._agent(m["pid"], "stored")
                self._rewallet(m["pid"])

    def _rewallet(self, pid: str):
        """After a restart the ledger adapter needs the account's key again (same label, same wallet)."""
        addr = self.engine.party(pid)["address"]
        if self.ledger.name == "mock":         # mock balances live in memory: open the same account again
            self.ledger.new_account(pid)
        elif not self.ledger.can_sign(addr) and self.ledger.new_account(pid) != addr:
            self.store.log(pid, "wallet_lost", f"{pid}: the saved wallet for {addr} is gone; it can receive but not sign")

    def enrol_all(self, authority):
        """Re-enrol every researcher and member key with the API's authority (it is rebuilt on reset)."""
        for c in self.store.q("SELECT id, institution_id, researcher_key FROM research_contracts"):
            authority.enrol(Identity(f"researcher@{c['id']}", "researcher", c["id"], c["researcher_key"]))
        for m in self.store.q("SELECT DISTINCT pid, public_hex FROM contract_members"):
            authority.enrol(Identity(m["pid"], "participant", m["pid"], m["public_hex"]))

    def _open_institution(self, iid: str):
        v = InstitutionVault(iid, LocalKeyStore(f"institution.{iid}", self.root))
        self.engine.register_public_key(iid, v.public_hex)
        self.engine.openers[iid] = v

    def _compliance(self) -> ComplianceRules:
        reg = self.engine.party(REGISTRY)["address"]
        return ComplianceRules(credential_check=lambda buyer: self.ledger.has_credential(
            self.engine.party(buyer)["address"], reg, ETHICS))

    def _agent(self, pid: str, data_source: str) -> PersonalAgent:
        pa = PersonalAgent(Person(pid, pid), self.engine, self._compliance())
        if self.root:     # the member's keyring (escrow keys, vault secret) survives a restart
            pa.keyring = ParticipantKeyring(pid, LocalKeyStore(f"participant.{pid}", self.root))
            pa.vault._secret = pa.keyring.vault_secret()
            self.engine.key_holders[pid] = pa.keyring
        if data_source.startswith("uniqdata:"):
            client = self.uniqdata.get(data_source.split(":", 1)[1])
            if client is None:
                raise ContractError("that UniQdata account is not connected to this service")
            from . import uniqdata_live
            uniqdata_live.attach(pa, client)
        else:
            pa.vault.sources = [StoredSource(s, self.store, pid) for s in pa.vault.sources]
            pa.vault.by_item = {i: s for s in pa.vault.sources for i in s.items}
        self.people[pid] = pa
        return pa

    # ---------- researcher: post a contract ----------

    def create(self, terms: dict, researcher_key: str) -> dict:
        t = self._check_terms(terms)
        if not re.fullmatch(r"[0-9a-f]{64}", researcher_key or ""):
            raise ContractError("researcher_key must be an Ed25519 public key (64 hex)")
        with self._lock:
            n = self.store.one("SELECT COUNT(*) n FROM research_contracts")["n"] + 1
            cid = f"RC{n}-{secrets.token_hex(3)}"
            iid = f"org_{_slug(t['institution'])}_{cid.split('-')[1]}"
            t = {**t, "id": cid, "institution_id": iid, "unit": units.UNIT, "display_unit": units.DISPLAY,
                 "payment_rail": self.rail, "posted_at": int(time.time())}
            terms_json = canonical(t)
            code = secrets.token_urlsafe(9)
            self.engine.add_party(iid, t["institution"], "organization", self.ledger.new_account(iid))
            self._open_institution(iid)
            self.engine.set_mandate(BuyerMandate(iid, t["budget_drops"], t["per_order_limit_drops"], [t["purpose"]]))
            reg = self.engine.party(REGISTRY)["address"]
            cred = self.ledger.issue_credential(reg, self.engine.party(iid)["address"], ETHICS)
            with self.store.tx() as c:
                c.execute("INSERT INTO research_contracts VALUES (?,?,?,?,?,?,?,?,NULL)",
                          (cid, iid, terms_json, sha256_hex(terms_json), _hash_code(code), researcher_key,
                           "open", time.time()))
            self.store.log(iid, "contract", f"{t['institution']} posted research contract {cid}: "
                           f"{', '.join(t['items'])}, weeks {t['weeks'][0]}-{t['weeks'][1]}, "
                           f"{units.fmt(t['price_per_item_drops'])} per item-week, budget {units.fmt(t['budget_drops'])}",
                           {"contract": cid, "terms_hash": sha256_hex(terms_json),
                            "ethics_credential_tx": cred[-1] if cred else None})
        return {"contract": self.public(cid), "invite_code": code, "researcher_sub": f"researcher@{cid}",
                "ethics_credential": {"tx": cred[-1] if cred else None,
                                      "url": self.ledger.explorer_url(cred[-1]) if cred else None}}

    def _check_terms(self, terms: dict) -> dict:
        def need(k):
            if terms.get(k) in (None, "", []):
                raise ContractError(f"{k} is required")
            return terms[k]
        title, inst, irb = str(need("title"))[:120], str(need("institution"))[:120], str(need("irb_approval"))[:60]
        purpose = need("purpose")
        if purpose not in PURPOSE_DUO:
            raise ContractError(f"purpose must be one of {sorted(PURPOSE_DUO)}")
        items = list(dict.fromkeys(need("items")))
        if any(i.startswith(T3_PREFIXES) for i in items):
            raise ContractError("genomic, CT and MRI go through the T3 lane with a fresh approval each time")
        bad = [i for i in items if i not in ITEMS]
        if bad:
            raise ContractError(f"unknown items: {', '.join(bad)}")
        w0, w1 = (int(x) for x in need("weeks"))
        if not (1 <= w0 <= w1 <= 52):
            raise ContractError("weeks must be 1 <= from <= to <= 52")
        price, budget = int(need("price_per_item_drops")), int(need("budget_drops"))
        cap = int(terms.get("capacity") or 60)
        if price <= 0 or budget < price or not (1 <= cap <= MAX_MEMBERS):
            raise ContractError("price must be > 0, budget at least one item, capacity 1-500")
        if self.rail == "ap4m" and price * len(items) > AP4M_MAX_MICRO:
            raise ContractError(f"AP4M pays at most {units.fmt(AP4M_MAX_MICRO)} per payment: price per item x "
                                f"items must be at most that per member-week (now {units.fmt(price * len(items))})")
        return {"title": title, "institution": inst, "irb_approval": irb, "irb_checked": "declared by the researcher",
                "purpose": purpose, "data_use": PURPOSE_DUO[purpose], "items": items,
                "sensitive": [i for i in items if SENSITIVITY.get(i) == "sensitive"],
                "weeks": [w0, w1], "price_per_item_drops": price, "budget_drops": budget,
                "per_order_limit_drops": price * len(items), "capacity": cap,
                "summary": str(terms.get("summary") or "")[:600],
                "round_every_s": self._every(terms.get("round_every_s"))}

    @staticmethod
    def _every(v) -> int | None:
        if v in (None, "", 0):
            return None
        v = int(v)
        if not 60 <= v <= 31_536_000:
            raise ContractError("round_every_s must be 60 seconds to a year")
        return v

    # ---------- reads ----------

    def _row(self, cid: str):
        c = self.store.one("SELECT * FROM research_contracts WHERE id=?", cid)
        if c is None:
            raise KeyError(cid)
        return c

    def terms(self, cid: str) -> dict:
        return json.loads(self._row(cid)["terms"])

    def public(self, cid: str) -> dict:
        """What anyone may see: the terms and how full it is. No member identities."""
        c = self._row(cid)
        t = json.loads(c["terms"])
        m = self.store.one("SELECT COUNT(*) n FROM contract_members WHERE contract_id=? AND status='active'", cid)["n"]
        spent = self.store.one("SELECT spent_drops, reserved_drops FROM mandates WHERE buyer_id=?", t["institution_id"])
        return {"id": cid, "status": c["status"], "terms": t, "terms_hash": c["terms_hash"], "members": m,
                "spent_drops": spent["spent_drops"], "budget_drops": t["budget_drops"],
                "institution_address": self.engine.party(t["institution_id"])["address"],
                "ledger": self.ledger.name}

    def list(self) -> list[dict]:
        return [self.public(r["id"]) for r in self.store.q("SELECT id FROM research_contracts ORDER BY created_at DESC")]

    # ---------- joining ----------

    def join_start(self, cid: str, invite_code: str, public_hex: str, items: list[str] | None,
                   automation: str, uniqdata_account: str | None = None, payout_address: str | None = None) -> dict:
        c = self._row(cid)
        if c["status"] != "open":
            raise ContractError("this contract is not taking new members")
        if not hmac.compare_digest(_hash_code(invite_code or ""), c["invite_hash"]):
            raise PermissionError("invite code does not match")
        if not re.fullmatch(r"[0-9a-f]{64}", public_hex or ""):
            raise ContractError("public_key must be an Ed25519 public key (64 hex)")
        if automation not in AUTOMATION_LEVELS:
            raise ContractError(f"automation must be one of {AUTOMATION_LEVELS}")
        t = json.loads(c["terms"])
        items = list(dict.fromkeys(items or t["items"]))
        if not items or any(i not in t["items"] for i in items):
            raise ContractError("you can agree only to items the contract asks for")
        if self.public(cid)["members"] >= t["capacity"]:
            raise ContractError("this contract is full")
        source = "stored"
        if uniqdata_account:
            if uniqdata_account not in self.uniqdata:
                raise ContractError("that UniQdata account is not connected to this service")
            source = f"uniqdata:{uniqdata_account}"
        if payout_address and not re.fullmatch(r"0x[0-9a-fA-F]{40}", payout_address):
            raise ContractError("payout_address must be an XRPL EVM address (0x + 40 hex)")
        pid = f"{cid.split('-')[0]}-{secrets.token_hex(4)}"
        doc = consent_document(pid, t["institution_id"], t["purpose"], items, tuple(t["weeks"]), automation,
                               t["price_per_item_drops"], "active", 1)
        doc["contract"] = {"id": cid, "terms_hash": c["terms_hash"]}
        doc["synthetic_demo"] = False
        doc["test_accounts_only"] = True
        if t.get("payment_rail") == "ap4m":
            doc["payment"] = {"rail": "ap4m", "max_per_payment": units.fmt(AP4M_MAX_MICRO),
                              "payout": payout_address or "kept in the team's AP4M merchant wallet, credited to you here"}
        h = sha256_hex(canonical(doc))
        with self._lock:
            now = time.time()
            self._pending = {k: v for k, v in self._pending.items() if v["expires"] > now}
            self._pending[pid] = {"cid": cid, "public_hex": public_hex, "items": items, "automation": automation,
                                  "doc": doc, "hash": h, "source": source, "expires": now + JOIN_TTL_S,
                                  "payout_address": payout_address}
        return {"pid": pid, "consent": doc, "consent_hash": h,
                "sign": f"agentrail-consent|{pid}|{h}", "expires_in": JOIN_TTL_S}

    def join_complete(self, cid: str, pid: str, signature: str, authority) -> dict:
        with self._lock:
            p = self._pending.get(pid)
            if not p or p["cid"] != cid or p["expires"] < time.time():
                raise KeyError(f"no pending join {pid}")
            if not verify_ed25519(p["public_hex"], consent_message(pid, p["hash"]), signature or ""):
                raise PermissionError("signature does not match the key you joined with")
            del self._pending[pid]
            t = self.terms(cid)
            pa = self._agent(pid, p["source"])
            self.engine.add_party(pid, f"Member {pid}", "person", self.ledger.new_account(pid))
            if hasattr(self.ledger, "token_optin") and self.ledger.can_sign(self.engine.party(pid)["address"]):
                self.ledger.token_optin(self.engine.party(pid)["address"], pid)
            pa.set_consent(t["institution_id"], t["purpose"], p["items"], tuple(t["weeks"]), p["automation"],
                           t["price_per_item_drops"])
            with self.store.tx() as c:
                c.execute("INSERT INTO contract_members (contract_id,pid,joined_via,public_hex,items,automation,"
                          "consent_hash,consent_signature,data_source,status,joined_at,payout_address) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (cid, pid, "invite", p["public_hex"], json.dumps(p["items"]), p["automation"], p["hash"],
                           signature, p["source"], "active", time.time(), p["payout_address"]))
            authority.enrol(Identity(pid, "participant", pid, p["public_hex"]))
            self.store.log(pid, "joined", f"{pid} joined {cid} ({', '.join(p['items'])}, automation "
                           f"{p['automation']}); signed consent {p['hash'][:12]}…", {"contract": cid})
        return self.member_view(pid)

    # ---------- the member's own records (when no UniQdata account is connected) ----------

    def store_records(self, pid: str, records: list[dict] | None = None, generate_weeks: list[int] | None = None) -> dict:
        """Records the member stores here. `generate_weeks` fills those weeks with generated test readings,
        labelled as such; anything else is what the member sent."""
        pa = self._person(pid)
        if not isinstance(pa.vault.sources[0], StoredSource):
            raise ContractError("your records come from your UniQdata account")
        rows = []
        for r in records or []:
            if r.get("item") not in ITEMS or not isinstance(r.get("value"), dict) or not (1 <= int(r.get("day", 0)) <= 366):
                raise ContractError("each record needs item, day (1-366) and a value object")
            rows.append((r["item"], int(r["day"]), r["value"], "member"))
        for wk in generate_weeks or []:
            for s in pa.vault.sources:
                for it in s.items:
                    for d in range((wk - 1) * 7 + 1, wk * 7 + 1):
                        import random
                        v = s.original.read(pid, it, d, random.Random(f"{pid}-{wk}-{it}-{d}"))
                        if v is not None:
                            rows.append((it, d, v, "generated_test"))
        with self.store.tx() as c:
            for it, d, v, src in rows:
                body = canonical({"pid": pid, "item": it, "day": d, "value": v})
                c.execute("INSERT OR REPLACE INTO member_records VALUES (?,?,?,?,?,?,?)",
                          (pid, it, d, json.dumps(v), src, sha256_hex(body), time.time()))
        return {"stored": len(rows), "records": self.store.one("SELECT COUNT(*) n FROM member_records WHERE pid=?", pid)["n"]}

    # ---------- rounds ----------

    def _person(self, pid: str) -> PersonalAgent:
        if pid not in self.people:
            raise KeyError(pid)
        return self.people[pid]

    def _members(self, cid: str, status: str = "active"):
        return self.store.q("SELECT * FROM contract_members WHERE contract_id=? AND status=?", cid, status)

    def run_round(self, cid: str, week: int) -> dict:
        t = self.terms(cid)
        if not (t["weeks"][0] <= week <= t["weeks"][1]):
            raise ContractError("week is outside the contract")
        members = self._members(cid)
        with self._lock:
            self.retry_payments(cid)
            self.store.log(t["institution_id"], "round", f"{cid} week {week}: asking {len(members)} members' agents "
                           f"for {', '.join(t['items'])} at {units.fmt(t['price_per_item_drops'])} per item")
            # Each member's agent answers from that member's own consent; the institution asks for every
            # item in the contract and gets only what each member agreed to.
            out = [{"person": m["pid"], **self._send_week(cid, m["pid"], week, list(t["items"]))} for m in members]
            for m in members:
                self.sync_uniqdata(cid, m["pid"])
            summary = {s: sum(1 for r in out if r["status"] == s) for s in {r["status"] for r in out}}
            with self.store.tx() as c:
                c.execute("INSERT INTO contract_rounds (contract_id,week,started_at,result) VALUES (?,?,?,?)",
                          (cid, week, time.time(), json.dumps(summary)))
        return {"contract": cid, "week": week, "members": len(members), "summary": summary, "results": out}

    def _send_week(self, cid: str, pid: str, week: int, items: list[str]) -> dict:
        t = self.terms(cid)
        pa = self._person(pid)
        d = pa.handle_request(t["institution_id"], t["purpose"], items, week, t["price_per_item_drops"])
        if not d.ok:
            return {"status": d.status, "reason": d.reason}
        req = OrderRequest(t["institution_id"], pid, pid, "personal.weekly", f"{pid}|week{week}", t["purpose"],
                           d.granted, t["price_per_item_drops"] * len(d.granted), pa.vault.extract(d.granted, week), d,
                           settle="escrow")
        try:
            oid = self.engine.place_order(req)
        except (BudgetExceeded, NeedsHumanApproval) as e:
            return {"status": "budget", "reason": str(e)}
        self.engine.process(oid)
        self._pay(cid, pid, oid)
        return self._order_view(oid)

    # ---------- AP4M: one payment per delivered member-week ----------

    def _rail(self, cid: str) -> str:
        return self.terms(cid).get("payment_rail", "ledger")

    def _pay(self, cid: str, pid: str, oid: int) -> dict | None:
        """Pay a delivered order through AP4M. Idempotent on the order (the rail is too, on ref); a failed
        or capped payment is recorded as unpaid, shown as such, and tried again at the next round."""
        if self._rail(cid) != "ap4m":
            return None
        o = self.store.one("SELECT status, price_drops, scope FROM orders WHERE id=?", oid)
        if o is None or o["status"] != "delivered":
            return None
        done = self.store.one("SELECT * FROM contract_payments WHERE order_id=?", oid)
        if done is not None and done["ok"]:
            return json.loads(done["result"])
        ref = f"rc-{cid}-{oid}"
        slot = json.loads(o["scope"])["slot"]
        to = self._member(cid, pid)["payout_address"]
        try:
            from . import ap4m_rail
            res = ap4m_rail.pay(ref, int(o["price_drops"]), {"contract": cid, "member": pid, "order": oid,
                                                            "week": int(slot.rsplit("week", 1)[-1])}, forward_to=to, pool="research")
        except Exception as e:                  # the rail is down or not installed: the order stays unpaid
            res = {"ok": False, "reason": f"ap4m rail error: {str(e)[:160]}"}
        res = {**res, "ref": ref, "forward_to": to}
        with self.store.tx() as c:
            c.execute("INSERT INTO contract_payments VALUES (?,?,?,?,?,?,?,?,1,?) ON CONFLICT(order_id) DO UPDATE SET "
                      "ok=excluded.ok, result=excluded.result, attempts=contract_payments.attempts+1, "
                      "updated_at=excluded.updated_at",
                      (oid, cid, pid, "ap4m", ref, int(o["price_drops"]), 1 if res.get("ok") else 0,
                       json.dumps(res), time.time()))
        if res.get("ok"):
            self.store.log(pid, "ap4m_paid", f"{pid}: {units.fmt(o['price_drops'])} paid through AP4M for {slot}",
                           {"order": oid, "receipt": res.get("receipt_url"), "voucher_tx": res.get("voucher_redeemed_tx")})
        else:
            self.store.log(pid, "ap4m_unpaid", f"{pid}: {slot} delivered, AP4M payment not made ({res.get('reason')})")
        return res

    def retry_payments(self, cid: str) -> int:
        """Delivered orders whose AP4M payment did not go through (cap, rail down): try them again."""
        if self._rail(cid) != "ap4m":
            return 0
        t = self.terms(cid)
        rows = self.store.q("SELECT o.id, o.seller_id FROM orders o LEFT JOIN contract_payments cp ON cp.order_id=o.id "
                            "WHERE o.buyer_id=? AND o.status='delivered' AND (cp.ok IS NULL OR cp.ok=0) ORDER BY o.id",
                            t["institution_id"])
        return sum(1 for r in rows if (self._pay(cid, r["seller_id"], r["id"]) or {}).get("ok"))

    def _payment(self, oid: int, rail: str, status: str, amount: int) -> dict:
        if rail != "ap4m":
            return {"rail": "xrpl_escrow", "status": "paid" if status == "delivered" else
                    ("held" if status in ("escrowed", "paid", "reserved") else "not_paid"), "amount_drops": amount}
        p = self.store.one("SELECT * FROM contract_payments WHERE order_id=?", oid)
        r = json.loads(p["result"]) if p else {}
        state = "paid" if p and p["ok"] else ("unpaid" if status == "delivered" else "not_due")
        fwd = r.get("forward_tx")
        return {"rail": "ap4m", "status": state, "amount_drops": amount,
                "payee": f"the member's wallet {r.get('forward_to') or ''}".strip() if fwd else AP4M_PAYEE,
                "forward": {"tx": fwd, "url": r.get("forward_url")},
                "reason": None if state != "unpaid" else (r.get("reason") or "not attempted yet"),
                "claim_id": r.get("claim_id"), "receipt_url": r.get("receipt_url"),
                "voucher_redeemed": {"tx": r.get("voucher_redeemed_tx"), "url": r.get("voucher_url")},
                "settlement_tx": r.get("settlement_tx"), "verified": r.get("verified")}

    def action_message(self, pid: str, cid: str, action: str) -> bytes:
        """What the member's key signs for one approval or a withdrawal: a fresh signature each time,
        bound to this member, this contract and the consent they signed."""
        m = self._member(cid, pid)
        return consent_message(pid, sha256_hex(f"{action}|{cid}|{m['consent_hash']}"))

    def _member(self, cid: str, pid: str):
        m = self.store.one("SELECT * FROM contract_members WHERE contract_id=? AND pid=?", cid, pid)
        if m is None:
            raise KeyError(f"{pid} in {cid}")
        return m

    def _check_signature(self, cid: str, pid: str, action: str, signature: str | None):
        if not verify_ed25519(self._member(cid, pid)["public_hex"], self.action_message(pid, cid, action),
                              signature or ""):
            raise PermissionError("this needs a fresh signature from your key")

    def approve(self, pid: str, cid: str, rid: int, items: list[str], signature: str | None) -> dict:
        """The member confirms a week (or more items) themself; the order then goes out at once."""
        t = self.terms(cid)
        pa = self._person(pid)
        self._check_signature(cid, pid, f"approve:{rid}:{','.join(sorted(items))}", signature)
        r = self.store.one("SELECT * FROM approval_requests WHERE id=? AND person_id=? AND buyer_id=?",
                           rid, pid, t["institution_id"])
        if r is None or r["status"] != "open":
            raise KeyError(f"request {rid}")
        with self._lock:
            pa.approve(rid, items)
            if r["week"] is None:
                return {"approved": items}
            order = self._send_week(cid, pid, r["week"], list(t["items"]))        # pays, if AP4M
            self.sync_uniqdata(cid, pid)
            return {"approved": items, "order": order}

    def withdraw(self, pid: str, cid: str, signature: str | None) -> dict:
        """Revoke: no key is published for rounds not yet paid, so those escrows go back to the institution
        at their deadline. Payments already made stay with the member. On the AP4M rail nothing is paid
        before delivery, so a withdrawal has nothing to refund: later weeks are simply never paid."""
        self._check_signature(cid, pid, "withdraw", signature)
        if self._member(cid, pid)["status"] == "withdrawn":
            raise ContractError("already withdrawn")
        t = self.terms(cid)
        iid = t["institution_id"]
        pa = self._person(pid)
        with self._lock:
            pa.revoke(iid)
            held = self.store.q("SELECT id, order_key FROM orders WHERE buyer_id=? AND seller_id=? AND status IN "
                                "('reserved','escrowed','paid')", iid, pid)
            for o in held:
                pa.keyring.forget(o["order_key"])
                self.engine.process(o["id"])       # the agent re-checks: consent revoked, so no key goes out
            with self.store.tx() as c:
                c.execute("UPDATE contract_members SET status='withdrawn', withdrawn_at=? WHERE contract_id=? AND pid=?",
                          (time.time(), cid, pid))
        self.engine.sweep()
        self.sync_uniqdata(cid, pid)
        return {**self.member_view(pid), "withheld_orders": [o["id"] for o in held]}

    def close(self, cid: str) -> dict:
        with self.store.tx() as c:
            c.execute("UPDATE research_contracts SET status='closed', closed_at=? WHERE id=?", (time.time(), cid))
        return self.public(cid)

    # ---------- UniQdata: the member's payments, in their own account ----------

    STATUS = {"delivered": "settled", "escrowed": "held", "paid": "held", "reserved": "held",
              "withheld": "withheld", "blocked": "withheld", "refunded": "refunded", "cancelled": "refunded"}

    def settlement_records(self, cid: str, pid: str) -> list[dict]:
        """The member's orders in this contract as UniQdata settlement records. Amounts are the server's,
        one record per order, so a held escrow that finishes later updates the same record."""
        t, m = self.terms(cid), self._member(cid, pid)
        ap4m = t.get("payment_rail") == "ap4m"
        out = []
        for r in self.store.q("SELECT id FROM orders WHERE buyer_id=? AND seller_id=? ORDER BY id", t["institution_id"], pid):
            o = self._order_view(r["id"])
            status = self.STATUS.get(o["status"])
            if status is None:
                continue                                    # a status this port does not know is never reported
            if status == "withheld" and o["escrow_cancel"]["tx"]:
                status = "refunded"
            if ap4m and status == "settled" and o["payment"]["status"] != "paid":
                status = "held"                             # delivered, AP4M payment still to go through
            out.append({"contract_id": cid, "consent_hash": m["consent_hash"], "order_ref": f"order-{o['order_id']}",
                        "institution": t["institution"], "study_title": t["title"],
                        "period": "week " + o["slot"].rsplit("week", 1)[-1], "amount_micro": o["amount_drops"],
                        "asset": units.UNIT, "display_unit": units.DISPLAY,
                        "network": "testnet" if ap4m else self.ledger.name, "status": status,
                        # XRPL L1 escrow hashes; an AP4M payment is on XRPL EVM and has its own receipt, not these
                        "escrow_create_tx": None if ap4m else o["escrow_create"]["tx"],
                        "escrow_finish_tx": None if ap4m else o["escrow_finish"]["tx"],
                        "escrow_cancel_tx": None if ap4m else o["escrow_cancel"]["tx"],
                        "contract_status": "withdrawn" if m["status"] == "withdrawn" else "active"})
        return out

    def sync_uniqdata(self, cid: str, pid: str) -> dict | None:
        """Push the member's payments to their UniQdata account. Only members who joined with a UniQdata
        account, and only from a test network (UniQdata keeps this record for dev chains only)."""
        m = self._member(cid, pid)
        test_net = self.ledger.name in ("testnet", "devnet") or self._rail(cid) == "ap4m"
        if not m["data_source"].startswith("uniqdata:") or not test_net:
            return None
        recs = self.settlement_records(cid, pid)
        if not recs:
            return None
        client = self.uniqdata[m["data_source"].split(":", 1)[1]]
        try:
            out = client.report_settlements(recs)
        except Exception as e:                      # the trade stands; the next sync reports it again
            self.store.log(pid, "uniqdata_sync_failed", f"{pid}: settlement report to UniQdata failed ({str(e)[:120]})")
            return None
        self.store.log(pid, "uniqdata_sync", f"{pid}: {out.get('written', 0)} settlement records in UniQdata")
        return out

    # ---------- views ----------

    def _order_view(self, oid: int) -> dict:
        o = self.store.one("SELECT o.id, o.status, o.price_drops, o.scope, o.buyer_id, p.tx_hash, p.finish_tx, "
                           "p.cancel_tx FROM orders o LEFT JOIN payments p ON p.order_id=o.id WHERE o.id=?", oid)
        url = lambda h: self.ledger.explorer_url(h) if h else None
        c = self.store.one("SELECT terms FROM research_contracts WHERE institution_id=?", o["buyer_id"])
        rail = json.loads(c["terms"]).get("payment_rail", "ledger") if c else "ledger"
        return {"order_id": oid, "status": o["status"], "amount_drops": o["price_drops"],
                "slot": json.loads(o["scope"])["slot"], "granted": json.loads(o["scope"])["granted"],
                "payment": self._payment(oid, rail, o["status"], o["price_drops"]),
                "escrow_create": {"tx": o["tx_hash"], "url": url(o["tx_hash"])},
                "escrow_finish": {"tx": o["finish_tx"], "url": url(o["finish_tx"])},
                "escrow_cancel": {"tx": o["cancel_tx"], "url": url(o["cancel_tx"])}}

    def console(self, cid: str) -> dict:
        """The researcher's view: members by contract number only, every order with its ledger links."""
        t = self.terms(cid)
        members = [{"pid": m["pid"], "items": json.loads(m["items"]), "automation": m["automation"],
                    "data_source": m["data_source"].split(":")[0], "status": m["status"]}
                   for m in self.store.q("SELECT * FROM contract_members WHERE contract_id=? ORDER BY joined_at", cid)]
        orders = [self._order_view(r["id"]) for r in
                  self.store.q("SELECT id FROM orders WHERE buyer_id=? ORDER BY id", t["institution_id"])]
        rounds = [{"week": r["week"], "at": r["started_at"], "summary": json.loads(r["result"])}
                  for r in self.store.q("SELECT * FROM contract_rounds WHERE contract_id=? ORDER BY id", cid)]
        paid = [o for o in orders if o["payment"]["status"] == "paid"]
        unpaid = [o for o in orders if o["payment"]["status"] == "unpaid"]
        return {**self.public(cid), "member_list": members, "orders": orders, "rounds": rounds,
                "payments": {"rail": t.get("payment_rail", "ledger"), "paid_count": len(paid),
                             "paid_drops": sum(o["amount_drops"] for o in paid), "unpaid_count": len(unpaid),
                             "unpaid_drops": sum(o["amount_drops"] for o in unpaid)}}

    @staticmethod
    def _latest_tx(orders: list[dict]) -> dict | None:
        for o in reversed(orders):
            v = o["payment"].get("voucher_redeemed") or {}
            if v.get("tx"):
                return {**v, "receipt_url": o["payment"].get("receipt_url"), "rail": "ap4m"}
            if o["payment"]["rail"] != "ap4m" and o["escrow_finish"]["tx"]:
                return o["escrow_finish"]
        return None

    def member_view(self, pid: str) -> dict:
        """One member's contracts in the shape the UniQdata 연구 기여 tab reads: proposals waiting for them,
        contracts with each institution, payments with their ledger links. Amounts are server totals."""
        rows = self.store.q("SELECT * FROM contract_members WHERE pid=?", pid)
        if not rows:
            raise KeyError(pid)
        contracts, history = [], []
        for m in rows:
            t = self.terms(m["contract_id"])
            iid = t["institution_id"]
            orders = [self._order_view(r["id"]) for r in
                      self.store.q("SELECT id FROM orders WHERE buyer_id=? AND seller_id=? ORDER BY id", iid, pid)]
            # paid = what reached the payee on the contract's rail; held = escrowed, or delivered and the
            # AP4M payment still to go through
            settled = sum(o["amount_drops"] for o in orders if o["payment"]["status"] == "paid")
            held = sum(o["amount_drops"] for o in orders if o["payment"]["status"] in ("held", "unpaid")
                       or o["status"] in ("escrowed", "paid", "reserved"))
            asks = [{"request_id": r["id"], "week": r["week"], "kind": r["kind"], "items": json.loads(r["items"]),
                     "price_per_item_drops": r["offered_price_drops"]}
                    for r in self.store.q("SELECT * FROM approval_requests WHERE person_id=? AND buyer_id=? AND "
                                          "status='open' ORDER BY id", pid, iid)]
            contracts.append({"contract": m["contract_id"], "title": t["title"], "institution": t["institution"],
                              "institution_verified": "ethics credential on ledger (IRB number declared by the researcher)",
                              "items": json.loads(m["items"]), "automation": m["automation"], "status": m["status"],
                              "consent_hash": m["consent_hash"], "pending_approvals": asks,
                              "payment_rail": t.get("payment_rail", "ledger"),
                              "settled_drops": settled, "held_drops": held,
                              "latest_tx": self._latest_tx(orders)})
            for o in orders:
                history.append({"contract": m["contract_id"], "institution": t["institution"], "study": t["title"], **o})
        return {"person": pid, "unit": units.UNIT, "display_unit": units.DISPLAY, "ledger": self.ledger.name,
                "active_institutions": len({c["institution"] for c in contracts if c["status"] == "active"}),
                "settled_drops": sum(c["settled_drops"] for c in contracts),
                "held_drops": sum(c["held_drops"] for c in contracts),
                "contracts": contracts, "history": history}
