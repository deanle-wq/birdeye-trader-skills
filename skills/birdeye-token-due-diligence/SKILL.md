---
name: birdeye-token-due-diligence
description: "Build one evidence-linked dossier across identity, price, security, liquidity, holder concentration and top-trader observations. Use when the trader asks: Does this token deserve deeper investigation?"
---

# 🧪 Token Due Diligence

Answer this daily trader job: **Does this token deserve deeper investigation?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token Due Diligence skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-due-diligence
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Build one dossier across token identity, price, security, liquidity, holder distribution and top-trader evidence.
- Keep each section endpoint-linked so the trader can see which evidence supports each observation.
- Return a research priority and material unknowns, not an automatic buy or safe-token verdict.

## Just say to your agent

- `Do a full Birdeye due-diligence check on <token address>.`
- `What should worry me about this token before I spend more time on it?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--limit` | Optional | `20` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token-dd run --token <token_address>`

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
| `token-liquidity-snapshot.liquidity_usd` | `decimal-string|null` | Liquidity usd. |
| `token-liquidity-snapshot.price_usd` | `decimal-string|null` | Price usd. |
| `token-liquidity-snapshot.token_address` | `string|null` | Token address. |
| `sections.holder-concentration-gate.answer` | `object|null` | Endpoint-linked answer section for `holder-concentration-gate`; see evidence and limitations. |
| `sections.token-data-completeness.answer` | `object|null` | Endpoint-linked answer section for `token-data-completeness`; see evidence and limitations. |
| `top-token-traders.traders` | `array[top-trader]` | Traders. |
| `top-token-traders.returned_count` | `integer` | Returned count. |
| `top-token-traders.time_frame` | `string` | Time frame. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Token Analysis`; trader stage: `DECIDE`; difficulty: `Advanced`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `current-token-price`, `holder-concentration-gate`, `token-data-completeness`, `token-liquidity-snapshot`, `token-metadata`, `token-security-check`, `top-token-traders`.
