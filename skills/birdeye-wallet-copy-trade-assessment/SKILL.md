---
name: birdeye-wallet-copy-trade-assessment
description: "Assess track-record quality and copyability under explicit position-size, liquidity and execution-delay assumptions. Use when the trader asks: Would this wallet's observed results survive my copy-trading constraints?"
---

# ⚖️ Wallet Copy-Trade Assessment

Answer this daily trader job: **Would this wallet's observed results survive my copy-trading constraints?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Wallet Copy-Trade Assessment skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-wallet-copy-trade-assessment
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Score the observable track record separately from copyability.
- Stress the result with caller-supplied position size and execution-delay assumptions using available market liquidity context.
- Explain failure modes, sample size and missing current-holdings data before giving a research verdict.

## Just say to your agent

- `Is <wallet address> realistically copyable with a $500 position and 30-second delay?`
- `Would this wallet's observed edge survive my execution constraints?`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--wallet` | Required | `—` | Exact Solana wallet address. |
| `--time-from` | Optional | `last 720 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--size-usd` | Optional | `100` | Hypothetical position size for liquidity and copyability context; no order is placed. |
| `--latency-seconds` | Optional | `30` | Assumed execution delay used by analytical copyability checks. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli wallet-score run --wallet <wallet_address> --size-usd 100 --latency-seconds 30`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.wallet-pnl-stats.answer` | `object|null` | Endpoint-linked answer section for `wallet-pnl-stats`; see evidence and limitations. |
| `sections.wallet-outcome-distribution.answer` | `object|null` | Endpoint-linked answer section for `wallet-outcome-distribution`; see evidence and limitations. |
| `sections.wallet-repeatability.answer` | `object|null` | Endpoint-linked answer section for `wallet-repeatability`; see evidence and limitations. |
| `sections.liquidity-adjusted-copyability.answer` | `object|null` | Endpoint-linked answer section for `liquidity-adjusted-copyability`; see evidence and limitations. |
| `sections.latency-adjusted-copyability.answer` | `object|null` | Endpoint-linked answer section for `latency-adjusted-copyability`; see evidence and limitations. |

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
- Internal dependencies: `latency-adjusted-copyability`, `liquidity-adjusted-copyability`, `wallet-outcome-distribution`, `wallet-pnl-stats`, `wallet-repeatability`.
