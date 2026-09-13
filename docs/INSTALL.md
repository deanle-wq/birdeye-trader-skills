# Installation

## 1. Inspect or install the skill packages

```bash
SOURCE="https://github.com/deanle-wq/birdeye-trader-skills"

npx --yes skills@latest add "$SOURCE" --list
npx --yes skills@latest add "$SOURCE" \
  --skill birdeye-market-radar --agent codex -y
npx --yes skills@latest add "$SOURCE" \
  --skill '*' --agent codex -y
```

Use `--all` only when every package should be installed for every detected agent.

## 2. Install the shared CLI runtime

```bash
python3 -m pip install \
  "git+https://github.com/deanle-wq/birdeye-trader-skills.git@main"

birdeye-cli doctor
birdeye-cli catalog market
```

## 3. Configure a user-owned API key

```bash
export BIRDEYE_API_KEY="<your-own-birdeye-api-key>"
birdeye-cli doctor
```

`doctor` reports only whether the key exists. It never returns the value. Configure credentials through the process environment or a secret manager, never through a prompt, JSON input, command argument, or committed file.

An API key enables the approved evaluation transport only. It does not make a Standard-only endpoint x402-eligible or override an explicit scope exclusion.

## Local development

```bash
python3 -m pip install -e .
npx --yes skills@latest add . --list
python3 scripts/audit_v3_core.py
python3 -m unittest discover -s tests -p 'test_*.py'
```
