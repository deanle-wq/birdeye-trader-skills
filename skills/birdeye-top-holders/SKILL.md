---
name: birdeye-top-holders
description: "Rank the largest indexed token holders by balance while keeping pagination and coverage limitations visible. Use when the user asks “Who are the biggest holders?”, “Show the top wallets” or wants the raw holder leaderboard. Choose birdeye-holder-distribution-analysis for concentration interpretation and birdeye-holder-concentration-change for comparison over time."
---

# 🐋 Top Token Holders

Answer this daily trader job: **Who are the largest indexed holders of this token?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Top Token Holders skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-top-holders
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Return the largest indexed holders for a Solana token.
- Show wallet address, indexed balance or share fields and requested ordering when available.
- Disclose pagination and denominator limits; do not claim cost basis, P&L, labels or funding source when x402 does not provide them.

## Just say to your agent

- `Who are the biggest holders of <token address>?`
- `Show the top 20 indexed holders and their observable shares.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--limit` | Optional | `50` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token holder-ranking --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `holder-positions.token_address` | `string|null` | Token address. |
| `holder-positions.ranked_holders` | `array[holder]` | Ranked holders. |
| `holder-positions.returned_count` | `integer` | Returned count. |
| `holder-positions.ordering` | `string` | Ordering. |

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
- Internal dependencies: `holder-positions`.
- Known absence: The approved x402 holder view does not provide cost basis, holder P&L, wallet tags or funding source. These fields are not claimed.
