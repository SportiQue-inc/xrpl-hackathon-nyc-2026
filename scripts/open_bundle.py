"""Open a contributed bundle with the key published on the ledger.

    python scripts/open_bundle.py <EscrowFinish tx hash> [--db agentrail.db] [--rows 3]

1. Reads the EscrowFinish from the XRPL ledger (Testnet by default, XRPL_RPC_URL to override) and
   takes its Fulfillment: the data key K the participant's agent published to get paid.
2. Checks that SHA-256(K) is the Condition of the EscrowCreate it finished.
3. Opens the study's sealed copy of that round: the outer layer with K from the ledger, the inner
   layer with the study's own box key (the institution vault in .keystore/, never the operator's).
4. Checks the bundle hash against the bundle hash in the EscrowCreate memo and prints a few rows.

Needs the run's database (AGENTRAIL_DB / --db) and keystore (AGENTRAIL_KEYSTORE, default .keystore)
for step 3; steps 1-2 need only the public ledger. If the participant withdrew, the study's copy was
destroyed and the script says so: the key on the ledger then opens nothing the study still holds.
Synthetic data, XRPL Testnet only.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nacl.public import SealedBox  # noqa: E402
from nacl.secret import SecretBox  # noqa: E402

from agentrail.engine import canonical, sha256_hex  # noqa: E402
from agentrail.ledger.conditions import condition_hex, key_from_fulfillment  # noqa: E402
from agentrail.security.keystore import LocalKeyStore  # noqa: E402

STUDY = "org_sleeplab"
EXPLORER = "https://testnet.xrpl.org/transactions/"


def ledger_tx(h: str) -> dict:
    from xrpl.clients import JsonRpcClient
    from xrpl.models.requests import Tx
    url = os.environ.get("XRPL_RPC_URL", "https://s.altnet.rippletest.net:51234/")
    r = JsonRpcClient(url).request(Tx(transaction=h)).result
    if r.get("error"):
        sys.exit(f"{h}: {r.get('error')} on {url}")
    return r


def memo_text(tx: dict) -> str:
    out = []
    for m in tx.get("Memos", []):
        d = m.get("Memo", {}).get("MemoData")
        if d:
            out.append(bytes.fromhex(d).decode(errors="replace"))
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tx_hash")
    ap.add_argument("--db", default=os.environ.get("AGENTRAIL_DB", "agentrail.db"))
    ap.add_argument("--keystore", default=os.environ.get("AGENTRAIL_KEYSTORE", ".keystore"))
    ap.add_argument("--rows", type=int, default=3)
    a = ap.parse_args()

    fin = ledger_tx(a.tx_hash)
    fj = fin.get("tx_json", fin)
    if fj.get("TransactionType") != "EscrowFinish" or not fj.get("Fulfillment"):
        sys.exit(f"{a.tx_hash} is a {fj.get('TransactionType')} without a Fulfillment")
    if fin.get("meta", {}).get("TransactionResult") != "tesSUCCESS":
        sys.exit(f"EscrowFinish result {fin.get('meta', {}).get('TransactionResult')}")
    key = key_from_fulfillment(fj["Fulfillment"])
    print(f"1. EscrowFinish {EXPLORER}{a.tx_hash}")
    print(f"   Fulfillment (K, published by the participant's agent): {fj['Fulfillment'][:24]}...")

    if not os.path.exists(a.db):
        sys.exit(f"2-4 need the run's database; {a.db} not found (--db)")
    db = sqlite3.connect(a.db)
    db.row_factory = sqlite3.Row
    p = db.execute("SELECT * FROM payments WHERE finish_tx=?", (a.tx_hash,)).fetchone()
    if p is None:
        sys.exit("this EscrowFinish is not in this run's database")
    o = db.execute("SELECT * FROM orders WHERE id=?", (p["order_id"],)).fetchone()
    create = ledger_tx(p["tx_hash"])
    cj = create.get("tx_json", create)
    ok_cond = cj.get("Condition", "").upper() == condition_hex(key)
    print(f"2. EscrowCreate {EXPLORER}{p['tx_hash']}")
    print(f"   Condition = SHA-256(K): {'yes' if ok_cond else 'NO'}")
    memo = memo_text(cj)
    print(f"   memo: {memo}")

    b = db.execute("SELECT * FROM bundles WHERE order_id=?", (p["order_id"],)).fetchone()
    print(f"3. Study {o['buyer_id']}, participant {o['seller_id']}, {o['scope']}")
    if b is None:
        ev = db.execute("SELECT message FROM events WHERE kind='deletion_confirmed' AND message LIKE ? "
                        "ORDER BY id DESC", (f"%{o['seller_id']}%",)).fetchone()
        print(f"   The study's copy no longer exists: {o['seller_id']} withdrew and the study destroyed it"
              + (f" ({ev['message']})" if ev else "") + ".")
        print("   K on the ledger stays public, but it opens nothing the study still holds.")
        return
    try:
        inner = SecretBox(key).decrypt(b["sealed"])
    except Exception:
        sys.exit("   K from the ledger does not open the outer layer")
    print("   outer layer opened with K from the ledger")
    box = LocalKeyStore(f"institution.{o['buyer_id']}", a.keystore).get("x25519")
    if box is None:
        sys.exit(f"   the inner layer needs the study's box key (institution.{o['buyer_id']} in {a.keystore})")
    from nacl.public import PrivateKey
    payload = json.loads(SealedBox(PrivateKey(box)).decrypt(inner))
    h = sha256_hex(canonical(payload))
    on_ledger = f"bundle:{h[:16]}" in memo
    print(f"4. bundle hash {h[:16]}...: equals the stored hash {'yes' if h == b['bundle_hash'] else 'NO'}, "
          f"equals the hash in the EscrowCreate memo {'yes' if on_ledger else 'NO'}")
    rows = payload["rows"]
    print(f"   {len(rows)} rows (synthetic); first {min(a.rows, len(rows))}:")
    for r in rows[: a.rows]:
        print("   " + json.dumps(r, sort_keys=True, ensure_ascii=False))
    sys.exit(0 if ok_cond and on_ledger and h == b["bundle_hash"] else 1)


if __name__ == "__main__":
    main()
