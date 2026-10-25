"""One record per contract attempt: the two agents' conversation, in order.

Each turn is {speaker, message, reasoning, checks, layer}. speaker is "buyer", "seller", "owner" or
"ledger"; checks are [{name, ok, detail}]; layer names which of our layers the turn belongs to (need,
discovery, quality, provenance, price, tier, consent, trust, escrow, delivery). The record ends with
both verdicts and the tx hashes, so the Act 1 replay and any other viewer can render the whole
negotiation from the log alone. Built from what the engine decided; nothing here re-decides.
"""
from __future__ import annotations

from .. import units

from .policies import GRADES, LABEL, PROHIBITED, data_class, trust_grade

SCHEMA = "agentrail.contract_trace/1"


def _x(d) -> str:
    return units.fmt(d)


def _wk(n) -> str:
    return f"{n} week" if n == 1 else f"{n} weeks"


def seller_checks(policy, trade_cols: list, purpose: str, buyer_attrs: dict, price: int) -> list[dict]:
    """What the seller's agent looks at, read-only (the policy's own decide() already ran)."""
    b = {**buyer_attrs, "owner_country": getattr(policy, "home", "KR")}
    g, score, why = trust_grade(b)
    classes = sorted({data_class(c, {"pseudonymized": True}) for c in trade_cols})
    bars = getattr(policy, "bars", {})
    out = [{"name": "purpose", "ok": purpose not in PROHIBITED, "detail": purpose},
           {"name": "buyer trust grade", "ok": True, "detail": f"{g} ({score}): {'; '.join(why)}"}]
    for k in classes:
        bar = bars.get(k)
        ok = bar is not None and GRADES.index(g) <= GRADES.index(bar)
        out.append({"name": f"tier {k}", "ok": ok,
                    "detail": f"{LABEL.get(k, k)}: sells on its own to grade {bar}+" if bar else
                              f"{LABEL.get(k, k)}: not set to sell on its own"})
    if any(k in ("T2", "T3", "genomic", "imaging", "imaging_pseudo") for k in classes):
        out.append({"name": "ethics (IRB) credential", "ok": bool(b.get("irb")) and not b.get("irb_expired"),
                    "detail": "read from the buyer's credentials" if b.get("irb") else "none on record"})
    out.append({"name": "autonomy level", "ok": True, "detail": getattr(policy, "preset", getattr(policy, "name", "open"))})
    return out


