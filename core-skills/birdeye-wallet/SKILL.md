---
name: birdeye-wallet
description: "Query a Solana wallet's indexed trade history, traded tokens, sells, net flow, reconstructed PnL evidence, transfers, developer launches and comparisons with Birdeye Data. Use for wallet facts; use birdeye-wallet-analysis or birdeye-wallet-score for a decision-oriented report."
---

# Birdeye Wallet

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `activity` | What has this wallet traded in the selected window? | `birdeye-cli wallet activity --wallet <wallet_address>` |
| `traded-tokens` | Which tokens has this wallet traded? | `birdeye-cli wallet traded-tokens --wallet <wallet_address>` |
| `sells` | What has this wallet sold recently? | `birdeye-cli wallet sells --wallet <wallet_address>` |
| `net-flow` | Which tokens is this wallet buying more than selling? | `birdeye-cli wallet net-flow --wallet <wallet_address>` |
| `pnl` | What PnL can be reconstructed from indexed wallet trades? | `birdeye-cli wallet pnl --wallet <wallet_address>` |
| `token-pnl` | Which covered tokens made or lost this wallet money? | `birdeye-cli wallet token-pnl --wallet <wallet_address>` |
| `outcomes` | How are this wallet's covered trade outcomes distributed? | `birdeye-cli wallet outcomes --wallet <wallet_address>` |
| `transfers` | Which indexed token transfers involved this wallet? | `birdeye-cli wallet transfers --token <token_address> --wallet <wallet_address>` |
| `created-tokens` | Which Birdeye-indexed launchpad tokens did this developer create? | `birdeye-cli wallet created-tokens --address <developer_wallet_address>` |
| `compare` | How do these wallets compare on the same observed metrics? | `birdeye-cli wallet compare --wallets <wallet_1,wallet_2>` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- State that Birdeye x402 does not currently expose a complete current-holdings observable; traded tokens are not holdings.
- Name the time window and reconstruction method whenever reporting PnL-like metrics.
- Do not expand one wallet request into multi-wallet comparison unless the user asks.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-wallet`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `developer-created-tokens`, `wallet-balance-changes`, `wallet-comparison`, `wallet-current-holdings`, `wallet-outcome-distribution`, `wallet-pnl-stats`, `wallet-sell-feed`, `wallet-token-pnl`, `wallet-trade-history`, `wallet-transfers`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
