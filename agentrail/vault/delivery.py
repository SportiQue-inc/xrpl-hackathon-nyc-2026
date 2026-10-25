"""Push delivery: the agreed scope, sealed on the person's side, pushed into the buyer's own store.

There is no access right and no subscription: no outside party ever reads the person's store. Many
cross-border rules forbid inbound access from abroad to where the data lives, so a standing "view"
link is the wrong shape for transfer abroad. Instead each trade is one push of exactly what was
agreed, encrypted end to end to the receiving institution's registered key. A repeated round is a
new push with its own consent check and contract.

  prepare   the engine assembles the agreed rows as canonical bytes for the person's page
  sealed    the page seals them (vault/keys.py, apps/shared/passkey.js) and returns the sealed record
            and the escrow condition SHA-256(K); the engine creates the escrow and pushes the sealed
            record to the institution's store. The engine never sees K or the clear bundle.
  reveal    the page (or the person's hosted agent, inside a delegation) publishes K in EscrowFinish:
            the person is paid and the institution can open what it already holds
  revoke    future pushes stop; for copies already delivered, a deletion request goes to the
            institution, which must answer with a signed deletion confirmation
"""
from __future__ import annotations

import hashlib
import json
import os

from ..engine import Engine, OrderRequest
from ..ledger.conditions import condition_hex, fulfillment_hex, key_from_fulfillment
from ..policy import ALLOW, DENY, BuyerMandate, Decision
from .keys import InstitutionKey, b64u, bundle_bytes


class _PageHolder:
    """Stands for the person's page in the engine: it knows K only after the page revealed it."""

    def __init__(self):
        self.keys: dict[str, bytes] = {}

    def fulfillment(self, order_key: str) -> str | None:
        k = self.keys.get(order_key)
        return fulfillment_hex(k) if k else None


class _Opener:
    def __init__(self, key: InstitutionKey):
        self.key = key

    def open(self, sealed: bytes, fulfillment: str | None) -> dict:
        rec = json.loads(sealed)
        return json.loads(self.key.open(rec, key_from_fulfillment(fulfillment)))


class _ScopePolicy:
    """Re-checked by the engine before money moves and before the key is published."""

    def __init__(self, d: "PushDelivery", pid: str):
        self.d, self.pid = d, pid

    def evaluate(self, buyer_id, purpose, fields, price_drops, week=None, for_delivery=False):
        scope = self.d.consents.get((self.pid, buyer_id))
        if scope is None or scope.get("revoked"):
            return Decision(DENY, reason="no active consent for this institution")
        if not set(fields) <= set(scope["columns"]) or purpose != scope["purpose"]:
            return Decision(DENY, reason="outside the consented scope")
        return Decision(ALLOW, granted=list(fields))


