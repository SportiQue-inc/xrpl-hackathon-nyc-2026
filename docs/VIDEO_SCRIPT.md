# Demo video script (draft, about 2 min 40 s)

Screens: researcher console (left), P-017's phone (right), dashboard boundary tab, XRPL Testnet
explorer. All data synthetic. Narration in English; on-screen captions short.

| Time | Screen | Narration | On screen |
|---|---|---|---|
| 0:00-0:15 | Title, then the stalled heatmap | "Health research is moving from big tables to one person followed over weeks. This sleep study lost three weeks of fatigue surveys for most of its 50 participants. Its power fell to 0.65." | heatmap with empty weeks 3-5, power 0.65 |
| 0:15-0:35 | Console: goal -> LLM reading next to code verdict | "The study's research agent reads the coverage table. The LLM proposes what is missing; code recomputes every gap from the table. For P-017 it finds fatigue weeks 3 to 5, heart rate week 4, and two clinic visits." | claims list: LLM evidence, code verdict |
| 0:35-0:50 | Console: approve with one signer -> refused; two signers -> approved | "The agent cannot give itself a budget. One signer is refused by the ledger. The principal investigator and compliance co-sign, and the owner signs the agent's spending mandate." | tefBAD_QUORUM / tefBAD_SIGNATURE, then tx link |
| 0:50-1:15 | Phone: request card | "P-017's own agent receives a participation request. The lab's ethics review and verified-organization credentials are read from XRPL. Heart rate is inside P-017's consent, so it goes automatically. Fatigue and clinic blood pressure need P-017." | badges, DUO chips, auto / needs you |
| 1:15-1:35 | Phone: preview -> approve | "Before anything leaves, P-017 sees exactly what will: a study-only pseudonym, shifted dates, only the requested items. Approve. The agent pays the clinic's export fee, seals each week, and the lab escrows the reward." | preview rows, export fee tx |
| 1:35-1:50 | Console: heatmap fills, bundle opens | "The reward is released only when P-017's agent publishes the key on the ledger, and the lab opens the bundle with that same key. The heatmap fills; power rises." | EscrowFinish tx, power 0.65 -> 0.75 |
| 1:50-2:15 | Dashboard boundary tabs | "We solved the hardest boundaries first. Consent: a new purpose stops for approval. Re-identification: birth date plus postal code plus rare diagnosis is refused. An unverified lab can't even pay P-017: the ledger says no." | evidence lines with tx links |
| 2:15-2:30 | Phone: revoke | "P-017 withdraws. The study's licence token is clawed back, the unreleased week is never released, and its escrow returns to the lab. Rewards already paid stay with P-017." | Clawback, EscrowCancel links; row greys out |
| 2:30-2:40 | Robot scene, closing line | "With a lighter consent layer the same engine runs robot data between companies on Testnet. The LLM proposes, code verifies, the ledger enforces." | scene A payments |

60-second pitch version (from docs/MARKET_THESIS.md; derived figures marked there)
1. 0-10 s: "When Roche bought Flatiron, one oncology patient's record was valued at about $1,000. The person it described got nothing. 23andMe's 15 million customers were sold off at about $20 each, and 1.9 million asked to be deleted."
2. 10-22 s: "In 2026 four things changed at once. AI ran out of public data, and OpenAI and Anthropic turned to records patients connect themselves. The US, the EU and Korea gave people the right to pull their own records. Data without consent now draws FTC orders and record fines. And agents got wallets."
3. 22-34 s: "Yet no country has a rail where a person consents per study and is paid directly. Studies cannot fill missing weeks: replacing one dropout costs close to $20,000, and remote participants leave after 5.5 days."
4. 34-48 s: "In AgentRail the study's agent finds the missing person-weeks and asks that person's agent. It contributes only what the person agreed to, and XRPL binds a consent hash, a revocable licence and an escrowed payment to every record. A $20 weekly contribution costs 88 cents by card and about $0.0002 on XRPL."
5. 48-60 s: "In year 3, 300 studies settle 3.9 million contributions a year for $11.4M revenue. We solved consent and withdrawal first on the hardest data, one person's longitudinal health record. The same engine runs AI training data."

Notes for recording
- Run `scripts/run_health_demo.py` once before recording so LLM answers are recorded; recording
  then uses live calls with the recorded answers as fallback.
- Use Testnet links only; keep the explorer tab ready.
- Words to avoid on screen and in narration: data sale, reward token, "cannot be re-identified",
  disease prediction, medical AI diagnosis, HIPAA compliant, product names.
