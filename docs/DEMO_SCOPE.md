# Demo scope

All people, institutions, records and amounts are synthetic. XRPL Testnet only.

## Cast

- **Northside Sleep Lab** (synthetic): an 8-week sleep and fatigue study, 50 participants, stalled
  at power 0.65. Holds an ethics-review Credential and a verified-organization Credential; its
  treasury is multi-signed (principal investigator + compliance officer).
- **P-017**, the participant the demo follows: wearable, survey app and clinic records joined on
  one time axis by their personal agent. Missing in the study: fatigue survey weeks 3-5, heart rate
  week 4. Consent: sleep, activity, heart rate, automatic; anything else asks P-017.
- 49 other participants with different automation levels (automatic, standard only, every round).
- An unverified lab, and an ad network with a prohibited purpose.
- Scene A (other domains): a robot developer and four data sellers.

## Flow (about 3 minutes)

| # | Surface | What really happens |
|---|---|---|
| 1 | Researcher console | Goal typed; the LLM reads the coverage table and analysis note and proposes gaps; code keeps fatigue w3-5 and heart rate w4-5 and shows the table cells; per-person reading for P-017 shown next to the code verdict |
| 2 | Console | One signer cannot release the budget (ledger refuses); PI + compliance co-sign the top-up |
| 3 | Console | Participation requests sent; agents answer auto / ask the person / blocked; auto contributions settle by key-reveal escrow; heatmap fills; power rises |
| 4 | P-017's phone | Request card: lab name, ethics-review and verified-organization badges read from the ledger, two-sentence reason, DUO chips, fatigue w3-5 "needs you", heart rate w4 "auto", payment in XRP |
| 5 | Phone | Preview of exactly what leaves: study pseudonym, shifted days, requested items only |
| 6 | Phone | Approve: escrow per week, P-017's agent publishes each key, payment made, the study reads the key from the ledger and opens the bundle; P-017 issues the study a non-transferable licence (MPT); week 5 is held until the round closes |
| 7 | Boundaries | New purpose stops for approval; unverified lab gets no answer and its direct payment fails (`tecNO_PERMISSION`); birth date + postal code + rare diagnosis refused; a bundle sealed to the study cannot be opened with the operator key |
| 8 | Phone | Withdrawals: another participant declines a round (nothing on the ledger); one pauses (payments stay); P-017 revokes: licence Clawback, week-5 key withheld, EscrowCancel refund; console row greys out |
| 9 | Other domains | Robot developer's agent closes its evaluation gaps from two sellers on Testnet with a multi-signed top-up; consent layer replaced by seller licence terms |

## Checks enforced by code or the ledger (never by the LLM)

- LLM proposals are recomputed from the coverage table; anything without support is removed.
- Consent, period, purpose (DUO), compliance, verified organization, sensitivity: code, on order and
  again before the key is published.
- The study must still hold the licence MPT for the key to be published.
- Budget only through a multi-signed treasury; per-order limit and reservation in the engine.
- Escrow condition = sha256 of the bundle key; refund only after `CancelAfter`.
- Payments carry order id, bundle hash and consent or terms hash; no health data on the ledger.

## Surfaces

- Participant app and researcher console: UI by the team on the API in [API.md](API.md).
- Dashboard (`/`): boundary tabs with this run's evidence, study heatmap, orders with explorer
  links, agent conversation.

## Out of scope

Real device, clinic or survey APIs; mainnet funds; RLUSD; recall of already delivered rounds;
medical interpretation of any kind.
