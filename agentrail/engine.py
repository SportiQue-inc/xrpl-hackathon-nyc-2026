r"""Common trade engine: order -> budget reservation -> XRPL payment -> permission
re-check -> sealed delivery. Same code for organization and personal data.

State machine of an order:
  reserved --pay validated--> paid --delivered+ack--> delivered
     |                           \--consent revoked--> withheld (payment kept, exception)
     \--policy blocks before pay / payment failed--> blocked | failed (reservation released)

Every side effect is driven from the outbox, so `recover()` after a restart
finishes whatever was in flight without paying twice.
"""
from __future__ import annotations

import hashlib
import os
import json
import re
import sqlite3
import time
from dataclasses import dataclass

from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox

from .db import Store
from .ledger import Ledger, LostResponse, Prepared
from .ledger.conditions import condition_hex, fulfillment_hex, key_from_fulfillment, new_key
from .policy import BuyerMandate, Decision


class OrderConflict(Exception):
    """Same order key, different content."""


class BudgetExceeded(Exception):
    pass


class NeedsHumanApproval(Exception):
    pass


class LostDelivery(Exception):
    pass


def sha256_hex(b: bytes | str) -> str:
    return hashlib.sha256(b.encode() if isinstance(b, str) else b).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class Inbox:
    """Buyer-side receiving endpoint. Dedupes by bundle hash; can lose acks."""

    def __init__(self):
        self.received: dict[int, tuple[str, bytes]] = {}
        self.lose_next_ack = False
        self.calls = 0

    def deliver(self, buyer_id: str, order_id: int, bundle_hash: str, sealed: bytes):
        self.calls += 1
        self.received[order_id] = (bundle_hash, sealed)
        if self.lose_next_ack:
            self.lose_next_ack = False
            raise LostDelivery("ack lost")


@dataclass
class OrderRequest:
    buyer_id: str
    seller_id: str          # agent/gate that provides the data
    payee_id: str           # who is paid (organization or the person)
    product_id: str
    slot: str               # e.g. "once" or "P017|week2"
    purpose: str
    granted: list[str]      # fields/items after policy
    price_drops: int
    rows: list[dict]        # the bundle content, fixed at order time
    decision: Decision
    settle: str = "payment"         # "payment" or "escrow" (paid only when the data key is published)
    escrow_window_s: int = 600      # CancelAfter = ledger time + window

    def content(self, bundle_hash: str) -> dict:
        return {"payee": self.payee_id, "granted": sorted(self.granted),
                "price": self.price_drops, "bundle": bundle_hash}


