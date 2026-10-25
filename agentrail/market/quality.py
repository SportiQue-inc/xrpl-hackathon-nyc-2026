"""Pre-trade quality certificate: what a buyer can know about data before paying for it.

  profile     the seller's agent states, per column, completeness, sampling rate, drift and the source
              issuer, and signs it (Ed25519). A person's few weeks and a company's whole dataset get
              the same certificate; only the row count differs.
  commitment  every row is hashed with its own salt and the hashes form a Merkle tree. The root is in
              the certificate. The buyer then picks random rows (after the root is fixed), the seller
              opens them with proofs, and the buyer checks them against the root and the stated profile.
              The delivered data must hash to the same root, so the seller cannot show good rows first
              and deliver others.
  reputation  the issuer's Credential (on the ledger) and the seller's past fitness pass rate, as a
              Beta(1+pass, 1+fail) mean so a newcomer starts at 0.5, not at 0 or 1.
  grade       A, B or C from the sample-checked completeness and the reputation. The offer carries the
              grade; price per grade is a fixed quote. A delivery below the grade fails the fitness
              check: the seller's grade falls for every later offer and a refund claim is recorded.
"""
from __future__ import annotations

import hashlib
import json
import os
import random

from nacl.signing import SigningKey, VerifyKey


def _h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()


def leaf(row: dict, salt: str) -> bytes:
    return _h(b"\x00" + salt.encode() + _canon(row))


def merkle(leaves: list[bytes]) -> list[list[bytes]]:
    levels = [leaves or [_h(b"")]]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt = [_h(b"\x01" + cur[i] + (cur[i + 1] if i + 1 < len(cur) else cur[i])) for i in range(0, len(cur), 2)]
        levels.append(nxt)
    return levels


def proof(levels, i: int) -> list[str]:
    out = []
    for lvl in levels[:-1]:
        j = i ^ 1
        out.append((lvl[j] if j < len(lvl) else lvl[i]).hex())
        i //= 2
    return out


def verify_proof(root_hex: str, row: dict, salt: str, i: int, path: list[str]) -> bool:
    h = leaf(row, salt)
    for sib in path:
        s = bytes.fromhex(sib)
        h = _h(b"\x01" + (h + s if i % 2 == 0 else s + h))
        i //= 2
    return h.hex() == root_hex


class Committed:
    """The seller's side: rows with per-row salts, committed before any buyer looks."""

    def __init__(self, rows: list[dict], salts: list[str] | None = None):
        self.rows = rows
        self.salts = salts or [os.urandom(8).hex() for _ in rows]
        self.levels = merkle([leaf(r, s) for r, s in zip(rows, self.salts)])

    @property
    def root(self) -> str:
        return self.levels[-1][0].hex()

    def open(self, idx: list[int]) -> list[dict]:
        return [{"i": i, "row": self.rows[i], "salt": self.salts[i], "proof": proof(self.levels, i)} for i in idx]


def profile(rows: list[dict], columns: dict, issuer: dict, slots_per_day: float = 1.0) -> dict:
    """Per column: completeness, sampling rate, drift (second half vs first half, in SDs), issuer."""
    out = {}
    for c, spec in columns.items():
        vals = [r.get(c) for r in rows]
        xs = [v for v in vals if isinstance(v, (int, float))]
        comp = len([v for v in vals if v is not None]) / max(1, len(vals))
        drift = 0.0
        if len(xs) >= 6:
            a, b = xs[: len(xs) // 2], xs[len(xs) // 2:]
            mu = sum(a) / len(a)
            sd = (sum((x - mu) ** 2 for x in a) / len(a)) ** 0.5 or 1.0
            drift = round(abs(sum(b) / len(b) - mu) / sd, 2)
        out[c] = {"completeness": round(comp, 3), "sampling_per_day": slots_per_day, "drift_sd": drift,
                  "issuer": issuer.get(c, "unknown"), "unit": spec.get("unit", "")}
    return out


GRADES = (("A", 0.9, 0.7), ("B", 0.75, 0.5), ("C", 0.55, 0.0))       # (grade, min completeness, min reputation)


def reputation(passed: int, failed: int, issuer_credential: bool) -> float:
    r = (1 + passed) / (2 + passed + failed)
    return round(r if issuer_credential else r * 0.5, 3)


def grade(min_completeness: float, rep: float) -> str | None:
    for g, c, r in GRADES:
        if min_completeness >= c and rep >= r:
            return g
    return None


class Seller:
    def __init__(self, sid: str, key: SigningKey | None = None):
        self.sid = sid
        self.key = key or SigningKey.generate()

    @property
    def public(self) -> str:
        return bytes(self.key.verify_key).hex()

    def certify(self, dataset: str, rows: list[dict], columns: dict, issuer: dict, rep: float,
                committed: Committed, scope: str = "person") -> dict:
        prof = profile(rows, columns, issuer)
        mc = min((p["completeness"] for p in prof.values()), default=0.0)
        body = {"seller": self.sid, "dataset": dataset, "scope": scope, "rows": len(rows), "columns": prof,
                "root": committed.root, "reputation": rep, "grade": grade(mc, rep)}
        sig = self.key.sign(_canon(body)).signature.hex()
        return {**body, "seller_key": self.public, "sig": sig}


def check_certificate(cert: dict) -> str | None:
    body = {k: v for k, v in cert.items() if k not in ("seller_key", "sig")}
    try:
        VerifyKey(bytes.fromhex(cert["seller_key"])).verify(_canon(body), bytes.fromhex(cert["sig"]))
    except Exception:
        return "certificate signature does not verify"
    return None


def sample_indices(n: int, k: int, buyer_nonce: str) -> list[int]:
    """Chosen by the buyer after the root is fixed."""
    rng = random.Random(f"{buyer_nonce}")
    return sorted(rng.sample(range(n), min(k, n)))


def check_sample(cert: dict, opened: list[dict], columns: dict, tolerance: float = 0.05) -> tuple[bool, str]:
    """The buyer's pre-trade check: proofs against the root, values in range, completeness near the claim."""
    for o in opened:
        if not verify_proof(cert["root"], o["row"], o["salt"], o["i"], o["proof"]):
            return False, f"row {o['i']} does not match the committed root"
    for c, spec in columns.items():
        vals = [o["row"].get(c) for o in opened]
        xs = [v for v in vals if isinstance(v, (int, float))]
        lo, hi = spec.get("lo"), spec.get("hi")
        if lo is not None and any(not lo <= x <= hi for x in xs):
            return False, f"{c}: sampled value outside {lo}-{hi}"
        comp = len([v for v in vals if v is not None]) / max(1, len(vals))
        claim = cert["columns"][c]["completeness"]
        slack = 2 * (claim * (1 - claim) / max(1, len(vals))) ** 0.5 + tolerance   # two binomial SDs
        if comp + slack < claim:
            return False, f"{c}: sample completeness {comp:.2f} well below the stated {cert['columns'][c]['completeness']}"
    return True, "sample matches the certificate"


def delivery_matches(cert: dict, rows: list[dict], salts: list[str]) -> bool:
    return Committed(rows, salts).root == cert["root"]
