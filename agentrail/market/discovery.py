"""How a buyer's agent gets from "I am missing something" to one counterparty.

1. Need formation. The agent compares what its own store holds with what its owner wants, finds the
   gap, and asks the LLM to turn that into a need: columns, weeks, quality floor, a price ceiling inside
   the owner's budget, and the reason. Code checks every field (columns must be in the gap, the ceiling
   inside the budget, weeks and grade in range); a proposal that fails is replaced by the rule.
2. Discovery. Sellers' agents list their certified datasets in one shared offer book. The book's
   Merkle root is anchored on the ledger in a payment memo, so every agent reads the same list and a
   listing that is not in the anchored book is ignored. The off-ledger registry is only the index.
3. Comparison. The candidates that survive the filters (columns, weeks, seller attributes, grade) and
   the hashed-sample check are scored: quality grade, price against the ceiling, seller track record.
4. Negotiation. The agent bargains with the best candidates in order: it opens below the ask, the
   seller's agent concedes toward its floor, and they meet or walk away. The LLM may explain the
   ranking in words; it never changes the ranking or the price.
"""
from __future__ import annotations

import hashlib
import json
import os

from ..reasoning import _ask

GRADE_RANK = {"A": 3, "B": 2, "C": 1}

NEED_SYSTEM = """You are the purchasing agent of one account in a data market. You see what your store
already holds, the gap against what your owner wants, the owner's budget and the asking prices by quality
grade. Decide the need. Reply with JSON only:
{"columns": [...], "weeks": int, "min_grade": "A"|"B"|"C", "max_price_drops": int, "why": "one or two sentences"}
Use only columns from the gap. Keep max_price_drops at or below budget_per_item_drops."""

PICK_SYSTEM = """You are a buyer's agent explaining a purchase you already decided. You get the need and
the scored candidates in rank order with the negotiation outcome. In plain words, say why the chosen
seller won and why each other candidate lost. Do not change the choice. Reply with JSON only:
{"why": "...", "others": {"<seller id>": "<reason>", ...}}"""


# ---------------- 1. need formation ----------------

def gap(holds: list[str], wants: list[str]) -> list[str]:
    have = set(holds)
    return [w for w in wants if w not in have]


def rule_need(col: str, weeks: int, budget_per_item: int, asks: dict) -> dict:
    return {"columns": [col], "weeks": weeks, "min_grade": "C",
            "max_price_drops": min(asks["A"] * 6 // 5, budget_per_item),
            "why": f"my store has no {col}; any grade C or better, up to 20% above the grade A asking price, "
                   f"inside the owner's budget"}


def form_need(buyer: str, holds: list[str], wants: list[str], col: str, weeks: int, quantity: int,
              budget_drops: int, open_needs: int, quote, propose=None, explain: bool = True) -> dict:
    """The agent's need for one gap column, with the reasoning text and who produced it."""
    g = gap(holds, wants)
    per_item = budget_drops // max(1, quantity * max(1, open_needs))
    asks = {gr: quote([col], weeks, gr) for gr in GRADE_RANK}
    base = rule_need(col, weeks, per_item, asks)
    inp = {"buyer": buyer, "holds": holds, "owner_wants": wants, "gap": g, "this_gap": col,
           "budget_drops": budget_drops, "budget_per_item_drops": per_item, "quantity": quantity,
           "asks_by_grade_drops": asks, "default_weeks": weeks}
    out, source, notes = None, "rules", []
    if explain:
        out, source = _ask(propose, NEED_SYSTEM, inp)
    need = dict(base)
    if isinstance(out, dict):
        cols = [c for c in out.get("columns") or [] if c in g]
        if cols != [col]:
            notes.append("columns outside this gap: kept the gap column")
        w = out.get("weeks")
        if isinstance(w, int) and 1 <= w <= 8:
            need["weeks"] = w
        elif w is not None:
            notes.append("weeks out of range: kept the default")
        if out.get("min_grade") in GRADE_RANK:
            need["min_grade"] = out["min_grade"]
        mp = out.get("max_price_drops")
        if isinstance(mp, int) and 0 < mp <= per_item:
            need["max_price_drops"] = mp
        elif mp is not None:
            notes.append(f"price ceiling {mp} above the budget per item {per_item}: kept {need['max_price_drops']}")
        if isinstance(out.get("why"), str) and out["why"].strip():
            need["why"] = out["why"].strip()[:400]
    else:
        source = "rules"
    return {**need, "holds": holds, "gap": g, "budget_drops": budget_drops, "budget_per_item_drops": per_item,
            "asks_by_grade_drops": asks, "quantity": quantity, "source": source, "checks": notes,
            "rule_weeks": weeks}


# ---------------- 2. shared offer book anchored on the ledger ----------------

def listing(o: dict) -> dict:
    ds = o["dataset"]
    body = {"seller": o["seller"], "dataset": ds.id, "columns": sorted(ds.columns), "weeks": ds.weeks,
            "cert_root": o["cert"]["root"]}
    return {**body, "id": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}


def merkle_root(leaves: list[str]) -> str:
    level = sorted(leaves) or [hashlib.sha256(b"").hexdigest()]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256((level[i] + level[i + 1]).encode()).hexdigest() for i in range(0, len(level), 2)]
    return level[0]


