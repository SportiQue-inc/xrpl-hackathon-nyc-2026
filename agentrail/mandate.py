"""Signed delegation chain for agent payments (Verifiable Intent L1 -> L2 -> L3, ES256 SD-JWT).

L1  issuer -> institution: the institution may spend up to a ceiling in XRP on XRPL.
L2  owner -> agent key: the owner's mandate (per-transaction max, total max, purposes, payees,
    expiry), bound to the agent's public key. This is the signed form of the `mandates` row.
L3  agent -> one order: invoice, amount, payee, order content hash, bound to L2 by sd_hash.

The engine verifies the whole chain right before any money moves. The `mandates` table can be
changed by code or by mistake; the owner's signature cannot. So an LLM-proposed order, or a raised
budget row, that the owner never signed is refused. Built on `x402_xrpl.vi` (signing); the
verification below is ours (the SDK has none). Private keys stay in memory; only public JWKs and
presentations are stored.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
from x402_xrpl.vi import (generate_ec_private_jwk, public_jwk_from_private_jwk, sd_hash_of_presentation,
                          sign_l2_delegation, sign_l3_final_action)
from x402_xrpl.vi.chain import _make_disclosure, _sign_jws

AUD = "agentrail"


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _verify_jws(jws: str, public_jwk: dict) -> dict:
    """ES256 compact JWS -> payload, or raises ValueError."""
    try:
        h, p, sig = jws.split(".")
        raw = _b64d(sig)
        pub = ec.EllipticCurvePublicNumbers(int.from_bytes(_b64d(public_jwk["x"]), "big"),
                                            int.from_bytes(_b64d(public_jwk["y"]), "big"),
                                            ec.SECP256R1()).public_key()
        der = utils.encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        pub.verify(der, f"{h}.{p}".encode("ascii"), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, KeyError) as e:
        raise ValueError(f"bad signature ({type(e).__name__})")
    return json.loads(_b64d(p))


def _disclosed(presentation: str, payload: dict) -> dict:
    """Disclosures whose digest is listed in the signed `_sd` array."""
    out = {}
    for d in presentation.split("~")[1:]:
        if not d:
            continue
        if base64.urlsafe_b64encode(hashlib.sha256(d.encode("ascii")).digest()).rstrip(b"=").decode() in payload.get("_sd", []):
            _, name, value = json.loads(_b64d(d))
            out[name] = value
    return out


def presentation_hash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()[:16]


class MandateChain:
    """Keys and presentations for one buyer. `issue` is called by the owner (with the issuer)."""

    def __init__(self, buyer_id: str):
        self.buyer_id = buyer_id
        self.issuer_key = generate_ec_private_jwk(kid=f"{buyer_id}-issuer")
        self.owner_key = generate_ec_private_jwk(kid=f"{buyer_id}-owner")
        self.agent_key = generate_ec_private_jwk(kid=f"{buyer_id}-agent")
        self.issuer_pub = public_jwk_from_private_jwk(self.issuer_key)
        self.owner_pub = public_jwk_from_private_jwk(self.owner_key)
        self.agent_pub = public_jwk_from_private_jwk(self.agent_key)
        self.l1 = self.l2 = None
        self.payees: list[str] | None = None
        self.ceiling_drops = 0

    def issue_from(self, mandate_row, store=None):
        """Owner signs the current mandate (after a co-signed budget change, for example)."""
        self.issue(max(self.ceiling_drops, mandate_row["total_drops"]), mandate_row["per_order_limit_drops"],
                   mandate_row["total_drops"], json.loads(mandate_row["purposes"]), self.payees)
        if store is not None:
            store.log(self.buyer_id, "mandate", f"owner signed the agent's delegation: up to "
                      f"{mandate_row['per_order_limit_drops'] / 1e6:g} XRP per payment, "
                      f"{mandate_row['total_drops'] / 1e6:g} XRP in total "
                      f"(Verifiable Intent L2 {presentation_hash(self.l2)})", {"l2": presentation_hash(self.l2)})

    def issue(self, ceiling_drops: int, per_tx_drops: int, total_drops: int, purposes: list[str],
              payees: list[str] | None, ttl_s: int = 24 * 3600, now: int | None = None):
        now = int(now if now is not None else time.time())
        disc, dig = _make_disclosure("credential", {"subject": self.buyer_id, "allowedChains": ["xrpl"],
                                                    "allowedAssets": ["XRP"], "spendingCeiling": ceiling_drops})
        l1 = _sign_jws({"alg": "ES256", "typ": "vc+sd-jwt", "kid": self.issuer_key["kid"]},
                       {"iss": "issuer", "sub": self.buyer_id, "aud": AUD, "iat": now, "exp": now + 30 * 86400,
                        "cnf": {"jwk": self.owner_pub}, "_sd": [dig], "_sd_alg": "sha-256"}, self.issuer_key)
        self.l1 = f"{l1}~{disc}~"
        self.l2 = sign_l2_delegation(
            owner_private_jwk=self.owner_key, agent_public_jwk=self.agent_pub, owner_kid=self.owner_key["kid"],
            agent_kid=self.agent_key["kid"], l1_presentation=self.l1, audience=AUD, now=now, ttl_seconds=ttl_s,
            constraints={"per_transaction_max": per_tx_drops, "total_max": total_drops,
                         "allowed_purposes": sorted(purposes), "allowed_payees": sorted(payees) if payees else ["*"]})
        return self.l2

    def sign_order(self, order: dict, now: int | None = None) -> str:
        """The agent's final action for one order (AP2 cart/payment mandate equivalent)."""
        return sign_l3_final_action(
            agent_private_jwk=self.agent_key, agent_kid=self.agent_key["kid"], l2_presentation=self.l2,
            audience=AUD, now=now, ttl_seconds=3600,
            transaction={"paymentRequirementsHash": order["content_hash"], "invoiceId": order["invoice_id"],
                         "amount": order["amount_drops"], "payTo": order["payee_id"], "orderId": order["order_id"],
                         "purpose": order["purpose"]})


