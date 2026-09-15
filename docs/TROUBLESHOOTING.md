# Troubleshooting

These checks are deliberately credential-safe. Do not print environment variables, shell history, `.env` contents, request headers, or raw debug traces that may contain an API key.

## Birdeye CLI is not found

Confirm Python and the installed package:

```bash
python3 --version
python3 -m pip show birdeye-trader-intelligence
python3 -m birdeye_intel.v3 --help
```

If the module command works but `birdeye-cli` does not, add the Python scripts directory reported by the local Python installation to `PATH`.

## The API key is not configured

Run:

```bash
birdeye-cli doctor
```

If `api_key_configured` is `false`, configure `BIRDEYE_API_KEY` in the same environment that starts the agent. A key set in another terminal window or process is not inherited automatically.

## Authentication returns 401 or 403

1. Stop after the first failed live request.
2. Confirm `birdeye-cli doctor` reports the key as configured.
3. Ask the user to verify or regenerate the key in [Birdeye Data Services](https://bds.birdeye.so/).
4. Confirm the account plan permits the requested data path.
5. Retry one read-only request after the user confirms the fix.

Never ask the user to send the key for inspection.

## Rate limit returns 429

Reduce concurrency and polling frequency, honor any provider retry information, and retry only the failed read. Do not loop aggressively. If the issue persists, review the account's rate limits and the [Birdeye Data documentation](https://docs.birdeye.so/).

## A command returns no rows

- Confirm the token or wallet address and Solana scope.
- Remove optional thresholds one at a time.
- Keep the requested time window unless the user agrees to broaden it.
- Inspect pagination and coverage fields.
- Report a genuine empty result as empty; do not substitute another provider or scrape a web page.

## A monitoring command requires a baseline

Monitoring skills compare a current observation with a caller-owned compatible baseline. Supply an earlier snapshot for the same skill, entity, schema, and methodology. The runtime must not invent a baseline or compare incompatible snapshots.

## A skill is installed but not discovered

1. Restart the agent client.
2. Run the installer with `--list` to confirm the source exposes the package.
3. Reinstall the exact package for the intended agent.
4. Check that the installed folder contains `SKILL.md`.

## Report a reproducible issue

Include:

- Birdeye CLI command name, with addresses redacted when necessary
- Python and operating-system versions
- response status and error category
- observation time
- whether the issue is consistent or intermittent

Exclude API keys, authorization headers, private keys, wallet secrets, and complete raw request dumps.
