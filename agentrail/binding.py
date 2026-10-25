"""One paid order, checked link by link: the contract, the provenance stamps, the escrow on the ledger,
the revealed key and the bundle all point at the same data.

    contract hash  ->  manifest inside the bundle (signed by the holder, stamps signed by the source)
    bundle hash    ->  EscrowCreate memo (validated)            condition = SHA-256(K)
    EscrowFinish   ->  K on the validated ledger                SHA-256(K) == condition
    K              ->  opens the outer layer only; the inner layer is sealed to the buyer's key
    opened bundle  ->  hashes to the bundle hash in the memo
    stamped values ->  verify before payment, open with K after, equal the delivered rows

Limits, stated: before the key is revealed the buyer can check the stamps' signatures and that the
sealed bytes are the ones the source signed, but not that the intake keys are wrapped with this K;
a seller who wraps them with another key is caught at opening (unopenable), after payment, and that
becomes a refund claim, not a prevented payment. Rows the seller computed are checked against the
stamped native values only where stamps exist.
"""
from __future__ import annotations

import json

from nacl.exceptions import CryptoError
from nacl.public import PrivateKey, SealedBox
from nacl.secret import SecretBox

from .engine import canonical, sha256_hex
from .ledger.conditions import condition_hex, key_from_fulfillment


def _step(out, name, ok, detail="", tx=None, url=None):
    out.append({"step": name, "ok": bool(ok), "detail": detail, **({"tx": tx} if tx else {}),
                **({"url": url} if url else {})})
    return ok


def chain(engine, buyer: str, oid: int) -> dict:
    L, out = engine.ledger, []
    o = engine.store.one("SELECT * FROM orders WHERE id=?", oid)
    p = engine.store.one("SELECT * FROM payments WHERE order_id=?", oid)
    b = engine.store.one("SELECT * FROM bundles WHERE order_id=?", oid)
    if not (o and p and b) or p["kind"] != "escrow":
        return {"order": oid, "ok": False, "steps": [{"step": "escrow order", "ok": False, "detail": "not found"}]}
    contract = o["product_id"].split("contract:", 1)[1] if "contract:" in o["product_id"] else None
    c = L.lookup(p["tx_hash"]) if p["tx_hash"] else None
    _step(out, "EscrowCreate validated", c and c.validated and c.success and (c.condition or "").upper() == p["condition"],
          f"{(c.result if c else 'missing')}; condition = stored SHA-256(K) condition", p["tx_hash"],
          L.explorer_url(p["tx_hash"]) if p["tx_hash"] else None)
    memo = L.memo_of(p["tx_hash"]) if p["tx_hash"] and hasattr(L, "memo_of") else None
    _step(out, "bundle hash in the EscrowCreate memo", memo is not None and f"bundle:{b['bundle_hash'][:16]}" in memo,
          memo or "memo not readable")
    if contract:
        _step(out, "contract hash in the memo", memo is not None and f"contract:{contract[:16]}" in memo, contract[:16])
    f = L.lookup(p["finish_tx"]) if p["finish_tx"] else None
    k = None
    if f and f.fulfillment:
        k = key_from_fulfillment(f.fulfillment)
    _step(out, "EscrowFinish validated, K on the ledger", f and f.validated and f.success and k is not None,
          f.result if f else "no finish", p["finish_tx"], L.explorer_url(p["finish_tx"]) if p["finish_tx"] else None)
    _step(out, "SHA-256(K) equals the escrow condition", k is not None and condition_hex(k) == p["condition"])
    sealed = bytes(b["sealed"])
    if buyer in engine.openers:
        payload = engine.open_payload(buyer, oid)
        _step(out, "outer layer sealed to the buyer's vault", True, "opened by the institution vault with K from the ledger")
    else:
        inner = None
        try:
            inner = SecretBox(k).decrypt(sealed) if k else None
        except CryptoError:
            pass
        _step(out, "K opens the outer layer", inner is not None)
        third = True
        try:
            SealedBox(PrivateKey.generate()).decrypt(inner or b"")
            third = False
        except CryptoError:
            pass
        _step(out, "K alone does not open the data (inner layer sealed to the buyer)", third,
              "a third party holding only K gets ciphertext")
        payload = json.loads(SealedBox(engine.box_keys[buyer]).decrypt(inner)) if inner else {}
    _step(out, "opened bundle hashes to the memo's bundle hash", payload and sha256_hex(canonical(payload)) == b["bundle_hash"],
          b["bundle_hash"][:16])
    m = payload.get("manifest") if isinstance(payload, dict) else None
    if m and contract:
        _step(out, "manifest names this contract", m.get("contract") == contract)
    if m and payload.get("sealed") and k is not None:
        from .contract.provenance import open_sealed, verify_seals
        pre = verify_seals(m, payload)
        _step(out, "source stamps match the sealed records", not pre, "; ".join(x["code"] for x in pre))
        post = open_sealed(m, payload, k)
        _step(out, "stamped records open with K and equal the delivered values", not post,
              "; ".join(x["code"] for x in post))
    return {"order": oid, "buyer": buyer, "seller": o["seller_id"], "bundle_hash": b["bundle_hash"],
            "contract": contract, "ok": all(s["ok"] for s in out), "steps": out,
            "limits": "the intake keys' wrap with this K is checked at opening, after payment; a failure there "
                      "is a refund claim, not a prevented payment"}


