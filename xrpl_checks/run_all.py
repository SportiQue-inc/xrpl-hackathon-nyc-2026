"""Run every check (or the ones named) against XRPL Testnet, then write RESULTS.md.
    python xrpl_checks/run_all.py            # all
    python xrpl_checks/run_all.py kyb mpt    # a subset"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = ["amendments", "kyb", "mpt_licence", "escrow", "batch", "x402", "x402_extra", "amm"]

if __name__ == "__main__":
    wanted = [c for c in CHECKS if not sys.argv[1:] or any(a in c for a in sys.argv[1:])]
    failed = []
    for name in wanted:
        r = subprocess.run([sys.executable, os.path.join(HERE, f"check_{name}.py")])
        if r.returncode:
            failed.append(name)
    subprocess.run([sys.executable, os.path.join(HERE, "report.py")])
    print("crashed:", failed or "none")