class Engine:
    def __init__(self, store: Store, ledger: Ledger, inbox: Inbox | None = None):
        self.store = store
        self.ledger = ledger
        self.inbox = inbox or Inbox()
        self.policies: dict[str, object] = {}   # seller/person id -> policy with evaluate()
        self.mandate_chains: dict[str, object] = {}   # buyer id -> mandate.MandateChain (owner-signed delegation)
        self.box_keys: dict[str, PrivateKey] = {}
        self.relay: str | None = None   # submits EscrowFinish for contributors whose keys we do not hold
        # Key separation (security/devices.py). A key holder is the participant's keyring: it creates
        # the escrow key K of each round and hands out only the fulfillment. An opener is the
        # institution's vault: it holds the box key bundles are sealed to. When registered, the
        # engine keeps neither K nor the private box key, only public keys and conditions.
        self.key_holders: dict[str, object] = {}
        self.openers: dict[str, object] = {}

    # ---------- setup ----------

    def add_party(self, pid: str, name: str, kind: str, address: str | None = None):
        key = self.box_keys.get(pid) or PrivateKey.generate()
        self.box_keys[pid] = key
        with self.store.tx() as c:
            c.execute("INSERT OR REPLACE INTO parties VALUES (?,?,?,?,?)",
                      (pid, name, kind, address, bytes(key.public_key).hex()))

    def register_public_key(self, pid: str, public_hex: str):
        """The party keeps its private box key; the engine stores only the public half."""
        self.box_keys.pop(pid, None)
        with self.store.tx() as c:
            c.execute("UPDATE parties SET box_pubkey=? WHERE id=?", (public_hex, pid))

    def set_mandate(self, m: BuyerMandate):
        with self.store.tx() as c:
            c.execute("""INSERT INTO mandates (buyer_id,total_drops,per_order_limit_drops,purposes)
                         VALUES (?,?,?,?) ON CONFLICT(buyer_id) DO UPDATE SET
                         total_drops=excluded.total_drops,
                         per_order_limit_drops=excluded.per_order_limit_drops,
                         purposes=excluded.purposes""",
                      (m.buyer_id, m.total_drops, m.per_order_limit_drops, json.dumps(m.purposes)))

    def available_drops(self, buyer_id: str) -> int:
        m = self.store.one("SELECT * FROM mandates WHERE buyer_id=?", buyer_id)
        return m["total_drops"] - m["spent_drops"] - m["reserved_drops"]

    def party(self, pid: str):
        return self.store.one("SELECT * FROM parties WHERE id=?", pid)

    # ---------- orders ----------

    def place_order(self, req: OrderRequest) -> int:
        """Idempotent. Returns the order id. Reserves budget atomically."""
        if not req.decision.ok:
            raise ValueError(f"policy did not grant anything: {req.decision.reason}")
        # Each round gets its own salt inside the sealed payload: the hash on the ledger cannot be matched
        # by guessing health values, and once the bundle is destroyed nothing links the hash to the data.
        rows_json = canonical({"rows": req.rows, "salt": os.urandom(16).hex()})
        bundle_hash = sha256_hex(rows_json)
        order_key = sha256_hex(f"{req.buyer_id}|{req.seller_id}|{req.product_id}|{req.slot}|{req.purpose}")
        content_hash = sha256_hex(canonical(req.content(sha256_hex(canonical(req.rows)))))   # off ledger: idempotency
        buyer_pub = PublicKey(bytes.fromhex(self.party(req.buyer_id)["box_pubkey"]))
        sealed = SealedBox(buyer_pub).encrypt(rows_json.encode())
        payee_addr = self.party(req.payee_id)["address"]
        data_key, condition = None, None
        holder = self.key_holders.get(req.seller_id)
        if req.settle == "escrow" and holder is not None:
            # K is created and kept by the contributor's keyring; the engine gets the lock and condition.
            sealed, condition = holder.lock(order_key, sealed)
        elif req.settle == "escrow":
            # Second lock: the bundle opens only with K, and K is what the escrow needs to pay out.
            data_key = new_key()
            sealed = SecretBox(data_key).encrypt(sealed)
            condition = condition_hex(data_key)

        conflict_with = None
        with self.store.tx() as c:
            ex = c.execute("SELECT id, content_hash FROM orders WHERE order_key=?", (order_key,)).fetchone()
            if ex and ex["content_hash"] == content_hash:
                self.store.log(req.buyer_id, "idempotent", f"order {ex['id']} already exists; returning it")
                return ex["id"]
            if ex:
                conflict_with = ex["id"]
                self.store.log(req.buyer_id, "conflict",
                               f"same order key as order {ex['id']} with different content: rejected")
        if conflict_with is not None:
            raise OrderConflict(f"order {conflict_with} exists with different content")
        with self.store.tx() as c:
            ex = c.execute("SELECT id, content_hash FROM orders WHERE order_key=?", (order_key,)).fetchone()
            if ex:  # created concurrently between the two transactions
                if ex["content_hash"] != content_hash:
                    raise OrderConflict(f"order {ex['id']} exists with different content")
                return ex["id"]
            m = c.execute("SELECT * FROM mandates WHERE buyer_id=?", (req.buyer_id,)).fetchone()
            if req.purpose not in json.loads(m["purposes"]):
                raise NeedsHumanApproval(f"purpose '{req.purpose}' not in mandate")
            if req.price_drops > m["per_order_limit_drops"]:
                raise NeedsHumanApproval(f"price {req.price_drops} above per-order limit")
            available = m["total_drops"] - m["spent_drops"] - m["reserved_drops"]
            if req.price_drops > available:
                raise BudgetExceeded(f"needs {req.price_drops} drops, {available} available")
            cur = c.execute(
                """INSERT INTO orders (order_key,content_hash,buyer_id,seller_id,payee_id,product_id,
                   scope,purpose,price_drops,bundle_hash,policy_snapshot,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (order_key, content_hash, req.buyer_id, req.seller_id, req.payee_id, req.product_id,
                 canonical({"slot": req.slot, "granted": sorted(req.granted)}), req.purpose,
                 req.price_drops, bundle_hash,
                 canonical({"status": req.decision.status, "version": req.decision.policy_version,
                            "refused": req.decision.refused, "pending": req.decision.pending}),
                 "reserved", time.time()))
            oid = cur.lastrowid
            c.execute("UPDATE mandates SET reserved_drops=reserved_drops+? WHERE buyer_id=?",
                      (req.price_drops, req.buyer_id))
            c.execute("INSERT INTO bundles VALUES (?,?,?)", (oid, bundle_hash, sealed))
            c.execute("""INSERT INTO payments (order_id,payee_address,amount_drops,invoice_id,status,updated_at,
                         kind,condition) VALUES (?,?,?,?,?,?,?,?)""",
                      (oid, payee_addr, req.price_drops, order_key.upper(), "pending", time.time(), req.settle,
                       condition))
            if data_key:
                c.execute("INSERT INTO escrow_keys VALUES (?,?)", (oid, data_key.hex()))
            if condition:
                c.execute("UPDATE payments SET cancel_after=? WHERE order_id=?",
                          (self.ledger.now() + req.escrow_window_s, oid))
            c.execute("INSERT INTO outbox (order_id,kind,status) VALUES (?,?,?)", (oid, "pay", "pending"))
            chain = self.mandate_chains.get(req.buyer_id)
            if chain is not None and chain.l2:
                # The agent signs this one order under the owner's delegation (Verifiable Intent L3).
                from .mandate import presentation_hash
                l3 = chain.sign_order({"content_hash": content_hash, "invoice_id": order_key.upper(),
                                       "amount_drops": req.price_drops, "payee_id": req.payee_id,
                                       "order_id": oid, "purpose": req.purpose})
                c.execute("INSERT INTO mandate_actions (order_id,l1,l2,l3,hash) VALUES (?,?,?,?,?)",
                          (oid, chain.l1, chain.l2, l3, presentation_hash(l3)))
            self.store.log(req.buyer_id, "order",
                           f"order {oid}: {req.product_id} [{', '.join(req.granted)}] "
                           f"{req.price_drops / 1e6:g} XRP reserved", {"order_id": oid, "slot": req.slot})
        return oid

    # ---------- outbox driver ----------

    def process(self, order_id: int, until: str | None = None) -> str:
        """Drive the order's outbox. `until="finish"` stops before the contributor publishes the key
        (the contributor's agent releases it at the end of the round)."""
        for _ in range(5):
            job = self.store.one("SELECT * FROM outbox WHERE order_id=? AND status='pending' ORDER BY id LIMIT 1",
                                 order_id)
            if not job:
                break
            kind = job["kind"]
            if kind == until:
                break
            escrow = self.store.one("SELECT kind FROM payments WHERE order_id=?", order_id)["kind"] == "escrow"
            if kind == "pay":
                done = self._escrow_create(order_id) if escrow else self._pay(order_id)
            elif kind == "deliver":
                done = self._deliver(order_id)
            elif kind == "finish":
                done = self._escrow_finish(order_id)
            else:
                done = self._escrow_cancel(order_id)
            if not done:
                break
        return self.store.one("SELECT status FROM orders WHERE id=?", order_id)["status"]

    def recover(self) -> list[int]:
        ids = [r["order_id"] for r in self.store.q("SELECT DISTINCT order_id FROM outbox WHERE status='pending'")]
        for oid in ids:
            self.store.log("engine", "recover", f"resuming order {oid} from outbox")
            self.process(oid)
        return ids

    def _recheck(self, o, for_delivery: bool) -> Decision:
        pol = self.policies[o["seller_id"]]
        scope = json.loads(o["scope"])
        week = None
        m = re.search(r"\|w(?:eek)?(\d+)", scope["slot"])
        if m:
            week = int(m.group(1))
        return pol.evaluate(buyer_id=o["buyer_id"], purpose=o["purpose"], fields=scope["granted"],
                            price_drops=o["price_drops"], week=week, for_delivery=for_delivery)

    def _mandate_check(self, o, p) -> tuple[bool, str, str]:
        """Verify the owner-signed delegation chain for this order right before money moves."""
        chain = self.mandate_chains.get(o["buyer_id"])
        if chain is None:
            return True, "", ""
        a = self.store.one("SELECT * FROM mandate_actions WHERE order_id=?", o["id"])
        if a is None:
            return False, "no signed order for this payment", ""
        from .mandate import verify
        m = self.store.one("SELECT spent_drops, reserved_drops FROM mandates WHERE buyer_id=?", o["buyer_id"])
        ok, why = verify(a["l1"], a["l2"], a["l3"], chain.issuer_pub,
                         {"content_hash": o["content_hash"], "invoice_id": p["invoice_id"],
                          "amount_drops": p["amount_drops"], "payee_id": o["payee_id"], "order_id": o["id"],
                          "purpose": o["purpose"]},
                         m["spent_drops"] + m["reserved_drops"] - o["price_drops"])
        with self.store.tx() as c:
            c.execute("UPDATE mandate_actions SET verdict=?, reason=? WHERE order_id=?",
                      ("ok" if ok else "refused", why, o["id"]))
        return ok, why, a["hash"]

    def _release(self, c, o, status: str, note: str):
        c.execute("UPDATE orders SET status=?, note=? WHERE id=?", (status, note, o["id"]))
        c.execute("UPDATE mandates SET reserved_drops=reserved_drops-? WHERE buyer_id=?",
                  (o["price_drops"], o["buyer_id"]))
        c.execute("UPDATE outbox SET status='done', last_error=? WHERE order_id=? AND kind='pay'",
                  (note, o["id"]))

    def _pay(self, oid: int) -> bool:
        o = self.store.one("SELECT * FROM orders WHERE id=?", oid)
        p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        if p["tx_hash"] is None:
            # Re-check permission right before money moves.
            d = self._recheck(o, for_delivery=False)
            if not d.ok:
                with self.store.tx() as c:
                    self._release(c, o, "blocked", d.reason)
                    self.store.log("engine", "blocked", f"order {oid} blocked before payment: {d.reason}")
                return False
            ok, why, mh = self._mandate_check(o, p)
            if not ok:
                with self.store.tx() as c:
                    self._release(c, o, "blocked", f"mandate check failed: {why}")
                    self.store.log("engine", "blocked", f"order {oid} blocked before payment: mandate check failed: {why}")
                return False
            buyer_addr = self.party(o["buyer_id"])["address"]
            pv = json.loads(o["policy_snapshot"]).get("version", "")
            memo = f"order:{oid}|bundle:{o['bundle_hash'][:16]}|terms:{pv}" + (f"|mandate:{mh}" if mh else "") + self._consent_tag(o)
            prep = self.ledger.prepare_payment(buyer_addr, p["payee_address"], p["amount_drops"],
                                               p["invoice_id"], memo)
            # Persist the signed tx BEFORE submitting: a lost response is then recoverable by hash.
            with self.store.tx() as c:
                c.execute("UPDATE payments SET tx_hash=?, tx_blob=?, status='submitted', updated_at=? WHERE order_id=?",
                          (prep.tx_hash, prep.blob, time.time(), oid))
            p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
            self._submit(oid, prep)

        st = self.ledger.wait_validated(p["tx_hash"])
        if not st.found:
            if self.ledger.is_expired(p["tx_blob"]):
                with self.store.tx() as c:
                    c.execute("UPDATE payments SET tx_hash=NULL, tx_blob=NULL, status='pending' WHERE order_id=?", (oid,))
                    self.store.log("engine", "expired", f"order {oid}: tx expired unapplied; will re-sign")
                return False
            # Same signed blob again: applies at most once on the ledger.
            self._submit(oid, Prepared(p["tx_hash"], p["tx_blob"]))
            st = self.ledger.wait_validated(p["tx_hash"])
        if not st.validated:
            with self.store.tx() as c:
                c.execute("UPDATE outbox SET attempts=attempts+1, last_error='not yet validated' "
                          "WHERE order_id=? AND kind='pay'", (oid,))
            return False
        with self.store.tx() as c:
            ok = (st.success and st.destination == p["payee_address"]
                  and st.amount_drops == p["amount_drops"]
                  and (st.invoice_id or "").upper() == (self.ledger.invoice_field_of(p["tx_blob"]) or "").upper())
            if not ok:
                self._release(c, o, "failed", "payment not successful on validated ledger")
                c.execute("UPDATE payments SET status='failed' WHERE order_id=?", (oid,))
                c.execute("INSERT INTO exceptions (order_id,kind,detail,cost_bearer,ts) VALUES (?,?,?,?,?)",
                          (oid, "payment_failed", "validated ledger shows failure or mismatch", None, time.time()))
                return False
            c.execute("UPDATE payments SET status='validated', ledger_index=?, updated_at=? WHERE order_id=?",
                      (st.ledger_index, time.time(), oid))
            c.execute("UPDATE orders SET status='paid' WHERE id=?", (oid,))
            c.execute("UPDATE mandates SET reserved_drops=reserved_drops-?, spent_drops=spent_drops+? "
                      "WHERE buyer_id=?", (o["price_drops"], o["price_drops"], o["buyer_id"]))
            c.execute("UPDATE outbox SET status='done' WHERE order_id=? AND kind='pay'", (oid,))
            c.execute("INSERT OR IGNORE INTO outbox (order_id,kind,status) VALUES (?,?,?)", (oid, "deliver", "pending"))
            via = " via x402 facilitator" if self.ledger.rail == "x402" else ""
            self.store.log("engine", "paid",
                           f"order {oid}: {o['price_drops'] / 1e6:g} XRP to {o['payee_id']}{via} "
                           f"validated in ledger {st.ledger_index}",
                           {"order_id": oid, "tx_hash": p["tx_hash"], "url": self.ledger.explorer_url(p["tx_hash"])})
        return True

    def _submit(self, oid: int, prep: Prepared):
        try:
            self.ledger.submit(prep)
        except LostResponse as e:
            self.store.log("engine", "lost_response",
                           f"order {oid}: submit response lost ({e}); will look up tx {prep.tx_hash[:12]}…")

    def _deliver(self, oid: int) -> bool:
        o = self.store.one("SELECT * FROM orders WHERE id=?", oid)
        d = self._recheck(o, for_delivery=True)
        if not d.ok:
            with self.store.tx() as c:
                c.execute("UPDATE orders SET status='withheld', note=? WHERE id=?", (d.reason, oid))
                c.execute("UPDATE outbox SET status='done', last_error=? WHERE order_id=? AND kind='deliver'",
                          (d.reason, oid))
                if d.status != "hold":
                    c.execute("INSERT INTO exceptions (order_id,kind,detail,cost_bearer,ts) VALUES (?,?,?,?,?)",
                              (oid, "delivery_withheld", d.reason + "; payment kept", o["buyer_id"], time.time()))
                self.store.log("engine", "withheld", f"order {oid}: delivery withheld ({d.reason}); payment kept")
            if d.status == "hold":  # fail closed but retryable
                with self.store.tx() as c:
                    c.execute("UPDATE orders SET status='paid' WHERE id=?", (oid,))
                    c.execute("UPDATE outbox SET status='pending' WHERE order_id=? AND kind='deliver'", (oid,))
            return False
        b = self.store.one("SELECT * FROM bundles WHERE order_id=?", oid)
        attempt = self.store.one("SELECT COUNT(*) n FROM deliveries WHERE order_id=?", oid)["n"] + 1
        try:
            self.inbox.deliver(o["buyer_id"], oid, b["bundle_hash"], b["sealed"])
            acked = True
        except LostDelivery as e:
            acked = False
            self.store.log("engine", "lost_delivery", f"order {oid}: delivery ack lost ({e}); will resend same bundle")
        with self.store.tx() as c:
            c.execute("INSERT INTO deliveries (order_id,bundle_hash,attempt,acked,ts) VALUES (?,?,?,?,?)",
                      (oid, b["bundle_hash"], attempt, int(acked), time.time()))
            if acked and o["status"] == "escrowed":
                c.execute("UPDATE outbox SET status='done' WHERE order_id=? AND kind='deliver'", (oid,))
                c.execute("INSERT OR IGNORE INTO outbox (order_id,kind,status) VALUES (?,?,?)", (oid, "finish", "pending"))
                self.store.log("engine", "locked_delivery",
                               f"order {oid}: locked bundle {b['bundle_hash'][:12]}… delivered to {o['buyer_id']}; "
                               f"it opens only with the key the escrow needs")
            elif acked:
                c.execute("UPDATE orders SET status='delivered' WHERE id=?", (oid,))
                c.execute("UPDATE outbox SET status='done' WHERE order_id=? AND kind='deliver'", (oid,))
                self.store.log("engine", "delivered",
                               f"order {oid}: sealed bundle {b['bundle_hash'][:12]}… delivered to {o['buyer_id']}")
            else:
                c.execute("UPDATE outbox SET attempts=attempts+1 WHERE order_id=? AND kind='deliver'", (oid,))
        return acked

    # ---------- escrow: payment and data key in one ledger transaction ----------

    def _send(self, oid: int, col: str, prep_fn) -> tuple[str, object]:
        """Sign once, store hash+blob, submit, look up; resubmit the same blob if not found."""
        p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        h, blob = p[f"{col}_tx" if col != "create" else "tx_hash"], p[f"{col}_blob" if col != "create" else "tx_blob"]
        if h is None:
            prep = prep_fn()
            hc, bc = ("tx_hash", "tx_blob") if col == "create" else (f"{col}_tx", f"{col}_blob")
            with self.store.tx() as c:
                c.execute(f"UPDATE payments SET {hc}=?, {bc}=?, updated_at=? WHERE order_id=?",
                          (prep.tx_hash, prep.blob, time.time(), oid))
                if col == "create":
                    c.execute("UPDATE payments SET offer_sequence=?, status='submitted' WHERE order_id=?",
                              (prep.sequence, oid))
            h, blob = prep.tx_hash, prep.blob
            self._submit(oid, prep)
        st = self.ledger.wait_validated(h)
        if not st.found:
            if self.ledger.is_expired(blob):
                # Past LastLedgerSequence and never applied: sign again (new sequence, new hash).
                prep = prep_fn()
                hc, bc = ("tx_hash", "tx_blob") if col == "create" else (f"{col}_tx", f"{col}_blob")
                with self.store.tx() as c:
                    c.execute(f"UPDATE payments SET {hc}=?, {bc}=?, updated_at=? WHERE order_id=?",
                              (prep.tx_hash, prep.blob, time.time(), oid))
                    if col == "create":
                        c.execute("UPDATE payments SET offer_sequence=? WHERE order_id=?", (prep.sequence, oid))
                h, blob = prep.tx_hash, prep.blob
            self._submit(oid, Prepared(h, blob))
            st = self.ledger.wait_validated(h)
        return h, st

    def _consent_tag(self, o) -> str:
        """The seller's passkey-signed approval statement, when one is being applied (security/passkey.py)."""
        try:
            from .security.passkey import memo_tag
            return memo_tag(self.store, o["seller_id"])
        except sqlite3.OperationalError:      # no passkey tables (engine used without the security layer)
            return ""

    def _escrow_create(self, oid: int) -> bool:
        o = self.store.one("SELECT * FROM orders WHERE id=?", oid)
        p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        if p["tx_hash"] is None:
            d = self._recheck(o, for_delivery=False)
            if not d.ok:
                with self.store.tx() as c:
                    self._release(c, o, "blocked", d.reason)
                    self.store.log("engine", "blocked", f"order {oid} blocked before escrow: {d.reason}")
                return False
        ok, why, mh = (self._mandate_check(o, p) if p["tx_hash"] is None else
                       (True, "", (self.store.one("SELECT hash FROM mandate_actions WHERE order_id=?", oid) or {"hash": ""})["hash"]))
        if not ok:
            with self.store.tx() as c:
                self._release(c, o, "blocked", f"mandate check failed: {why}")
                self.store.log("engine", "blocked", f"order {oid} blocked before escrow: mandate check failed: {why}")
            return False
        buyer_addr = self.party(o["buyer_id"])["address"]
        pv = json.loads(o["policy_snapshot"]).get("version", "")
        memo = f"order:{oid}|bundle:{o['bundle_hash'][:16]}|terms:{pv}" + (f"|mandate:{mh}" if mh else "") + self._consent_tag(o)
        h, st = self._send(oid, "create", lambda: self.ledger.prepare_escrow_create(
            buyer_addr, p["payee_address"], p["amount_drops"], p["condition"], p["cancel_after"], memo))
        if not st.validated:
            return False
        with self.store.tx() as c:
            ok = (st.success and st.tx_type == "EscrowCreate" and st.destination == p["payee_address"]
                  and st.amount_drops == p["amount_drops"] and (st.condition or "").upper() == p["condition"])
            if not ok:
                self._release(c, o, "failed", f"escrow not created on validated ledger ({st.result})")
                c.execute("UPDATE payments SET status='failed' WHERE order_id=?", (oid,))
                c.execute("INSERT INTO exceptions (order_id,kind,detail,cost_bearer,ts) VALUES (?,?,?,?,?)",
                          (oid, "escrow_failed", f"ledger result {st.result}", None, time.time()))
                self.store.log("engine", "refused", f"order {oid}: ledger refused the escrow ({st.result})",
                               {"tx_hash": h, "url": self.ledger.explorer_url(h)})
                return False
            c.execute("UPDATE payments SET status='escrowed', ledger_index=? WHERE order_id=?", (st.ledger_index, oid))
            c.execute("UPDATE orders SET status='escrowed' WHERE id=?", (oid,))
            c.execute("UPDATE outbox SET status='done' WHERE order_id=? AND kind='pay'", (oid,))
            c.execute("INSERT OR IGNORE INTO outbox (order_id,kind,status) VALUES (?,?,?)", (oid, "deliver", "pending"))
            self.store.log("engine", "escrowed",
                           f"order {oid}: {o['price_drops'] / 1e6:g} XRP locked in escrow for {o['payee_id']}; "
                           f"pays out only when the data key is published", {"order_id": oid, "tx_hash": h,
                                                                             "url": self.ledger.explorer_url(h)})
        return True

    def escrow_create_batch(self, oids: list[int]) -> bool:
        """Create every week's escrow of one participant's round in one Batch (ALL_OR_NOTHING), so the
        participant never holds half a promise. Each order passes the same checks as alone; if any
        fails, nothing is batched and the orders go one by one. After submit, each order's payment
        points at its inner tx and process() carries on as usual."""
        prep_batch = getattr(self.ledger, "prepare_escrow_batch", None)
        if prep_batch is None or len(oids) < 2:
            return False
        legs, buyer = [], None
        for oid in oids:
            o = self.store.one("SELECT * FROM orders WHERE id=?", oid)
            p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
            if p["tx_hash"] is not None or p["kind"] != "escrow" or (buyer and o["buyer_id"] != buyer):
                return False
            buyer = o["buyer_id"]
            if not self._recheck(o, for_delivery=False).ok:
                return False
            ok, why, mh = self._mandate_check(o, p)
            if not ok:
                return False
            pv = json.loads(o["policy_snapshot"]).get("version", "")
            legs.append({"destination": p["payee_address"], "amount_drops": p["amount_drops"],
                         "condition": p["condition"], "cancel_after": p["cancel_after"],
                         "memo": f"order:{oid}|bundle:{o['bundle_hash'][:16]}|terms:{pv}" + (f"|mandate:{mh}" if mh else "")
                                 + self._consent_tag(o)})
        try:
            outer, hashes, seqs = prep_batch(self.party(buyer)["address"], legs)
            self.ledger.submit(outer)
        except Exception as e:
            self.store.log("engine", "batch", f"batch of {len(oids)} escrows not submitted ({e}); one by one instead")
            return False
        st = self.ledger.wait_validated(outer.tx_hash)
        applied = st.validated and all(self.ledger.wait_validated(h, 10).found for h in hashes)
        if not applied:
            self.store.log("engine", "batch", f"batch of {len(oids)} escrows: nothing applied ({st.result}); "
                           "one by one instead", {"tx_hash": outer.tx_hash, "url": self.ledger.explorer_url(outer.tx_hash)})
            return False
        with self.store.tx() as c:
            for oid, h, sq in zip(oids, hashes, seqs):
                # The inner tx is what the ledger records per escrow; the outer blob is resubmittable.
                c.execute("UPDATE payments SET tx_hash=?, tx_blob=?, offer_sequence=?, status='submitted', "
                          "updated_at=? WHERE order_id=?", (h, outer.blob, sq, time.time(), oid))
        self.store.log("engine", "batch", f"{len(oids)} weekly escrows submitted together (Batch, all or nothing): "
                       f"{st.result}", {"tx_hash": outer.tx_hash, "url": self.ledger.explorer_url(outer.tx_hash),
                                         "orders": oids})
        return True

    def _escrow_finish(self, oid: int) -> bool:
        """Contributor side: re-check permission, then publish the key to get paid."""
        o = self.store.one("SELECT * FROM orders WHERE id=?", oid)
        p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        if p["finish_tx"] is None:
            d = self._recheck(o, for_delivery=True)
            if not d.ok:
                with self.store.tx() as c:
                    c.execute("UPDATE orders SET status='withheld', note=? WHERE id=?", (d.reason, oid))
                    c.execute("UPDATE outbox SET status='done', last_error=? WHERE order_id=? AND kind='finish'",
                              (d.reason, oid))
                    c.execute("INSERT OR IGNORE INTO outbox (order_id,kind,status) VALUES (?,?,?)",
                              (oid, "cancel", "pending"))
                    self.store.log("engine", "withheld", f"order {oid}: key not published ({d.reason}); "
                                   f"escrow returns to {o['buyer_id']} after its deadline")
                return False
        holder = self.key_holders.get(o["seller_id"])
        if holder is not None:
            fulfillment = holder.fulfillment(o["order_key"])
            if fulfillment is None and p["finish_tx"] is None:   # keyring forgot K (withdrawal): never published
                return False
        else:
            key = bytes.fromhex(self.store.one("SELECT key_hex FROM escrow_keys WHERE order_id=?", oid)["key_hex"])
            fulfillment = fulfillment_hex(key)
        payee = p["payee_address"]
        submitter = payee if self.ledger.can_sign(payee) else self.relay
        buyer_addr = self.party(o["buyer_id"])["address"]
        h, st = self._send(oid, "finish", lambda: self.ledger.prepare_escrow_finish(
            submitter, buyer_addr, p["offer_sequence"], p["condition"], fulfillment, f"order:{oid}"))
        if not st.validated:
            return False
        with self.store.tx() as c:
            if not st.success:
                c.execute("UPDATE outbox SET status='done', last_error=? WHERE order_id=? AND kind='finish'",
                          (st.result, oid))
                c.execute("INSERT OR IGNORE INTO outbox (order_id,kind,status) VALUES (?,?,?)", (oid, "cancel", "pending"))
                self.store.log("engine", "refused", f"order {oid}: escrow finish failed ({st.result})")
                return False
            c.execute("UPDATE payments SET status='validated', ledger_index=? WHERE order_id=?", (st.ledger_index, oid))
            c.execute("UPDATE orders SET status='delivered' WHERE id=?", (oid,))
            c.execute("UPDATE mandates SET reserved_drops=reserved_drops-?, spent_drops=spent_drops+? "
                      "WHERE buyer_id=?", (o["price_drops"], o["price_drops"], o["buyer_id"]))
            c.execute("UPDATE outbox SET status='done' WHERE order_id=? AND kind='finish'", (oid,))
            self.store.log("engine", "paid", f"order {oid}: key published in EscrowFinish; {o['price_drops'] / 1e6:g} "
                           f"XRP released to {o['payee_id']} in ledger {st.ledger_index}; {o['buyer_id']} can open "
                           f"the bundle", {"order_id": oid, "tx_hash": h, "url": self.ledger.explorer_url(h)})
        return True

    def _escrow_cancel(self, oid: int) -> bool:
        o = self.store.one("SELECT * FROM orders WHERE id=?", oid)
        p = self.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        if p["cancel_tx"] is None and self.ledger.now() < p["cancel_after"]:
            return False   # not due yet; sweep() retries
        buyer_addr = self.party(o["buyer_id"])["address"]
        h, st = self._send(oid, "cancel", lambda: self.ledger.prepare_escrow_cancel(
            buyer_addr, buyer_addr, p["offer_sequence"]))
        if not (st.validated and st.success):
            return False
        with self.store.tx() as c:
            c.execute("UPDATE payments SET status='refunded' WHERE order_id=?", (oid,))
            self._release(c, o, "refunded", "escrow cancelled after its deadline; locked amount returned")
            c.execute("UPDATE outbox SET status='done' WHERE order_id=? AND kind='cancel'", (oid,))
            self.store.log("engine", "refunded", f"order {oid}: EscrowCancel returned {o['price_drops'] / 1e6:g} XRP "
                           f"to {o['buyer_id']}", {"order_id": oid, "tx_hash": h, "url": self.ledger.explorer_url(h)})
        return True

    def sweep(self) -> list[int]:
        """Cancel escrows whose deadline has passed without the key being published."""
        ids = [r["order_id"] for r in self.store.q("SELECT order_id FROM outbox WHERE kind='cancel' AND status='pending'")]
        return [oid for oid in ids if self._escrow_cancel(oid)]

    # ---------- buyer side ----------

    def open_bundle(self, buyer_id: str, order_id: int) -> list[dict]:
        bundle_hash, sealed = self.inbox.received[order_id]
        p = self.store.one("SELECT kind, finish_tx FROM payments WHERE order_id=?", order_id)
        opener = self.openers.get(buyer_id)
        if opener is not None:
            # The institution's vault opens it; K comes from the validated ledger, not the contributor.
            f = self.ledger.lookup(p["finish_tx"]).fulfillment if p["kind"] == "escrow" else None
            payload = opener.open(sealed, f)
            assert sha256_hex(canonical(payload)) == bundle_hash
            return payload["rows"]
        if p["kind"] == "escrow":
            # The key is read from the ledger, not from the contributor.
            st = self.ledger.lookup(p["finish_tx"])
            sealed = SecretBox(key_from_fulfillment(st.fulfillment)).decrypt(sealed)
        payload = json.loads(SealedBox(self.box_keys[buyer_id]).decrypt(sealed))
        assert sha256_hex(canonical(payload)) == bundle_hash
        return payload["rows"]
