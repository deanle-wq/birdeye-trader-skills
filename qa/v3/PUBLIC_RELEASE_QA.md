# Public repository release QA

Run date: 2026-09-11.

## Release surface

- Public skill folders: 47.
- Core composition packages: 12.
- Core CLI commands: 65.
- Unique approved x402 endpoints used: 27.
- Explicitly excluded endpoint overlap: zero.
- Repository layout: public skills are located directly under `skills/`.

## Checks completed before publication

| Check | Result |
|---|---|
| V3 package and dependency audit | Pass |
| Marketplace detail-contract gate | 47/47 pass |
| Official skill validator | 59/59 pass |
| Standalone focused regression | 27/27 pass |
| Generic remote skill-installer discovery | 47 skills found |
| Clean wheel build and isolated install | Pass |
| Installed `birdeye-cli doctor` smoke | Pass |
| Installed Market Radar catalog smoke | Pass |
| Repository-link migration | No source-monorepo references remain |
| Secret-pattern scan | No candidate credential files found |
| Competitor-name scan | Zero case-insensitive matches in the release tree |
| GitHub visibility and anonymous page access | Public; pass |

The source project previously passed the broader 205-test, 277-subtest regression recorded in `QA_REPORT.md`. The standalone public repository deliberately ships the focused V3 release suite rather than legacy V1/V2 packaging tests.

## Honest readiness boundary

The package gate passes, but the production-answer gate remains blocked. Thirty-nine of 65 core commands have atomic or deterministic typed paths. The remaining 26 analytical commands need deterministic calculation contracts, fresh user-key-injected live QA, and trader acceptance before the complete catalog can be labelled production-ready.

No API key, private key, or reusable credential is included. Live users must supply their own `BIRDEYE_API_KEY` through their environment or secret manager.
