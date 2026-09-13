---
name: birdeye-market
description: "Discover active, new, trending, launch-stage, smart-money and top-performing tokens, or fetch OHLCV and recent market activity with Birdeye Data. Use for market discovery and chart-data requests; use birdeye-market-radar when the user wants a ranked multi-signal shortlist."
---

# Birdeye Market

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
| `trending-5m` | Which tokens are trading most actively in the last five minutes? | `birdeye-cli market trending-5m` |
| `launchpad-trending` | Which tokens are trending on this launchpad right now? | `birdeye-cli market launchpad-trending` |
| `launchpad-new` | Which tokens were created on this launchpad in the last 24 hours? | `birdeye-cli market launchpad-new` |
| `pumpfun-trending` | Which Pump.fun tokens are hottest over the last hour? | `birdeye-cli market pumpfun-trending` |
| `pumpfun-new` | Which Pump.fun tokens were created in the last 24 hours? | `birdeye-cli market pumpfun-new` |
| `near-graduation` | Which launchpad tokens are closest to graduating? | `birdeye-cli market near-graduation` |
| `migrated` | Which launchpad tokens graduated to a DEX in the last 24 hours? | `birdeye-cli market migrated` |
| `migrated-quality` | Which recently migrated tokens pass practical liquidity and market-cap filters? | `birdeye-cli market migrated-quality` |
| `volume-surge-5m` | Which tokens have the strongest five-minute volume acceleration? | `birdeye-cli market volume-surge-5m` |
| `price-surge-5m` | Which liquid tokens are surging most over five minutes? | `birdeye-cli market price-surge-5m` |
| `most-traded-5m` | Which tokens have the most trades in the last five minutes? | `birdeye-cli market most-traded-5m` |
| `trending` | Which tokens are trending right now? | `birdeye-cli market trending` |
| `new-listings` | Which tokens were listed recently? | `birdeye-cli market new-listings` |
| `launch-stages` | Which launchpad tokens are near or past graduation? | `birdeye-cli market launch-stages` |
| `screen` | Which tokens match my numeric market filters? | `birdeye-cli market screen` |
| `smart-money` | Which tokens appear in Birdeye smart-money data? | `birdeye-cli market smart-money` |
| `gainers` | Which indexed traders are gaining or losing the most? | `birdeye-cli market gainers` |
| `kline` | Show this token's candles for the selected window. | `birdeye-cli market kline --token <token_address>` |
| `activity` | What trades are happening across the market now? | `birdeye-cli market activity` |

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

- Choose the narrowest command that answers the request; do not run every discovery feed by default.
- Apply user-supplied filters before optional enrichment and preserve the selected window and sort order.
- Treat trending, smart-money and gainers lists as discovery evidence, not buy signals.

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.

## Runtime contract

- Public package: `birdeye-market`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: `EP-002`, `EP-006`, `bonding-curve-token-stages`, `configurable-token-filter`, `newly-listed-tokens`, `recent-market-activity`, `smart-money-token-feed`, `token-kline-data`, `trader-gainers-losers`, `trending-tokens`.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
