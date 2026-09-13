# Monitoring workflow

1. Require a caller-owned baseline from the same entity, fields, units, filters and window definition.
2. Select the narrowest `birdeye-monitor` command: wallet flow, wallet PnL, wallet behavior, token security, token liquidity, holders, bonding curve, graduation, pool or watchlist.
3. Compare only like-for-like observations and label incompatible fields as unknown.
4. Report material deltas, data freshness, coverage and failed calls. Do not claim background scheduling or push alerts.
5. Return the current observation so the caller can persist it as the next baseline.
