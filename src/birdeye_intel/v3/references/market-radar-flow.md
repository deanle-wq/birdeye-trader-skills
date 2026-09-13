# Market radar flow

This flow defines a bounded, deterministic market-ranking method within Birdeye's audited, Solana-only x402 data boundary. It does not import third-party fields, thresholds, labels or execution behavior.

## Route ownership

Use this skill when the trader provides no token address and wants a selected, explainable research list. Use `birdeye-5-minute-trending-tokens` or another focused ranking when the trader asks for one raw feed. Use `birdeye-token-due-diligence` after the trader selects a token. Never execute a trade.

## Deterministic run order

1. Build the primary cohort from EP-002 ranked by 24-hour volume. Apply the declared market-cap, liquidity and listing-time floors in the request.
2. If the primary cohort is empty, stop and return an empty, unpadded result. Otherwise fetch EP-002 cohorts ranked by 1-hour and 5-minute volume.
3. Fetch the one-hour Birdeye trending cohort from EP-005 and the one-day smart-money cohort from EP-008 as confirmation sources. They do not bypass the primary hard gates.
4. Deduplicate by a valid Solana token address. Sanitize token names and symbols before display.
5. Reapply market-cap, liquidity, optional holder and listing-time gates locally. Missing gate data fails the gate; an unknown listing time never becomes a young-token pass.
6. Score eligible candidates with methodology `birdeye-market-radar-1.0.0`. Components total 100 points: 24-hour/1-hour/5-minute cohort ranks 14/12/10, liquidity depth 14, holder depth 10, five-minute volume acceleration 12, five-minute trade participation 10, smart-money confirmation 10 and Birdeye trending confirmation 8.
7. A missing component earns no positive evidence and reduces `score_coverage_pct`. Apply the score-coverage floor and score floor before `limit`.
8. Return fewer than the requested count when fewer candidates pass. Never pad, replace or manually promote a candidate.

## Default policy

- Window: tokens listed during the last seven days.
- Minimum market cap: $500,000.
- Minimum indexed liquidity: $100,000.
- Score floor: 60/100.
- Minimum score coverage: 70%.
- Maximum returned candidates: 10.
- Source fetch limit: 50 rows, except EP-008's documented 20-row limit.
- Maximum requests: five, including repeated EP-002 windows.

Caller overrides must be shown in `answer.policy`. The local gates always use the effective values.

## Stop and failure rules

- Stop after an empty primary 24-hour cohort; mark later sources as policy-skipped, not queried.
- Stop further requests after a rate-limit response.
- Stop after the first authentication error and tell the user to configure their own `BIRDEYE_API_KEY` in the process environment.
- Stop when the command call cap is reached and label every omitted source.
- Continue after another isolated source failure when budget remains, but return `partial` and preserve missing score components.
- Never retry outside the shared client's bounded retry policy.

## Required response

Return the observation time, effective policy, score weights, candidate funnel, ranked survivors, near misses, empty sources, source statuses, call counts and limitations. The funnel must reconcile raw rows, unique candidates, hard-gate survivors, score-floor survivors and listed rows.

Every listed row must show its address, score, coverage, source ranks, component scores, key market fields, missing fields and `security_check`. This bounded sweep has no per-candidate security call, so `security_check` must remain `not_run`. The output is a research queue, not a safety verdict or buy list.