class PushDelivery:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.institutions: dict[str, dict] = {}
        self.consents: dict[tuple, dict] = {}       # (pid, institution) -> scope and push record
        self.prepared: dict[str, dict] = {}
        self.pushes: list[dict] = []

    def register_institution(self, iid: str, country: str, key: InstitutionKey, address: str | None = None):
        if self.engine.party(iid) is None:
            self.engine.add_party(iid, iid, "organization", address or self.engine.ledger.new_account(iid))
        self.institutions[iid] = {"country": country, "jwk": key.jwk()}
        self.engine.openers[iid] = _Opener(key)

    def consent(self, pid: str, iid: str, columns: list, purpose: str):
        if self.engine.party(pid) is None:
            self.engine.add_party(pid, pid, "person", self.engine.ledger.new_account(pid))
        self.consents[(pid, iid)] = {"columns": list(columns), "purpose": purpose, "revoked": False, "pushes": []}
        self.engine.policies[pid] = _ScopePolicy(self, pid)
        self.engine.key_holders.setdefault(pid, _PageHolder())

    def prepare(self, pid: str, iid: str, rows: list, columns: list, contract: str, price_drops: int) -> dict:
        c = self.consents.get((pid, iid))
        if c is None or c["revoked"]:
            raise PermissionError("no active consent: nothing is pushed")
        trade_id = f"{pid}.{iid}.{len(c['pushes']) + len([p for p in self.prepared.values() if p['pid'] == pid]) + 1}"
        payload = {"trade": trade_id, "contract": contract, "columns": columns,
                   "rows": [{k: r.get(k) for k in ["day"] + list(columns) if k in r} for r in rows],
                   "salt": os.urandom(16).hex()}
        b = bundle_bytes(payload)
        bh = hashlib.sha256(b).hexdigest()
        self.prepared[trade_id] = {"pid": pid, "iid": iid, "bundle_hash": bh, "columns": columns,
                                   "price": price_drops, "contract": contract}
        return {"order_id": trade_id, "bundle_b64u": b64u(b), "bundle_hash": bh,
                "institution_jwk": self.institutions[iid]["jwk"], "institution": iid,
                "country": self.institutions[iid]["country"], "contract": contract}

    def accept_sealed(self, pid: str, record: dict, condition: str) -> dict:
        p = self.prepared.get(record.get("order_id"))
        if p is None or p["pid"] != pid:
            return {"ok": False, "reason": "unknown trade"}
        if record.get("bundle_hash") != p["bundle_hash"]:
            return {"ok": False, "reason": "sealed bundle is not the prepared one"}
        iid = p["iid"]
        c = self.consents[(pid, iid)]
        if c["revoked"]:
            return {"ok": False, "reason": "consent revoked: nothing is pushed"}
        if self.engine.store.one("SELECT 1 FROM mandates WHERE buyer_id=?", iid) is None:
            self.engine.set_mandate(BuyerMandate(iid, 10**12, 10**10, [c["purpose"]]))
        req = OrderRequest(iid, pid, pid, f"contract:{p['contract']}", record["order_id"], c["purpose"], p["columns"],
                           p["price"], [{"bundle_hash": p["bundle_hash"]}],
                           Decision(ALLOW, granted=p["columns"], policy_version="push"), settle="escrow",
                           presealed={"record": record, "condition": condition})
        oid = self.engine.place_order(req)
        status = self.engine.process(oid)             # escrow created, sealed record pushed; K not yet public
        pm = self.engine.store.one("SELECT * FROM payments WHERE order_id=?", oid)
        push = {"trade": record["order_id"], "order_id": oid, "institution": iid,
                "country": self.institutions[iid]["country"], "bundle_hash": p["bundle_hash"],
                "escrow_create": pm["tx_hash"], "status": status}
        c["pushes"].append(push)
        self.pushes.append({"person": pid, **push})
        self.engine.store.log(pid, "push", f"sealed bundle pushed to {iid} ({push['country']}); "
                              f"escrow {status}", {"tx_hash": pm["tx_hash"], "bundle": p["bundle_hash"][:16]})
        p["order_key"] = self.engine.store.one("SELECT order_key FROM orders WHERE id=?", oid)["order_key"]
        p["oid"] = oid
        return {"ok": True, **push}

    def reveal(self, pid: str, trade_id: str, k: bytes) -> dict:
        p = self.prepared.get(trade_id)
        if p is None or p["pid"] != pid or "oid" not in p:
            return {"ok": False, "reason": "unknown trade"}
        if self.consents[(pid, p["iid"])]["revoked"]:
            return {"ok": False, "reason": "consent revoked: the key is not published"}
        pm = self.engine.store.one("SELECT condition FROM payments WHERE order_id=?", p["oid"])
        if condition_hex(k) != pm["condition"]:
            return {"ok": False, "reason": "key does not match the escrow condition"}
        self.engine.key_holders[pid].keys[p["order_key"]] = k
        status = self.engine.process(p["oid"])
        pm = self.engine.store.one("SELECT finish_tx FROM payments WHERE order_id=?", p["oid"])
        return {"ok": status == "delivered", "status": status, "escrow_finish": pm["finish_tx"]}

    def revoke(self, pid: str, iid: str) -> dict:
        c = self.consents.get((pid, iid))
        if c is None:
            return {"ok": False}
        c["revoked"] = True
        delivered = [p for p in c["pushes"] if p["status"] in ("delivered", "escrowed")]
        req = {"person": pid, "institution": iid, "copies": [p["bundle_hash"][:16] for p in delivered],
               "answer_with": "signed deletion confirmation"}
        self.engine.store.log(pid, "withdrawal", f"pushes to {iid} stopped; deletion requested for "
                              f"{len(delivered)} delivered cop{'y' if len(delivered) == 1 else 'ies'}", req)
        return {"ok": True, "deletion_request": req}
