---
name: birdeye-wallet-recent-sells
description: "Show a wallet's recent observable sells while excluding ambiguous transactions rather than guessing direction. Use when the trader asks: What has this wallet sold recently?"
---

# 📤 Wallet Recent Sells

Answer this daily trader job: **What has this wallet sold recently?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Wallet Recent Sells skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-wallet-recent-sells
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Filter a wallet's indexed recent activity to observable sells.
- Exclude transactions whose side cannot be classified reliably.
- Show sold token, amount, USD value and timestamp with the selected lookback window.

## Just say to your agent

- `What did <wallet address> sell today?`
- `Show this wallet's recent sells in the last 6 hours.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--time-from` | Optional | `last 168 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet sells --wallet <wallet_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `wallet-sell-feed.sells` | `array[market-trade]` | Sells. |
| `wallet-sell-feed.returned_count` | `integer` | Returned count. |
| `wallet-sell-feed.time_from` | `integer-string|null` | Time from. |
| `wallet-sell-feed.time_to` | `integer-string|null` | Time to. |
| `wallet-sell-feed.classification_method` | `string` | Classification method. |
| `wallet-sell-feed.closed_window_complete` | `boolean` | Closed window complete. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `MONITOR`; difficulty: `Basic`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `wallet-sell-feed`.
