# Data Vault Market: requirements (from daniel, 2026-10-25)

## Service
1. A real, deployed service running on a server. No simulation and no pause/resume.
2. Real database, real XRPL Testnet ledger, tiny amounts, trading continuously.
3. 50 agents, each with an LLM. They keep uploading, buying and selling among themselves.
4. Realistic data (GPS routes, sleep stages, receipts with items, voice metadata, sensor time series), not toy rows.

## Market site
5. Left: buyer demand list, public to everyone.
6. Middle: market overview (agents online, contracts settled and rejected, volume, traded by domain) and the live ledger history (who paid whom, how much, for what).
7. Contract detail opens as a popup: the buyer agent's and seller agent's reasoning as written, and the negotiation between them as one chat transcript in order, ending in agreed or rejected.
8. Right: my DB, sorted by the agent into bundles by domain and by demand, each with expected sales and agreed/rejected negotiation counts.
9. "Ask my agent" chat sits over my DB on the right and expands when clicked.

## Agent behaviour
10. I tell my agent what I want to sell or need; it posts to the board, negotiates and settles.
11. Autonomy and trust settings: it buys good offers on its own within limits; selling waits for my OK.
12. Intake filter at upload: sensitive data is refused, raw data can be cleaned for a fee.
13. Pseudonymized at upload; personal data sold only in lots of at least 5 people; sealed push to the buyer; escrow where payment releases the key; source signatures checked before payment.
14. Duplicate or overlapping data: the buyer agent detects it and rejects the contract.
15. My data grows over time; agents can combine what they bought into bigger bundles and resell them.

## Other
16. A separate site to manage my DB.
17. Dark mode, gray plus one blue.
18. Contract traces use the same JSON shape as the build thread's Act 1 trace (buyer_trace, seller_trace, verdicts, tx hashes).

## Added 08:17
19. My DB page (manage, upload, demand view): an AI ontology scans my whole DB and recommends "these data have demand; pseudonymize or anonymize them and sell?" I decide whether to list each one.
20. Marketplace page organized by domain. I configure my own buy agent and sell agent there.
21. On the buy list I can mark a posting as "interested": my agent negotiates that one first. Otherwise it decides on its own (auto).
22. The AI standardizes and filters at intake, then signs an attestation of what it checked (schema, ranges, duplicates, identifiers removed). Each bundle commits to a Merkle root of its records; the root goes into the escrow memo, and the buyer verifies a random sample of records against it before paying. A full zero-knowledge proof is a later step.
