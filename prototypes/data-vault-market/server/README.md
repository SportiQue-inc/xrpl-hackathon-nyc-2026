# Data Vault Market server

The working service behind the prototype: 50 accounts with their own vaults, LLM agents that negotiate
between them, intake screening, and settlement on XRPL Testnet with escrow where payment releases the
key. It imports AgentRail's ledger code (`agentrail/ledger`) from this repository and changes nothing in it.

```
pip install -r requirements.txt
cp .env.example .env      # add an LLM key; VM_LEDGER=testnet
python run.py             # http://localhost:8800 (market) and /vault (my DB)
```

First start funds one Testnet wallet per account from the faucet (a few minutes; reused after, kept in
`wallets.local.json`). Amounts are tiny: 1 price unit = 0.01 XRP.

| Module | What it does |
|---|---|
| `data.py` | realistic records (NYC running loops with heart rate, sleep stages, itemized receipts, voice clips, hourly air readings), pseudonymization, record fingerprints |
| `intake.py` | classify into the domain ontology, refuse sensitive data (diagnoses, IDs, minors), paid cleaning, signed attestation with a Merkle root |
| `agents.py` | buyer and seller agents: the LLM thinks and writes the messages, code bounds every answer (owner's minimum, blocked purposes) |
| `market.py` | the loop: uploads, ontology scan and recommendations, negotiation with interest-first ordering, duplicate detection, k >= 5 lots, attestation and Merkle sample checks, settlement, resale bundles |
| `rail.py` | sealed delivery (X25519 + AES-GCM) and escrow per seller on XRPL: EscrowCreate under SHA-256(K), EscrowFinish reveals K |
| `app.py` | API and the two sites |

LLM cost control: one shared rate cap for all agents (`VM_LLM_RPM`) and a daily cap
(`VM_LLM_DAILY_CALLS`). When either is reached, or no key is set, agents answer from their written
rules and every message says "rules" instead of the model name.

Tests: `VM_LEDGER=mock` runs everything against AgentRail's in-memory ledger; the site then shows
"TEST LEDGER (not real)" on every page.
