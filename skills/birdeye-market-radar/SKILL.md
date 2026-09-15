---
name: birdeye-market-radar
description: "Sweep several Birdeye activity windows, apply market-quality gates and return a transparently scored shortlist for further research. Use when the user asks “What hot Solana tokens are worth researching?”, “Find quality momentum candidates” or wants curation rather than a raw ranking. Choose a five-minute or launchpad trending skill when the user wants an unscored leaderboard. This skill does not provide a trade recommendation."
---

# 🔥 Curated Hot Token Radar

Answer this daily trader job: **Which hot Solana tokens are actually worth researching right now?**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the Curated Hot Token Radar skill.

From this repository, install the public package:

```bash
npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill birdeye-market-radar
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

- Sweep eligible Solana tokens across 24-hour, 1-hour and 5-minute activity windows, then add Birdeye trending and smart-money confirmation within a five-call cap.
- Require observable market cap, liquidity and listing age before scoring, and reapply every hard gate locally so provider filtering is never trusted blindly.
- Score candidates with a versioned 100-point method, enforce score and evidence-coverage floors before limiting the output, and never pad a weak market.
- Show the complete candidate funnel, component scores, source ranks, near misses, source failures and unperformed token-security checks.

## Just say to your agent

- `Which hot Solana tokens are actually worth researching right now?`
- `Build me a top-10 hot-token research list, but return fewer if the evidence is weak.`
- `Show a curated Solana radar with at least $250K liquidity and explain why every token made the cut.`

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
| `--time-from` | Optional | `last 168 hours` | Inclusive Unix-second start of the observation window. |
| `--time-to` | Optional | `now` | Inclusive Unix-second end of the observation window. |
| `--limit` | Optional | `10` | Maximum result rows returned to the caller. |
| `--min-liquidity` | Optional | `100000` | Minimum indexed USD liquidity. |
| `--min-market-cap` | Optional | `500000` | Minimum indexed USD market cap. |
| `--score-floor` | Optional | `60` | Minimum deterministic radar score required before a candidate can be listed. |
| `--min-score-coverage` | Optional | `70` | Minimum percentage of score weight backed by observed source or metric evidence. |

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

1. `birdeye-cli market-radar run`

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.

## Flow reference

Read [references/flow.md](references/flow.md) before running. It is the canonical sweep → gate → score → shortlist contract for this card.

## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
| `methodology_version` | `typed` | Version of the deterministic scoring and gate policy. |
| `policy` | `typed` | Effective time, market-quality, score, coverage and result-count rules. |
| `score_weights` | `typed` | Point weights for every ranking component; the weights total 100. |
| `funnel` | `typed` | Reconciled raw, unique, hard-gated, score-passing and listed candidate counts. |
| `tokens[]` | `typed` | Ranked candidates that passed hard gates, score coverage and score floor. |
| `tokens[].score` | `typed` | Deterministic score out of 100. |
| `tokens[].score_coverage_pct` | `typed` | Percentage of score weight backed by observed evidence. |
| `tokens[].source_ranks` | `typed` | Candidate position in every fetched activity or confirmation cohort. |
| `tokens[].score_components` | `typed` | Per-component point contribution; null means the source evidence was unavailable. |
| `tokens[].security_check` | `typed` | Always `not_run` in this bounded sweep; follow-up token due diligence is separate. |
| `near_misses[]` | `typed` | Highest-scoring candidates that did not enter the final list, with the failed floor. |
| `changes` | `typed` | New, stayed and dropped addresses when the caller supplies a compatible baseline. |

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `Discovery`; trader stage: `DISCOVER`; difficulty: `Advanced`.
- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.
- Birdeye Data, Solana and read-only only.
- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: `EP-002`, `EP-005`, `EP-008`.
