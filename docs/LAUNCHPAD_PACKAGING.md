# Launchpad skill packaging

## Decision

Use a hybrid public surface:

- Keep `birdeye-pumpfun-trending-tokens` and `birdeye-pumpfun-new-tokens` as dedicated cards because traders recognize and request these exact daily jobs.
- Use `birdeye-launchpad-trending-tokens` for the same trending question across all supported Solana launchpads or one selected source.
- Use `birdeye-launchpad-new-tokens` for the same new-launch question across all supported Solana launchpads or one selected source.
- Keep lifecycle questions separate: Near-Graduation Tokens, Recently Migrated Tokens and Migrated Token Quality Screener.

This preserves question-level specificity without creating duplicate packages such as `moonshot-new`, `launchlab-new` and `meteora-new` when only the source preset differs.

## Supported source presets

| Trader wording | Canonical Birdeye value | Solana live QA |
|---|---|---|
| All supported launchpads | `all` | Pass |
| Pump.fun / Pumpfun | `pump_dot_fun` | Pass, source matched |
| Moonshot | `moonshot` | Pass, source matched |
| Raydium LaunchLab / LaunchLab | `raydium_launchlab` | Pass, source matched |
| Meteora DBC / Meteora | `meteora_dynamic_bonding_curve` | Pass, source matched |

The runtime normalizes the human names above. It rejects every other source before the network call in V3 Solana mode. Although EP-006 documents additional enum values, live Solana probes for `four.meme`, `nad.fun`, `flap`, `something` and `lfj_token_mill` returned HTTP 400 and are not advertised as supported.

## When to create another dedicated launchpad card

A source earns a dedicated public card only when at least one of these is true:

1. Traders repeatedly ask for the platform by name and the dedicated card materially improves discovery.
2. The platform needs unique filters, ranking semantics or output fields that the shared card cannot express cleanly.
3. The platform owns a distinct workflow rather than only a different `source` value.

The new card must also pass source-matched live QA, x402 dependency audit, package validation and trader-language review. Public skill count is therefore allowed to grow or shrink with accepted trader jobs; it is never fixed to 100 or any other target.

## Credential boundary

Launchpad skills do not include a Birdeye API key. After installing the package and shared runtime, each user configures their own `BIRDEYE_API_KEY` in the local process environment or secret manager. Prompts, CLI flags, JSON input, manifests, fixtures and generated QA artifacts must not contain the key.
