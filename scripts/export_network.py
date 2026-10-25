"""Write the Act 1 node-network replay as one offline HTML file (mock ledger, synthetic data).

    python scripts/export_network.py [out.html]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The replay shows prices in the settlement token (test USD standing in for RLUSD) even when the shell
# still carries SETTLE_ASSET=XRP from a Testnet run of the XRP path.
os.environ["SETTLE_ASSET"] = os.environ.get("EXPORT_UNIT", "USD")

from agentrail import network_view  # noqa: E402
from agentrail.market import acts  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "docs/demo/act1-network.html"
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
data = network_view.build(acts.act1()["exchange"])
with open(out, "w") as f:
    f.write(network_view.render(data))
# one record per contract (schema agentrail.contract_trace/1): both agents' turns, verdicts, tx hashes
with open(os.path.splitext(out)[0].replace("network", "contracts") + ".json", "w") as f:
    json.dump(data["contracts"], f, indent=1)
print(out, data["totals"], len(data["contracts"]), "contracts")
