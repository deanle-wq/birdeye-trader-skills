---
name: birdeye-monitor
description: "Compare current Birdeye token, wallet, holder, pool or bonding-curve evidence with a caller-supplied baseline. Use when the user asks what changed since an earlier observation. This skill does not provide a scheduler, subscription or push alert service."
---

# Birdeye Monitor

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `wallet-flow` | How did this wallet's observed token flow change? | `birdeye-cli monitor wallet-flow --wallet <wallet_address> --baseline-json '<baseline_json>'` |
| `wallet-pnl` | How did reconstructed wallet PnL change? | `birdeye-cli monitor wallet-pnl --wallet <wallet_address> --baseline-json '<baseline_json>'` |
| `wallet-behavior` | Is this wallet behaving differently from the baseline? | `birdeye-cli monitor wallet-behavior --wallet <wallet_address> --baseline-json '<baseline_json>'` |
| `token-security` | Which observable token security fields changed? | `birdeye-cli monitor token-security --token <token_address> --baseline-json '<baseline_json>'` |
| `token-liquidity` | How did current indexed token liquidity change? | `birdeye-cli monitor token-liquidity --token <token_address> --baseline-json '<baseline_json>'` |
| `holders` | How did observed holder concentration change? | `birdeye-cli monitor holders --token <token_address> --baseline-json '<baseline_json>'` |
| `bonding-curve` | How did this token's bonding-curve progress change? | `birdeye-cli monitor bonding-curve --token <token_address> --baseline-json '<baseline_json>'` |
| `graduation` | Did this launchpad token's graduation status change? | `birdeye-cli monitor graduation --token <token_address> --baseline-json '<baseline_json>'` |
| `pool` | How did this pool's activity change? | `birdeye-cli monitor pool --pair <pair_address> --baseline-json '<baseline_json>'` |
| `watchlist` | What materially changed for this watched token and wallet? | `birdeye-cli monitor watchlist --token <token_address> --wallet <wallet_address> --baseline-json '<baseline_json>'` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Require a compatible caller baseline; never describe a current feed as a change monitor.
- Compare like-for-like entity, fields, units, filters, windows and coverage.
- Return material deltas with evidence and unknowns; do not predict the next move.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-monitor`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `bonding-curve-progress-delta`, `graduation-status-delta`, `holder-concentration-delta`, `pool-activity-delta`, `token-liquidity-delta`, `token-security-delta`, `wallet-behavior-deviation`, `wallet-pnl-delta`, `wallet-position-delta`, `watchlist-material-change`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
