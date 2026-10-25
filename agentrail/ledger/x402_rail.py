"""x402 settlement through the T54 XRPL facilitator (Testnet).

The gate issues x402 PaymentRequirements for an order (payTo = payee, amount =
order price, invoiceId bound to the order and its terms). The buyer agent presigns
the Payment with the x402-xrpl payer; the facilitator verifies and settles it.
The engine still stores the signed blob and hash first and confirms the result on a
validated ledger itself - the facilitator's answer alone never releases data.
"""
from __future__ import annotations

import os
import uuid

import httpx
from x402_xrpl import FacilitatorClient, FacilitatorClientOptions, PaymentRequirements
from x402_xrpl.client.presigned_payment_payer import (XRPLPresignedPaymentPayer,
                                                      XRPLPresignedPaymentPayerOptions)
from xrpl.models.transactions.transaction import Transaction

from .base import LostResponse, Prepared

FACILITATOR_URL = os.environ.get("X402_FACILITATOR_URL", "https://xrpl-facilitator-testnet.t54.ai")
NETWORK = "xrpl:1"  # Testnet
# The T54 facilitator refuses requirements without extra.sourceTag (source_tag_mismatch);
# 804681468 is the x402-xrpl SDK default analytics tag.
SOURCE_TAG = int(os.environ.get("X402_SOURCE_TAG", "804681468"))


class X402Mixin:
    rail = "x402"

    def _x402_state(self) -> dict:
        if not hasattr(self, "_x402"):
            self._x402 = {}
            self.challenges: list[dict] = []
        return self._x402

    def payment_requirements(self, destination: str, amount_drops: int, invoice: str) -> PaymentRequirements:
        """What the gate answers with HTTP 402 for this order."""
        return PaymentRequirements(scheme="exact", network=NETWORK, amount=str(amount_drops), asset="XRP",
                                   pay_to=destination, max_timeout_seconds=300,
                                   extra={"invoiceId": invoice, "sourceTag": SOURCE_TAG})

    def prepare_payment(self, source, destination, amount_drops, invoice_id, memo):
        state = self._x402_state()
        # invoiceId carries the order terms; a nonce keeps it unique across demo runs.
        invoice = f"{memo}|n:{uuid.uuid4().hex[:8]}"
        req = self.payment_requirements(destination, amount_drops, invoice)
        self.challenges.append({"status": 402, "x402Version": 2, "accepts": [req.to_dict()]})
        payer = XRPLPresignedPaymentPayer(
            XRPLPresignedPaymentPayerOptions(wallet=self.wallets[source], network=NETWORK,
                                             rpc_url=self.client.url),
            client=self.client)
        prep = payer.prepare_payment(req)
        tx_hash = Transaction.from_blob(prep.signed_tx_blob).get_hash()
        state[tx_hash] = (prep.payment_header, req)
        return Prepared(tx_hash=tx_hash, blob=prep.signed_tx_blob)

    def submit(self, prepared: Prepared) -> None:
        hdr_req = self._x402_state().get(prepared.tx_hash)
        if hdr_req is None:
            # After a restart we no longer hold the header: resubmit the same signed blob
            # directly. Same hash, so it can apply at most once.
            return super().submit(prepared)
        header, req = hdr_req
        fac = FacilitatorClient(FacilitatorClientOptions(base_url=FACILITATOR_URL, timeout_seconds=60))
        try:
            v = fac.verify(payment_header=header, payment_requirements=req)
            if not v.is_valid:
                raise RuntimeError(f"x402 verify rejected: {v.invalid_reason}")
            s = fac.settle(payment_header=header, payment_requirements=req)
        except (httpx.TransportError, httpx.TimeoutException) as e:
            raise LostResponse(f"facilitator unreachable: {e}") from e
        if not s.success:
            raise RuntimeError(f"x402 settle failed: {s.error_reason}")