def build(need, plan: dict, disc: dict, cand: dict, neg: dict, record: dict | None, seller, buyer,
          track: tuple[int, int] = (0, 0)) -> dict:
    turns = []

    def say(speaker, message, reasoning="", checks=(), layer=""):
        turns.append({"speaker": speaker, "message": message, "reasoning": reasoning,
                      "checks": list(checks), "layer": layer})

    cols = ", ".join(need.columns)
    ceiling = (plan or {}).get("max_price_drops") or neg.get("ceiling")
    say("buyer", f"I need {cols} for {_wk(need.weeks)}, purpose {need.purpose}.",
        (plan or {}).get("why") or need.why,
        [{"name": "gap in my store", "ok": True, "detail": f"I hold {len((plan or {}).get('holds', []))} columns, not {cols}"},
         {"name": "owner's budget", "ok": True,
          "detail": f"at most {_x(ceiling)} each of {_x((plan or {}).get('budget_drops', 0))}" if ceiling else "set by the owner"},
         {"name": "need formed by", "ok": True, "detail": (plan or {}).get("source", "rules")}], "need")
    say("buyer", f"Your listing {cand['dataset']} is in the shared offer book; I checked a sample.",
        f"{disc.get('listed', 0)} listings in the anchored book; {len(disc.get('sampled', []))} candidates sampled; "
        f"you rank #{cand.get('rank', '?')} with score {cand['score']} "
        f"(quality {cand['parts']['quality']}, price {cand['parts']['price']}, track record {cand['parts']['track']})",
        [{"name": "listing proof to the ledger root", "ok": True,
          "detail": f"root {str(disc.get('anchored_root'))[:16]}…, tx {str(disc.get('anchor_tx'))[:16]}…"},
         {"name": "hashed sample vs certificate", "ok": True, "detail": f"grade {cand['grade']}, 12 rows opened"}],
        "discovery")
    if cand.get("overlap"):
        say("buyer", f"I already hold {round(cand['overlap'] * 100)}% of this; I pay only for the new part.",
            f"{cand['overlap_why']}; the ask {_x(cand['full_ask_drops'])} becomes {_x(cand['ask_drops'])}",
            [{"name": "overlap with my store", "ok": True, "detail": f"{round(cand['overlap'] * 100)}%"}], "provenance")
    ref, sc = neg.get("reference") or {}, neg.get("scarcity") or {}
    say("seller", f"Listed at {_x(cand['ask_drops'])}, grade {cand['grade']}.",
        (f"reference {_x(ref['price'])} ({ref['source']}) × scarcity {sc.get('factor')} "
         f"({sc.get('demand')} needs for these columns in the last day, {sc.get('supply')} listings); "
         f"never under my owner's floor {_x(neg.get('owner_floor', 0))}") if ref else
        "asking price from the column tier rate × weeks × grade; certificate root commits to every row",
        [{"name": "certificate", "ok": True, "detail": f"grade {cand['grade']}"}] +
        ([{"name": "market reference", "ok": True,
           "detail": f"{_x(ref['low'])}–{_x(ref['high'])}, {ref['n']} settled trades"}] if ref else []), "price")
    for r in neg.get("rounds", []):
        say("buyer", f"I offer {_x(r['bid'])}.",
            (f"opening at the low end of the market range {_x(ref['low'])}" if ref else "opening at 80% of the ask")
            if r["round"] == 1 else f"raising toward my ceiling {_x(ceiling)}"
            + (f" ({neg['ceiling_why']})" if neg.get("ceiling_why") else ""), [], "price")
        if r["bid"] >= r["counter"]:
            break
        say("seller", f"My price is {_x(r['counter'])}." if r["round"] == 1 else f"I can do {_x(r['counter'])}.",
            f"my floor is {_x(neg['floor'])} (my record: {track[0]} fit, {track[1]} unfit)", [], "price")
    if not neg.get("deal"):
        say("buyer", "No deal; I move to the next candidate.", neg.get("why", ""), [], "price")
        return _close(need, seller, buyer, turns, "reject", "no deal", None, neg)
    say("buyer", f"Agreed at {_x(neg['price_drops'])}.", "first bid at or above your counter", [], "price")
    st = record["status"]
    sc = seller_checks(seller.policy, need.columns, need.purpose, buyer.attrs, neg["price_drops"]) \
        if seller.policy is not None else []
    if st == "refused":
        say("seller", "I can't sell this to you.", record["why"], sc, "consent")
        return _close(need, seller, buyer, turns, "agree", "reject", record, neg)
    if st in ("awaiting_owner", "declined") or record.get("why", "").startswith("owner approved"):
        say("seller", "This needs my owner.", record["why"] if st != "settled" else "outside what I may sell on my own",
            sc, "consent")
        if st == "awaiting_owner":
            say("owner", "(not answered yet)", "the request waits for the person; nothing moves meanwhile", [], "consent")
            return _close(need, seller, buyer, turns, "agree", "ask_owner", record, neg)
        if st == "declined":
            say("owner", "No.", record["why"], [], "consent")
            return _close(need, seller, buyer, turns, "agree", "reject", record, neg)
        say("owner", "Yes.", record["why"], [], "consent")
    elif st in ("no_budget", "not_settled"):
        say("buyer", "My side cannot pay this.", record["why"], [], "escrow")
        return _close(need, seller, buyer, turns, "reject", "agree", record, neg)
    else:
        say("seller", "Deal. Lock the payment.", record["why"], sc, "consent")
    tx = record.get("txs") or {}
    sim = "" if any((record.get("urls") or {}).values()) else " (simulated on the mock ledger, not Testnet)"
    say("ledger", f"EscrowCreate {(tx.get('escrow_create') or '')[:16]}…: {_x(record.get('paid_drops', 0))} locked "
                  f"to the hash of the data key{sim}.", "the buyer's agent pays; the seller can collect only by revealing the key",
        [{"name": "owner-signed mandate", "ok": True, "detail": "checked before the escrow"}], "escrow")
    say("seller", "Key revealed.", "EscrowFinish publishes the key; the payment and the key are one transaction",
        [], "escrow")
    say("ledger", f"EscrowFinish {(tx.get('escrow_finish') or '')[:16]}…: paid{sim}.", "", [], "escrow")
    sig = record.get("signals") or []
    say("buyer", "Opened and checked: fits." if st == "settled" else "Opened and checked: not as promised.",
        "the delivery must hash to the certified root, with values in range and complete as certified",
        [{"name": "delivery hashes to the certified root", "ok": not any(s["code"] == "not_as_committed" for s in sig),
          "detail": ""}] + [{"name": s["code"], "ok": False, "detail": s.get("column", s.get("detail", ""))} for s in sig],
        "provenance")
    if st == "settled_unfit":
        say("buyer", f"Refund claim recorded: {_x(record.get('refund_claim_drops', 0))}.",
            "paid money is never taken back on the ledger; the claim and the seller's record carry it", [], "delivery")
    return _close(need, seller, buyer, turns, "agree" if st == "settled" else "reject", "agree", record, neg)


def _close(need, seller, buyer, turns, bv, sv, record, neg) -> dict:
    return {"schema": SCHEMA, "contract": (record or {}).get("contract"), "need": need.id, "buyer": buyer.id,
            "seller": seller.id, "columns": need.columns, "status": (record or {}).get("status", "no_deal"),
            "price_drops": neg.get("price_drops"), "turns": turns,
            "verdicts": {"buyer": bv, "seller": sv}, "txs": (record or {}).get("txs") or {},
            "urls": (record or {}).get("urls") or {}}
