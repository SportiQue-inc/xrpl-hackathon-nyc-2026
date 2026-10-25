"""Sensitive (T3) data end to end on the act 2 pipeline: genomic variants, CT and MRI.

    LEDGER=testnet python scripts/t3_testnet_check.py      # XRPL Testnet (faucet accounts), a few minutes
    python scripts/t3_testnet_check.py                     # mock ledger

Six participants who hold T3 data (P-001 approves by hand) and the four institutions. Checked per type:
- no automatic sale: every T3 request waits for the owner, or is refused where the owner never allows T3;
- genomic data leaves only as an aggregate over the study's signed loci;
- after the owner's approval: sealed delivery, EscrowCreate, then EscrowFinish publishing the key;
- the same MRI request from a lower-graded institution is held.
Prints one line per check with explorer links. Synthetic data only.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentrail.catalog import columns as catalog  # noqa: E402
from agentrail.ledger import make_ledger  # noqa: E402
from agentrail.market import acts, policies  # noqa: E402
from agentrail.market.exchange import Account, Exchange, Need  # noqa: E402

PEOPLE = ["P-001", "P-004", "P-012", "P-022", "P-023", "P-031", "P-049", "P-050"]   # the last two live in Mongolia


def main():
    prof = acts.load()
    sub = {**prof, "participants": {p: prof["participants"][p] for p in PEOPLE}}
    people = acts.participants(sub, act=2)
    acts._build_rows(people)
    from agentrail.uniqdata_live import feed_market, market_clients
    uq = feed_market(people, market_clients())       # T3 datasets need a UniQdata intake record behind them
    insts = [Account(i["id"], i["name"], "org", attrs=acts.institution_record(i)) for i in prof["institutions"]]
    ledger = make_ledger(os.environ.get("LEDGER", "mock"))
    ex = Exchange(people + insts, ledger=ledger, seed=11)
    for inst in prof["institutions"]:
        rs = [r for r, v in prof["researchers"].items() if v["institution"] == inst["id"]]
        I = acts.Institution(inst["id"], rs)
        b = {"institution": inst["id"], "total_drops": 20_000_000, "per_order_drops": 5_000_000,
             "purposes": [acts.INSTITUTIONS[inst["id"]]["purpose"]]}
        I.open_budget(ex.engine, b, {rs[0]: I.sign(rs[0], b), rs[1]: I.sign(rs[1], b)})
    grades = {i.id: policies.trust_grade({**i.attrs, "owner_country": "KR"})[0] for i in insts}
    needs = [
        Need("genomics-vcf", "org_genomics", ["genome.vcf"], 1, 8, acts.INSTITUTIONS["org_genomics"]["purpose"],
             posted_h=1.0, why="org_genomics: variant risk vs sleep phenotype"),
        Need("neuroimg-ct", "org_neuroimg", ["imaging.ct"], 1, 8, acts.INSTITUTIONS["org_neuroimg"]["purpose"],
             posted_h=1.5, why="org_neuroimg: pseudonymized CT"),
        Need("neuroimg-mri", "org_neuroimg", ["imaging.mri"], 1, 8, acts.INSTITUTIONS["org_neuroimg"]["purpose"],
             posted_h=2.0, why="org_neuroimg: pseudonymized MRI"),
        Need("genomics-mri", "org_genomics", ["imaging.mri"], 1, 8, acts.INSTITUTIONS["org_genomics"]["purpose"],
             posted_h=2.5, why="org_genomics: pseudonymized MRI (same request, other institution)"),
    ]
    needs[0].output, needs[0].loci = "aggregate", ["CYP1A2", "MCM6"]
    first = {n.id: ex.fill(n) for n in needs}
    log = ex.activity().get("recent", [])
    pending = list(ex.pending)
    approved = []
    for _ in range(len(ex.pending)):                 # P-001 answers each queued trade (simulated Touch ID)
        p = ex.pending[0]
        owner = ex.accounts[p["seller"]].policy.owner
        inst = p["trade"]["buyer_attrs"].get("institution", p["buyer"])
        pkg = owner.package(inst)
        a = owner.device.assert_(pkg["hash"]) if pkg else None
        approved.append(ex.approve_pending(0, a))
    trades = [t for t in ex.trades] if hasattr(ex, "trades") else []
    def prov(seller, cols):
        for ds in ex.accounts[seller].datasets:
            if ds.columns == cols and ds.meta.get("provenance"):
                p = ds.meta["provenance"]
                return {"record_hash": p["record_hash"][:16], "dataq": p.get("dataq"), "source_type": p.get("source_type")}
        return None

    for r in log + approved:
        if r.get("seller"):
            r["provenance"] = prov(r["seller"], r.get("columns") or [])
    out = {"ledger": ledger.name, "grades": grades, "uniqdata_connected": bool(uq),
           "t3_listed": {a.id: [d.columns[0] for d in a.datasets if d.meta.get("provenance")] for a in people},
           "first_answers": {k: {"filled": v["filled"], "rejected": v["rejected"]} for k, v in first.items()},
           "queued_for_owner": [{k: p[k] for k in ("seller", "buyer", "columns", "why")} for p in pending],
           "after_owner": [{k: r.get(k) for k in ("status", "seller", "buyer", "columns", "urls", "why", "provenance")} for r in approved],
           "recent": [{k: r.get(k) for k in ("status", "seller", "buyer", "columns", "why", "urls", "buyer_grade", "provenance")}
                      for r in log]}
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
