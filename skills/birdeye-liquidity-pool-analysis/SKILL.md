---
name: birdeye-liquidity-pool-analysis
description: "Show a token’s current indexed liquidity and the pools or markets where it trades. Use when the user asks “How liquid is this token?”, “Where can it be traded?” or wants to inspect pool depth and market venues. Choose birdeye-token-liquidity-change when the question is whether liquidity increased or was removed since an earlier snapshot."
---

# 💧 Liquidity Pool Analysis

Answer this daily trader job: **How liquid is this token and where is that liquidity?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Liquidity Pool Analysis skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-liquidity-pool-analysis
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Show the token's current indexed liquidity and valuation context.
- List the Birdeye-indexed markets or pools where the token trades.
- Report pool address, exchange identity and available reserve or activity fields with pagination coverage.

## Just say to your agent

- `Where is the liquidity for <token address>, and how deep is it?`
- `List the main pools for this token and show the liquidity Birdeye currently indexes.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--limit` | Optional | `20` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token liquidity --token <token_address>`
2. `birdeye-cli token pools --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `token-liquidity-snapshot.liquidity_usd` | `decimal-string|null` | Liquidity usd. |
| `token-liquidity-snapshot.price_usd` | `decimal-string|null` | Price usd. |
| `token-liquidity-snapshot.token_address` | `string|null` | Token address. |
| `token-markets-and-pools.markets` | `array[market]` | Markets. |
| `token-markets-and-pools.ordering` | `string` | Ordering. |
| `token-markets-and-pools.returned_count` | `integer` | Returned count. |
| `token-markets-and-pools.total` | `integer-string|null` | Total. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Token Analysis`; trader stage: `RESEARCH`; difficulty: `Intermediate`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `token-liquidity-snapshot`, `token-markets-and-pools`.
