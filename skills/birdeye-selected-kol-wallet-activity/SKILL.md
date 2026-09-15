---
name: birdeye-selected-kol-wallet-activity
description: "Show recent trades for KOL wallet addresses supplied by the user, including direction, token, value and time when available. Use when the user asks “What are these KOL wallets buying?”, “Did these influencers sell?” or provides a KOL watchlist. This skill does not discover or invent a KOL directory; choose birdeye-wallet-activity-feed for a regular single wallet."
---

# 📡 Selected KOL Wallet Activity

Answer this daily trader job: **What did these selected KOL wallets trade recently?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Selected KOL Wallet Activity skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-selected-kol-wallet-activity
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Track recent indexed trades for caller-supplied KOL wallet addresses.
- Combine the selected wallets into one time-ordered activity view with wallet identity preserved.
- Never imply that the supplied list is Birdeye's complete KOL universe.

## Just say to your agent

- `What did these KOL wallets trade today: <wallets>?`
- `Show only the recent buys from this list of KOL wallets.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallets` | Required | `—` | Comma-separated Solana wallet addresses; comparison needs at least two. |
| `--time-from` | Optional | `last 24 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `100` | Maximum result rows returned to the caller. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli track kol --wallets <wallet_1,wallet_2>`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `kol-trades.trades` | `array[market-trade]` | Trades. |
| `kol-trades.wallets_requested` | `integer` | Wallets requested. |
| `kol-trades.wallets_queried` | `integer` | Wallets queried. |
| `kol-trades.time_from` | `integer-string|null` | Time from. |
| `kol-trades.time_to` | `integer-string|null` | Time to. |
| `kol-trades.coverage_complete` | `boolean` | Coverage complete. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Wallet Intelligence`; trader stage: `MONITOR`; difficulty: `Intermediate`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `kol-trades`.
- Known absence: The caller must provide the KOL wallets. The skill does not invent or claim a provider-wide KOL directory.
