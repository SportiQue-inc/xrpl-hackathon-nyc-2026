# XRPL Latest Features & Agentic Payments: Fact Sheet (as of 2026-10-25)

> **Method note:** From this research environment, xrpl.org, xrpscan.com, docs.ripple.com, docs.t54.ai, coindesk.com and the Testnet RPC endpoints were unreachable (proxy/DNS blocks). Sources used instead:
> - xrpl.org doc sources, via the dev-portal repo on raw.githubusercontent.com. The status badges there are template macros, so they do not show enable dates.
> - The rippled `features.macro` on the develop branch.
> - The xrpl-py CHANGELOG and PyPI.
> - Web-search snippets.
>
> Mainnet enable dates come mostly from secondary trackers and news, and are marked as such. **Before the demo, the team should run the `feature` RPC on Testnet (xrpl-py `Feature()` request) to confirm what is enabled there.**

## 1. Amendment status and key transaction fields

### Takeaway
On Mainnet, the "institutional permissioning stack" is live: Credentials (2025-09-04), MPTokensV1 (2025-10-01), PermissionedDomains (2026-02-04), TokenEscrow (2026-02-12) and PermissionedDEX (2026-02-18). BatchV1_1 and fixBatchV1_2 were reportedly enabled on 2026-10-09; this comes from secondary sources and is likely but should be verified. Three groups are not enabled on Mainnet:
- **Still voting:** SingleAssetVault, LendingProtocol, LendingProtocolV1_1 and DynamicMPT.
- **Not shipped as supported in rippled:** SmartEscrow (Devnet / WASM Devnet only) and MPTokensV2 (MPT DEX).
- **Gone:** Hooks is not part of rippled/xrpld.

### Cited Findings

**Amendment registry (rippled develop `features.macro`).** The registry lists the following. `Supported::No` means the code is not ready for voting in a release, and `Supported::Yes` means it is included and votable.
- **`Supported::Yes`:**
  - Credentials, PermissionedDomains, PermissionedDEX, MPTokensV1, DynamicMPT
  - TokenEscrow, fixTokenEscrowV1, SingleAssetVault, LendingProtocol, LendingProtocolV1_1
  - BatchV1_1, fixBatchV1_2 (DefaultYes), Sponsor (XLS-68), ConfidentialTransfer, PermissionDelegationV1_1
  - DynamicNFT, DID, PriceOracle, fixPriceOracleOrder, AMMClawback, fixAMMv1_3, DeepFreeze, NFTokenMintOffer
  - fixCleanup3_1_3 / 3_2_0 / 3_3_0 / 3_4_0 / 3_5_0, fixDirectoryLimit, fixMPTDeliveredAmount
