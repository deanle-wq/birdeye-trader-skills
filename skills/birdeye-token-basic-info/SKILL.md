---
name: birdeye-token-basic-info
description: "Resolve a Solana token and return its current identity, price and valuation evidence in one card. Use when the trader asks: What are this token's identity, price, market cap and valuation?"
---

# 🪪 Token Basic Info

Answer this daily trader job: **What are this token's identity, price, market cap and valuation?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token Basic Info skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-basic-info
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Resolve a Solana token address to its name, symbol, decimals and metadata.
- Return its current indexed price, market cap, FDV, supply, liquidity and holder count when present.
- Keep missing fields explicit instead of substituting unsupported bundle, sniper, rat-wallet or KOL counts.

## Just say to your agent

- `Give me the basic info for this Solana token: <token address>.`
- `What are the price, market cap, liquidity and holder count for <token address>?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token info --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `token-metadata.canonical_address` | `string|null` | Canonical address. |
| `token-metadata.decimals` | `integer-string|null` | Decimals. |
| `token-metadata.extensions` | `object|null` | Extensions. |
| `token-metadata.logo_uri` | `string|null` | Logo uri. |
| `token-metadata.name` | `string|null` | Name. |
| `token-metadata.symbol` | `string|null` | Symbol. |
| `current-token-price.is_scaled_ui_token` | `boolean|null` | Is scaled ui token. |
| `current-token-price.price_change_24h_pct` | `decimal-string|null` | Price change 24h pct. |
| `current-token-price.price_native` | `decimal-string|null` | Price native. |
| `current-token-price.price_usd` | `decimal-string|null` | Price usd. |
| `current-token-price.provider_update_human` | `string|null` | Provider update human. |
| `current-token-price.provider_update_unix` | `integer-string|null` | Provider update unix. |
| `token-valuation-snapshot.canonical_address` | `string|null` | Canonical address. |
| `token-valuation-snapshot.circulating_supply` | `decimal-string|null` | Circulating supply. |
| `token-valuation-snapshot.fdv_usd` | `decimal-string|null` | Fdv usd. |
| `token-valuation-snapshot.holder_count` | `integer-string|null` | Holder count. |
| `token-valuation-snapshot.liquidity_usd` | `decimal-string|null` | Liquidity usd. |
| `token-valuation-snapshot.market_cap_usd` | `decimal-string|null` | Market cap usd. |
| `token-valuation-snapshot.price_usd` | `decimal-string|null` | Price usd. |
| `token-valuation-snapshot.total_supply` | `decimal-string|null` | Total supply. |

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
- Internal dependencies: `current-token-price`, `token-metadata`, `token-valuation-snapshot`.
- Known absence: The approved x402 basic-info path does not provide rat-wallet, bundle, sniper-wallet or KOL-buyer counts. They are not synthesized.
