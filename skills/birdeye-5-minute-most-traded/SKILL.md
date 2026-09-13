---
name: birdeye-5-minute-most-traded
description: "Rank liquid Solana tokens by five-minute trade count to surface immediate on-chain attention. Use when the trader asks: What tokens have the most trades in the last five minutes?"
---

# ⚡ 5-Min Most-Traded Tokens

Answer this daily trader job: **What tokens have the most trades in the last five minutes?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the 5-Min Most-Traded Tokens skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-5-minute-most-traded
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Rank Solana tokens by five-minute trade count.
- Filter out tokens below $10K liquidity by default.
- Show trade count together with five-minute volume, price change, holders, liquidity and market cap.

## Just say to your agent

- `What tokens had the most trades in the last 5 minutes?`
- `Show the 10 most-traded tokens with at least $50K liquidity.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--limit` | Optional | `20` | Maximum result rows returned to the caller. |
| `--sort-by` | Optional | `trade_5m_count` | Provider-supported ranking field. |
| `--sort-type` | Optional | `desc` | Ascending or descending order. |
| `--min-liquidity` | Optional | `10000` | Minimum indexed USD liquidity. |
| `--max-liquidity` | Optional | `None` | Maximum indexed USD liquidity. |
| `--min-market-cap` | Optional | `None` | Minimum indexed USD market cap. |
| `--max-market-cap` | Optional | `None` | Maximum indexed USD market cap. |
| `--min-holder` | Optional | `None` | Minimum indexed holder count. |
| `--min-volume-5m-usd` | Optional | `None` | Minimum indexed five-minute USD volume. |
| `--min-volume-1h-usd` | Optional | `None` | Minimum indexed one-hour USD volume. |
| `--min-volume-5m-change-percent` | Optional | `None` | Minimum five-minute volume-change percentage. |
| `--min-price-change-5m-percent` | Optional | `None` | Minimum five-minute price-change percentage. |
| `--min-trade-5m-count` | Optional | `None` | Minimum five-minute trade count. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli market most-traded-5m`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `ranking_basis` | `typed` | Exact field used to rank the result. |
| `filters` | `typed` | Effective endpoint and client-side filters. |
| `fetched_count` | `typed` | Rows observed before client-side filtering. |
| `returned_count` | `typed` | Rows returned after filtering and the output limit. |
| `has_next` | `typed` | Provider pagination signal when available. |
| `tokens[].address` | `typed` | Solana token address. |
| `tokens[].symbol` | `typed` | Token symbol. |
| `tokens[].price_usd` | `typed` | Current indexed USD price. |
| `tokens[].market_cap_usd` | `typed` | Current indexed USD market cap. |
| `tokens[].liquidity_usd` | `typed` | Current indexed USD liquidity. |
| `tokens[].holder_count` | `typed` | Indexed holder count. |
| `tokens[].volume_5m_usd` | `typed` | Five-minute indexed USD volume. |
| `tokens[].volume_change_5m_pct` | `typed` | Five-minute volume change percentage. |
| `tokens[].price_change_5m_pct` | `typed` | Five-minute price change percentage. |
| `tokens[].trade_count_5m` | `typed` | Five-minute indexed trade count. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Discovery`; trader stage: `DISCOVER`; difficulty: `Basic`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `EP-002`.
