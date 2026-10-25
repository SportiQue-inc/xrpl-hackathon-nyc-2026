"""Each contribution (one provider, one window) is checked against its contract as it arrives.

Before the escrow is created (no values needed, nothing paid yet): the manifest. Holder signature,
contract hash, issuer signatures and DATA_SOURCE Credentials, the export made for this holder, the
slots inside the window. A failure here means no escrow: nothing is paid.

After the key is revealed (the 80% is paid at that moment, as the key-reveal escrow requires): the
values. Native values match the attestation, normalization reproduces the rows, completeness per
column meets the contract, values sit in the unit's possible range (a factor of 60 off is reported as
a unit error), the window mean stays within the drift tolerance of the profile the provider shared,
and the series was not already delivered by another provider. The 20% held for this contribution is
released only when it passes; a failure goes to a named reviewer.

Code decides every check. No LLM is involved.
"""
from __future__ import annotations

import hashlib

from . import market
from .profile import _num
from .provenance import (Holder, manifest, open_sealed, seal_values, values_hash, verify_manifest, verify_seals,
                         verify_values, wrap_key)
from .terms import canonical

PRE = {"bad_signature", "wrong_contract", "wrong_source", "different_person", "wrong_period", "tampered", "unsealed"}
POST_SEAL = {"unopenable"}
POST = {"tampered", "incomplete", "wrong_unit", "impossible_value", "drift", "duplicate"}


def holder_for(provider_id: str, buyer: str) -> Holder:
    return Holder(hashlib.sha256(f"holder|{provider_id}|{buyer}".encode()).digest())


# ---------------- provider side ----------------

def deliver(p: market.Provider, contract, wnum: int, issuers: dict, consent_hash: str,
            twins: dict | None = None, key: bytes | None = None) -> dict:
    """What the provider's agent seals for one window: rows, native values, manifest. Faults in the
    synthetic provider change what it sends; the code that checks it does not know about them."""
    fault = next((p.faults[w] for w in sorted(p.faults) if w <= wnum), None)
    me = holder_for(p.id, contract.buyer)
    lo, hi = market.slots_for_window(wnum)
    src_w = wnum - 2 if fault == "wrong_period" else wnum
    a, b = market.slots_for_window(src_w)
    slots = list(range(a, b + 1))
    rows = [{"slot": s} for s in range(lo, hi + 1)]
    native, atts, steps, sealed, wrapped = {}, [], [], {}, {}
    for t in contract.terms:
        if wnum not in t["windows"]:
            continue
        col = t["column"]
        if col not in p.cols:
            vals = [None] * market.SLOTS
        elif fault == "duplicate" and twins and col in twins.cols:
            vals = twins.native(col, src_w)
        else:
            sd = market.MEANS[col][1]
            vals = p.native(col, src_w, value_offset=4 * sd if fault == "drift" else 0.0)
        factor = p.factor(col) if col in p.cols else 1.0
        if fault == "wrong_unit" and col == "sleep_minutes":
            factor = 1.0
            vals = [None if v is None else round(v / 60, 2) if p.cols[col].native_unit != "h/day" else v
                    for v in vals]
        native[col] = vals
        for r, v in zip(rows, vals):
            r[col] = None if v is None else round(v * factor, 3)
        issuer = issuers["unknown_app"] if fault == "wrong_source" else issuers[p.cols[col].source if col in p.cols
                                                                                  else t["source"]]
        holder = holder_for(f"other-of-{p.id}", contract.buyer).pub if fault == "different_person" else me.pub
        if key is None:
            atts.append(issuer.attest(holder, col, slots, vals))
        else:
            # stamped at intake: the source sealed and signed these records when they entered the
            # person's store; the agent only wraps the intake key with the escrow's K
            ik = hashlib.sha256(f"intake|{p.id}|{col}|{src_w}".encode()).digest()
            a, blob = issuer.seal(holder, col, slots, vals, ik)
            if fault == "tampered":
                # the provider "improves" values after intake; it can re-encrypt them with the intake
                # key, but cannot sign as the source
                vals = [None if v is None else round(v * 1.15, 3) for v in vals]
                native[col] = vals
                for r, v in zip(rows, vals):
                    r[col] = None if v is None else round(v * factor, 3)
                blob = seal_values(vals, ik, col)
            atts.append(a)
            sealed[col] = blob.hex()
            wrapped[col] = wrap_key(ik, key, col)
        steps.append({"column": col, "from": p.cols[col].native_unit if col in p.cols else t["unit"],
                      "to": t["unit"], "factor": factor})
    qc = {"rows": len(rows), "filled": {c: sum(v is not None for v in vs) for c, vs in native.items()}}
    m = manifest(me, contract.hash, consent_hash, wnum, atts, steps, qc)
    return {"rows": rows, "native": native, "manifest": m, **({"sealed": sealed, "wrapped": wrapped} if key is not None else {})}


# ---------------- buyer side ----------------

def precheck(m: dict, contract, registry, payload: dict | None = None) -> list[dict]:
    out = verify_manifest(m, registry, contract, contract.holder or None, market.slots_for_window)
    if payload is not None and "sealed" in payload:
        out += verify_seals(m, payload)
    return out


def _series_key(native: dict) -> str:
    return hashlib.sha256(canonical(sorted((c, v) for c, v in native.items())).encode()).hexdigest()


def check_values(payload: dict, contract, profile: dict, seen: dict, provider: str,
                 key: bytes | None = None) -> list[dict]:
    m, out = payload["manifest"], verify_values(payload["manifest"], payload)
    if key is not None and payload.get("sealed"):
        out += open_sealed(m, payload, key)
    wnum = m["window"]
    for t in contract.terms:
        if wnum not in t["windows"]:
            continue
        col = t["column"]
        meta = market.COLUMNS[col]
        vals = [_num(r.get(col), None) for r in payload["rows"]]
        have = [v for v in vals if v is not None]
        comp = len(have) / market.SLOTS
        if comp < t["min_completeness"]:
            out.append({"code": "incomplete", "column": col, "completeness": round(comp, 2),
                        "minimum": t["min_completeness"]})
        if have:
            inside = [v for v in have if meta.lo <= v <= meta.hi]
            if len(inside) < 0.9 * len(have):
                scaled = [v for v in have if meta.lo <= v * 60 <= meta.hi or meta.lo <= v / 60 <= meta.hi]
                code = "wrong_unit" if len(scaled) >= 0.9 * len(have) else "impossible_value"
                out.append({"code": code, "column": col, "values": have[:3]})
            else:
                d = profile["columns"].get(col, {}).get("distribution")
                if d and d["sd"]:
                    z = abs(sum(have) / len(have) - d["mean"]) / (d["sd"] / max(1, len(have)) ** 0.5)
                    if z > t["drift_sd"] * 1.5:
                        out.append({"code": "drift", "column": col, "z": round(z, 1)})
        key = (wnum, col, values_hash(payload["native"].get(col)))
        if have and seen.setdefault(key, provider) != provider:
            out.append({"code": "duplicate", "column": col, "detail": "series already delivered by another provider"})
    return out


def verdict(signals: list[dict]) -> str:
    return "pass" if not signals else "fail"