def proof(leaves: list[str], leaf: str) -> list[tuple[str, str]]:
    level, i, out = sorted(leaves), sorted(leaves).index(leaf), []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = i ^ 1
        out.append(("L" if sib < i else "R", level[sib]))
        level = [hashlib.sha256((level[j] + level[j + 1]).encode()).hexdigest() for j in range(0, len(level), 2)]
        i //= 2
    return out


def verify(leaf: str, path: list[tuple[str, str]], root: str) -> bool:
    h = leaf
    for side, sib in path:
        h = hashlib.sha256((sib + h if side == "L" else h + sib).encode()).hexdigest()
    return h == root


class OfferBook:
    """The index every agent queries. Its root is on the ledger; agents trust a listing only if it is in
    the anchored book."""

    def __init__(self, ledger, registry: str, sink: str):
        self.ledger, self.registry, self.sink = ledger, registry, sink
        self.listings: dict[str, dict] = {}
        self.root, self.anchor_tx, self.anchored_ids = None, None, frozenset()

    def publish(self, offers: list[dict]) -> dict:
        """List every certified dataset and anchor the book's root in a 1-drop payment memo."""
        for o in offers:
            li = listing(o)
            self.listings[li["id"]] = li
        ids = sorted(self.listings)
        self.root = merkle_root(ids)
        p = self.ledger.prepare_payment(self.registry, self.sink, 1, self.root[:64].upper(),
                                        f"agentrail:offerbook:{len(ids)}:{self.root}")
        self.ledger.submit(p)
        st = self.ledger.wait_validated(p.tx_hash, timeout=120)
        # agents take the root from the ledger, not from the registry
        if st.found and st.success and (st.invoice_id or "").lower() != self.root:
            raise RuntimeError("offer book root on the ledger differs from the registry")
        if st.found and not st.success:
            raise RuntimeError(f"offer book anchor failed on the ledger ({st.result})")
        self.anchor_tx, self.anchored_ids = p.tx_hash, frozenset(ids)
        return {"listings": len(ids), "root": self.root, "tx": p.tx_hash, "validated": bool(st.validated),
                "url": self.ledger.explorer_url(p.tx_hash)}

    def anchored(self, o: dict) -> bool:
        li = listing(o)
        return li["id"] in self.anchored_ids and verify(li["id"], proof(sorted(self.anchored_ids), li["id"]), self.root)


# ---------------- 3. scoring ----------------

def score(o: dict, ask: int, need: dict, track: tuple[int, int]) -> dict:
    """Quality, price against the ceiling, and the seller's track record, each 0..1."""
    q = GRADE_RANK[o["grade"]] / 3
    ceiling = max(1, need["max_price_drops"])
    p = max(0.0, 1 - ask / ceiling) if ask <= ceiling else 0.0
    passed, failed = track
    t = (1 + passed) / (2 + passed + failed)
    s = round(0.45 * q + 0.35 * p + 0.20 * t, 4)
    return {"seller": o["seller"], "dataset": o["dataset"].id, "grade": o["grade"], "ask_drops": ask,
            "score": s, "parts": {"quality": round(q, 3), "price": round(p, 3), "track": round(t, 3)},
            "over_ceiling": ask > ceiling}


