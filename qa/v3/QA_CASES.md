# V3 QA cases

## Catalog and dependency gates

| ID | Case | Expected |
|---|---|---|
| V3-CAT-001 | Load canonical core catalog | 12 internal packages and 65 unique commands |
| V3-CAT-002 | Load marketplace catalog | 47 unique daily-job cards with valid core mappings and no Decision Support category |
| V3-CAT-003 | Resolve every private leaf | All 62 referenced leaves exist |
| V3-X402-001 | Cross-check active endpoint IDs | 27 unique endpoints, all x402 eligible and approved |
| V3-X402-002 | Intersect with explicit exclusion registry | Empty intersection, including every excluded multiple/batch, holder, liquidity, wallet-PnL-chart and token-fee route |
| V3-BUD-001 | Validate declared command budgets | Dependency estimate never exceeds `max_calls` |
| V3-BUD-002 | Run composite with caller cap two | At most two runtime calls; remaining sections are explicitly blocked |
| V3-MKT-001 | Five-minute trending defaults | Uses native `volume_5m_usd`, not a renamed one-hour list |
| V3-MKT-002 | Pump.fun trending defaults | Uses `source=pump_dot_fun` and one-hour volume ranking |
| V3-MKT-003 | Pump.fun new-token window | Maps the default 24-hour window to creation-time filters |
| V3-MKT-004 | Migrated quality screen | Fetches a bounded migrated cohort and applies the three default quality filters deterministically |
| V3-MKT-005 | Identity-defining filter override | Pump.fun source and graduation state remain locked after CLI, JSON and endpoint override merging |
| V3-MKT-006 | Human launchpad source aliases | Pump.fun, Moonshot, Raydium LaunchLab and Meteora DBC normalize to canonical EP-006 values |
| V3-MKT-007 | Unsupported Solana launchpad source | Reject before network; never silently query an EVM-only enum under Solana |
| V3-MKT-008 | Live source matrix | `all` plus four advertised sources return successfully; each named source returns a matching `meme_info.source` |
| V3-MKT-009 | Public launchpad packaging | Two cross-launchpad jobs plus two Pump.fun presets; no duplicate package per source-only variation |
| V3-RAD-001 | Intent ownership | No-address request for a curated shortlist routes to Market Radar; raw feed requests stay with their specific ranking skill |
| V3-RAD-002 | Ordered source sweep | EP-002 24h → EP-002 1h → EP-002 5m → EP-005 trending → EP-008 smart money, within five calls |
| V3-RAD-003 | Empty primary cohort | Stop after the first request, return an empty list and mark later sources as policy-skipped |
| V3-RAD-004 | Candidate deduplication | Repeated observations collapse to one validated token address while preserving source ranks |
| V3-RAD-005 | Local hard-gate backstop | Market cap, liquidity, optional holders and listing time are rechecked locally; unknown age fails |
| V3-RAD-006 | Versioned scoring | Nine declared component weights total 100 and missing source evidence never earns positive points |
| V3-RAD-007 | Floor-before-limit | Score coverage and score floor apply before top-N; weak results are not padded |
| V3-RAD-008 | Near misses and funnel | Raw, unique, rejected, eligible, score-passing and listed counts reconcile; near misses name the failed floor |
| V3-RAD-009 | Terminal conditions | Call cap, authentication and rate limit stop later requests and leave each omitted source visible |
| V3-RAD-010 | Attacker-controlled metadata | Control and markup characters are removed from displayed token names and symbols |
| V3-RAD-011 | Baseline comparison | Compatible address baseline produces new/stayed/dropped sets; invalid address rejects before network |
| V3-RAD-012 | Security boundary | Every listed candidate says `security_check=not_run` and routes follow-up review to token due diligence |

## Input and credential gates

| ID | Case | Expected |
|---|---|---|
| V3-IN-001 | Token command with primary address | Address maps to `token_address` |
| V3-IN-002 | Wallet composite with no window | Stable default `time_from` and `time_to` are applied |
| V3-IN-003 | Wallet comparison with one address | Reject before network |
| V3-IN-004 | Monitor without baseline | Reject before network |
| V3-IN-005 | Monitor with JSON baseline | Baseline reaches only the selected monitor leaf |
| V3-SEC-001 | API key in JSON input | Reject before network |
| V3-SEC-002 | Doctor with secret environment value | Return configured boolean and never the value |

## Packaging and distribution gates

| ID | Case | Expected |
|---|---|---|
| V3-PKG-001 | Generate public packages | Exactly 47 marketplace folders plus 12 internal core folders; no entry-check package |
| V3-PKG-002 | Official skill validator | All 59 folders valid |
| V3-PKG-003 | Generic installer discovery | Finds exactly the 47 marketplace skills from the repository root |
| V3-PKG-004 | Build and install clean wheel | `birdeye-cli doctor` and `catalog market` work in an isolated environment |
| V3-PKG-005 | Codex, Claude and Cursor manifests | Each points to `./skills/` within the V3 package |
| V3-DET-001 | Detail registry coverage | Exactly one detail contract for every public skill; no missing or extra records |
| V3-DET-002 | Detail-page structure | Installation, capabilities, example prompts, inputs, outputs and boundaries exist on all 47 cards |
| V3-DET-003 | Card specificity | At least three card-specific capabilities and two natural trader prompts per card |
| V3-DET-004 | Exact installation | Each card's installation command targets that exact `birdeye-*` package |
| V3-DET-005 | Output contract | Direct cards document typed answer fields; leaf/composite cards document endpoint-linked answer sections or accepted field schemas |
| V3-DET-006 | Provider capability boundary | Known unavailable fields are explicitly disclosed as absent rather than silently claimed |
| V3-DET-007 | Catalog export | CSV includes capability and example-prompt columns for every card |
| V3-REG-001 | Full project regression | Existing V1/V2 plus V3 test suite passes |
| V3-BLD-001 | Build from clean source copy | Wheel contains only files present in source and installs into a fresh virtual environment |
| V3-BLD-002 | Installed CLI smoke | `doctor` reports 12/65 and installed catalogs expose focused launchpad commands plus deterministic Market Radar |
| V3-BRN-001 | Public competitor-name scan | Zero case-insensitive competitor-brand matches across all tracked release files |

## Product acceptance gates

| ID | Case | Expected before production |
|---|---|---|
| V3-ANS-001 | Atomic command live answer | Typed output, current evidence, sparse and failure cases pass |
| V3-ANS-002 | Analytical/composite command | Accepted deterministic method, golden/sparse/partial cases and unseen live forward test |
| V3-BIZ-001 | Trader usefulness review | Two recorded reviewers can select and interpret the skill without internal leaf knowledge |
| V3-OPS-001 | Production runtime | Quotas, observability, circuit breaking, concurrency/load/soak and rollback pass |
| V3-PAY-001 | Paid x402 path | Separately approved wallet/budget; idempotency, replay and double-charge controls pass |

Automated packaging success cannot override the product acceptance gates.
