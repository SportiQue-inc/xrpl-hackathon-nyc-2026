"""Give every cohort participant their own XRPL Testnet wallet and fund it from the Testnet faucet.

    AGENTRAIL_KEYSTORE=runs/keystore python scripts/fund_participant_wallets.py

The seed is created in the participant's device keystore (AGENTRAIL_KEYSTORE, gitignored) and never
printed; the same key signs the participant's consent documents. Only the addresses are written to
.participant_wallets.json, which LEDGER=testnet runs then use instead of the shared fixture addresses.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.scenario import FIXTURE  # noqa: E402
from agentrail.security.devices import ParticipantWalletDevice  # noqa: E402

OUT = ".participant_wallets.json"


def fund(pid):
    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import generate_faucet_wallet
    d = ParticipantWalletDevice(pid)
    client = JsonRpcClient(os.environ.get("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234/"))
    for attempt in range(4):
        try:
            generate_faucet_wallet(client, wallet=d.wallet(), usage_context="agentrail-hackathon")
            return pid, d.address, None
        except Exception as e:           # faucet throttling: try again
            err = type(e).__name__
    return pid, d.address, err


def main():
    if not os.environ.get("AGENTRAIL_KEYSTORE"):
        sys.exit("set AGENTRAIL_KEYSTORE to a local directory so the seeds persist")
    pids = [a["account_id"] for a in json.load(open(FIXTURE))["accounts"] if a["role"] == "participant"][:50]
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [p for p in pids if p not in done]
    with ThreadPoolExecutor(4) as ex:
        for pid, addr, err in ex.map(fund, todo):
            if err is None:
                done[pid] = addr
                json.dump(done, open(OUT, "w"), indent=1)
            print(f"{pid} {addr} {'funded' if err is None else 'NOT funded: ' + err}", flush=True)
    print(f"{len(done)}/{len(pids)} participant wallets funded on Testnet")


if __name__ == "__main__":
    main()
