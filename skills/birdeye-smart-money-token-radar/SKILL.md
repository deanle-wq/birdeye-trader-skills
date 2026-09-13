---
name: birdeye-smart-money-token-radar
description: "Rank tokens in Birdeye's smart-money feed by smart-trader participation, market cap or net flow. Use when the trader asks: What tokens are attracting the most Birdeye smart-money wallets?"
---

# 🧠 Smart-Money Token Radar

Answer this daily trader job: **What tokens are attracting the most Birdeye smart-money wallets?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Smart-Money Token Radar skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-smart-money-token-radar
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Query Birdeye's smart-money token feed for 1-day, 7-day or 30-day windows.
- Rank by smart-trader count, net flow or market cap and preserve the selected trader-style filter.
- Return provider-labeled smart-money observations without presenting them as a buy signal.

## Just say to your agent

- `What tokens are attracting the most smart-money wallets today?`
- `Show 7-day smart-money tokens ranked by net flow.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--interval` | Optional | `1d` | Provider-supported ranking or analysis interval. |
| `--limit` | Optional | `20` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli market smart-money`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `smart-money-token-feed.tokens` | `array[smart-money-token]` | Tokens. |
| `smart-money-token-feed.returned_count` | `integer` | Returned count. |
| `smart-money-token-feed.interval` | `string` | Interval. |
| `smart-money-token-feed.trader_style` | `string` | Trader style. |
| `smart-money-token-feed.ordering` | `string` | Ordering. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Discovery`; trader stage: `DISCOVER`; difficulty: `Intermediate`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `smart-money-token-feed`.
