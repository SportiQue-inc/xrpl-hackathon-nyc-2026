"""Cohort lots: the agents assemble k people before anything leaves.

A buyer taking one person at a time can never pass a k-anonymity check, and a lone seller waits
forever. So when a need arrives, the sellers' agents whose data matches (same domain and tier bundle,
the columns asked for, the grade asked for, inside each person's own rules) join a pending lot. The
lot is released only when it holds at least k people and every combination of the released
quasi-identifiers appears at least k times in it; until then the agents keep recruiting, or coarsen
the quasi-identifiers (region, then age group, then sex). Below k, nothing leaves.

Verification is per lot: each member's agent attests consent scope, provenance (the intake stamps)
and the quality grade, and the buyer checks the lot once. Delivery is one sealed push of the lot into
the buyer's store; payment is still one key-reveal escrow per member, so each person is paid for
exactly their own part.

Lowers the risk that a record is linked back to a person; it does not remove it.
"""
from __future__ import annotations

import hashlib
import random

from ..catalog import columns as catalog
from ..catalog.scope import TouchID
from ..db import Store
from ..engine import Engine
from ..ledger.mock import MockLedger
from ..vault import keys as K
from ..vault.delivery import PushDelivery
from . import products
from .exchange import quote

LEVELS = [["age_group", "sex", "region"], ["age_group", "sex"], ["sex"], []]
TAP_HOURS = (2, 30)          # a person answering a one-tap request, in hours (synthetic)


def k_check(members: list[dict], k: int) -> tuple[list[str] | None, int]:
    """The least coarse level at which every released combination occurs at least k times."""
    if len(members) < k:
        return None, len(members)
    for i, keys in enumerate(LEVELS):
        groups = {}
        for m in members:
            groups.setdefault(tuple(m["qi"][x] for x in keys), []).append(m)
        if min(len(g) for g in groups.values()) >= k:
            return keys, i
    return None, len(members)


def _member(pid, p, home, cols, tier, rng, tap_ok) -> dict | None:
    holds = [catalog.canon(c) for c in p["holds"].get("health", []) if catalog.canon(c) in catalog.CATALOG]
    holds, _ = products.collect(pid, holds, __import__("agentrail.market.acts", fromlist=["x"]).connected_sources(pid))
    if not set(cols) <= set(holds) or tier in p.get("never", []) or home != "KR":
        return None
    if any(products.DOMAIN_OF.get(c) == "genomic" for c in cols):
        return None
    auto = tier in p.get("auto_tiers", ["T0"])
    if not auto and not tap_ok:
        return None
    return {"pid": pid, "home": home, "qi": products.quasi(pid, home), "how": "auto" if auto else "tap",
            "joined_h": 0.0 if auto else round(rng.uniform(*TAP_HOURS), 1)}


def form(need: dict, prof: dict, k: int = products.K_ANON, seed: int = 5, tap_ok: bool = True) -> dict:
    """need: {id, institution, columns, weeks}. Members join in the order their agents answer."""
    rng = random.Random(f"{seed}|{need['id']}")
    people = sorted(prof["participants"])
    tier = products._tier(need["columns"])
    dom = {products.DOMAIN_OF.get(c) for c in need["columns"]}
    if len(dom) != 1:
        return {"need": need["id"], "status": "refused", "why": "a lot never spans two domains"}
    pool = [m for i, pid in enumerate(people)
            if (m := _member(pid, prof["participants"][pid], "MN" if i >= len(people) - 2 else "KR",
                             need["columns"], tier, rng, tap_ok))]
    pool.sort(key=lambda m: (m["joined_h"], m["pid"]))
    want = need.get("quantity", 3 * k)
    lot, keys, fill_h = [], None, None
    for m in pool:
        lot.append(m)
        got, _ = k_check(lot, k)
        if got is not None and (keys is None or len(got) > len(keys)):
            keys = got
        if len(lot) >= want and keys is not None:
            break
    keys, _ = k_check(lot, k)           # what the final lot can release
    fill_h = lot[-1]["joined_h"] if lot else None
    if keys is None:
        return {"need": need["id"], "status": "pending", "members": len(lot), "k": k, "tier": tier,
                "why": f"{len(lot)} matching people; the lot stays closed until k={k} share every released combination"}
    price = quote(need["columns"], need["weeks"], "B")
    return {"need": need["id"], "status": "released", "institution": need["institution"], "domain": dom.pop(),
            "tier": tier, "columns": need["columns"], "k": k, "members": [m["pid"] for m in lot],
            "joined": {m["pid"]: {"how": m["how"], "h": m["joined_h"]} for m in lot},
            "released_quasi": keys, "fill_h": fill_h, "price_per_member_drops": price,
            "generalized": [x for x in LEVELS[0] if x not in keys]}


def deliver(lot: dict, prof: dict, ledger=None) -> dict:
    """One sealed push of the lot to the buyer; one escrow per member."""
    insts = {i["id"]: i for i in prof["institutions"]}
    inst = insts[lot["institution"]]
    pd = PushDelivery(Engine(Store(":memory:"), ledger or MockLedger()))
    key = K.InstitutionKey()
    pd.register_institution(inst["id"], inst["country"], key)
    pk = K.SoftPasskey()
    member_hashes, paid = [], 0
    for pid in lot["members"]:
        c = products.candidates(pid, lot["columns"], lambda c: "wearable_a")[0]
        qi = {x: products.quasi(pid, "KR")[x] for x in lot["released_quasi"]}
        released = products.deidentify_rows(pid, inst["id"], c["rows"], lot["columns"], {**qi, "country": "KR"})
        r = products.sell(pd, pid, inst["id"], inst["study"], {**c, "price_drops": lot["price_per_member_drops"]},
                          released, pk)
        paid += lot["price_per_member_drops"] if r["paid"] else 0
        member_hashes.append(r["escrow_create"])
    lot_hash = hashlib.sha256("|".join(sorted(h or "" for h in member_hashes)).encode()).hexdigest()
    return {"lot": lot["need"], "pushed_to": inst["id"], "members_paid": sum(1 for h in member_hashes if h),
            "paid_drops": paid, "lot_hash": lot_hash, "carries_person_id": False}


def run(prof: dict | None = None, k: int = products.K_ANON) -> dict:
    """Every open posting and a few everyday needs, one person at a time against lots."""
    from . import acts
    prof = prof or acts.load()
    needs = [{"id": p["posting"], "institution": p["institution"], "columns": part, "weeks": 8}
             for p in products.postings(prof) for _, _, part in products.bundles(p["columns"])
             if not any(products.DOMAIN_OF.get(c) in ("genomic", "imaging") for c in part)]
    insts = sorted(i["id"] for i in prof["institutions"] if i["country"] == "KR")
    for i, cols in enumerate([["sleep.daily"], ["heart_rate.daily"], ["mood.score", "fatigue.survey"]]):
        needs.append({"id": f"everyday-{i + 1}", "institution": insts[i % len(insts)], "columns": cols, "weeks": 8})
    lots = [form(n, prof, k) for n in needs]
    one_at_a_time = sum(1 for n in needs if k_check([{"qi": {}}], k)[0] is not None)     # a lot of one never passes
    rel = [x for x in lots if x["status"] == "released"]
    return {"k": k, "needs": len(needs), "lots_released": len(rel), "lots_pending": len(lots) - len(rel),
            "cleared_one_at_a_time": one_at_a_time,
            "median_fill_h": sorted(x["fill_h"] for x in rel)[len(rel) // 2] if rel else None,
            "lots": lots}
