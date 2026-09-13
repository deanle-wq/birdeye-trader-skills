# Packaging

The public repository follows the one-folder-per-skill convention used by major skill repositories:

```text
.
├── .claude-plugin/
├── .codex-plugin/
├── .cursor-plugin/
├── docs/workflows/
├── core-skills/             # 12 internal composition packages
├── manifest.json
├── marketplace-catalog.csv
└── skills/                  # 47 public daily-job packages
    ├── birdeye-5-minute-trending-tokens/
    ├── birdeye-launchpad-trending-tokens/
    ├── birdeye-pumpfun-trending-tokens/
    ├── birdeye-market-radar/
    ├── birdeye-token-basic-info/
    └── ...
```

Packaging rules:

- A public skill owns one recognizable trader question.
- `SKILL.md` contains routing, required behavior, inputs, outputs, and boundaries.
- `agents/openai.yaml` contains matching UI metadata and a default invocation prompt.
- Conditional or advanced flow detail belongs in `references/`.
- One shared `birdeye-cli` owns credentials, API calls, validation, budgets, and result envelopes.
- Core packages compose reusable commands but do not duplicate the public marketplace menu.
- Cross-package workflows live under `docs/workflows/`; a workflow is not sold as another skill unless it owns a distinct user question.
- The `birdeye-` namespace prevents collisions with other data providers.

Launchpads use a hybrid rule: Pump.fun keeps dedicated public cards because the jobs are widely recognized, while Moonshot, Raydium LaunchLab, and Meteora DBC are supported through validated `source` presets unless distinct demand or data semantics justify a dedicated package.
