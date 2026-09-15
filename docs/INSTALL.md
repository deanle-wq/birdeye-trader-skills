# Install Birdeye Trader Skills

This guide is written for both users and AI agents. The skills and their shared runtime are installed separately: skill packages teach the agent when and how to answer a trader question, while Birdeye CLI performs the audited read-only data calls.

## Rules for an installing agent

1. You may install or update the runtime and the skill packages requested by the user.
2. The user must create and enter their own Birdeye API key locally.
3. Never ask the user to paste a key into chat, a prompt, JSON input, a CLI argument, an issue, or a committed file.
4. Do not print, inspect, transform, or repeat a configured key. Use `birdeye-cli doctor`, which reports only whether a key is present.
5. Stop after the first authentication failure. Ask the user to verify the local key and account access before retrying.
6. Do not imply that an API key expands the repository's endpoint allowlist or read-only boundary.

## Prerequisites

- Python 3.9 or newer
- Git
- Node.js with `npx`
- A user-owned API key from [Birdeye Data Services](https://bds.birdeye.so/)

## Step 1 — Install the shared runtime

```bash
python3 -m pip install \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"
```

Confirm that the command is available:

```bash
birdeye-cli --help
```

## Step 2 — Inspect and install skills

Set the repository source once for the current shell:

```bash
SOURCE="https://github.com/deanle-wq/birdeye-trader-skills"
```

List packages before installing:

```bash
npx --yes skills@latest add "$SOURCE" --list
```

Install one focused package:

```bash
npx --yes skills@latest add "$SOURCE" \
  --skill birdeye-5-minute-trending-tokens --agent codex -y
```

Install the full public set only when the user requests it:

```bash
npx --yes skills@latest add "$SOURCE" \
  --skill '*' --agent codex -y
```

Replace `codex` with the target agent supported by the installer. Restart the client when it does not refresh skills automatically.

## Step 3 — User configures their API key

The user should sign in to Birdeye Data Services, open the API-key security area, and create or copy their own key. They must enter it outside the agent conversation.

For a private, session-only macOS or Linux prompt, the user can run:

```bash
export BIRDEYE_API_KEY="$(python3 -c 'import getpass; print(getpass.getpass("Birdeye API key: "))')"
```

For persistent use, store the value in the user's existing operating-system or development secret manager and expose it to the process that launches the agent. Do not place a real key in `.env.example` or any tracked file.

## Step 4 — Verify configuration without exposing the key

```bash
birdeye-cli doctor
```

Expected properties include:

```json
{
  "status": "ok",
  "api_key_configured": true
}
```

Additional fields may be present. The key itself must never appear.

## Step 5 — Verify one live read-only request

```bash
birdeye-cli market trending-5m --limit 3 --pretty
```

Setup is complete when the command returns a structured response rather than an authentication or configuration error. Preserve the response's `status`, observation time, coverage, limitations, and endpoint evidence.

## Step 6 — Test natural-language routing

Send this prompt to the installed agent:

```text
Show me the most active Solana tokens in the last five minutes with at least $25K liquidity.
```

The agent should select `birdeye-5-minute-trending-tokens`, retain the five-minute window and liquidity threshold, and answer from Birdeye CLI output.

Other useful tests:

```text
What security and authority risks are observable for this token: <token_address>?
How does this wallet trade: <wallet_address>?
What launchpad tokens are closest to graduating?
```

## Updating

```bash
python3 -m pip install --upgrade \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"

npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills \
  --skill '*' --agent codex -y

birdeye-cli doctor
birdeye-cli market trending-5m --limit 3 --pretty
```

If the user installed only selected skills, reinstall only those packages instead of silently expanding the installation.

## Uninstalling

Use the agent client's skill manager or remove the packages installed by `skills`. Then uninstall the shared runtime:

```bash
python3 -m pip uninstall birdeye-trader-intelligence
```

Remove any Birdeye credential from the user's secret manager separately. Never delete or rotate a credential without the user's explicit request.

## Local development

```bash
git clone https://github.com/deanle-wq/birdeye-trader-skills.git
cd birdeye-trader-skills
python3 -m pip install -e .
npx --yes skills@latest add . --list
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Next references

- [Troubleshooting](TROUBLESHOOTING.md)
- [Workflow router](workflows/README.md)
- [Birdeye Data documentation](https://docs.birdeye.so/)
- [Birdeye x402 reference](https://docs.birdeye.so/reference/x402)
