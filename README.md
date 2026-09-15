# Birdeye Trader Skills

Installable, read-only Solana research skills powered by Birdeye Data. Ask a natural-language trader question; the selected skill maps it to a bounded `birdeye-cli` workflow, calls only audited data paths, and returns structured evidence with freshness and limitations preserved.

## What is included

```text
.
├── skills/                 # Installable, question-specific marketplace skills
├── docs/workflows/         # Cross-skill research flows
├── src/birdeye_intel/      # Shared Birdeye CLI runtime
├── tests/                  # Runtime and distribution checks used by CI
├── manifest.json           # Machine-readable public skill catalog
└── marketplace-catalog.csv # Human-reviewable catalog export
```

Every public package under `skills/` has a `SKILL.md` entrypoint and agent-facing metadata. Complex packages may include a focused `references/` directory. The catalog is intentionally not capped at a fixed number: a skill exists only when it owns a clear trader question.

## Quick start for AI agents

If you are helping a user install this repository, complete the steps in order:

1. Install the shared Birdeye CLI runtime.
2. List the available skills and install the requested package, or the full public set if the user explicitly asks for it.
3. Run `birdeye-cli doctor`.
4. If no API key is configured, stop and ask the user to configure their own key privately in their terminal or secret manager. Never ask them to paste it into chat.
5. Run one read-only live query to verify the connection.

Full agent instructions: [docs/INSTALL.md](docs/INSTALL.md).

Or give the agent this installation request:

```text
Install Birdeye Trader Skills from https://github.com/deanle-wq/birdeye-trader-skills and follow docs/INSTALL.md. List the available packages before installing them. Install Birdeye CLI, then pause while I configure my own BIRDEYE_API_KEY privately; do not ask me to paste the key into chat. Verify with doctor and one read-only live query.
```

## Installation

### Prerequisites

- Python 3.9 or newer
- Node.js with `npx`
- A user-owned Birdeye Data API key from [Birdeye Data Services](https://bds.birdeye.so/)

### 1. Install Birdeye CLI

```bash
python3 -m pip install \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"
```

### 2. Inspect and install skills

List available packages:

```bash
npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills --list
```

Install one package:

```bash
npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills \
  --skill birdeye-5-minute-trending-tokens --agent codex -y
```

Install the full public set:

```bash
npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills \
  --skill '*' --agent codex -y
```

Replace `codex` with the target agent supported by the installer. Restart the client if it does not refresh installed skills automatically.

### 3. Configure your API key privately

Create or copy a key in Birdeye Data Services, then set `BIRDEYE_API_KEY` yourself in the local terminal or secret manager used to start the agent. A shell-safe interactive option for macOS or Linux is:

```bash
export BIRDEYE_API_KEY="$(python3 -c 'import getpass; print(getpass.getpass("Birdeye API key: "))')"
```

The prompt hides the value and does not place the key directly in shell history. Do not send the key to an agent, add it to a command argument, or commit it to the repository.

### 4. Verify setup

```bash
birdeye-cli doctor
birdeye-cli market trending-5m --limit 3 --pretty
```

`doctor` confirms whether the key is visible without printing its value. The second command proves the runtime can make a live read-only request.

## Try it with natural language

After installation, ask the agent questions such as:

```text
Show me the most active Solana tokens in the last five minutes with at least $25K liquidity.
What are the hottest Pump.fun tokens right now?
What security and authority risks are observable for this token: <token_address>?
How does this wallet trade: <wallet_address>?
What launchpad tokens are closest to graduating?
What materially changed for this watched token and wallet since my last snapshot?
```

The agent should select the narrowest matching skill, preserve the user's filters and time window, and report unknown or unavailable fields instead of filling gaps with assumptions.

## Typical research flows

```text
Discover an opportunity
trending or launchpad scan → market-quality filter → token due diligence

Research a token
basic info → security → liquidity → holders and top traders

Assess a wallet
recent activity → trading style → reconstructed P&L → copy constraints

Monitor change
caller-owned baseline → current observation → material differences and limitations
```

See [docs/workflows](docs/workflows/README.md) for the maintained workflow routes. Workflows compose skills; they are not separately priced skills unless they own a distinct user question.

## Useful commands

```bash
birdeye-cli --help
birdeye-cli catalog
birdeye-cli catalog market
birdeye-cli market trending-5m --min-liquidity 10000 --limit 20 --pretty
birdeye-cli market pumpfun-trending --min-market-cap 50000 --pretty
birdeye-cli market-radar run --min-liquidity 250000 --score-floor 65 --pretty
birdeye-cli token security --address <token_address> --pretty
birdeye-cli wallet activity --address <wallet_address> --pretty
```

## Client guides

- [Codex](.codex/INSTALL.md)
- [OpenCode](.opencode/INSTALL.md)
- [Generic agent installation](docs/INSTALL.md)

The repository also includes plugin manifests for compatible Claude, Cursor, and Codex clients.

## Update

Refresh the runtime and reinstall the desired skills from the same repository:

```bash
python3 -m pip install --upgrade \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"

npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills \
  --skill '*' --agent codex -y
```

Run the verification commands again after updating.

## Troubleshooting

- `birdeye-cli: command not found`: confirm the Python scripts directory is on `PATH`, or run `python3 -m birdeye_intel.v3 --help`.
- `api_key_configured` is `false`: start the agent from a process that can read `BIRDEYE_API_KEY`.
- HTTP `401` or `403`: generate or copy a valid key in Birdeye Data Services and confirm its plan and permissions.
- HTTP `429`: reduce request frequency and retry after the provider's indicated wait period.
- Empty results: broaden optional filters, confirm the address and keep the returned coverage and freshness notes visible.
- A monitor requests a baseline: supply a compatible earlier observation for the same entity and method; the repository does not invent historical baselines.

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for diagnostic steps that do not expose credentials.

## Safety and product boundaries

- Solana and read-only research only.
- Active dependencies must remain inside the audited Birdeye x402 allowlist.
- No swaps, signing, token creation, private-key handling, or automatic copy trading.
- Monitoring compares a caller-owned baseline with a current observation; it is not a scheduler or push-alert service.
- A missing field is reported as unknown and never converted into positive evidence.
- Credentials are never bundled with a skill or accepted in skill inputs.
- Do not scrape Birdeye web pages or use third-party provider data. Use Birdeye CLI and its audited Birdeye Data dependencies.

## Release status and QA

This repository is a release candidate, not an unqualified production release. Typed atomic and deterministic paths are available now; production integrations should still run their own live acceptance tests with the intended account plan, inputs and operating limits.

For local development:

```bash
python3 -m pip install -e .
npx --yes skills@latest add . --list
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Documentation

- [Birdeye Data documentation](https://docs.birdeye.so/)
- [Birdeye Data API reference](https://docs.birdeye.so/reference/)
- [Birdeye x402 reference](https://docs.birdeye.so/reference/x402)
- [Marketplace catalog](marketplace-catalog.csv)

## License

This repository is published as a proprietary prototype for review and testing. Public visibility does not change the license declared in `pyproject.toml` or grant rights beyond those provided by the repository owner.
