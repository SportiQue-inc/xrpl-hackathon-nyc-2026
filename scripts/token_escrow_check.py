"""One token-escrow trade on Testnet, end to end: issuer flags, trust lines, funding, EscrowCreate in
the USD test token locked to SHA-256(K), EscrowFinish revealing K, then both read back as validated.

  SETTLE_ASSET=USD python scripts/token_escrow_check.py

Synthetic accounts, Testnet only. Wallet seeds stay in wallets.local.json (git-ignored).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SETTLE_ASSET", "USD")

from agentrail import units  # noqa: E402
from agentrail.ledger import make_ledger  # noqa: E402
from agentrail.ledger.conditions import condition_hex, fulfillment_hex, new_key  # noqa: E402

L = make_ledger("testnet")
buyer, seller = L.new_account("tokencheck_buyer"), L.new_account("tokencheck_seller")
print(f"token {units.LABEL}: issuer {L.issuer}")
for s in L.setup_txs:
    print(f"  {s['what']}: {L.explorer_url(s['tx'])}")
b0, s0 = L.balance_drops(buyer), L.balance_drops(seller)
k = new_key()
amount = 1_250_000                       # 1.25 USD
cond = condition_hex(k)
create = L.prepare_escrow_create(buyer, seller, amount, cond, L.now() + 600, "agentrail token escrow check")
L.submit(create)
st = L.wait_validated(create.tx_hash, 60)
print(f"EscrowCreate {st.result} validated={st.validated} amount={units.fmt(st.amount_drops)} "
      f"condition_ok={(st.condition or '').upper() == cond}\n  {L.explorer_url(create.tx_hash)}")
assert st.validated and st.success and st.amount_drops == amount, "token escrow not created"
fin = L.prepare_escrow_finish(seller, buyer, create.sequence, cond, fulfillment_hex(k), "key revealed")
L.submit(fin)
sf = L.wait_validated(fin.tx_hash, 60)
print(f"EscrowFinish {sf.result} validated={sf.validated}\n  {L.explorer_url(fin.tx_hash)}")
b1, s1 = L.balance_drops(buyer), L.balance_drops(seller)
print(f"buyer {units.fmt(b0)} -> {units.fmt(b1)}; seller {units.fmt(s0)} -> {units.fmt(s1)}")
assert sf.validated and sf.success and s1 - s0 == amount, "finish did not pay the seller"
print("OK: one token trade settled through TokenEscrow with the SHA-256(K) condition")
