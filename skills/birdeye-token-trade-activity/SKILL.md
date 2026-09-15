---
name: birdeye-token-trade-activity
description: "Show a token’s recent indexed buys and sells over a chosen time window with direction, value, timestamp and pagination evidence when available. Use when the user asks “What trades just happened?”, “Show recent buys and sells” or wants a token activity feed. Choose birdeye-large-trade-scanner for only the biggest trades and birdeye-token-transfer-activity for non-trade token movements."
---

# 🔄 Token Trade Activity

Answer this daily trader job: **What buys and sells happened for this token recently?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token Trade Activity skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-trade-activity
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Return recent indexed buys and sells for an exact token address.
- Filter by transaction type and bounded time range where the endpoint supports it.
- Show timestamp, side, amount, USD value, wallet and transaction identity when present.

## Just say to your agent

- `Show recent buys and sells for <token address>.`
- `What trades happened in this token during the last 30 minutes?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--time-from` | Optional | `last 24 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token trades --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `token-trade-feed.trades` | `array[market-trade]` | Trades. |
| `token-trade-feed.returned_count` | `integer` | Returned count. |
| `token-trade-feed.time_from` | `integer-string|null` | Time from. |
| `token-trade-feed.time_to` | `integer-string|null` | Time to. |
| `token-trade-feed.has_next` | `boolean|null` | Has next. |
| `token-trade-feed.closed_window_complete` | `boolean` | Closed window complete. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Token Analysis`; trader stage: `RESEARCH`; difficulty: `Basic`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `token-trade-feed`.
