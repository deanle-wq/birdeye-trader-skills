---
name: birdeye-wallet-pnl-analysis
description: "Reconstruct wallet performance from the indexed trades covered in a selected window and show observed wins, losses, trade counts and assumptions. Use when the user asks “Is this wallet profitable?”, “What is its PnL or win rate?” or wants a performance review. Choose birdeye-wallet-copy-trade-assessment for realistic follower outcomes. This is a bounded reconstruction, not guaranteed complete wallet PnL."
---

# 💵 Wallet P&L Analysis

Answer this daily trader job: **What P&L can be reconstructed from this wallet's indexed trades?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Wallet P&L Analysis skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-wallet-pnl-analysis
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Reconstruct wallet performance from the indexed trades available in the selected window.
- Show covered realized outcomes, wins, losses, trade counts and reconstruction assumptions.
- State that the result is not provider-complete wallet P&L and does not include unsupported current-position data.

## Just say to your agent

- `Reconstruct the last 30 days of P&L for <wallet address>.`
- `How profitable does this wallet look from Birdeye's indexed trades, and what is missing?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--time-from` | Optional | `last 720 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet pnl --wallet <wallet_address>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.wallet-pnl-stats.answer` | `object|null` | Endpoint-linked answer section for `wallet-pnl-stats`; see evidence and limitations. |

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
- Internal dependencies: `wallet-pnl-stats`.
- Known absence: This is a bounded reconstruction from indexed trades, not Birdeye's complete wallet P&L or current holdings product.
