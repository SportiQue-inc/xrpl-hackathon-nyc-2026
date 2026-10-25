"""0. Which amendments the checks rely on are enabled on Testnet right now."""
import json
import os

from common import HERE, amendment_status, client

NAMES = ["Credentials", "DepositAuth", "DepositPreauth", "MPTokensV1", "Clawback", "Escrow", "TokenEscrow",
         "Batch", "fixBatchInnerSigs", "AMM", "fixAMMv1_1", "fixAMMv1_2", "fixAMMv1_3", "AMMClawback",
         "PermissionedDomains", "DynamicMPT", "SingleAssetVault"]

if __name__ == "__main__":
    st = amendment_status(client(), NAMES)
    for k, v in st.items():
        print(f"{k:22s} {v}")
    with open(os.path.join(HERE, "results", "0_amendments.json"), "w") as f:
        json.dump(st, f, indent=1)
