---
name: birdeye-token-transfer-activity
description: "Inspect a token's indexed transfer events and total transfer coverage for a bounded window. Use when the trader asks: What token transfers occurred during the selected window?"
---

# 📨 Token Transfer Activity

Answer this daily trader job: **What token transfers occurred during the selected window?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token Transfer Activity skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-transfer-activity
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Inspect indexed token transfers over a bounded time window.
- Show sender, receiver, amount, timestamp and transaction identity when present.
- Report transfer totals and pagination coverage separately from the returned event sample.

## Just say to your agent

- `Show recent transfers for <token address>.`
- `What transfers happened in this token during the last hour?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--time-from` | Optional | `last 24 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli token transfers --token <token_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `token-transfers.transfers` | `array[transfer]` | Transfers. |
| `token-transfers.returned_count` | `integer` | Returned count. |
| `token-transfers.provider_total` | `integer-string|null` | Provider total. |
| `token-transfers.time_from` | `integer-string|null` | Time from. |
| `token-transfers.time_to` | `integer-string|null` | Time to. |
| `token-transfers.page_complete` | `boolean` | Page complete. |

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
- Internal dependencies: `token-transfers`.
