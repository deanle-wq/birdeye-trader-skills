# Install Birdeye Trader Skills in Codex

Use native skill discovery through the `skills` installer, then install the shared Birdeye CLI runtime.

## Prerequisites

- Python 3.9 or newer
- Node.js with `npx`
- A user-owned API key from [Birdeye Data Services](https://bds.birdeye.so/)

## Install

```bash
python3 -m pip install \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"

npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills \
  --skill birdeye-5-minute-trending-tokens --agent codex -y
```

To browse packages before choosing:

```bash
npx --yes skills@latest add \
  https://github.com/deanle-wq/birdeye-trader-skills --list
```

To install the full public set, replace the single `--skill` value with `--skill '*'`. Restart Codex if the new skill does not appear immediately.

## Configure and verify

The user must configure `BIRDEYE_API_KEY` privately in the environment or secret manager used to launch Codex. Do not paste it into the conversation.

```bash
birdeye-cli doctor
birdeye-cli market trending-5m --limit 3 --pretty
```

Then ask Codex:

```text
Use Birdeye Data to show me the most active Solana tokens in the last five minutes with at least $25K liquidity.
```

For key setup, updates, uninstalling, and error recovery, follow [the complete installation guide](../docs/INSTALL.md).
