"""Why does a run see fewer offers? Act 1 once, then where each need's candidates went.

    python scripts/diagnose_discovery.py                       # generated rows
    UNIQDATA_ROSTER=.uniqdata_roster.json python scripts/diagnose_discovery.py

Prints: trades by status; how needs were formed (rules or a recorded/live LLM answer) with their
minimum grade and weeks; the offer book by grade and weeks; drop reasons summed over needs; and the
need-side filters that removed the most offers. Mock ledger, synthetic data.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.llm import voice  # noqa: E402
from agentrail.market import acts  # noqa: E402

r = acts.act1()
ex = r["exchange"]
needs = r["needs"]
print("llm:", voice().label(), "| roster:", bool(os.environ.get("UNIQDATA_ROSTER")),
      "| uniqdata records used:", sum((r.get("uniqdata_records_used") or {}).values()))
print("trades:", dict(Counter(t["status"] for t in ex.trades)), "| offers_seen:", sum(n["offers_seen"] for n in needs))
plans = [n["plan"] for n in needs if n.get("plan")]
print("needs formed by:", dict(Counter(p.get("source") for p in plans)),
      "| min_grade:", dict(Counter(p.get("min_grade") for p in plans)),
      "| weeks:", dict(Counter(p.get("weeks") for p in plans)))
offers = ex.offers()
print("offer book:", len(offers), "| grades:", dict(Counter(o["grade"] for o in offers)),
      "| weeks:", dict(Counter(o["dataset"].weeks for o in offers)))
drops = Counter()
for n in needs:
    drops.update(n["discovery"]["dropped"])
print("dropped (summed over needs):", drops.most_common())
print("needs relaxed to the rule floor:", sum(1 for n in needs if n["discovery"].get("relaxed")))
print("rejected by stage:", dict(Counter(x.get("stage") for n in needs for x in n["rejected"])))
src = Counter(c for a in ex.accounts.values() for d in a.datasets for c in (d.meta.get("source") or {}).values())
print("dataset columns by source:", dict(src))
