"""Write the Act 1 node-network replay as one offline HTML file (mock ledger, synthetic data).

    python scripts/export_network.py [out.html]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentrail import network_view  # noqa: E402
from agentrail.market import acts  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "docs/demo/act1-network.html"
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
data = network_view.build(acts.act1()["exchange"])
with open(out, "w") as f:
    f.write(network_view.render(data))
print(out, data["totals"])
