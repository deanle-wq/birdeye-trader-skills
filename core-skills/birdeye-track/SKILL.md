---
name: birdeye-track
description: "Inspect current smart-money token activity, token-specific smart-money evidence, selected KOL wallet trades, wallet activity, exits and post-exit rotation through Birdeye Data. Use for current activity and tracking questions, not unattended alerts or automatic copy trading."
---

# Birdeye Track

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `smart-money` | Which tokens are visible in Birdeye's smart-money feed? | `birdeye-cli track smart-money` |
| `smart-money-token` | What smart-money evidence is visible for this token? | `birdeye-cli track smart-money-token --token <token_address>` |
| `kol` | What did these selected KOL wallets trade? | `birdeye-cli track kol --wallets <wallet_1,wallet_2>` |
| `wallet` | What did this wallet trade recently? | `birdeye-cli track wallet --wallet <wallet_address>` |
| `exit` | Where did observable activity go after this wallet reduced a token? | `birdeye-cli track exit --token <token_address> --wallet <wallet_address>` |
| `rotation` | What did this wallet buy after selling this token? | `birdeye-cli track rotation --token <token_address> --wallet <wallet_address>` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Use the broad smart-money feed for discovery and token-specific evidence only after a token is named.
- Require explicit wallet addresses for KOL activity because Birdeye x402 does not provide a complete KOL directory.
- Separate current feeds from monitoring: a feed has no prior baseline and makes no change claim.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-track`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `exit-destination-trace`, `kol-trades`, `same-wallet-rotation`, `smart-money-token-feed`, `smart-money-trades`, `wallet-trade-history`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
