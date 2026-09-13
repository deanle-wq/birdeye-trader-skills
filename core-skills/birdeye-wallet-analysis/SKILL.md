---
name: birdeye-wallet-analysis
description: "Build a practical wallet dossier from indexed trade history, reconstructed performance evidence, trading style, holding duration, repeatability and current performance trend. Use when a trader asks how a wallet trades and whether its observed behavior fits their monitoring criteria."
---

# Birdeye Wallet Analysis

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `run` | How does this wallet trade, and is the observed behavior still consistent? | `birdeye-cli wallet-analysis run --wallet <wallet_address>` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Lead with the wallet's observed style, sample window and coverage before any assessment.
- Separate profitability, recency, reachability and loss behavior; do not hide them in one opaque score.
- Keep traded-token history distinct from unavailable complete current holdings.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-wallet-analysis`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `wallet-holding-duration`, `wallet-performance-trend`, `wallet-pnl-stats`, `wallet-repeatability`, `wallet-trade-history`, `wallet-trading-style`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
