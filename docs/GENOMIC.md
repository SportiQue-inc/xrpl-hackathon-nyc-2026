# Genomic data (T3)

법률 자문 아님 · 합성 데이터 · Testnet. Every variant here is synthetic. Legal requirements are reflected in the design; this is not a compliance claim. The legal review is in `review/legal/agent-delegated-genomic-consent.md` (project files).

## Threat model

1. **A genome identifies its owner by itself.** We never claim that it cannot be traced back to a person.
2. **It exposes blood relatives** who never consented.
3. **It is permanent.** A leak cannot be undone, so withdrawal cannot fully protect data already delivered.
4. **Small slices can still link** a person, for example through rare variants.

## Principle

The agent is a tool that executes the person's signed consent; it is never a proxy that consents for them.
- Raw variants are never delegated: each study needs the person's own passkey signature.
- Inside a study the person signed in advance (institution, purpose, loci, period), the agent delivers computed or aggregate outputs each round.
- Anything new goes back to the person: a new institution, a new purpose, or a request for raw data.
- There is no "proceed unless refused" mode.
- Participants in Mongolia: their raw genomic data is out of this MVP. Their data is stored and processed only in Mongolia, and institutions abroad receive only aggregates that do not identify anyone.

## Design (`agentrail/vault/genomic.py`)

| piece | what it does | standard it follows |
|---|---|---|
| region keys | The VCF is cut by gene region. Each region's key is HKDF(passkey root, "region\|gene\|study"), so a trade opens only the loci asked for, and a wrong region or study key fails | n/a |
| least revealing first | The buyer's agent tries a cohort aggregate first, then a yes/no presence answer (rate-limited per buyer), and only then raw loci with a stated reason. The ladder records which level was accepted and why | GA4GH Beacon (presence answers) |
| compute-only enclave | Holds only the signed loci's keys. Runs only whitelisted computations (allele count, carrier count) and returns outputs, never raw data. Refuses cohorts below k = 20. Destroys its keys when the signed period ends | n/a |
| container | The header carries the data key encrypted to the recipient's X25519 key, followed by 64 KiB ChaCha20-Poly1305 segments, pushed into the recipient's own store. It follows the Crypt4GH structure; byte compatibility with the reference tool is not tested | GA4GH Crypt4GH |
| watermark | Each recipient's copy orders its records by a recipient-keyed permutation and carries recipient-keyed record ids | n/a |
| consent | Never automatic: a fresh Touch ID for each package (assertion bound to the package hash, at most 120 s old). The package shows the relatives warning, the permanence warning, the exact loci, the recipient and country, and the IRB credential, which must be valid and carry the genetic-studies-only code. Delivery abroad also needs the separate transfer-abroad consent | GA4GH DUO (DUO:0000016 GSO) |
| ledger | Only a salted, per-round hash goes on the ledger, never a variant id or anything derived from genotypes | n/a |
| keys after use | Region keys in the enclave are destroyed at period end. View keys for imaging and raw loci expire with the keyring entry (see `docs/SECURITY.md` §11) | n/a |
| withdrawal | Stops further pushes and sends deletion requests. The UI says plainly that copies already delivered can be withdrawn only by contract (deletion request and signed confirmation), not technically | n/a |

## What the watermark can and cannot show

- **Can show:** a leaked copy with its ordering and record ids intact points to one recipient, which is evidence for the contract's penalty process.
- **Cannot show:** who leaked a copy that was re-sorted, had its ids stripped, or was retyped. It also cannot show that nobody memorised a variant. It deters and traces; it does not prevent. On its own it is not legal proof.

## Reverse direction: a wellness trait report

A person can buy a report with their own data (`market/acts.py buy_report`).
- The provider must hold a credential for the report types allowed for direct-to-consumer testing: wellness, trait and ancestry. Anything else is refused.
- The person's agent sends only the variants at the loci the report needs.
- Payment is escrowed and released when the report is delivered.
- The provider signs a deletion confirmation for the variants it received.
- The report is labelled "wellness information, not a diagnosis".

Tests: `tests/test_genomic.py`, `tests/test_market.py`.
