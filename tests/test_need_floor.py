"""A recorded or live LLM need that asks for more than the book holds (grade A, eight weeks) used to leave
the market almost empty; the buyer's agent now steps back to the rule floor once and records it."""
from collections import Counter

from agentrail.market import acts


def _strict(system, payload):
    if "min_grade" in system:
        return {"columns": [payload.get("this_gap")], "weeks": 8, "min_grade": "A", "why": "strict"}
    return None


def test_strict_needs_fall_back_to_rule_floor():
    r = acts.act1(propose=_strict)
    trades = Counter(t["status"] for t in r["exchange"].trades)
    relaxed = [n["discovery"]["relaxed"] for n in r["needs"] if n["discovery"].get("relaxed")]
    assert relaxed and all(x["to"]["min_grade"] == "C" for x in relaxed)
    assert all(x["from"] == {"min_grade": "A", "weeks": 8} for x in relaxed)
    assert trades["settled"] >= 50
