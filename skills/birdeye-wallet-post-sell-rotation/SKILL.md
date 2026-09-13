---
name: birdeye-wallet-post-sell-rotation
description: "Identify the same wallet's observable buys after a named-token sale within a bounded window. Use when the trader asks: What did this wallet buy after selling the token?"
---

# 🔁 Wallet Post-Sell Rotation

Answer this daily trader job: **What did this wallet buy after selling the token?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Wallet Post-Sell Rotation skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-wallet-post-sell-rotation
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Identify a specified token sale and search the same wallet's subsequent indexed buys.
- Rank or sequence the post-sale purchases within a bounded follow-up window.
- Show timing gaps and exclude buys that occurred before the observed sale.

## Just say to your agent

- `What did <wallet address> buy after selling <token address>?`
- `Show this wallet's post-sell rotation during the next 6 hours.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--time-from` | Optional | `last 72 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli track rotation --token <token_address> --wallet <wallet_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.same-wallet-rotation.answer` | `object|null` | Endpoint-linked answer section for `same-wallet-rotation`; see evidence and limitations. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Monitor`; trader stage: `MONITOR`; difficulty: `Advanced`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `same-wallet-rotation`.
