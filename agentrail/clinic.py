"""The clinic's records-export service, paid per request with x402 over real HTTP.

GET /clinic/export without a payment answers 402 Payment Required with x402 v2 PaymentRequirements
(exact scheme on XRPL: amount in drops, payTo the clinic, invoiceId bound to this person, items and
nonce). The person's agent signs an XRPL Payment for exactly that and retries with PAYMENT-SIGNATURE.
The clinic settles it (through the T54 facilitator on Testnet, or by submitting the signed blob
itself) and confirms the payment on a validated ledger before it answers 200 with the export.

A separate service from the AgentRail API: its own small app, mounted at /clinic, not behind the
API's sign-in (it is the clinic's own endpoint), and it never sees health values.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from .ledger.base import Prepared

NETWORK_TESTNET = "xrpl:1"
FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://xrpl-facilitator-testnet.t54.ai")
SOURCE_TAG = int(os.environ.get("X402_SOURCE_TAG", "804681468"))

app = FastAPI(title="Clinic records export (synthetic)")
CLINIC_PATH = "/export"          # mounted at /clinic by the API server: GET /clinic/export
_cfg: dict = {}
_used: set[str] = set()
_lock = threading.Lock()


def configure(ledger, pay_to: str, fee_drops: int):
    _cfg.update(ledger=ledger, pay_to=pay_to, fee=fee_drops)


def invoice_for(person: str, items: str, nonce: str) -> str:
    return hashlib.sha256(f"export|{person}|{items}|{nonce}".encode()).hexdigest().upper()


def invoice_field(invoice_id: str) -> str:
    """XRPL exact scheme: Payment.InvoiceID = SHA-256(invoiceId)."""
    return hashlib.sha256(invoice_id.encode()).hexdigest().upper()


def requirements(person: str, items: str, nonce: str) -> dict:
    L = _cfg["ledger"]
    return {"scheme": "exact", "network": NETWORK_TESTNET if L.name == "testnet" else f"xrpl:{L.name}",
            "amount": str(_cfg["fee"]), "asset": "XRP", "payTo": _cfg["pay_to"], "maxTimeoutSeconds": 300,
            "extra": {"invoiceId": invoice_for(person, items, nonce), "sourceTag": SOURCE_TAG}}


def b64(d: dict) -> str:
    return base64.b64encode(json.dumps(d, separators=(",", ":"), sort_keys=True).encode()).decode()


def _payment_required(resource: str, req: dict, error: str | None = None) -> JSONResponse:
    body = {"x402Version": 2, "resource": {"url": resource, "description": "clinic visit records export",
                                           "mimeType": "application/json"},
            "accepts": [req], "extensions": {}}
    if error:
        body["error"] = error
    return JSONResponse(body, status_code=402, headers={"PAYMENT-REQUIRED": b64(body)})


def _settle_with_facilitator(header: str, req: dict) -> tuple[bool, str]:
    from x402_xrpl import FacilitatorClient, FacilitatorClientOptions, PaymentRequirements
    fac = FacilitatorClient(FacilitatorClientOptions(base_url=FACILITATOR_URL, timeout_seconds=60))
    r = PaymentRequirements.from_dict(req)
    v = fac.verify(payment_header=header, payment_requirements=r)
    if not v.is_valid:
        return False, f"verify: {v.invalid_reason}"
    s = fac.settle(payment_header=header, payment_requirements=r)
    return bool(s.success), s.error_reason or ""


@app.get("/export")
def export(request: Request, person: str, items: str, nonce: str,
           payment_signature: str | None = Header(default=None, alias="PAYMENT-SIGNATURE")):
    L = _cfg["ledger"]
    req = requirements(person, items, nonce)
    if not payment_signature:
        return _payment_required(str(request.url), req)
    try:
        p = json.loads(base64.b64decode(payment_signature))
        blob, accepted = p["payload"]["signedTxBlob"], p["accepted"]
    except Exception:
        return _payment_required(str(request.url), req, "invalid_payment_header")
    if any(accepted.get(k) != req[k] for k in ("amount", "payTo", "asset")) or \
            accepted.get("extra", {}).get("invoiceId") != req["extra"]["invoiceId"]:
        return _payment_required(str(request.url), req, "payment_requirements_mismatch")
    if L.invoice_field_of(blob) != invoice_field(req["extra"]["invoiceId"]):
        return _payment_required(str(request.url), req, "invoice_not_bound")
    tx_hash = _hash_of(L, blob)
    with _lock:
        if tx_hash in _used:
            return _payment_required(str(request.url), req, "payment_already_used")
        _used.add(tx_hash)
    settled_by = "server"
    if L.name == "testnet" and os.environ.get("CLINIC_SETTLE", "facilitator") == "facilitator":
        try:
            ok, why = _settle_with_facilitator(payment_signature, req)
            settled_by = "T54 facilitator"
            if not ok:
                raise RuntimeError(why)
        except Exception:
            settled_by = "server"            # facilitator down: the signed blob is still valid
    if settled_by == "server":
        try:
            L.submit(Prepared(tx_hash=tx_hash, blob=blob))
        except Exception:
            pass                             # outcome unknown: the ledger lookup below decides
    st = L.wait_validated(tx_hash)
    paid = st.xrp_drops if st.xrp_drops is not None else st.amount_drops     # the fee is in XRP (asset above)
    if not (st.validated and st.success and st.destination == _cfg["pay_to"] and paid == _cfg["fee"]):
        with _lock:
            _used.discard(tx_hash)
        return _payment_required(str(request.url), req, f"not_settled:{st.result}")
    receipt = {"success": True, "transaction": tx_hash, "network": req["network"], "settledBy": settled_by}
    return JSONResponse({"export": {"person": person, "items": items.split(","), "format": "clinic native (SYSBP, DIABP)",
                                    "status": "released to the person's agent"}, "receipt": receipt},
                        headers={"PAYMENT-RESPONSE": b64(receipt)})


def _hash_of(L, blob: str) -> str:
    if L.name == "testnet":
        from xrpl.models.transactions.transaction import Transaction
        return Transaction.from_blob(blob).get_hash()
    return hashlib.sha256(blob.encode()).hexdigest().upper()


# ---------------- the person's agent side ----------------

def pay_and_fetch(L, payer_address: str, person: str, items: list[str], nonce: str, base_url: str | None = None):
    """GET -> 402 -> sign exactly what was asked -> GET with PAYMENT-SIGNATURE -> 200.
    Returns (status trail, response json)."""
    import httpx
    params = {"person": person, "items": ",".join(items), "nonce": nonce}
    if base_url:
        client = httpx.Client(base_url=base_url, timeout=120)
    else:                                      # same process: still a full HTTP exchange through ASGI
        from fastapi.testclient import TestClient
        client = TestClient(app)
    r1 = client.get(CLINIC_PATH, params=params)
    if r1.status_code != 402:
        return [r1.status_code], r1.json()
    req = json.loads(base64.b64decode(r1.headers["PAYMENT-REQUIRED"]))["accepts"][0]
    header = _payment_header(L, payer_address, req)
    r2 = client.get(CLINIC_PATH, params=params, headers={"PAYMENT-SIGNATURE": header})
    return [r1.status_code, r2.status_code], r2.json()


def _payment_header(L, payer: str, req: dict) -> str:
    inv = req["extra"]["invoiceId"]
    if L.name == "testnet":
        try:
            from x402_xrpl import PaymentRequirements
            from x402_xrpl.client.presigned_payment_payer import (XRPLPresignedPaymentPayer,
                                                                  XRPLPresignedPaymentPayerOptions)
            payer_ = XRPLPresignedPaymentPayer(XRPLPresignedPaymentPayerOptions(
                wallet=L.wallets[payer], network=req["network"], rpc_url=L.client.url,
                invoice_binding=os.environ.get("X402_INVOICE_BINDING", "both")), client=L.client)
            with L._seq_lock:
                L._seq.pop(payer, None)      # the SDK autofills the sequence from the ledger
            return payer_.prepare_payment(PaymentRequirements.from_dict(req)).payment_header
        except ImportError:
            pass
    # the fee is XRP (asset above) even when orders settle in a token
    prep = L.prepare_payment(payer, req["payTo"], int(req["amount"]), invoice_field(inv), "clinic records export",
                             xrp=True)
    return b64({"x402Version": 2, "accepted": req, "payload": {"signedTxBlob": prep.blob, "invoiceId": inv}})