- **`Supported::No`:** SmartEscrow, MPTokensV2, LendingProtocolV1_2, Cosign, ConfidentialMPTKeyRotation.
- **Batch:** the original `Batch` is no longer listed.
- Source: [rippled features.macro](https://raw.githubusercontent.com/XRPLF/rippled/develop/include/xrpl/protocol/detail/features.macro)

**Known Amendments page notes**
- Batch: "disabled in v3.1.1 due to a bug and replaced by BatchV1_1"; BatchV1_1 implements XLS-56. — [xrpl.org Known Amendments (source)](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/resources/known-amendments.md)
- SmartEscrow status is "In Development: TBD" (XLS-100, WASM engine; custom functions control when an escrow can finish). MPTokensV2 (XLS-82) is also "In Development". — [Known Amendments (source)](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/resources/known-amendments.md)
- LendingProtocol supports "on-chain, fixed-term, uncollateralized loans using pooled funds from a Single Asset Vault", with off-chain underwriting (XLS-66). LendingProtocolV1_1 adds closed-ended vaults (subscription, investment and redemption phases) and cash-basis accounting. — [Known Amendments (source)](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/resources/known-amendments.md)
- DynamicMPT makes MPT metadata, the transfer fee and capability flags mutable unless they are declared in `ImmutableFlags`. — [Known Amendments (source)](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/resources/known-amendments.md)

**Mainnet enable dates (secondary sources: Jake Claver amendment index, cited via search)**

| Amendment | Enabled | Ledger |
|---|---|---|
| Credentials | 2025-09-04 | 98,615,297 |
| PermissionedDomains | 2026-02-04 | 102,017,793 |
| TokenEscrow | 2026-02-12 | 102,204,929 |
| PermissionedDEX | 2026-02-18 | 102,328,065 |
| MPTokensV1 | 2025-10-01 | 99,226,369 |
| DeepFreeze | 2025-05-04 | 95,893,505 |

Sources:
- [jakeclaver.com index](https://www.jakeclaver.com/xrp-ledger-amendments-complete-index/)
- PermissionedDomains: RippleX said "Permissioned Domains are now live on XRPL Mainnet, and Permissioned DEX has achieved validator consensus to activate in 2 weeks" ([RippleX on X](https://x.com/RippleXDev/status/2019165474752524686)), and coverage reported a 91% vote ([CoinCentral](https://coincentral.com/ripples-permissioned-domains-go-live-on-xrpl-mainnet-after-91-vote/))
- MPTokensV1: 28/38 validators, Oct 1 2025 ([CryptoRank](https://cryptorank.io/news/feed/4ad0e-mpt-standard-on-xrp-ledger-mainnet))

**Testnet**
- A GitHub research repo that read the on-ledger Amendments object on 2026-10-02 reports these as enabled on both Testnet and Mainnet: DepositAuth, DepositPreauth, Credentials, PermissionedDomains, PermissionedDEX, Clawback, DeepFreeze, TokenEscrow and MPTokensV1. This is a single third-party source. — [IllestAlive/xrpl-input-credit](https://github.com/IllestAlive/xrpl-input-credit)
- The Testnet runs "stable releases", and its amendment status "is intended to closely" track Mainnet. Devnet runs "beta releases" with features "not yet enabled on the Mainnet". — [parallel-networks doc (source)](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/concepts/networks-and-servers/parallel-networks.md)

**Batch (XLS-56)**
- The original Batch had a signature-validation flaw, reported on 2026-02-19, that let an attacker run inner transactions for victim accounts. It was never live on Mainnet, and rippled 3.1.1 disabled it. — [xrpl.org vuln report Feb 2026](https://xrpl.org/blog/2026/vulnerabilitydisclosurereport-bug-feb2026); [rippled 3.1.1 blog](https://xrpl.org/es-es/blog/2026/rippled-3.1.1)
- BatchV1_1 had been on a conditional path to activate on Sept 29. Validators then voted "no" to reset its clock after a 3.4.0 bug. It was reportedly enabled on Mainnet on 2026-10-09 together with fixBatchV1_2. All of these reports are secondary.
  - [Crypto Times Oct 11](https://www.cryptotimes.io/2026/10/11/xrp-ledger-reveals-critical-bug-that-could-have-minted-xrp-beyond-its-100-billion-supply/)
  - [Finwire](https://finwire.io/news/crypto-news/xrp-ledger-batch-goes-live-enabling-bundled-transactions)
  - [CCN](https://www.ccn.com/education/crypto/xrp-ledger-batch-v1-1-atomic-multi-account-transactions/)
  - [KuCoin Sept 29 schedule](https://www.kucoin.com/news/flash/xrp-ledger-s-batchv1-1-upgrade-set-for-sept-29-activation)
- Server operators must run xrpld 3.4.1 or newer to stay in sync. — [xrpl.org 3.4.1 vuln report](https://xrpl.org/blog/2026/vulnerabilitydisclosurereport-bug-20261009)
- **Batch fields:**
  - `Flags` takes exactly one mode: `tfAllOrNothing` 0x00010000, `tfOnlyOne` 0x00020000, `tfUntilFailure` 0x00040000, or `tfIndependent` 0x00080000.
  - `RawTransactions` holds 2 to 8 inner transactions.
  - `BatchSigners` is needed only for multi-account batches (up to 24 signatures).
  - Inner transactions must:
    - set `tfInnerBatchTxn` (0x40000000);
    - have `Fee` "0";
    - have `SigningPubKey` "" and no `TxnSignature`;
    - have either a `Sequence` or a `TicketSequence`.
  - Some Loan/LoanBroker transactions are not allowed as inner transactions (`temINVALID_INNER_BATCH`).
  - Source: [batch.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/batch.md)
- Client caveat: xrpl.js 5.0.0 produced the old Batch signature format, which BatchV1_1 nodes reject; the fix is in 5.1.0. — [Yahoo/BatchV1_1 coverage](https://finance.yahoo.com/markets/crypto/articles/xrp-ledger-one-vote-away-090844733.html)

**Lending and vaults (XLS-65/66)**
- Not enabled on Mainnet. LendingProtocolV1_1 opened for voting around 2026-10-01, with no activation date. A 2026-09-17 third-party snapshot showed 16/35 validators supporting SingleAssetVault and 13/35 supporting LendingProtocol.
  - [CryptoTimes Oct 1](https://www.cryptotimes.io/2026/10/01/xrpl-opens-new-lending-protocol-amendment-for-validator-vote/)
  - [allaboutxrp](https://allaboutxrp.com/news/xrpl-lendingprotocol-v1-1-supported-develop)
  - [Yahoo: three amendments](https://finance.yahoo.com/markets/crypto/articles/three-amendments-define-path-xrpl-140822049.html)
- **VaultCreate fields:**
  - `Asset` (XRP, IOU or MPT), `AssetsMaximum`, `Data` (256 B), `DomainID`, `MPTokenMetadata` (share metadata)
  - `Scale`, `WithdrawalPolicy`
  - `VaultKind` (0 = open-ended, 1 = closed-ended) and `SubscriptionDate` / `RedemptionDate` (both V1_1)
  - Flags: `tfVaultPrivate`, `tfVaultShareNonTransferable`
  - A vault cannot be created for an MPT without CanTransfer.
  - Source: [vaultcreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/vaultcreate.md)
- **LoanSet fields:**
  - `LoanBrokerID`, `PrincipalRequested`, `Counterparty`, `CounterpartySignature`
  - `InterestRate` (in 1/10 basis points), `PaymentTotal`, `PaymentInterval`, `GracePeriod`
  - Fees: origination, service, late and close
  - The transaction is co-signed by broker and borrower.
  - Source: [loanset.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/loanset.md)
- **Demo viability:** inferred as Devnet only (Supported::Yes but not enabled on Mainnet; whether it is on Testnet is unverified).

**DynamicMPT**
- Shipped in xrpld 3.3.0 (Aug 6 2026). Not active; trackers disagree on the vote (about 17–19 yes out of 29–36). — [xrpl.to insights](https://xrpl.to/insights/xrpl-amendments-explained); [xrpldashboard](https://xrpldashboard.com/amendments)

**Smart Escrows (XLS-100)**
- The ninth Smart Escrow Devnet launched around early Oct 2026. The WASM VM integration moved from C++ to Rust (30–50% faster per host function call). Two security audits were done before Devnet 8.
  - [Bitget](https://www.bitget.com/amp/news/detail/12560605914998)
  - [U.Today](https://u.today/xrp-ledger-takes-big-step-toward-smart-escrow-launch)
  - [Coin Republic](https://www.thecoinrepublic.com/2026/02/20/xrp-ledger-smart-escrow-update-bags-major-devnet-overhaul/)
- The xrpl.org faucets page lists a separate "WASM Devnet" for XLS-100. — [XRP Faucets](https://xrpl.org/resources/dev-tools/xrp-faucets) (search snippet)
- The spec is still a draft. — [XLS-0100](https://xls.xrpl.org/xls/XLS-0100-smart-escrows.html); [opensource.ripple.com XLS-100](https://opensource.ripple.com/docs/xls-100-smart-escrows)
- A Coinpedia headline says "XLS-100 Smart Escrows Goes Live". This conflicts with rippled `Supported::No`, so treat it as Devnet-only. — [Coinpedia](https://coinpedia.org/news/xls-100-smart-escrows-goes-live-xrpl-gets-its-own-programmable-payments-layer/)

**Hooks**
- Hooks are not part of XRPL mainline. xrpl-py 5.2.0 removed the Hook/Emit field definitions "as Hooks is no longer supported", and xrpl-py 2.6.0 removed the Hooks faucet "since it's now on the Xahau testnet". — [xrpl-py CHANGELOG](https://raw.githubusercontent.com/XRPLF/xrpl-py/main/CHANGELOG.md)

**Transaction fields: Credentials and DepositPreauth**
- **CredentialCreate** (sent by the issuer):
  - `Subject` (required)
  - `CredentialType` (hex, 1–64 bytes, required)
  - `Expiration` (optional, seconds since the Ripple Epoch)
  - `URI` (optional hex)
  - Errors: `tecDUPLICATE`, `tecEXPIRED`, `tecNO_TARGET`
  - Source: [credentialcreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/credentialcreate.md)
- **CredentialAccept** (sent by the subject): `Issuer` and `CredentialType`. If the credential has expired, it returns `tecEXPIRED` and also deletes the expired credential. — [credentialaccept.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/credentialaccept.md)
- **CredentialDelete:** fields not fetched; field names are not confirmed in these notes (gap).
- **DepositPreauth:** exactly one of `Authorize`, `AuthorizeCredentials`, `Unauthorize` or `UnauthorizeCredentials`. Each credential entry is `{Issuer, CredentialType}`. Each entry costs one owner-reserve item. — [depositpreauth.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/depositpreauth.md)
- Payment and EscrowFinish take `CredentialIDs` (a Vector256 of Credential ledger-entry IDs) to satisfy a destination's credential-based preauthorization. — [escrowfinish.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/escrowfinish.md)

**Transaction fields: Permissioned Domains and DEX**
- **PermissionedDomainSet:** `DomainID` (omit it to create a domain) and `AcceptedCredentials` (1–10 `{Issuer, CredentialType}` entries, no duplicates). Returns `temDISABLED` if either PermissionedDomains or Credentials is off. — [permissioneddomainset.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/permissioneddomainset.md)
- **Permissioned DEX:** OfferCreate takes `DomainID` (the offer is restricted to that domain's order book), and the `tfHybrid` flag (0x00100000) lets an offer use both the domain book and the open DEX. — [offercreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/offercreate.md)

**Transaction fields: MPTokenIssuanceCreate**
- Fields:
  - `AssetScale`, `MaximumAmount` (default max 2^63−1)
  - `TransferFee` (0–50,000; requires CanTransfer)
  - `MPTokenMetadata` (≤1024 bytes hex; the XLS-89 JSON schema is recommended)
  - `DomainID` (requires `tfMPTRequireAuth`)
  - `ImmutableFlags` (DynamicMPT)
- Flags:

| Flag | Value |
|---|---|
| `tfMPTCanLock` | 0x02 |
| `tfMPTRequireAuth` | 0x04 |
| `tfMPTCanEscrow` | 0x08 |
| `tfMPTCanTrade` | 0x10 |
| `tfMPTCanTransfer` | 0x20 |
| `tfMPTCanClawback` | 0x40 |
| `tfMPTCanHoldConfidentialBalance` | 0x80 (ConfidentialTransfer) |

- Source: [mptokenissuancecreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/mptokenissuancecreate.md)
- **MPT on the DEX:** MPTokensV2 (XLS-82, MPT DEX integration) is `Supported::No` and "In Development", so MPTs cannot trade on the Mainnet DEX or AMM yet. — [features.macro](https://raw.githubusercontent.com/XRPLF/rippled/develop/include/xrpl/protocol/detail/features.macro); [Known Amendments (source)](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/resources/known-amendments.md)

**Transaction fields: Token Escrow (XLS-85)**
- EscrowCreate `Amount` can now be an IOU or MPT.
  - IOUs need the issuer's **Allow Trust Line Locking** flag.
  - MPTs need both **CanEscrow** and **CanTransfer**.
  - If the token requires authorization, both sender and recipient must be pre-authorized.
  - Errors: `tecNO_PERMISSION`, `tecNO_AUTH`, `tecFROZEN`.
  - Source: [escrowcreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/escrowcreate.md)
- Time-based escrows with no `Condition` are labeled "XRP only" in the field-combination table. Whether this still holds for tokens is unverified.

**Transaction fields: DIDSet**
- `Data`, `DIDDocument`, `URI` (at least one is required; otherwise `temEMPTY_DID` / `tecEMPTY_DID`). — [didset.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/didset.md)

**xrpl-py support by version**

| Version | Date | Adds |
|---|---|---|
| 2.5.0 | | DID |
| 2.6.0 | | PriceOracle, DynamicNFT |
| 4.0.0 | 2024-12-23 | MPT, Credentials |
| 4.1.0 | 2025-02 | DeepFreeze, PermissionedDomains, AMMClawback, `simulate` RPC |
| 4.2.0 | 2025-06 | SingleAssetVault, Permission Delegation (XLS-74/75), original Batch |
| 4.3.0 | 2025-07 | TokenEscrow, NFTokenMintOffer, PermissionedDEX |
| 4.3.1 | 2025-11 | XLS-89 `encode_mptoken_metadata` / `decode_mptoken_metadata` (breaking MPTokenMetadata type change) |
| 4.4.0 | 2025-12 | Lending Protocol |
| 4.5.0 | 2026-02 | `sign_loan_set_by_counterparty` |
| 5.0.0 | 2026-06 | Python ≥3.10; `Wallet.from_seed` algorithm now inferred from the seed prefix |
| 5.1.0 | 2026-08 | Confidential MPT (XLS-96), Sponsored Fees/Reserves (XLS-68), DynamicMPT (XLS-94), **BatchV1_1 signing; old Batch signing dropped** |
| 5.2.0 | 2026-09-16 | LendingProtocolV1_1, fixCleanup3_4_0 signing prefixes, Hooks fields removed |

- The latest stable release is 5.2.0; 5.3.0b0 came out on 2026-10-15.
- Sources: [xrpl-py CHANGELOG](https://raw.githubusercontent.com/XRPLF/xrpl-py/main/CHANGELOG.md); [PyPI xrpl-py](https://pypi.org/project/xrpl-py/)

### Inferences
- **Safest Testnet demo stack:** Credentials → DepositPreauth with AuthorizeCredentials → PermissionedDomain → MPT with `DomainID` + RequireAuth, or permissioned DEX offers. Add Token Escrow of an MPT/IOU and Batch as needed. All of these are Mainnet-enabled and should be on Testnet.
- Batch demos need xrpl-py ≥5.1.0 (or xrpl.js ≥5.1.0). Older 4.x builds sign in the old format, which is rejected.
- For Vault, Lending, DynamicMPT and Smart Escrow, plan on Devnet / WASM Devnet. Confirm with the `feature` RPC first.
- Use xrpl-py 5.2.0 to cover every transaction type above.

### Gaps
- No official ledger-sourced enable dates were retrieved; xrpl.org and XRPScan were blocked. Not verified here: AMM, DID, PriceOracle, Clawback, AMMClawback and DynamicNFT dates. From memory (UNVERIFIED): AMM ~2024-03-22, Clawback ~2024-02, DID ~2024-10, PriceOracle ~2024-11, AMMClawback ~2025-01, DynamicNFT ~2025.
- The live Testnet and Devnet amendment sets were not queried.
- Oracle (OracleSet) field details and the CredentialDelete doc were not fetched.

## 2. RLUSD on XRPL

### Takeaway
Testnet RLUSD is a trust-line (IOU) token from issuer `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV`, with currency hex `524C555344000000000000000000000000000000`. Recipients need a trust line. Test RLUSD reportedly comes from tryrlusd.com (GitHub login, 10/day, no API). No MPT version of RLUSD was found.

### Cited Findings
- Ripple docs (via search snippet) give the Testnet issuer as `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV` on wss://s.altnet.rippletest.net:51233, with currency code `524C555344000000000000000000000000000000`. Users set a trust line to the issuer to hold the token, and Testnet tokens have no value. — [RLUSD on the XRPL (docs.ripple.com)](https://docs.ripple.com/products/stablecoin/developer-resources/rlusd-on-the-xrpl)
- A developer PR says the only faucet is tryrlusd.com: it needs a GitHub login and a browser wallet, gives 10 per day and has no API. This is a secondary source. — [dassie PR #244](https://github.com/justmoon/dassie/pull/244)
- t54 publishes an `rlusd-cli`: fund the wallet from the XRP Testnet faucet, set the RLUSD trust line, then receive RLUSD. — [t54-labs/rlusd-cli](https://github.com/t54-labs/rlusd-cli)

### Inferences
- Get test RLUSD early. Because of the daily cap, a demo agent wallet should be pre-funded, and the team might also issue its own "mock RLUSD" IOU or MPT as a fallback.
- RLUSD is an IOU, so a Token Escrow of RLUSD needs the issuer's Allow Trust Line Locking flag. Whether Ripple's Testnet issuer sets it is unverified.

### Gaps
- The Mainnet RLUSD issuer address, the issuer's clawback/freeze flags and any MPT RLUSD could not be verified, because docs.ripple.com was unreachable.

## 3. Agentic payments on XRPL

### Takeaway
t54's x402 facilitator has been live on XRPL since about Feb 2026 and handles XRP and RLUSD. Ripple shipped an "XRPL AI Starter Kit" on 2026-06-10 with an XRPL Docs MCP server and Claude skills. The NYC XRPL hackathon (XRPL Commons and the XRP Ledger Foundation, Oct 24–25, 2026, before Swell) has an "Agentic Finance" track.

### Cited Findings
- **t54 x402 facilitator:**
  - t54 announced: "The x402 facilitator is now live on the XRPL. AI agents can now pay for services using $XRP and $RLUSD." — [t54.ai on X](https://x.com/t54ai/status/2024484156487377388); [TradingView/Coinpedia](https://www.tradingview.com/news/coinpedia:f04d471eb094b:0-xrp-ledger-news-today-ai-agents-can-now-pay-with-xrp-and-rlusd-via-x402/)
  - The docs (via search snippet) say it implements the x402 "exact" scheme with a payer-signed XRPL Payment. A hosted facilitator runs at `xrpl-x402.t54.ai`, with an Express middleware example. SDKs exist for Python, TypeScript, FastAPI and Express, and the docs say the developer experience "is still evolving". — [docs.t54.ai XRPL x402 Facilitator](https://docs.t54.ai/docs/xrpl/x402-facilitator)
  - In July 2026, t54 added Mastercard Verifiable Intent support plus "Trustline" risk screening before settlement. — [t54.ai on X](https://x.com/t54ai/status/2080708873178992737)
  - On 2026-03-19, Virtuals Protocol and t54 announced agent commerce on XRPL. — [Bitcoinist](https://bitcoinist.com/xrp-ledger-ai-agent-payments-virtuals-t54/)
  - t54's GitHub is at [t54 labs](https://github.com/t54-labs).
- **Ripple XRPL AI Starter Kit (2026-06-10):** includes the XRPL Docs MCP Server (for Claude Code, Claude Desktop and Cursor), an "XRPL Agent Wallet Skill", an "XRPL Payment Skill", and x402 integration. — [Cryptonomist](https://en.cryptonomist.ch/2026/06/11/ripple-xrpl-ai-starter-kit-2/); [CoinMarketCap Academy](https://coinmarketcap.com/academy/article/ripple-launches-ai-agent-payments-with-xrp-and-rlusd); [Bitcoin.com](https://news.bitcoin.com/xrp-gets-ai-agent-payment-support-in-ripples-xrpl-ai-starter-kit-as-executive-sees-billions-ahead/)
- **Adoption claims:** about 13.41M cumulative x402 payments and 166 merchants, attributed to RippleX's J. Ayo Akinyele. These are company-sourced and unaudited. — [Digital Today](https://www.digitaltoday.co.kr/en/view/113211/xrpl-expands-ai-agent-payment-network-cumulative-total-tops-13-million)
- **Skeptical view:** the Motley Fool questioned how much incremental network activity this brings. — [Motley Fool](https://www.fool.com/investing/2026/07/03/ripple-is-bringing-agentic-ai-payments-to-the-xrp/)
- **NYC hackathon:**
  - Tracks: Agentic Finance, Protocol Innovation, Lending & Borrowing (XLS-65/66) and "Why Not". 36 hours on Oct 24–25, 2026.
  - Reports of Mastercard involvement are not confirmed by the official page.
  - Sources: [Swell hackathon page](https://swell.ripple.com/hackathon); [Luma](https://luma.com/xrpl-hackathon-nyc); [Genfinity](https://genfinity.io/2026/08/24/xrp-ledger-hackathon-nyc-october-2026-xrpl-commons-swell/); [Crypto Economy](https://crypto-economy.com/mastercard-joins-xrpl-hackathon/)
- **Unverified:** "XRPL Commons launches AI payment framework" (Oct 21, 2026), with no corroboration. — [emergent.sh](https://emergent.sh/news/xrpl-commons-launches-ai-payment-framework)

### Inferences
- A strong Agentic Finance demo would layer three things:
  1. x402 pay-per-request in RLUSD or XRP through the t54 facilitator;
  2. Credentials / DepositPreauth so that only KYC'd agents can pay a merchant;
  3. Batch (AllOrNothing) for atomic multi-leg settlement.
- Since a Lending track exists, judges are likely to value Vault/Loan use. Those features are Devnet-only, so the team should state the network explicitly.

### Gaps
- Whether t54's facilitator supports Testnet (CAIP-2 `xrpl:1`), and its exact npm/PyPI package names, could not be confirmed; docs.t54.ai was unreachable.
- No independent security review of the facilitator was found.

## 4. Gotchas

### Takeaway
The main traps:
- Reserves: 1 XRP base plus 0.2 XRP per object.
- Altnet resets: Devnet in particular is reset.
- Credential `Expiration` is in Ripple-epoch seconds; expired credentials fail and get deleted.
- DepositAuth blocks EscrowFinish by third parties unless they are preauthorized or present credentials.
- Batch needs current SDKs.

### Cited Findings
- **Reserves:** since 2024-12-02, the Mainnet base reserve is 1 XRP and the owner reserve is 0.2 XRP per item (cut from 10 and 2). — [xrpl.org blog: lower reserves](https://xrpl.org/blog/2024/lower-reserves-are-in-effect); [The Block](https://www.theblock.co/post/329247/xrp-ledger-base-reserve)
  - Each Credential, DepositPreauth entry, PermissionedDomain, MPTokenIssuance and MPToken is an owned object (see the `tecINSUFFICIENT_RESERVE` errors). — [depositpreauth.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/depositpreauth.md); [permissioneddomainset.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/permissioneddomainset.md)
- **Resets:** Test XRP "is lost when the network is reset". The Testnet and Devnet use a non-diverse validator set run by Ripple. — [parallel-networks.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/concepts/networks-and-servers/parallel-networks.md)
  - A Devnet reset was announced alongside rippled 3.1.1. — [rippled 3.1.1 blog](https://xrpl.org/es-es/blog/2026/rippled-3.1.1)
  - Altnets may delete the destination of a pending escrow, in which case EscrowFinish returns `tecNO_TARGET`. — [escrowfinish.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/escrowfinish.md)
- **Credential expiration:**
  - `Expiration` is a UInt32 in seconds since the Ripple Epoch (2000-01-01). Creating a credential with a past expiration returns `tecEXPIRED`. — [credentialcreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/credentialcreate.md)
  - Accepting an expired credential returns `tecEXPIRED` and deletes it. — [credentialaccept.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/credentialaccept.md)
  - A credential must be accepted by the subject before it counts. — [credentialaccept.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/credentialaccept.md)
- **DepositAuth and EscrowFinish:** an account with DepositAuth receives XRP from EscrowFinish only if the EscrowFinish sender is the escrow's destination, or if the destination has preauthorized that sender. Otherwise, the finisher passes `CredentialIDs` that match an `AuthorizeCredentials` preauth. — [depositauth.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/concepts/accounts/depositauth.md); [escrowfinish.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/escrowfinish.md)
- **MPT configuration:** a non-zero `TransferFee` without CanTransfer gives `temMALFORMED`. A `DomainID` without RequireAuth also gives `temMALFORMED`. A `DomainID` on an MPT gives `temDISABLED` unless both PermissionedDomains and SingleAssetVault are enabled. — [mptokenissuancecreate.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/mptokenissuancecreate.md)
  - **Important:** because SingleAssetVault is not enabled on Mainnet, MPT `DomainID` is likely unusable on Mainnet and Testnet. This is an inference.
- **Token escrow of MPTs:** the escrow destination must already hold the MPT (`tecNO_ENTRY`), or have a trust line for IOUs (`tecNO_LINE`). — [escrowfinish.md](https://raw.githubusercontent.com/XRPLF/xrpl-dev-portal/master/docs/references/protocol/transactions/types/escrowfinish.md)
- **xrpl-py 5.0 wallet change:** `Wallet.from_seed` now infers the algorithm from the seed prefix, which changes the derived address for an `s...` seed that was used as ED25519 without an explicit algorithm. — [xrpl-py CHANGELOG](https://raw.githubusercontent.com/XRPLF/xrpl-py/main/CHANGELOG.md)

### Inferences
- Fund each demo account with at least 10 test XRP. Show credentials with an `Expiration` a few minutes ahead to demonstrate expiry live. Avoid MPT `DomainID` on Testnet unless the `feature` RPC shows SingleAssetVault enabled; use the permissioned DEX (OfferCreate `DomainID`) to show domains instead.

### Gaps
- Current Testnet reserve values and any Testnet reset scheduled for late Oct 2026 were not verified.