# ---------------- 4. negotiation ----------------

def negotiate(ask: int, ceiling: int, track: tuple[int, int], rounds: int = 4) -> dict:
    """The buyer opens at 80% of the ask; the seller's agent concedes toward its floor (90% of the ask,
    95% when its record is shaky). A deal is the first bid at or above the seller's standing price."""
    passed, failed = track
    floor = int(ask * (0.95 if failed > passed else 0.90))
    bid, counter, log = min(int(ask * 0.80), ceiling), ask, []
    for r in range(1, rounds + 1):
        log.append({"round": r, "bid": bid, "counter": counter})
        if bid >= counter:
            return {"deal": True, "price_drops": counter, "rounds": log, "floor": floor}
        counter = max(floor, counter - (counter - floor) // 2 - 1)
        bid = min(ceiling, bid + (ask - bid) // 3 + 1)
        if bid >= counter:
            log.append({"round": r + 1, "bid": bid, "counter": counter})
            return {"deal": True, "price_drops": counter, "rounds": log, "floor": floor}
    return {"deal": False, "price_drops": None, "rounds": log, "floor": floor,
            "why": f"ceiling {ceiling} below the seller's floor {floor}" if ceiling < floor else "no meeting point"}


def rule_explanation(ranked: list[dict], chosen: list[str]) -> dict:
    if not ranked:
        return {"why": "no listing passed the filters and the sample check", "others": {}}
    top = next((r for r in ranked if r["seller"] in chosen), ranked[0])
    others = {}
    for r in ranked:
        if r["seller"] in chosen:
            continue
        if len(others) >= 5:
            others["…"] = f"{len(ranked) - len(chosen) - 5} more candidates ranked lower"
            break
        if r.get("negotiation") and not r["negotiation"]["deal"]:
            others[r["seller"]] = f"no deal: {r['negotiation'].get('why', 'no meeting point')}"
        elif r["over_ceiling"]:
            others[r["seller"]] = f"asks {r['ask_drops']} drops, above my ceiling"
        elif r["score"] >= top["score"]:
            others[r["seller"]] = f"tied at {r['score']}; the need was already filled by sellers earlier in the book"
        else:
            worse = min(r["parts"], key=lambda k: r["parts"][k] - top["parts"][k])
            others[r["seller"]] = f"scored {r['score']} vs {top['score']}: weaker on {worse}"
    return {"why": f"{top['seller']} scored highest ({top['score']}): grade {top['grade']}, "
                   f"price {top['parts']['price']}, track record {top['parts']['track']}", "others": others}


def explain(need_id: str, need: dict, ranked: list[dict], chosen: list[str], propose=None,
            use_llm: bool = True) -> dict:
    """Words for the choice. Code decided; the LLM only explains, and an explanation that names
    sellers that were not candidates is dropped."""
    base = rule_explanation(ranked, chosen)
    if not use_llm or not ranked:
        return {**base, "source": "rules"}
    inp = {"need": need_id, "columns": need["columns"], "weeks": need["weeks"],
           "ceiling_drops": need["max_price_drops"], "chosen": chosen,
           "candidates": [{k: r.get(k) for k in ("seller", "grade", "ask_drops", "score", "parts", "over_ceiling")}
                          | {"deal": (r.get("negotiation") or {}).get("deal")} for r in ranked[:5]]}
    out, source = _ask(propose, PICK_SYSTEM, inp)
    names = {r["seller"] for r in ranked}
    if isinstance(out, dict) and isinstance(out.get("why"), str) and \
            set((out.get("others") or {}).keys()) <= names | {"…"}:
        return {"why": out["why"][:500], "others": {k: str(v)[:200] for k, v in (out.get("others") or {}).items()},
                "source": source}
    return {**base, "source": "rules"}


def explain_budget() -> int:
    """How many needs per run get an LLM explanation (the rest get the rule text)."""
    return int(os.environ.get("MARKET_EXPLAIN_LLM", "12"))
