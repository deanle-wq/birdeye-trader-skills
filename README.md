# Birdeye Trader Skills

Installable, read-only Solana trader skills powered by Birdeye Data. The repository exposes 47 focused public skills, 12 broader core packages, one shared CLI runtime, workflow references, and reproducible QA evidence.

The number of skills is not a quota. Each public package owns a concrete trader question such as “What are the hottest Pump.fun tokens right now?” or “How does this wallet trade?”

## Repository layout

```text
.
├── skills/                 # 47 public, installable daily-job skills
├── core-skills/            # 12 internal composition packages
├── docs/workflows/         # Cross-skill routing flows
├── src/birdeye_intel/      # Shared birdeye-cli runtime
├── qa/                     # Sanitized QA reports and endpoint audit
├── manifest.json           # Public skill catalog
└── marketplace-catalog.csv # Reviewable spreadsheet export
```

Every folder under `skills/` contains a `SKILL.md` and `agents/openai.yaml`. Complex skills may also include a focused `references/` directory.

## Install skills

Inspect the available packages:

```bash
SOURCE="https://github.com/deanle-wq/birdeye-trader-skills"
npx --yes skills@latest add "$SOURCE" --list
```

Install one skill:

```bash
npx --yes skills@latest add "$SOURCE" \
  --skill birdeye-5-minute-trending-tokens --agent codex -y
```

Install all public skills:

```bash
npx --yes skills@latest add "$SOURCE" --skill '*' --agent codex -y
```

## Install the runtime

The skills call one shared Python executable:

```bash
python3 -m pip install \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"
```

Each user supplies their own Birdeye API key through their local environment or secret manager:

```bash
export BIRDEYE_API_KEY="<your-own-birdeye-api-key>"
birdeye-cli doctor
```

Never paste an API key into an agent prompt, skill input, command argument, issue, or committed file.

## Example commands

```bash
birdeye-cli market trending-5m --min-liquidity 10000 --limit 20 --pretty
birdeye-cli market pumpfun-trending --min-market-cap 50000 --pretty
birdeye-cli market-radar run --min-liquidity 250000 --score-floor 65 --pretty
birdeye-cli token security --address <token_address> --pretty
birdeye-cli wallet activity --address <wallet_address> --pretty
```

## Product boundaries

- Solana and read-only research only.
- Active dependencies must remain inside the audited Birdeye x402 allowlist.
- No swaps, signing, token creation, private-key handling, or automatic copy trading.
- Monitoring compares a caller-owned baseline with a current observation; it is not a scheduler or push-alert service.
- A missing field is reported as unknown and never converted into positive evidence.
- Credentials are never bundled with a skill.

## Readiness

The package and dependency gate passes. The current surface contains 47 public skills and 65 core commands over 27 approved x402 endpoints, with zero overlap against the explicit endpoint exclusion list.

This is a release candidate, not an unqualified production release. Thirty-nine core commands have typed atomic or deterministic paths; 26 analytical commands still require calculation contracts, fresh live QA, and trader acceptance. See [the QA report](qa/v3/QA_REPORT.md) for the exact split.

## License

This repository is published as a proprietary prototype for review and testing. Public visibility does not change the license declared in `pyproject.toml` or grant rights beyond those provided by the repository owner.
