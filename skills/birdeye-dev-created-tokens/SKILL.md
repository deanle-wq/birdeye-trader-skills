---
name: birdeye-dev-created-tokens
description: "List Birdeye-indexed launchpad tokens associated with a developer wallet and return available launch dates, token addresses and graduation status. Use when the user asks “What tokens did this developer create?”, “What has this dev launched?” or wants a creator history list. Choose birdeye-dev-launch-track-record when the user wants performance or reputation analysis rather than the raw launch record."
---

# 👩🏻‍🍳 Dev Created Tokens

Answer this daily trader job: **What Birdeye-indexed launchpad tokens did this developer create?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Dev Created Tokens skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-dev-created-tokens
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- List Birdeye-indexed launchpad tokens associated with a supplied creator wallet.
- Show token identity, launchpad, creation time, graduation state and current market fields when present.
- Keep index coverage visible and do not claim a complete creator history outside supported launchpad data.

## Just say to your agent

- `What tokens did <developer wallet> create?`
- `List this developer's indexed launches and show which ones graduated.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--developer` | Required | `—` | Exact Solana creator or developer wallet address. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet created-tokens --address <developer_wallet_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `developer-created-tokens.developer_wallet` | `string|null` | Developer wallet. |
| `developer-created-tokens.tokens` | `array[launch-token]` | Tokens. |
| `developer-created-tokens.returned_count` | `integer` | Returned count. |
| `developer-created-tokens.total` | `integer-string|null` | Total. |
| `developer-created-tokens.has_next` | `boolean|null` | Has next. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `RESEARCH`; difficulty: `Basic`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `developer-created-tokens`.
