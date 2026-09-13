---
name: birdeye-token-dd
description: "Build one evidence-linked due-diligence dossier for a Solana token from Birdeye identity, price, security, liquidity, holder concentration, data completeness and top-trader observations. Use when the user asks whether a token deserves deeper research, not for a single raw field or a buy/sell instruction."
---

# Birdeye Token Due Diligence

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `run` | Does this token deserve deeper investigation based on observable conditions? | `birdeye-cli token-dd run --token <token_address>` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Resolve identity first and stop when the address is invalid or not a token.
- Report security, liquidity, holder structure and activity as independent gates with observed, failed and unknown states.
- Do not collapse missing evidence into a passing score or output a universal safe/buy verdict.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-token-dd`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `current-token-price`, `holder-concentration-gate`, `token-data-completeness`, `token-liquidity-snapshot`, `token-metadata`, `token-security-check`, `top-token-traders`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
