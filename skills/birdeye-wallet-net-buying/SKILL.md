---
name: birdeye-wallet-net-buying
description: "Compare indexed buys and sells to identify positive observed token flow for one wallet. Use when the trader asks: What tokens is this wallet buying more than selling?"
---

# 💸 Wallet Net Buying

Answer this daily trader job: **What tokens is this wallet buying more than selling?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Wallet Net Buying skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-wallet-net-buying
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Aggregate indexed buys and sells by token for one wallet.
- Rank tokens where observed buy value exceeds observed sell value during the selected window.
- Show gross buys, gross sells, net flow, trade count and coverage rather than implying current ownership.

## Just say to your agent

- `What tokens is <wallet address> net buying this week?`
- `Where has this wallet's positive net flow gone in the last 24 hours?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--time-from` | Optional | `last 168 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet net-flow --wallet <wallet_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.wallet-balance-changes.answer` | `object|null` | Endpoint-linked answer section for `wallet-balance-changes`; see evidence and limitations. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `MONITOR`; difficulty: `Intermediate`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `wallet-balance-changes`.
