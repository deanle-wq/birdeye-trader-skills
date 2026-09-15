---
name: birdeye-dev-launch-track-record
description: "Review a developer wallet’s indexed token launches and summarize observable market outcomes, liquidity, valuation and graduation history. Use when the user asks “Is this developer any good?”, “How did this dev’s previous launches perform?” or wants creator due diligence. Choose birdeye-dev-created-tokens when the user only needs the list of tokens the wallet created."
---

# 🧐 Dev Launch Track Record

Answer this daily trader job: **How did this developer's indexed token launches perform?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Dev Launch Track Record skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-dev-launch-track-record
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Review a developer's indexed token launches using a consistent outcome window and market-data method.
- Summarize launch count, observed graduation or survival outcomes and current market context where available.
- Surface missing launches and coverage limits before assigning any reputation interpretation.

## Just say to your agent

- `How have the tokens created by <developer wallet> performed?`
- `Does this developer have a repeatable launch track record in Birdeye's indexed data?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--developer` | Required | `—` | Exact Solana creator or developer wallet address. |
| `--time-from` | Optional | `last 720 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli dev-analysis run --address <developer_wallet_address>`

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
| `sections.developer-launch-track-record.answer` | `object|null` | Endpoint-linked answer section for `developer-launch-track-record`; see evidence and limitations. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `RESEARCH`; difficulty: `Advanced`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `developer-created-tokens`, `developer-launch-track-record`.