def proof(w) -> dict:
    """The three cases of one run on one version: a paid contract checked link by link, a contribution
    refused before payment, and a withdrawal that stopped the next delivery."""
    from .study import LAB
    L, out = w.ledger, {"ledger": w.ledger.name}
    r = getattr(w, "contract_round", None)
    paid = next((o for o in (r.outcomes if r else []) if (o.get("txs") or {}).get("escrow_finish")), None)
    if paid:
        oid = w.store.one("SELECT order_id FROM payments WHERE finish_tx=?", paid["txs"]["escrow_finish"])["order_id"]
        out["paid_trade"] = chain(w.engine, LAB, oid)
    else:
        row = w.store.one("SELECT p.order_id FROM payments p WHERE p.finish_tx IS NOT NULL AND p.kind='escrow' LIMIT 1")
        out["paid_trade"] = chain(w.engine, LAB, row["order_id"]) if row else {"ok": False, "steps": []}
    refused = next((o for o in (r.outcomes if r else []) if o.get("stage") == "before_payment"), None)
    out["refused_before_payment"] = ({"provider": refused.get("provider", refused.get("pid")), "window": refused.get("window"),
                                      "signals": refused["signals"], "paid_drops": refused["paid_drops"],
                                      "escrow": None} if refused else None)
    wd = next((x for x in getattr(w.study, "withdrawals", []) if x.get("kind") == "revoke"), None)
    if wd:
        held = [w.store.one("SELECT id, status, note FROM orders WHERE id=?", i) for i in wd.get("withheld", [])]
        ct = (wd.get("clawback") or {}).get("tx") if isinstance(wd.get("clawback"), dict) else wd.get("clawback")
        out["withdrawal"] = {"person": wd["person"], "clawback_tx": ct, "clawback_url": L.explorer_url(ct) if ct else None,
                             "next_deliveries": [{"order": h["id"], "status": h["status"], "why": h["note"]} for h in held if h],
                             "refunds": wd.get("refunds", [])}
    else:
        out["withdrawal"] = None
    return out


def summary(p: dict) -> str:
    lines = [f"Proof of one trade ({p['ledger']})"]
    t = p.get("paid_trade") or {}
    lines.append(f"  paid trade, order {t.get('order')}: {'ALL LINKS HOLD' if t.get('ok') else 'A LINK FAILED'}")
    for s in t.get("steps", []):
        lines.append(f"    [{'ok' if s['ok'] else 'NO'}] {s['step']}" + (f"  {s.get('url') or s['tx']}" if s.get("tx") else ""))
    rf = p.get("refused_before_payment")
    lines.append("  refused before payment: " + (f"{rf['provider']} window {rf['window']}: "
                 f"{', '.join(x['code'] for x in rf['signals'])}; paid {rf['paid_drops']} drops, no escrow" if rf else "none in this run"))
    wd = p.get("withdrawal")
    lines.append("  withdrawal: " + (f"{wd['person']}: clawback {wd['clawback_url'] or wd['clawback_tx']}; next deliveries "
                 + ", ".join(f"order {d['order']} {d['status']}" for d in wd["next_deliveries"]) if wd else "none in this run"))
    return "\n".join(lines)
