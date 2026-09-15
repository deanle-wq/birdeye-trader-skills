# Install Birdeye Trader Skills in OpenCode

Install the shared runtime, then add the question-specific skills through native skill discovery.

## Install

```bash
python3 -m pip install \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"

npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills \
  --skill birdeye-5-minute-trending-tokens --agent opencode -y
```

List packages first with:

```bash
npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills --list
```

Restart OpenCode if it does not refresh the installed skill automatically.

## Configure and verify

The user must configure `BIRDEYE_API_KEY` privately in the environment or secret manager used to launch OpenCode. Do not paste it into an agent conversation.

```bash
birdeye-cli doctor
birdeye-cli market trending-5m --limit 3 --pretty
```

For complete setup, updates, uninstalling, and troubleshooting, see [docs/INSTALL.md](../docs/INSTALL.md).
