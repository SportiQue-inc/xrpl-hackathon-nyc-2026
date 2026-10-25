"""SQLite store. Every state change that moves money or data goes through
`tx()`, which takes a write lock up front (BEGIN IMMEDIATE) so budget
reservations and order creation are serialized across threads/processes."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS parties (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
  address TEXT, box_pubkey TEXT
);
CREATE TABLE IF NOT EXISTS mandates (
  buyer_id TEXT PRIMARY KEY, total_drops INTEGER NOT NULL,
  spent_drops INTEGER NOT NULL DEFAULT 0, reserved_drops INTEGER NOT NULL DEFAULT 0,
  per_order_limit_drops INTEGER NOT NULL, purposes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consents (
  person_id TEXT NOT NULL, buyer_id TEXT NOT NULL, purpose TEXT NOT NULL,
  items TEXT NOT NULL, period_from INTEGER NOT NULL, period_to INTEGER NOT NULL,
  automation TEXT NOT NULL, min_price_drops INTEGER NOT NULL,
  status TEXT NOT NULL, version INTEGER NOT NULL,
  doc TEXT NOT NULL, doc_hash TEXT NOT NULL,
  PRIMARY KEY (person_id, buyer_id)
);
CREATE TABLE IF NOT EXISTS consent_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL, buyer_id TEXT NOT NULL,
  version INTEGER NOT NULL, status TEXT NOT NULL, doc TEXT NOT NULL, doc_hash TEXT NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS approval_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL, buyer_id TEXT NOT NULL,
  kind TEXT NOT NULL, week INTEGER, items TEXT NOT NULL, offered_price_drops INTEGER NOT NULL, status TEXT NOT NULL,
  decided_items TEXT, created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_key TEXT NOT NULL UNIQUE, content_hash TEXT NOT NULL,
  buyer_id TEXT NOT NULL, seller_id TEXT NOT NULL, payee_id TEXT NOT NULL,
  product_id TEXT NOT NULL, scope TEXT NOT NULL, purpose TEXT NOT NULL,
  price_drops INTEGER NOT NULL, bundle_hash TEXT NOT NULL,
  policy_snapshot TEXT NOT NULL, status TEXT NOT NULL, note TEXT,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS bundles (
  order_id INTEGER PRIMARY KEY, bundle_hash TEXT NOT NULL, sealed BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
  order_id INTEGER PRIMARY KEY, payee_address TEXT NOT NULL, amount_drops INTEGER NOT NULL,
  invoice_id TEXT NOT NULL, tx_hash TEXT, tx_blob TEXT, status TEXT NOT NULL,
  ledger_index INTEGER, updated_at REAL NOT NULL,
  kind TEXT NOT NULL DEFAULT 'payment', condition TEXT, offer_sequence INTEGER, cancel_after INTEGER,
  finish_tx TEXT, finish_blob TEXT, cancel_tx TEXT, cancel_blob TEXT
);
CREATE TABLE IF NOT EXISTS escrow_keys (
  order_id INTEGER PRIMARY KEY, key_hex TEXT NOT NULL   -- held by the contributor's agent until it finishes
);
CREATE TABLE IF NOT EXISTS deliveries (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
  bundle_hash TEXT NOT NULL, attempt INTEGER NOT NULL, acked INTEGER NOT NULL, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, kind TEXT NOT NULL,
  status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
  UNIQUE (order_id, kind)
);
CREATE TABLE IF NOT EXISTS exceptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, kind TEXT NOT NULL,
  detail TEXT NOT NULL, cost_bearer TEXT, ts REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS mandate_actions (
  order_id INTEGER PRIMARY KEY, l1 TEXT NOT NULL, l2 TEXT NOT NULL, l3 TEXT NOT NULL, hash TEXT NOT NULL,
  verdict TEXT, reason TEXT
);
CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, scene TEXT, agent TEXT NOT NULL, task TEXT NOT NULL,
  source TEXT NOT NULL, input TEXT, proposal TEXT, verdict TEXT NOT NULL, final TEXT, notes TEXT, hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, scene TEXT,
  actor TEXT NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL, data TEXT
);
"""


class Store:
    """Thin wrapper; one connection per thread, shared file."""

    def __init__(self, path: str = ":memory:"):
        # Several threads need their own connections, so ":memory:" means a throwaway file.
        if path == ":memory:":
            fd, path = tempfile.mkstemp(prefix="agentrail-", suffix=".db")
            os.close(fd)
        self.path = path
        self._local = threading.local()
        self._keepalive = self._connect()
        self._keepalive.executescript(SCHEMA)
        self.scene = None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, uri=self.path.startswith("file:"),
                               isolation_level=None, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        if not self.path.startswith("file:"):
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @property
    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = self._local.conn = self._connect()
        return c

    @contextmanager
    def tx(self):
        c = self.conn
        c.execute("BEGIN IMMEDIATE")
        try:
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise

    def q(self, sql: str, *args) -> list[sqlite3.Row]:
        return self.conn.execute(sql, args).fetchall()

    def one(self, sql: str, *args):
        r = self.conn.execute(sql, args).fetchone()
        return r

    def log(self, actor: str, kind: str, message: str, data: dict | None = None):
        self.conn.execute(
            "INSERT INTO events (ts, scene, actor, kind, message, data) VALUES (?,?,?,?,?,?)",
            (time.time(), self.scene, actor, kind, message, json.dumps(data or {}, sort_keys=True)),
        )
