"""Delegated offline operation: the person's phone can be off while their agent executes what they
signed.

When the person sets their rules, one Touch ID signs a delegation grant: which scopes (tier x
purpose x institution class), until when, within what budget, plus the per-kind buyer-grade bars.
For each scope the page derives a scope key from the passkey root and wraps it to the person's
hosted agent (its X25519 key, in a TEE or HSM in production, a sealed keystore here). The grant is
stored and its hash anchored, Verifiable-Intent style.

The hosted agent is a tool executing that signed grant, never a proxy deciding for the person:
  - inside a scope: derives the trade key from the scope key, seals, pushes, settles
  - outside every scope: queues "needs you" for the next time the phone is on
  - T0-T1 can be delegated; T2 only if the person opted in; T3 never (genomic, imaging,
    mental and reproductive health: a fresh Touch ID every time)
Revoking from the phone signs a new grant version. The agent drops every key of the old version at
once, and requests under it are refused.

Stealing the hosted agent gives: the delegated scopes only, within budget and time, never T3.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.signing import SigningKey, VerifyKey

from ..catalog.columns import TIERS
from .keys import hkdf

NEVER_DELEGATED = "T3"


def _canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def scope_id(s: dict) -> str:
    return f"{s['tier']}|{s['purpose']}|{s['inst_class']}"


@dataclass
class Grant:
    owner: str
    version: int
    scopes: list                 # [{tier, purpose, inst_class}]
    until: float
    budget_drops: int
    t2_opt_in: bool = False
    bars: dict = field(default_factory=dict)
    sig: str = ""

    def body(self) -> dict:
        return {"owner": self.owner, "version": self.version, "scopes": self.scopes, "until": self.until,
                "budget_drops": self.budget_drops, "t2_opt_in": self.t2_opt_in, "bars": self.bars}

    @property
    def hash(self) -> str:
        return hashlib.sha256(_canon(self.body())).hexdigest()


class Phone:
    """The person's device: holds the passkey root (only while used) and signs grants with Touch ID."""

    def __init__(self, pid: str, root: bytes, device_key: SigningKey | None = None):
        self.pid, self._root = pid, root
        self.key = device_key or SigningKey.generate()
        self.version = 0

    @property
    def public(self) -> str:
        return bytes(self.key.verify_key).hex()

    def delegate(self, agent_pub: bytes, scopes: list, until: float, budget_drops: int, t2_opt_in=False,
                 bars=None) -> tuple[Grant, dict]:
        for s in scopes:
            if s["tier"] == NEVER_DELEGATED:
                raise ValueError("T3 is never delegated: a fresh Touch ID every time")
            if s["tier"] == "T2" and not t2_opt_in:
                raise ValueError("T2 is delegated only if the person opted in")
        self.version += 1
        g = Grant(self.pid, self.version, scopes, until, budget_drops, t2_opt_in, bars or {})
        g.sig = self.key.sign(_canon(g.body())).signature.hex()
        box = SealedBox(PublicKey(agent_pub))
        wrapped = {scope_id(s): box.encrypt(self.scope_key(s, g.version)).hex() for s in scopes}
        return g, wrapped

    def scope_key(self, s: dict, version: int) -> bytes:
        return hkdf(self._root, f"scope|{scope_id(s)}|v{version}")

    def revoke(self) -> Grant:
        """A new, empty grant version: the agent loses every scope at once."""
        self.version += 1
        g = Grant(self.pid, self.version, [], 0, 0)
        g.sig = self.key.sign(_canon(g.body())).signature.hex()
        return g


class HostedAgent:
    """Runs while the phone is off. Holds only wrapped scope keys and its own unwrap key."""

    def __init__(self, owner_device_pub: str, clock=time.time):
        self._box = PrivateKey.generate()
        self.owner_pub = owner_device_pub
        self.clock = clock
        self.grant: Grant | None = None
        self._keys: dict[str, bytes] = {}
        self.spent = 0
        self.queue: list[dict] = []          # "needs you", shown when the phone is next on
        self.log: list[dict] = []

    @property
    def public(self) -> bytes:
        return bytes(self._box.public_key)

    def install(self, g: Grant, wrapped: dict) -> str | None:
        try:
            VerifyKey(bytes.fromhex(self.owner_pub)).verify(_canon(g.body()), bytes.fromhex(g.sig))
        except Exception:
            return "grant not signed by the owner's device"
        if self.grant and g.version <= self.grant.version:
            return "stale grant version"
        self.grant = g
        self._keys = {sid: SealedBox(self._box).decrypt(bytes.fromhex(w)) for sid, w in wrapped.items()}
        self.spent = 0
        return None

    def apply_revocation(self, g: Grant) -> str | None:
        err = self.install(g, {})
        return err

    def handle(self, req: dict) -> dict:
        """req: {trade, tier, purpose, inst_class, price_drops}. Returns the action taken."""
        g = self.grant
        why = None
        if req["tier"] == NEVER_DELEGATED:
            why = "T3 needs a fresh Touch ID every time"
        elif g is None or not g.scopes:
            why = "no active delegation"
        elif self.clock() > g.until:
            why = "delegation expired"
        elif self.spent + req["price_drops"] > g.budget_drops:
            why = "delegated budget reached"
        else:
            s = next((s for s in g.scopes if s["purpose"] == req["purpose"] and s["inst_class"] == req["inst_class"]
                      and TIERS.index(req["tier"]) <= TIERS.index(s["tier"])), None)
            if s is None:
                why = "outside the scopes you signed"
        if why:
            q = {**req, "status": "needs_owner", "why": why}
            self.queue.append(q)
            self.log.append(q)
            return q
        sk = self._keys[scope_id(s)]
        k = hkdf(sk, f"trade|{req['trade']}")
        self.spent += req["price_drops"]
        out = {**req, "status": "executed", "why": f"within the grant you signed (v{g.version}, {scope_id(s)})",
               "grant": g.hash, "trade_key_id": hashlib.sha256(k).hexdigest()[:16]}
        self.log.append(out)
        return out
