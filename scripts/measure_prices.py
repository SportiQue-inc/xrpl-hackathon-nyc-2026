"""Do prices move with supply and demand? Act 1 (mock ledger, synthetic accounts) run under four
market conditions; prints the settled price as a share of the rate card, per data tier and overall.

  python scripts/measure_prices.py            # writes docs/demo/price-discovery.json too
"""
import json
import os
import sys
from statistics import median

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agentrail.market import acts  # noqa: E402

CASES = [("baseline", 1, 1.0), ("3x demand", 3, 1.0), ("half the supply", 1, 0.5), ("3x demand, half the supply", 3, 0.5)]


def run(demand, supply):
    ex = acts.act1(demand_scale=demand, supply_share=supply)["exchange"]
    tiers = {k: round(median(h["ratio"] for h in v), 3) for k, v in sorted(ex.pricing.history.items())}
    every = [h["ratio"] for v in ex.pricing.history.values() for h in v]
    return {"settled": len(every), "median_ratio": round(median(every), 3) if every else None,
            "mean_ratio": round(sum(every) / len(every), 3) if every else None,
            "by_tier": tiers, "last_reference": {k: round(median(h["ratio"] for h in v[-20:]), 3)
                                                 for k, v in ex.pricing.history.items()}}


if __name__ == "__main__":
    out = {}
    for name, d, s in CASES:
        out[name] = run(d, s)
        r = out[name]
        print(f"{name:28s} settled {r['settled']:4d}  median price / rate card {r['median_ratio']} (mean {r['mean_ratio']})  by tier {r['by_tier']}")
    with open(os.path.join(os.path.dirname(__file__), "..", "docs", "demo", "price-discovery.json"), "w") as f:
        json.dump(out, f, indent=1)
