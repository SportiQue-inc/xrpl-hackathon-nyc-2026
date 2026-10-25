"""Check which public demo addresses exist on XRPL Testnet and their balances.

    python scripts/check_addresses.py [fixtures/testnet-addresses.public.json]
"""
import json
import os
import sys

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo

path = sys.argv[1] if len(sys.argv) > 1 else "fixtures/testnet-addresses.public.json"
client = JsonRpcClient(os.environ.get("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234/"))
accounts = json.load(open(path))["accounts"]
found = 0
for a in accounts:
    r = client.request(AccountInfo(account=a["classic_address"], ledger_index="validated")).result
    if "account_data" in r:
        found += 1
        print(f"{a['account_id']:<8} {a['classic_address']}  exists  {int(r['account_data']['Balance']) / 1e6:g} XRP")
    else:
        print(f"{a['account_id']:<8} {a['classic_address']}  not found ({r.get('error')})")
print(f"{found}/{len(accounts)} accounts exist on Testnet")
