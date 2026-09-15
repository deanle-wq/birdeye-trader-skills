---
name: birdeye-holder-concentration-change
description: "Compare current holder concentration with a compatible earlier snapshot using the same ranking and denominator policy. Use when the user asks “Are whales accumulating?”, “Did top-holder concentration increase?” or wants to monitor ownership concentration over time. Choose birdeye-holder-distribution-analysis for a current structural analysis and birdeye-top-holders for the raw holder ranking."
---

# 🐋 Holder Concentration Change

Answer this daily trader job: **Has this token's holder concentration changed materially?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Holder Concentration Change skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-holder-concentration-change
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Recalculate observable holder concentration under the same denominator and ranking policy as the baseline.
- Show absolute and relative changes for the tracked concentration bands.
- Refuse comparison when pagination, denominator or token identity is incompatible.

## Just say to your agent

- `Has holder concentration increased for <token address> since my last check?`
- `Compare the top-holder share with this compatible baseline.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--token` | Required | `—` | Exact Solana token address; symbols are not accepted when identity is ambiguous. |
| `--baseline-json` | Required | `—` | Compatible JSON snapshot from an earlier run for the same entity and methodology. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli monitor holders --token <token_address> --baseline-json '<baseline_json>'`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `sections.holder-concentration-delta.answer` | `object|null` | Endpoint-linked answer section for `holder-concentration-delta`; see evidence and limitations. |

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
- Internal dependencies: `holder-concentration-delta`.
