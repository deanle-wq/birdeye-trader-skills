---
name: birdeye-token-wallet-watchlist
description: "Compare a watched token and wallet with a compatible earlier snapshot and summarize material changes across both entities. Use when the user asks “What changed in my watchlist?”, “Did this wallet or token move materially?” or wants a bounded follow-up check. This skill requires a caller-owned baseline and does not create a hosted watchlist, background scheduler or push alert."
---

# 👀 Token & Wallet Watchlist Check

Answer this daily trader job: **What materially changed for this watched token and wallet?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Token & Wallet Watchlist Check skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-token-wallet-watchlist
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Run a bounded change check for one watched token and one watched wallet.
- Combine only the token and wallet observations declared by the watchlist workflow and compare them with the caller baseline.
- Return section-level failures and material changes without treating the check as a persistent Birdeye-hosted watchlist.

## Just say to your agent

- `What materially changed for <token address> and <wallet address> since this watchlist snapshot?`
- `Check this token-wallet pair and show only changes that pass my baseline thresholds.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--baseline-json` | Required | `—` | Compatible JSON snapshot from an earlier run for the same entity and methodology. |
| `--time-from` | Optional | `last 24 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli monitor watchlist --token <token_address> --wallet <wallet_address> --baseline-json '<baseline_json>'`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.watchlist-material-change.answer` | `object|null` | Endpoint-linked answer section for `watchlist-material-change`; see evidence and limitations. |

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
- This change-monitoring card requires a compatible caller baseline. A current feed is not a change alert.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `watchlist-material-change`.
- Known absence: This is a caller-baseline comparison, not a hosted account watchlist or continuous background subscription.