def verify(l1: str, l2: str, l3: str, issuer_pub: dict, order: dict, committed_drops: int,
           now: int | None = None) -> tuple[bool, str]:
    """Check the chain for one order. committed_drops = spent + reserved by other orders."""
    now = int(now if now is not None else time.time())
    try:
        p1 = _verify_jws(l1.split("~")[0], issuer_pub)
        cred = _disclosed(l1, p1).get("credential", {})
        owner_pub = p1["cnf"]["jwk"]
        p2 = _verify_jws(l2.split("~")[0], owner_pub)
    except ValueError as e:
        return False, f"owner delegation not signed by the institution's owner key: {e}"
    if p2.get("sd_hash") != sd_hash_of_presentation(l1):
        return False, "owner delegation is not bound to this institution credential"
    if p2.get("exp", 0) < now or p1.get("exp", 0) < now:
        return False, "owner delegation expired"
    c = _disclosed(l2, p2).get("constraints", {})
    try:
        p3 = _verify_jws(l3.split("~")[0], p2["cnf"]["jwk"])
    except ValueError as e:
        return False, f"order not signed by the delegated agent key: {e}"
    if p3.get("sd_hash") != sd_hash_of_presentation(l2):
        return False, "order is not bound to the owner's delegation"
    if p3.get("exp", 0) < now:
        return False, "order signature expired"
    t = p3.get("transaction", {})
    for k, v in (("invoiceId", order["invoice_id"]), ("amount", order["amount_drops"]),
                 ("payTo", order["payee_id"]), ("paymentRequirementsHash", order["content_hash"])):
        if t.get(k) != v:
            return False, f"signed order differs from the payment ({k})"
    amt = order["amount_drops"]
    if amt > c.get("per_transaction_max", 0):
        return False, f"{amt / 1e6:g} XRP is above the owner's signed per-transaction max {c.get('per_transaction_max', 0) / 1e6:g}"
    if committed_drops + amt > c.get("total_max", 0):
        return False, f"would exceed the owner's signed total {c.get('total_max', 0) / 1e6:g} XRP"
    if committed_drops + amt > cred.get("spendingCeiling", 0):
        return False, "above the institution's spending ceiling"
    if order["purpose"] not in c.get("allowed_purposes", []):
        return False, f"purpose '{order['purpose']}' not in the owner's signed mandate"
    payees = c.get("allowed_payees", [])
    if "*" not in payees and order["payee_id"] not in payees:
        return False, f"payee {order['payee_id']} not in the owner's signed mandate"
    return True, "ok"
