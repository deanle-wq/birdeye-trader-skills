---
name: birdeye-token-security-check
description: "Inspect Birdeye token-security fields and clearly separate observed, missing and unknown conditions. Use when the trader asks: What security and authority risks are observable for this token?"
---

# 🛡️ Token Security Check

Answer this daily trader job: **What security and authority risks are observable for this token?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token Security Check skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-security-check
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Inspect the token-security response for authority, ownership and other provider-observed risk fields.
- Separate affirmative observations, negative observations and missing values.
- Return the raw field names needed to verify the conclusion and never turn missing data into a safe verdict.

## Just say to your agent

- `Check the observable security risks for <token address>.`
- `Are mint or freeze authority risks visible for this Solana token?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token security --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `token-security-check.creator_address` | `string|null` | Creator address. |
| `token-security-check.freeze_authority` | `string|null` | Freeze authority. |
| `token-security-check.freezeable` | `boolean|null` | Freezeable. |
| `token-security-check.is_token_2022` | `boolean|null` | Is token 2022. |
| `token-security-check.jupiter_strict_list` | `boolean|null` | Jupiter strict list. |
| `token-security-check.mutable_metadata` | `boolean|null` | Mutable metadata. |
| `token-security-check.non_transferable` | `boolean|null` | Non transferable. |
| `token-security-check.top10_holder_percent` | `decimal-string|null` | Top10 holder percent. |
| `token-security-check.top10_user_percent` | `decimal-string|null` | Top10 user percent. |
| `token-security-check.total_supply` | `decimal-string|null` | Total supply. |

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
- Internal dependencies: `token-security-check`.
