# Birdeye Data Skills V3 QA report

Run date: 2026-09-11.

## Outcome

- Package/dependency gate: **PASS**.
- Public surface: 47 specific daily-job skills; the Decision Support card remains removed and Curated Hot Token Radar was added as a distinct daily question owner.
- Internal composition surface: 12 core packages and 65 commands; the corresponding Entry Check package was also removed.
- Internal evidence coverage: 62 unique V2 leaves over 27 unique approved x402 endpoints.
- Explicitly excluded endpoint overlap: zero.
- Official skill-creator validation: 59/59 pass across public and core packages.
- Generic `skills` installer discovery: exactly 47 public skills, including 5-Min Trending, cross-launchpad Trending/New, Pump.fun Trending/New, Curated Hot Token Radar and Token Basic Info cards.
- Marketplace detail-contract gate: **47/47 pass**. Every public card has installation, at least three card-specific capabilities, at least two natural-language prompts, documented inputs/filters, documented outputs and explicit boundaries.
- Public agentic-skill marketplace research informed the packaging and detail-page structure; competitor names and links are intentionally excluded from this repository.
- Clean wheel build/install and `birdeye-cli` smoke: pass.
- Focused-card identity lock: pass. Pump.fun cards enforce `source=pump_dot_fun`; graduation cards enforce the declared graduated/ungraduated state even if conflicting CLI or JSON input is supplied.
- Authenticated live atomic command QA: 38/38 complete with zero failed cases.
- Market Radar flow QA: 12/12 pass for routing, five-source order, early empty stop, address dedupe, local gates, versioned score, floor-before-limit, no padding, funnel arithmetic, terminal conditions, metadata sanitization, baseline validation and the explicit security boundary.
- Launchpad source QA: `all`, Pump.fun, Moonshot, Raydium LaunchLab and Meteora DBC passed; all four named sources returned matching source identity. Five non-Solana source enums returned HTTP 400 under the Solana header and are rejected locally before network use.
- Full deterministic regression: 205/205 tests pass.
- Clean-source wheel build, isolated install, `doctor` and installed Market Radar catalog smoke: pass. Release builds must start from a clean source copy or clean checkout so stale local `build/` contents cannot enter an artifact.
- Production answer gate: **BLOCKED**, intentionally not relabeled as pass.

## What was tested

The suite cross-checks every command against the audited V2 leaf catalog, rejects non-x402, unapproved and explicit-scope-excluded dependencies, validates command budgets, ensures monitors require a baseline before any request, verifies credential redaction and input rejection, checks package metadata for three agent ecosystems, exercises leaf, direct, composite and deterministic-radar routing, builds a clean wheel, and asks the generic installer to enumerate the source.

The discovery-specific cases prove that five-minute cards use Birdeye's native `volume_5m_usd`, `volume_5m_change_percent`, `price_change_5m_percent` and `trade_5m_count` dimensions. Pump.fun cards use `source=pump_dot_fun`; creation and graduation cards map the declared 24-hour horizon to the correct provider timestamp fields. The cross-launchpad cards normalize trader wording for Pump.fun, Moonshot, Raydium LaunchLab and Meteora DBC to live-tested EP-006 source values. The migrated quality card applies its default market-cap and liquidity thresholds client-side after a bounded provider fetch because the live provider returned HTTP 400 for that multi-filter combination.

The detail-contract cases prove that the generated card is no longer just a title and router. They check exact single-skill installation, required page sections, capability and example counts, catalog export, output-schema presence and known-absence disclosures for unavailable fields such as bundle rate, fresh-wallet rate, enriched holder P&L/tags/funding source and provider-wide KOL coverage.

The focused-card identity case catches a packaging/runtime mismatch that documentation alone would miss: identity-defining filters are now locked after user input and endpoint overrides are merged. A Pump.fun card cannot silently become an all-launchpad query, and a migrated card cannot silently become an ungraduated query.

The Market Radar case validates the complete orchestration path instead of returning five unrelated evidence sections. It sweeps 24-hour, 1-hour and 5-minute EP-002 cohorts, then adds EP-005 trending and EP-008 smart-money confirmation; deduplicates by address; reapplies hard gates locally; calculates a versioned 100-point score; applies coverage and score floors before top-N; and returns the candidate funnel, near misses and stop reasons. Raw feed skills remain separate. Its exact flow is packaged in both public and core `references/flow.md` files.

`birdeye-cli` was also tested with no configured API key. Market Radar returned one sanitized authentication error, stopped the four later sources, and did not expose a credential or fabricate an answer.

## Honest readiness split

Of the 65 core commands, 39 use atomic or deterministic typed paths, including the new Market Radar; the other 26 include at least one evidence-only analytical, baseline or conditional leaf. Of the 47 marketplace cards, 29 are typed paths and 18 include analytical evidence. Across the 62 referenced internal leaves, 27 are `READY_ATOMIC`, 25 are `EVIDENCE_ONLY_ANALYSIS`, and 10 are `EVIDENCE_ONLY_BASELINE`.

This means V3 now fixes the product menu, routing, packaging and bounded execution, but the 26 analytical commands are not yet production-accepted outputs. Their skill instructions can guide an agent through the evidence today; they still need deterministic calculation contracts and trader acceptance before pricing or an unqualified production label.

## Live API status

The live run loaded a user-owned `BIRDEYE_API_KEY` from the local QA environment without printing or persisting its value. It bootstrapped current token, pair, wallet and developer fixtures, then exercised all 38 V3 commands whose dependencies are entirely atomic. All 38 completed. The source-specific probe separately verified the four advertised Solana launchpad sources. Evidence files store statuses, source labels, answer presence, call counts and error codes only; they store no API key or on-chain entity values.

EP-002, EP-005 and EP-008—the three endpoint paths used by Market Radar—each have a complete authenticated live command result in that artifact. The new combined radar was not rerun live because `BIRDEYE_API_KEY` was not present in the current process. The runtime correctly stopped at the first authentication failure and exposed the missing BYOK configuration. This is recorded without ambiguity in `market-radar-flow-qa.json`; a fresh integrated run remains open rather than being mislabeled as complete.

The install contract is bring-your-own-key: every user configures `BIRDEYE_API_KEY` on their own machine or agent host after installation. No shared Birdeye key is included in the repository, skill packages, manifests, examples or QA artifacts, and runtime inputs reject credential-shaped fields.

The live transport used response-compatible Standard API counterparts for QA. No paid x402 request was attempted. This verifies real user/agent command paths but does not substitute for paid-settlement QA.

## Remaining gates

1. Inject a user-owned key and run the integrated Market Radar against fresh data; inspect the funnel and calibrate defaults with trader review.
2. Implement and fixture the 26 commands that still include evidence-only analysis.
3. Run each newly accepted analytical command against fresh, sanitized live cases with an injected API key.
4. Record two trader reviews for selection clarity and decision usefulness.
5. Add production operations controls and separately approved paid-x402 settlement QA.
6. Only after those gates pass, replace the V2 public release assets and assign sellable pricing.

The detailed machine-readable surface and all 47 detail rows are in `core-surface-audit.json`; the radar flow evidence is in `market-radar-flow-qa.json`; the prior authenticated atomic command run is in `live-atomic-command-qa.json`; the launchpad matrix is in `launchpad-source-qa.json`; case definitions are in `QA_CASES.md`.
