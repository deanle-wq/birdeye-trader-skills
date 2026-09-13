---
name: birdeye-top-token-traders
description: "Rank indexed token traders by the selected Birdeye metric and time frame. Use when the trader asks: Who are the top traders for this token over the selected period?"
---

# 🏅 Top Token Traders

Answer this daily trader job: **Who are the top traders for this token over the selected period?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Top Token Traders skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-top-token-traders
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Rank the token's indexed traders using the chosen Birdeye ordering and time frame.
- Show the trading metrics returned for each wallet, including buy, sell, volume or P&L fields when present.
- Keep wallet labels and funding-source claims out unless they are explicitly returned by the endpoint.

## Just say to your agent

- `Who are the top traders for <token address> this week?`
- `Show the most profitable indexed traders for this token over 30 days.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--time-frame` | Optional | `24h` | Provider-supported trader-ranking time frame. |
| `--limit` | Optional | `20` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token traders --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `top-token-traders.traders` | `array[top-trader]` | Traders. |
| `top-token-traders.returned_count` | `integer` | Returned count. |
| `top-token-traders.time_frame` | `string` | Time frame. |
| `top-token-traders.ordering` | `string` | Ordering. |

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
- Internal dependencies: `top-token-traders`.
- Known absence: Wallet tags and funding-source attribution are not claimed unless they appear explicitly in endpoint evidence.
