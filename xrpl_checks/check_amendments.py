"""0. Which amendments the checks rely on are enabled on Testnet right now."""
import json
import os

from common import HERE, amendment_status, client

NAMES = ["Credentials", "DepositAuth", "DepositPreauth", "MPTokensV1", "Clawback", "Escrow", "TokenEscrow",
         "Batch", "BatchV1_1", "fixBatchV1_2", "fixBatchInnerSigs", "AMM", "fixAMMv1_1", "fixAMMv1_2", "fixAMMv1_3", "AMMClawback",
         "PermissionedDomains", "DynamicMPT", "SingleAssetVault"]
# xrpl-py >= 5.0 changed the Wallet.from_seed default algorithm; all seeds here are created fresh by this run.

if __name__ == "__main__":
    c = client()
    st = amendment_status(c, NAMES)
    # Cross-check with the `feature` RPC where the public server allows it.
    from xrpl.models.requests import GenericRequest
    for n in NAMES:
        try:
            r = c.request(GenericRequest(method="feature", feature=n)).result
            f = next(iter(v for v in r.values() if isinstance(v, dict) and "enabled" in v), None)
            if f is not None:
                st[n] += f" | feature rpc: enabled={f.get('enabled')} supported={f.get('supported')}"
        except Exception as e:  # noqa: BLE001
            st[n] += f" | feature rpc error: {str(e)[:80]}"
    for k, v in st.items():
        print(f"{k:22s} {v}")
    with open(os.path.join(HERE, "results", "0_amendments.json"), "w") as f:
        json.dump(st, f, indent=1)
