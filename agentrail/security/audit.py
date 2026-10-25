"""Tamper-evident event log.

Every row of `events` carries hash = sha256(prev_hash | row) (written atomically by Store.log), so
editing, deleting or reordering any past row breaks verification from that row on. The head hash is
anchored on the ledger in a memo (AccountSet from the operator's account), so a rewrite of the whole
chain is caught too: the anchored hash must still be in the chain at the anchored row.
"""
from __future__ import annotations

import threading
import time

from ..db import _chain_hash, event_body

ANCHOR_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_anchors (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, head_hash TEXT NOT NULL,
  tx_hash TEXT, ts REAL NOT NULL
);
"""


def verify_chain(store) -> dict:
    prev, n = None, 0
    for r in store.q("SELECT id, ts, scene, actor, kind, message, data, prev_hash, hash FROM events ORDER BY id"):
        if r["prev_hash"] != prev:
            return {"ok": False, "broken_at": r["id"], "reason": "row does not point at the previous row", "checked": n}
        if _chain_hash(prev, event_body(r["ts"], r["scene"], r["actor"], r["kind"], r["message"], r["data"])) != r["hash"]:
            return {"ok": False, "broken_at": r["id"], "reason": "row content changed after it was written", "checked": n}
        prev, n = r["hash"], n + 1
    anchors = [dict(a) for a in store.q("SELECT * FROM audit_anchors ORDER BY id")]
    for a in anchors:
        row = store.one("SELECT hash FROM events WHERE id=?", a["event_id"])
        if row is None or row["hash"] != a["head_hash"]:
            return {"ok": False, "broken_at": a["event_id"], "reason": "an anchored hash is no longer in the chain",
                    "checked": n}
    return {"ok": True, "checked": n, "head": prev, "anchors": len(anchors),
            "last_anchor": anchors[-1] if anchors else None}


def anchor(w) -> dict:
    """Put the current head hash on the ledger. Only hashes leave: no event content."""
    st = w.store
    head = st.one("SELECT id, hash FROM events ORDER BY id DESC LIMIT 1")
    if head is None:
        return {"ok": False, "message": "empty log"}
    last = st.one("SELECT event_id FROM audit_anchors ORDER BY id DESC LIMIT 1")
    if last and last["event_id"] == head["id"]:
        return {"ok": True, "message": "already anchored", "event_id": head["id"]}
    memo = f"agentrail-audit|{head['id']}|{head['hash']}"
    h = _anchor_tx(w.ledger, w.engine.relay, memo)
    with st.tx() as c:
        c.execute("INSERT INTO audit_anchors (event_id, head_hash, tx_hash, ts) VALUES (?,?,?,?)",
                  (head["id"], head["hash"], h, time.time()))
    st.log("operator", "audit_anchor", f"event log head {head['hash'][:16]} (row {head['id']}) anchored on the ledger",
           {"tx_hash": h, "url": w.ledger.explorer_url(h)})
    return {"ok": True, "event_id": head["id"], "head_hash": head["hash"], "tx": h, "url": w.ledger.explorer_url(h)}


def _anchor_tx(ledger, account: str, memo: str) -> str:
    if ledger.name != "testnet":
        return ledger._fake_tx("AccountSet", Account=account, Memo=memo)
    from xrpl.models.transactions import AccountSet, Memo
    from xrpl.transaction import submit_and_wait
    from ..ledger.xrpl_extras import _check
    r = submit_and_wait(AccountSet(account=account, memos=[Memo(memo_type=b"agentrail/audit".hex().upper(),
                                                                 memo_data=memo.encode().hex().upper())]),
                        ledger.client, ledger.wallets[account])
    with getattr(ledger, "_seq_lock", threading.Lock()):
        getattr(ledger, "_seq", {}).pop(account, None)     # autofill used the account's sequence
    return _check(r, "AccountSet audit anchor")


class Anchorer:
    """Anchors the head every `interval` seconds while the server runs (skips when nothing changed)."""

    def __init__(self, get_world, interval: float, lock):
        self.get_world, self.interval, self.lock = get_world, interval, lock
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._run, daemon=True, name="audit-anchor").start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.wait(self.interval):
            try:
                w = self.get_world()
                with self.lock:
                    anchor(w)
            except Exception:
                pass
