---
name: birdeye-wallet-trading-style
description: "Profile observable holding duration, trade cadence, outcomes, repeatability and recent performance trend. Use when the trader asks: How does this wallet trade?"
---

# 🎯 Wallet Trading Style

Answer this daily trader job: **How does this wallet trade?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Wallet Trading Style skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-wallet-trading-style
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Profile observable trade cadence, holding duration, position repetition and outcome distribution.
- Describe whether the wallet behaves more like a fast trader, swing trader or slower holder only when the evidence supports it.
- Show sample size, coverage window and uncertainty behind every style label.

## Just say to your agent

- `How does <wallet address> usually trade?`
- `Does this wallet flip quickly or hold positions longer, based on the last 30 days?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--time-from` | Optional | `last 720 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet-analysis run --wallet <wallet_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `wallet-trade-history.closed_window_complete` | `boolean` | Closed window complete. |
| `wallet-trade-history.filtered_out_after_time_to` | `integer` | Filtered out after time to. |
| `wallet-trade-history.returned_count` | `integer` | Returned count. |
| `wallet-trade-history.time_from` | `integer-string|null` | Time from. |
| `wallet-trade-history.time_to` | `integer-string|null` | Time to. |
| `wallet-trade-history.trades` | `array[trade]` | Trades. |
| `sections.wallet-pnl-stats.answer` | `object|null` | Endpoint-linked answer section for `wallet-pnl-stats`; see evidence and limitations. |
| `sections.wallet-trading-style.answer` | `object|null` | Endpoint-linked answer section for `wallet-trading-style`; see evidence and limitations. |
| `sections.wallet-holding-duration.answer` | `object|null` | Endpoint-linked answer section for `wallet-holding-duration`; see evidence and limitations. |
| `sections.wallet-repeatability.answer` | `object|null` | Endpoint-linked answer section for `wallet-repeatability`; see evidence and limitations. |
| `sections.wallet-performance-trend.answer` | `object|null` | Endpoint-linked answer section for `wallet-performance-trend`; see evidence and limitations. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `RESEARCH`; difficulty: `Advanced`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `wallet-holding-duration`, `wallet-performance-trend`, `wallet-pnl-stats`, `wallet-repeatability`, `wallet-trade-history`, `wallet-trading-style`.
