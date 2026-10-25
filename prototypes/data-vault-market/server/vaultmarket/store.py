"""SQLite store. One file, one lock: the market loop and the web handlers share it."""
from __future__ import annotations

import json
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY, name TEXT, type TEXT, address TEXT, pid TEXT, trust REAL, verified INT,
  sell_agent TEXT, buy_agent TEXT, online INT DEFAULT 1, created REAL);
CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, kind TEXT, name TEXT, raw TEXT, clean TEXT,
  status TEXT,             -- private | listed | locked | bought
  fps TEXT, sig TEXT, source TEXT, derived_from TEXT, sold INT DEFAULT 0, resale INT DEFAULT 0, bytes INT, created REAL);
CREATE TABLE IF NOT EXISTS postings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, buyer TEXT, kind TEXT, offer REAL, max REAL, purpose TEXT, lot INT,
  min_trust REAL, resale INT, status TEXT, once INT, settled INT DEFAULT 0, rejected INT DEFAULT 0, created REAL);
CREATE TABLE IF NOT EXISTS interests (account TEXT, posting INT, created REAL, PRIMARY KEY (account, posting));
CREATE TABLE IF NOT EXISTS contracts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, posting INT, buyer TEXT, kind TEXT, status TEXT, reason TEXT,
  total REAL, items INT, sellers TEXT, trace TEXT, created REAL);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, contract INT, speaker TEXT, side TEXT, text TEXT, thinking TEXT, created REAL);
CREATE TABLE IF NOT EXISTS txs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, contract INT, type TEXT, hash TEXT, src TEXT, dst TEXT, drops INT,
  result TEXT, created REAL);
CREATE TABLE IF NOT EXISTS uploads (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, name TEXT, verdict TEXT, why TEXT, fee REAL, file INT, created REAL);
CREATE TABLE IF NOT EXISTS chat (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, role TEXT, text TEXT, actions TEXT, done INT DEFAULT 0, created REAL);
CREATE TABLE IF NOT EXISTS recs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT, kind TEXT, text TEXT, status TEXT, created REAL);
CREATE TABLE IF NOT EXISTS ledger_stats (k TEXT PRIMARY KEY, v REAL);
CREATE TABLE IF NOT EXISTS users (
  username TEXT PRIMARY KEY, pw TEXT, salt TEXT, account TEXT,
  wallet TEXT, wallet_tag INT, wallet_tx TEXT,   -- personal XRPL wallet; verified when wallet_tx is set
  created REAL);
CREATE TABLE IF NOT EXISTS prices (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, price REAL, contract INT, created REAL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, created REAL);
"""


class Store:
    def __init__(self, path: str):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.executescript(SCHEMA)
            cols = {r[1] for r in self.db.execute("PRAGMA table_info(accounts)")}
            if "payout" not in cols:          # databases from before signup
                self.db.execute("ALTER TABLE accounts ADD COLUMN payout TEXT")

    def q(self, sql: str, args=()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def one(self, sql: str, args=()) -> dict | None:
        r = self.q(sql, args)
        return r[0] if r else None

    def x(self, sql: str, args=()) -> int:
        with self.lock:
            return self.db.execute(sql, args).lastrowid

    def insert(self, table: str, **kw) -> int:
        kw.setdefault("created", time.time())
        for k, v in kw.items():
            if isinstance(v, (dict, list)):
                kw[k] = json.dumps(v)
        cols = ",".join(kw)
        return self.x(f"INSERT INTO {table} ({cols}) VALUES ({','.join('?' * len(kw))})", tuple(kw.values()))

    def bump(self, k: str, by: float = 1):
        self.x("INSERT INTO ledger_stats (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = v + ?", (k, by, by))

    def stat(self, k: str) -> float:
        r = self.one("SELECT v FROM ledger_stats WHERE k = ?", (k,))
        return r["v"] if r else 0
