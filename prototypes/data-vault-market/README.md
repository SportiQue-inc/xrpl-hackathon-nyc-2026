# Data Vault Market (prototype)

A standalone demo of a general personal-data marketplace built on the AgentRail ideas. It does not
import or change anything in `agentrail/` or `apps/`.

Open `index.html` in a browser (no server, no build). Press the main button to walk the cycle:

1. Upload with sell flags: marked files are pseudonymized at upload, the rest stay private, identity
   documents are blocked even when marked. Each file gets a source signature (provenance at intake).
2. The agent sorts the vault into packages.
3. A buyer request arrives (pick "running tracks" for a sale, "voice memos" to see a non-match).
4. The agent matches across six other synthetic vaults, applies their standing rules, and builds a
   lot only when it reaches k = 5 people. You get a per-deal pseudonym.
5. You tap OK or Decline on the signing sheet. Declining drops you; the rest still sell if k holds.
6. Sale: the buyer locks XRP under SHA-256(K), the bundle is pushed sealed to the buyer's key,
   provenance is checked, EscrowFinish reveals K, the buyer opens the bundle and checks its hash.

Crypto (HMAC, ECDSA, ECDH P-256, AES-GCM, SHA-256) is real Web Crypto. The ledger is simulated.

Business note: [PLATFORM.md](PLATFORM.md).
