# Market opportunity workflow

1. Route a raw-feed request such as “5-minute trending” or “Pump.fun trending” to the matching `birdeye-market` command. Route a no-address request for selected hot candidates to `birdeye-market-radar run`.
2. The radar sweeps the 24-hour EP-002 cohort first. If it is empty, stop without padding. Otherwise add 1-hour and 5-minute EP-002 cohorts, then EP-005 trending and EP-008 smart-money confirmation within the five-call cap.
3. Deduplicate on validated token address. Reapply market-cap, liquidity, optional holder and listing-time gates locally; missing required gate evidence fails the gate.
4. Score the eligible cohort using the versioned policy in the [Market Radar flow](../../skills/birdeye-market-radar/references/flow.md). Apply score coverage and score floor before the result limit. Return the funnel and near misses.
5. For each candidate the user chooses, run `birdeye-token-dd run`; the radar itself must show that token security was not checked.
6. If chart context matters, run `birdeye-kline-pattern run` only for the remaining candidates.
7. Return a short comparison with coverage, freshness and failed sections. Never auto-buy, pad a weak list, or rank missing evidence as safe.
