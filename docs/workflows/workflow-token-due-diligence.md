# Token due-diligence workflow

1. Use `birdeye-token info` to confirm address identity when the input is ambiguous.
2. Use `birdeye-token-dd run` for identity, price, security, liquidity, holder concentration, completeness and top-trader evidence.
3. Add `birdeye-holder-analysis run` only when ownership structure is material to the question.
4. Add `birdeye-kline-pattern run` only when the user asks about price action.
5. Summarize independent gates as observed, failed or unknown. Do not turn incomplete data into a universal safe/buy verdict.
