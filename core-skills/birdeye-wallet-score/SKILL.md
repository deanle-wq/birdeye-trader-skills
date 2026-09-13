---
name: birdeye-wallet-score
description: "Evaluate observable wallet track-record quality and copyability under explicit time, liquidity, delay and position-size assumptions using Birdeye Data. Use when the user asks whether a wallet's past results could survive their own execution constraints; return evidence and scenario ranges, not a guaranteed return or follow command."
---

# Birdeye Wallet Copyability

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `run` | How copyable are this wallet's observed results under my assumptions? | `birdeye-cli wallet-score run --wallet <wallet_address> --size-usd 100 --latency-seconds 30` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Keep track-record quality and copyability as separate dimensions.
- Require sufficient closed-trade coverage before presenting a score or grade.
- Expose every latency, liquidity, fee and size assumption; never describe the result as an executable backtest.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-wallet-score`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `latency-adjusted-copyability`, `liquidity-adjusted-copyability`, `wallet-outcome-distribution`, `wallet-pnl-stats`, `wallet-repeatability`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
