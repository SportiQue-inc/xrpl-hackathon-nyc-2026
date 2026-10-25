"""Measure the data-contract layer on synthetic streams with bad records mixed in.

    python scripts/measure_contracts.py            # prints JSON, writes docs/img/reliability.svg

1. Trains the delivery reliability forecast on synthetic histories and reports its Brier score
   against the base rate, with a reliability table (and the plot).
2. Buys the same target of usable provider-windows from the same synthetic markets three ways:
   manual (lowest price, terms as asked, paid in full, reviewed at the end), checks (negotiated
   contracts, incremental checks, per-contribution holdback, replacement), forecast (the same,
   ranked by expected usable windows per XRP, with early backups).
Synthetic data only; the numbers describe this generator, not a real market.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agentrail.contract import forecast, measure  # noqa: E402

model, info = measure.train()
cmp = measure.compare(model)
out = os.path.join(os.path.dirname(__file__), "..", "docs", "img", "reliability.svg")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    f.write(forecast.reliability_svg(info["reliability"], before=info["reliability_before"]))
print(json.dumps({"forecast": info, "comparison": cmp}, indent=1))
