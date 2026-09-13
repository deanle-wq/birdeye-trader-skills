---
name: birdeye-token
description: "Query one token's identity, price, valuation, security fields, liquidity, pools, holders, traders, trades, creation, mint/burn activity and transfers through Birdeye Data. Use for direct token facts; use birdeye-token-dd for a consolidated due-diligence report."
---

# Birdeye Token

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `info` | Give me the token's basic identity, price and valuation. | `birdeye-cli token info --token <token_address>` |
| `price` | What is this token's current price? | `birdeye-cli token price --token <token_address>` |
| `security` | Which observable authority and security fields are present? | `birdeye-cli token security --token <token_address>` |
| `liquidity` | How much indexed liquidity does this token have now? | `birdeye-cli token liquidity --token <token_address>` |
| `pools` | Where is this token traded and which pools are indexed? | `birdeye-cli token pools --token <token_address>` |
| `holders` | How is this token distributed across holders? | `birdeye-cli token holders --token <token_address>` |
| `holder-ranking` | Who are the largest indexed holders? | `birdeye-cli token holder-ranking --token <token_address>` |
| `traders` | Who are the top indexed traders for this token? | `birdeye-cli token traders --token <token_address>` |
| `trades` | Show this token's indexed trades for the selected window. | `birdeye-cli token trades --token <token_address>` |
| `large-trades` | Were there unusually large indexed token trades? | `birdeye-cli token large-trades --token <token_address>` |
| `creation` | Who created this token and when? | `birdeye-cli token creation --token <token_address>` |
| `mint-burn` | Has this token been minted or burned recently? | `birdeye-cli token mint-burn --token <token_address>` |
| `transfers` | What token transfers occurred in the selected window? | `birdeye-cli token transfers --token <token_address>` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Require an exact Solana token address and reject symbols when identity is ambiguous.
- Use a single command for a single fact; use info only when the user requests a basic token card.
- Keep provider tags, security fields and holder observations separate from conclusions.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-token`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `current-token-price`, `holder-distribution`, `holder-positions`, `large-token-trades`, `mint-burn-activity`, `token-creation-evidence`, `token-liquidity-snapshot`, `token-markets-and-pools`, `token-metadata`, `token-security-check`, `token-trade-feed`, `token-transfers`, `token-valuation-snapshot`, `top-token-traders`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
