---
name: birdeye-dev-analysis
description: "Review the Birdeye-indexed launchpad tokens associated with a developer wallet and summarize their observable market track record. Use when the user asks what a developer launched or how those launches performed; limit claims to Birdeye-indexed creation evidence."
---

# Birdeye Developer Analysis

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `run` | What has this developer launched and how did the indexed launches perform? | `birdeye-cli dev-analysis run --address <developer_wallet_address>` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Resolve a token input to its creator only when Birdeye exposes direct creation evidence; otherwise require the developer wallet.
- State launch-index coverage and do not imply a complete lifetime record.
- Compare tokens under the same price window and missing-data policy.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-dev-analysis`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `developer-created-tokens`, `developer-launch-track-record`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
