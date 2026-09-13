---
name: birdeye-token-kline-chart
description: "Fetch bounded token candlesticks for the requested resolution and time window. Use when the trader asks: What does this token's recent OHLCV history look like?"
---

# 📊 Token Kline Data

Answer this daily trader job: **What does this token's recent OHLCV history look like?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token Kline Data skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-kline-chart
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Fetch OHLCV candles for an exact Solana token address.
- Support a caller-selected resolution and Unix time window.
- Return open, high, low, close, volume and candle timestamps with gaps and coverage disclosed.

## Just say to your agent

- `Show 5-minute candles for <token address> over the last 24 hours.`
- `Get the 1-hour OHLCV history for this token for the past 7 days.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--time-from` | Optional | `last 24 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--resolution` | Optional | `1H` | Provider-supported OHLCV candle resolution. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli market kline --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `token-kline-data.candles` | `array[candle]` | Candles. |
| `token-kline-data.gap_count_estimate` | `integer|null` | Gap count estimate. |
| `token-kline-data.requested_slot_estimate` | `integer|null` | Requested slot estimate. |
| `token-kline-data.resolution` | `string` | Resolution. |
| `token-kline-data.returned_count` | `integer` | Returned count. |
| `token-kline-data.time_from` | `integer-string|null` | Time from. |
| `token-kline-data.time_to` | `integer-string|null` | Time to. |

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
- Internal dependencies: `token-kline-data`.
