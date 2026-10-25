"""Withdrawal as a ledger event, live on the researcher's screen.

On Testnet a background thread holds one WebSocket `subscribe` (accounts stream) on the study's account.
Every validated Clawback of the study's licence and every EscrowCancel of its escrows arrives here
within seconds of the ledger closing; the page asks for new ones every second and greys the person's
row. The provider is whatever XRPL_WS_URL points at (a QuickNode endpoint in the demo; the public
Testnet server otherwise), and the label says which.

On the mock ledger there is no stream: the same events are read from the mock's own transaction list,
labelled as such.
"""
from __future__ import annotations

import os
import threading
import time
from urllib.parse import urlparse

RIPPLE_EPOCH = 946684800
WATCH = ("Clawback", "EscrowCancel")
DEFAULT_WS = "wss://s.altnet.rippletest.net:51233/"


def ws_url() -> str:
    return os.environ.get("XRPL_WS_URL") or DEFAULT_WS


def provider(url: str) -> str:
    host = urlparse(url).hostname or url
    return "QuickNode" if "quiknode" in host or "quicknode" in host else host


class LiveFeed:
    def __init__(self, w):
        self.w = w
        self.events: list[dict] = []
        self.status = "not started"
        self._lock = threading.Lock()
        self._thread = None

    # ---- who is this about ----
    def _person(self, tx: dict) -> str | None:
        st = self.w.store
        if tx.get("TransactionType") == "Clawback":
            r = st.one("SELECT id FROM parties WHERE address=?", tx.get("Account"))
            return r["id"] if r else None
        r = st.one("SELECT o.seller_id FROM payments p JOIN orders o ON o.id=p.order_id WHERE p.offer_sequence=? "
                   "AND p.kind='escrow'", tx.get("OfferSequence"))
        return r["seller_id"] if r else None

    def _add(self, tx: dict, h: str, closed_at: float | None, source: str):
        received = time.time()
        with self._lock:
            if any(e["tx"] == h for e in self.events):
                return
            self.events.append({
                "id": len(self.events) + 1, "type": tx.get("TransactionType"), "tx": h,
                "url": self.w.ledger.explorer_url(h), "person": self._person(tx), "received_at": received,
                "ledger_closed_at": closed_at,
                "latency_s": round(received - closed_at, 1) if closed_at else None, "source": source})

    # ---- Testnet stream ----
    def start(self):
        if self._thread or self.w.ledger.name != "testnet":
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="ledger-stream")
        self._thread.start()

    def _run(self):
        from xrpl.clients import WebsocketClient
        from xrpl.models.requests import Subscribe
        lab = self.w.engine.party("org_sleeplab")["address"]
        url = ws_url()
        src = f"WebSocket subscribe ({provider(url)})"
        while True:
            try:
                with WebsocketClient(url) as c:
                    c.send(Subscribe(accounts=[lab]))
                    self.status = f"subscribed: {src}"
                    for msg in c:
                        if msg.get("type") != "transaction" or not msg.get("validated"):
                            continue
                        tx = msg.get("tx_json") or msg.get("transaction") or {}
                        if tx.get("TransactionType") not in WATCH:
                            continue
                        if msg.get("meta", {}).get("TransactionResult") != "tesSUCCESS":
                            continue
                        date = tx.get("date")
                        closed = date + RIPPLE_EPOCH if isinstance(date, int) else None
                        if closed is None and msg.get("close_time_iso"):
                            from datetime import datetime
                            closed = datetime.fromisoformat(msg["close_time_iso"].replace("Z", "+00:00")).timestamp()
                        self._add(tx, msg.get("hash") or tx.get("hash"), closed, src)
            except Exception as e:                      # reconnect; the page shows the state
                self.status = f"reconnecting ({type(e).__name__})"
                time.sleep(3)

    # ---- mock ----
    def _poll_mock(self):
        L = self.w.ledger
        for h, t in list(getattr(L, "txs", {}).items()):
            if t.get("TransactionType") in WATCH and t.get("result") == "tesSUCCESS":
                self._add(t, h, None, "mock ledger (no stream)")

    def since(self, after: int = 0) -> dict:
        if self.w.ledger.name == "mock":
            self._poll_mock()
            self.status = "mock ledger: events read from its transaction list"
        else:
            self.start()
        with self._lock:
            return {"status": self.status, "events": [e for e in self.events if e["id"] > after]}


def feed(w) -> LiveFeed:
    f = w.__dict__.get("live_feed")
    if f is None:
        f = w.__dict__["live_feed"] = LiveFeed(w)
    return f
