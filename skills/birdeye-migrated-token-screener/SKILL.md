---
name: birdeye-migrated-token-screener
description: "Screen recently migrated tokens with default market cap of $50K–$200K and at least $10K indexed liquidity. Use when the trader asks: What recently migrated tokens meet practical liquidity and market-cap thresholds?"
---

# 🔍 Migrated Token Quality Screener

Answer this daily trader job: **What recently migrated tokens meet practical liquidity and market-cap thresholds?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Migrated Token Quality Screener skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-migrated-token-screener
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Fetch recently graduated tokens and apply a default $50K–$200K market-cap band.
- Require at least $10K indexed liquidity by default, then rank the survivors by one-hour volume.
- Let the trader override the market-cap and liquidity thresholds while disclosing that unavailable bundle, fresh-wallet and top-10 filters are not applied.

## Just say to your agent

- `Screen newly migrated tokens between $50K and $200K market cap with at least $10K liquidity.`
- `Find recently graduated tokens above $25K liquidity and tell me exactly which filters were applied.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--time-from` | Optional | `last 24 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `20` | Maximum result rows returned to the caller. |
| `--sort-by` | Optional | `volume_1h_usd` | Provider-supported ranking field. |
| `--sort-type` | Optional | `desc` | Ascending or descending order. |
| `--source` | Optional | `None` | Solana launchpad source: `all`, Pump.fun, Moonshot, Raydium LaunchLab or Meteora DBC; common human-readable aliases are normalized. |
| `--graduated` | Fixed | `true` | Whether launchpad tokens must already be graduated. |
| `--min-liquidity` | Optional | `10000` | Minimum indexed USD liquidity. |
| `--max-liquidity` | Optional | `None` | Maximum indexed USD liquidity. |
| `--min-market-cap` | Optional | `50000` | Minimum indexed USD market cap. |
| `--max-market-cap` | Optional | `200000` | Maximum indexed USD market cap. |
| `--min-holder` | Optional | `None` | Minimum indexed holder count. |
| `--min-volume-5m-usd` | Optional | `None` | Minimum indexed five-minute USD volume. |
| `--min-volume-1h-usd` | Optional | `None` | Minimum indexed one-hour USD volume. |
| `--min-volume-5m-change-percent` | Optional | `None` | Minimum five-minute volume-change percentage. |
| `--min-price-change-5m-percent` | Optional | `None` | Minimum five-minute price-change percentage. |
| `--min-trade-5m-count` | Optional | `None` | Minimum five-minute trade count. |
| `--min-progress-percent` | Optional | `None` | Minimum bonding-curve completion percentage. |
| `--max-progress-percent` | Optional | `None` | Maximum bonding-curve completion percentage. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli market migrated-quality`

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
| `tokens[].market_cap_usd` | `typed` | Current indexed USD market cap. |
| `tokens[].liquidity_usd` | `typed` | Current indexed USD liquidity. |
| `tokens[].holder_count` | `typed` | Indexed holder count. |
| `tokens[].launchpad` | `typed` | Observed launchpad source. |
| `tokens[].creator` | `typed` | Observed creator address when present. |
| `tokens[].creation_time` | `typed` | Observed launch time. |
| `tokens[].bonding_curve_progress_pct` | `typed` | Observed bonding-curve progress. |
| `tokens[].graduated` | `typed` | Observed graduation state. |
| `tokens[].graduated_time` | `typed` | Observed graduation time when present. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Discovery`; trader stage: `DISCOVER`; difficulty: `Advanced`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `EP-006`.
- Known absence: The approved x402 surface does not expose bundle-rate, fresh-wallet-rate or top-10 concentration filters on the launchpad list. This card does not claim or apply them.
