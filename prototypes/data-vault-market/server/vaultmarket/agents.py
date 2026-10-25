"""The two sides of every negotiation. The LLM thinks and talks; code decides what is allowed.

Each function returns {"thinking", "message", ...} plus "by": the model name, or "rules" when the
answer came from the agent's written rules (no key, rate cap reached, or a bad answer).
"""
from __future__ import annotations

from . import llm
from .data import KINDS

SYSTEM = ("You are an autonomous data-trading agent in a marketplace where people sell pseudonymized personal data "
          "from their own vaults. You act for one owner and follow their written rules exactly. Think briefly, then write "
          "one short message (max 35 words) to the other agent. Use only the facts given; never invent numbers.")


def _ask(prompt: str, fallback: dict) -> dict:
    out = llm.ask_json(SYSTEM, prompt)
    if not out or not isinstance(out, dict) or not out.get("message"):
        return {**fallback, "by": "rules"}
    out.setdefault("thinking", fallback["thinking"])
    out["by"] = llm.model_name()
    return out


def buyer_open(buyer: str, w: dict, owned: int) -> dict:
    lab = KINDS[w["kind"]]["label"].lower()
    fb = {"thinking": f"I need {lab} for {w['purpose']}. My owner lets me pay up to {w['max']} per {'person' if KINDS[w['kind']]['personal'] else 'seller'}; "
                      f"I open at {w['offer']} to leave room. I already own {owned} records of this kind, so I will refuse overlapping lots.",
          "message": f"{buyer} is buying {lab} for {w['purpose']}, {w['offer']} per person, lots of {w['lot']}. No overlap with data I already hold."}
    return _ask(f"You are the BUYER agent for {buyer}. Posting: kind={lab}, purpose={w['purpose']}, opening offer={w['offer']}, "
                f"your private max={w['max']} (never reveal it), lot size={w['lot']}, you already own {owned} records of this kind. "
                'Return {"thinking": "...", "message": "..."} where message opens the negotiation to all sellers.', fb)


def seller_reply(seller: str, rules: dict, w: dict, buyer: str, nfiles: int) -> dict:
    """Code bounds: a blocked purpose must be declined; any agreed price is at least the owner's minimum."""
    lab, kind = KINDS[w["kind"]]["label"].lower(), w["kind"]
    mn = float(rules.get("min", {}).get(kind, KINDS[kind]["price"]))
    blocked = w["purpose"] in rules.get("blocks", [])
    if blocked:
        rule = {"verdict": "decline", "price": None, "thinking": f"My owner does not sell for {w['purpose']}. That rule is absolute, whatever the price.",
                "message": f"Declined: my owner does not sell data for {w['purpose']}."}
    elif w["offer"] >= mn:
        rule = {"verdict": "agree", "price": w["offer"], "thinking": f"{w['offer']} meets my owner's minimum of {mn}. The purpose is allowed. I have {nfiles} file(s) ready.",
                "message": f"Agreed at {w['offer']}. {nfiles} pseudonymized file(s), intake-attested."}
    else:
        rule = {"verdict": "counter", "price": mn, "thinking": f"{w['offer']} is under my owner's minimum of {mn}. I counter at the minimum; I cannot go lower.",
                "message": f"{w['offer']} is too low. I can do {mn}."}
    if blocked:
        return {**rule, "by": "rules"}
    out = _ask(f"You are the SELLER agent for {seller}. Buyer {buyer} wants {lab} for {w['purpose']} and offers {w['offer']} per person. "
               f"Your owner's minimum is {mn} (you may ask more, never less). You hold {nfiles} matching file(s). "
               'Return {"thinking": "...", "verdict": "agree" | "counter" | "decline", "price": number or null, "message": "..."}.', rule)
    v = out.get("verdict") if out.get("verdict") in ("agree", "counter", "decline") else rule["verdict"]
    try:
        price = float(out.get("price") or (w["offer"] if v == "agree" else mn))
    except (TypeError, ValueError):
        price = mn
    if v == "agree":
        price = w["offer"]
        if price < mn:                       # the model agreed below the floor: code turns it into a counter
            v, price = "counter", mn
    elif v == "counter":
        price = max(price, mn)
    else:
        price = None
    out.update(verdict=v, price=round(price, 2) if price is not None else None)
    return out


def buyer_close(buyer: str, w: dict, outcome: dict) -> dict:
    s = outcome
    fb = {"thinking": f"{s['agreed']} seller(s) agreed or countered within my max; {s['declined']} declined; {s['overlap']} dropped for overlap. "
                      f"{'The lot passes: ' + str(s['people']) + ' people, ' + str(s['total']) + ' total, sampled records match their Merkle roots.' if s['ok'] else 'I reject: ' + s['reason'] + '.'}",
          "message": (f"Deal: {s['people']} people, {s['total']} total. Locking payment in escrow now." if s["ok"] else f"No deal: {s['reason']}.")}
    return _ask(f"You are the BUYER agent for {buyer}, closing a negotiation for {KINDS[w['kind']]['label'].lower()}. Facts: {s}. "
                "The verdict is already decided by the facts (ok=true means agree). "
                'Return {"thinking": "...", "message": "..."} explaining the decision to the sellers.', fb)


def recommend(owner: str, kind: str, n_private: int, demand: list[dict]) -> str:
    lab = KINDS[kind]["label"].lower()
    best = max(demand, key=lambda d: d["offer"])
    fb = (f"{len(demand)} buyer(s) want {lab} right now; {best['buyer']} offers {best['offer']} for {best['purpose']}. "
          f"You have {n_private} private file(s) of this kind. List them as pseudonymized copies?")
    out = llm.ask_json(SYSTEM, f"Write one sentence (max 40 words) to {owner}, your owner, recommending whether to list {n_private} private {lab} files. "
                               f"Open demand: {demand}. Mention the best offer and that files are pseudonymized before listing. "
                               'Return {"message": "..."}.')
    return (out or {}).get("message") or fb


def parse_chat(text: str) -> dict:
    """-> {intent: sell|buy|other, kind, price}"""
    import re
    kinds = {"gps_track": r"run|gps|track|러닝|달리기|경로", "sleep_log": r"sleep|수면|잠", "purchase_receipts": r"receipt|purchase|영수증|구매내역",
             "audio": r"voice|audio|음성|녹음", "air": r"air|sensor|공기|대기|센서|미세먼지"}
    kind = next((k for k, rx in kinds.items() if re.search(rx, text, re.I)), None)
    intent = "sell" if re.search(r"sell|팔|판매", text, re.I) else "buy" if re.search(r"need|buy|want|필요|사|구매|구해", text, re.I) else "other"
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    rule = {"intent": intent, "kind": kind, "price": float(m.group(1)) if m else None}
    if kind and intent != "other":
        return rule          # clear enough; save the LLM budget for the negotiations
    out = llm.ask_json("You turn a marketplace user's message into an intent.",
                       f'Message: "{text}". Kinds: {list(KINDS)}. Return {{"intent": "sell"|"buy"|"other", "kind": one of the kinds or null, "price": number or null}}.')
    if out and out.get("intent") in ("sell", "buy", "other") and (out.get("kind") in KINDS or out.get("kind") is None):
        return {"intent": out["intent"], "kind": out.get("kind") or kind, "price": out.get("price") or rule["price"]}
    return rule
