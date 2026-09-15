---
name: birdeye-holder-distribution-analysis
description: "Analyze a token’s current holder structure through concentration bands, smart-money presence and top-trader context, with coverage clearly stated. Use when the user asks “Who holds this token?”, “Is supply concentrated?” or wants holder or chip-distribution analysis. Choose birdeye-top-holders for a raw balance ranking and birdeye-holder-concentration-change for comparison with an earlier snapshot."
---

# 👥 Holder Distribution Analysis

Answer this daily trader job: **How concentrated is this token's observable holder distribution?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Holder Distribution Analysis skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-holder-distribution-analysis
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Analyze the indexed holder ranking and holder-stat snapshots under a disclosed denominator policy.
- Calculate observable concentration bands and distinguish holder balance from trader performance.
- Add smart-money and top-trader context only where the underlying endpoints provide it.

## Just say to your agent

- `How concentrated are the holders of <token address>?`
- `Do the top holders control too much of this token, based on Birdeye's indexed coverage?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--limit` | Optional | `50` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli holder-analysis run --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `holder-distribution.token_address` | `string|null` | Token address. |
| `holder-distribution.mode` | `string|null` | Mode. |
| `holder-distribution.holders` | `array[holder]` | Holders. |
| `holder-distribution.summary` | `holder-summary|null` | Summary. |
| `holder-distribution.returned_count` | `integer` | Returned count. |
| `sections.holder-concentration-analysis.answer` | `object|null` | Endpoint-linked answer section for `holder-concentration-analysis`; see evidence and limitations. |
| `sections.holder-category-composition.answer` | `object|null` | Endpoint-linked answer section for `holder-category-composition`; see evidence and limitations. |
| `sections.smart-money-holder-presence.answer` | `object|null` | Endpoint-linked answer section for `smart-money-holder-presence`; see evidence and limitations. |
| `top-trader-performance.traders` | `array[top-trader]` | Traders. |
| `top-trader-performance.returned_count` | `integer` | Returned count. |
| `top-trader-performance.time_frame` | `string` | Time frame. |
| `top-trader-performance.ordering` | `string` | Ordering. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Token Analysis`; trader stage: `RESEARCH`; difficulty: `Advanced`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `holder-category-composition`, `holder-concentration-analysis`, `holder-distribution`, `smart-money-holder-presence`, `top-trader-performance`.
- Known absence: Holder profile, holder positions and tag-holdings chart endpoints were explicitly excluded because they are not x402-supported.
