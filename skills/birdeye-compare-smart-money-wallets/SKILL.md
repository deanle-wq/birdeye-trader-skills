---
name: birdeye-compare-smart-money-wallets
description: "Compare two or more wallets over the same period using consistent activity, reconstructed performance and trading-style evidence. Use when the user asks “Which wallet is better?”, “Who has the stronger track record?” or wants a smart-money leaderboard. Choose birdeye-wallet-trading-style for one wallet’s habits and birdeye-wallet-copy-trade-assessment when realistic copy execution is the main question."
---

# 🏁 Compare Smart-Money Wallets

Answer this daily trader job: **Which of these wallets looks stronger on the same observed metrics?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Compare Smart-Money Wallets skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-compare-smart-money-wallets
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Compare at least two wallet addresses over the same time window and reconstruction method.
- Rank them on shared observed metrics rather than mixing unequal periods or coverage.
- Show the metric-by-metric evidence, sample-size differences and reasons a winner may still be unsuitable to copy.

## Just say to your agent

- `Compare these three wallets over the last 30 days: <wallets>.`
- `Which of these wallets looks strongest on the same win, P&L and trading-frequency evidence?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallets` | Required | `—` | Comma-separated Solana wallet addresses; comparison needs at least two. |
| `--time-from` | Optional | `last 720 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet compare --wallets <wallet_1,wallet_2>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.wallet-comparison.answer` | `object|null` | Endpoint-linked answer section for `wallet-comparison`; see evidence and limitations. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `DECIDE`; difficulty: `Advanced`.
- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `wallet-comparison`.
