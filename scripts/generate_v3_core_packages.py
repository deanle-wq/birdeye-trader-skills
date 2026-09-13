#!/usr/bin/env python3
"""Generate the small V3 public skill surface from the canonical core catalog."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src" / "birdeye_intel" / "v3" / "catalog.json"
MARKETPLACE_PATH = ROOT / "src" / "birdeye_intel" / "v3" / "marketplace.json"
MARKETPLACE_DETAILS_PATH = ROOT / "src" / "birdeye_intel" / "v3" / "marketplace_details.json"
CORE_OUTPUT = ROOT / "core-skills"
OUTPUT = ROOT / "skills"
PUBLIC_SOURCE = "https://github.com/deanle-wq/birdeye-trader-skills"
REFERENCE_SOURCES = {
    "birdeye-market-radar": ROOT / "src" / "birdeye_intel" / "v3" / "references" / "market-radar-flow.md",
}


INPUT_HELP = {
    "token_address": "Exact Solana token address; symbols are not accepted when identity is ambiguous.",
    "wallet_address": "Exact Solana wallet address.",
    "wallet_addresses": "Comma-separated Solana wallet addresses; comparison needs at least two.",
    "developer_wallet_address": "Exact Solana creator or developer wallet address.",
    "pair_address": "Exact Solana pool or pair address.",
    "baseline": "Compatible JSON snapshot from an earlier run for the same entity and methodology.",
    "time_from": "Inclusive Unix-second start of the observation window.",
    "time_to": "Inclusive Unix-second end of the observation window.",
    "interval": "Provider-supported ranking or analysis interval.",
    "resolution": "Provider-supported OHLCV candle resolution.",
    "time_frame": "Provider-supported trader-ranking time frame.",
    "limit": "Maximum result rows returned to the caller.",
    "sort_by": "Provider-supported ranking field.",
    "sort_type": "Ascending or descending order.",
    "source": "Solana launchpad source: `all`, Pump.fun, Moonshot, Raydium LaunchLab or Meteora DBC; common human-readable aliases are normalized.",
    "graduated": "Whether launchpad tokens must already be graduated.",
    "min_liquidity": "Minimum indexed USD liquidity.",
    "max_liquidity": "Maximum indexed USD liquidity.",
    "min_market_cap": "Minimum indexed USD market cap.",
    "max_market_cap": "Maximum indexed USD market cap.",
    "min_holder": "Minimum indexed holder count.",
    "min_volume_5m_usd": "Minimum indexed five-minute USD volume.",
    "min_volume_1h_usd": "Minimum indexed one-hour USD volume.",
    "min_volume_5m_change_percent": "Minimum five-minute volume-change percentage.",
    "min_price_change_5m_percent": "Minimum five-minute price-change percentage.",
    "min_trade_5m_count": "Minimum five-minute trade count.",
    "min_progress_percent": "Minimum bonding-curve completion percentage.",
    "max_progress_percent": "Maximum bonding-curve completion percentage.",
    "score_floor": "Minimum deterministic radar score required before a candidate can be listed.",
    "min_score_coverage": "Minimum percentage of score weight backed by observed source or metric evidence.",
    "size_usd": "Hypothetical position size for liquidity and copyability context; no order is placed.",
    "latency_seconds": "Assumed execution delay used by analytical copyability checks.",
}

DIRECT_INPUT_ORDER = [
    "limit", "sort_by", "sort_type", "source", "graduated",
    "time_from", "time_to", "min_progress_percent", "max_progress_percent",
    "min_liquidity", "max_liquidity", "min_market_cap", "max_market_cap",
    "min_holder", "min_volume_5m_usd", "min_volume_1h_usd",
    "min_volume_5m_change_percent", "min_price_change_5m_percent",
    "min_trade_5m_count",
]

DIRECT_OUTPUTS = {
    "ranked-token-list-v1": {
        "ranking_basis": "Exact field used to rank the result.",
        "filters": "Effective endpoint and client-side filters.",
        "fetched_count": "Rows observed before client-side filtering.",
        "returned_count": "Rows returned after filtering and the output limit.",
        "has_next": "Provider pagination signal when available.",
        "tokens[].address": "Solana token address.",
        "tokens[].symbol": "Token symbol.",
        "tokens[].price_usd": "Current indexed USD price.",
        "tokens[].market_cap_usd": "Current indexed USD market cap.",
        "tokens[].liquidity_usd": "Current indexed USD liquidity.",
        "tokens[].holder_count": "Indexed holder count.",
        "tokens[].volume_5m_usd": "Five-minute indexed USD volume.",
        "tokens[].volume_change_5m_pct": "Five-minute volume change percentage.",
        "tokens[].price_change_5m_pct": "Five-minute price change percentage.",
        "tokens[].trade_count_5m": "Five-minute indexed trade count.",
    },
    "ranked-launchpad-token-list-v1": {
        "ranking_basis": "Exact field used to rank the result.",
        "filters": "Effective endpoint and client-side filters.",
        "fetched_count": "Rows observed before client-side filtering.",
        "returned_count": "Rows returned after filtering and the output limit.",
        "has_next": "Provider pagination signal when available.",
        "tokens[].address": "Solana token address.",
        "tokens[].symbol": "Token symbol.",
        "tokens[].market_cap_usd": "Current indexed USD market cap.",
        "tokens[].liquidity_usd": "Current indexed USD liquidity.",
        "tokens[].holder_count": "Indexed holder count.",
        "tokens[].launchpad": "Observed launchpad source.",
        "tokens[].creator": "Observed creator address when present.",
        "tokens[].creation_time": "Observed launch time.",
        "tokens[].bonding_curve_progress_pct": "Observed bonding-curve progress.",
        "tokens[].graduated": "Observed graduation state.",
        "tokens[].graduated_time": "Observed graduation time when present.",
    },
}

RADAR_OUTPUTS = {
    "methodology_version": "Version of the deterministic scoring and gate policy.",
    "policy": "Effective time, market-quality, score, coverage and result-count rules.",
    "score_weights": "Point weights for every ranking component; the weights total 100.",
    "funnel": "Reconciled raw, unique, hard-gated, score-passing and listed candidate counts.",
    "tokens[]": "Ranked candidates that passed hard gates, score coverage and score floor.",
    "tokens[].score": "Deterministic score out of 100.",
    "tokens[].score_coverage_pct": "Percentage of score weight backed by observed evidence.",
    "tokens[].source_ranks": "Candidate position in every fetched activity or confirmation cohort.",
    "tokens[].score_components": "Per-component point contribution; null means the source evidence was unavailable.",
    "tokens[].security_check": "Always `not_run` in this bounded sweep; follow-up token due diligence is separate.",
    "near_misses[]": "Highest-scoring candidates that did not enter the final list, with the failed floor.",
    "changes": "New, stayed and dropped addresses when the caller supplies a compatible baseline.",
}

KNOWN_ABSENCES = {
    "birdeye-launchpad-trending-tokens": "Only Solana launchpad sources that returned source-matched data in live QA are exposed: Pump.fun, Moonshot, Raydium LaunchLab and Meteora DBC. Other EP-006 enum values belong to unsupported chain contexts and are rejected.",
    "birdeye-launchpad-new-tokens": "Only Solana launchpad sources that returned source-matched data in live QA are exposed: Pump.fun, Moonshot, Raydium LaunchLab and Meteora DBC. Other EP-006 enum values belong to unsupported chain contexts and are rejected.",
    "birdeye-migrated-token-screener": "The approved x402 surface does not expose bundle-rate, fresh-wallet-rate or top-10 concentration filters on the launchpad list. This card does not claim or apply them.",
    "birdeye-token-basic-info": "The approved x402 basic-info path does not provide rat-wallet, bundle, sniper-wallet or KOL-buyer counts. They are not synthesized.",
    "birdeye-top-holders": "The approved x402 holder view does not provide cost basis, holder P&L, wallet tags or funding source. These fields are not claimed.",
    "birdeye-top-token-traders": "Wallet tags and funding-source attribution are not claimed unless they appear explicitly in endpoint evidence.",
    "birdeye-holder-distribution-analysis": "Holder profile, holder positions and tag-holdings chart endpoints were explicitly excluded because they are not x402-supported.",
    "birdeye-wallet-trade-history": "Trade history is not current wallet holdings. The x402-excluded holder-position and wallet P&L chart endpoints are not used.",
    "birdeye-wallet-pnl-analysis": "This is a bounded reconstruction from indexed trades, not Birdeye's complete wallet P&L or current holdings product.",
    "birdeye-selected-kol-wallet-activity": "The caller must provide the KOL wallets. The skill does not invent or claim a provider-wide KOL directory.",
    "birdeye-token-wallet-watchlist": "This is a caller-baseline comparison, not a hosted account watchlist or continuous background subscription.",
}


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def invocation(group: str, command: dict) -> str:
    parts = ["birdeye-cli", group, command["name"]]
    required = set(command.get("requires", []))
    entity = command["entity"]
    if "wallet_addresses" in required:
        parts += ["--wallets", "<wallet_1,wallet_2>"]
    elif "developer_wallet_address" in required:
        parts += ["--address", "<developer_wallet_address>"]
    else:
        if "token_address" in required:
            parts += ["--token", "<token_address>"]
        if "wallet_address" in required:
            parts += ["--wallet", "<wallet_address>"]
        if "pair_address" in required:
            parts += ["--pair", "<pair_address>"]
    if not required and entity == "pair":
        parts += ["--address", "<pair_address>"]
    if "baseline" in command.get("requires", []):
        parts += ["--baseline-json", "'<baseline_json>'"]
    if "size_usd" in command.get("defaults", {}):
        parts += ["--size-usd", str(command["defaults"]["size_usd"])]
    if "latency_seconds" in command.get("defaults", {}):
        parts += ["--latency-seconds", str(command["defaults"]["latency_seconds"])]
    return " ".join(parts)


def skill_markdown(skill: dict) -> str:
    group = skill["name"].removeprefix("birdeye-")
    rows = [
        f"| `{command['name']}` | {command['question']} | `{invocation(group, command)}` |"
        for command in skill["commands"]
    ]
    playbook = "\n".join(f"- {rule}" for rule in skill["playbook"])
    dependencies = sorted({
        dependency
        for command in skill["commands"]
        for dependency in command.get("leaves", []) + command.get("endpoint_ids", [])
    })
    flow_reference = (
        "\n\n## Flow reference\n\nRead [references/flow.md](references/flow.md) before running this skill. It defines routing ownership, source order, hard gates, scoring, no-padding behavior, stop rules and the required response.\n\n"
        if skill["name"] in REFERENCE_SOURCES
        else "\n\n"
    )
    return f"""---
name: {skill['name']}
description: {yaml_quote(skill['description'])}
---

# {skill['title']}

Use the shared `birdeye-cli` to answer the user's actual trader question with current, read-only Birdeye Data. This package owns the workflow and interpretation; the V2 leaf names below are private implementation dependencies, not skills the user must select.

## Before running

Run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be set in the process environment. Never ask the user to paste credentials into a prompt or command input.

Choose the narrowest command that fully answers the question. Do not run every command in this package by default.

## Commands

| Command | Trader question | Example |
|---|---|---|
{chr(10).join(rows)}

Pass additional safe filters as a JSON object with `--input-json`. Explicit CLI flags override JSON values. Use `--time-from` and `--time-to` when the user names a window. Add `--pretty` only for human-readable terminal output.

## Analysis rules

{playbook}

- Lead with a direct answer, then show the evidence, window, coverage and limitations that materially affect it.
- Distinguish observed facts, deterministic calculations and interpretation. Never invent missing values.
- Stop or return partial evidence when identity, coverage, pagination, freshness or upstream calls are inadequate.
- This skill is research-only. It must not sign, swap, launch, submit a transaction, or turn historical observations into guaranteed returns.{flow_reference}## Runtime contract

- Public package: `{skill['name']}`
- Shared executable: `birdeye-cli`
- Data boundary: audited Solana Birdeye x402 allowlist only; the evaluation transport uses response-compatible API-key counterparts.
- Maximum calls are bounded per command and reported in the result envelope.
- Internal evidence dependencies: {', '.join(f'`{leaf}`' for leaf in dependencies)}.

Return the V3 envelope without stripping `status`, `answer`, `sections`, `summary`, `limitations`, or endpoint-linked evidence. For a composite command, synthesize across sections only when their coverage supports the conclusion.
"""


def openai_yaml(skill: dict) -> str:
    short = f"Birdeye {skill['title'].removeprefix('Birdeye ')} workflows"
    if len(short) < 25:
        short += " for Solana traders"
    if len(short) > 64:
        short = short[:64].rstrip()
    return "\n".join(
        [
            "interface:",
            f"  display_name: {yaml_quote(skill['title'])}",
            f"  short_description: {yaml_quote(short)}",
            f"  default_prompt: {yaml_quote(skill['default_prompt'])}",
            "",
        ]
    )


def _format_default(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _flag(name: str) -> str:
    special = {
        "token_address": "--token",
        "wallet_address": "--wallet",
        "wallet_addresses": "--wallets",
        "developer_wallet_address": "--developer",
        "pair_address": "--pair",
        "baseline": "--baseline-json",
    }
    return special.get(name, "--" + name.replace("_", "-"))


def _input_rows(card: dict, command_specs: list[dict], endpoint_specs: dict) -> list[tuple[str, str, str, str]]:
    rows: dict[str, tuple[str, str, str, str]] = {}
    for command in command_specs:
        required = set(command.get("requires", []))
        for name in required:
            rows[name] = (_flag(name), "Required", "—", INPUT_HELP.get(name, name.replace("_", " ").title()))
        defaults = dict(command.get("defaults", {}))
        params = dict(command.get("params", {}))
        locked_params = dict(command.get("locked_params", {}))
        client_filters = dict(command.get("client_filters", {}))
        if command.get("default_lookback_seconds"):
            hours = command["default_lookback_seconds"] / 3600
            lookback = f"last {hours:g} hours"
            rows.setdefault("time_from", (_flag("time_from"), "Optional", lookback, INPUT_HELP["time_from"]))
            rows.setdefault("time_to", (_flag("time_to"), "Optional", "now", INPUT_HELP["time_to"]))
        if command.get("mode") == "direct":
            endpoint = endpoint_specs[command["endpoint_ids"][0]]
            allowed = set(re.findall(
                r"query:([a-zA-Z0-9_]+)",
                f"{endpoint.get('required_query_parameters', '')}|{endpoint.get('optional_query_parameters', '')}",
            ))
            available = allowed | set(defaults) | set(params) | set(client_filters)
            for name in DIRECT_INPUT_ORDER:
                if name not in available and not (name in {"time_from", "time_to"} and command.get("window_fields")):
                    continue
                default = client_filters.get(name, params.get(name, defaults.get(name)))
                mode = "Fixed" if name in locked_params else "Optional"
                rows.setdefault(name, (_flag(name), mode, _format_default(default), INPUT_HELP[name]))
        else:
            for name, default in defaults.items():
                if name in INPUT_HELP:
                    rows.setdefault(name, (_flag(name), "Optional", _format_default(default), INPUT_HELP[name]))
            for name in ("time_from", "time_to", "limit"):
                if name in rows:
                    continue
                endpoint_fields = "|".join(
                    endpoint_specs[endpoint_id].get("optional_query_parameters", "")
                    for leaf in command.get("leaves", [])
                    for endpoint_id in []
                )
                if name in endpoint_fields:
                    rows[name] = (_flag(name), "Optional", "Provider default", INPUT_HELP[name])
    ordering = list(INPUT_HELP)
    flag_names = {
        "--token": "token_address",
        "--wallet": "wallet_address",
        "--wallets": "wallet_addresses",
        "--developer": "developer_wallet_address",
        "--pair": "pair_address",
        "--baseline-json": "baseline",
    }
    def order(row: tuple[str, str, str, str]) -> int:
        name = flag_names.get(row[0], row[0].removeprefix("--").replace("-", "_"))
        return ordering.index(name) if name in ordering else 999
    return sorted(rows.values(), key=order)


def _output_rows(command_specs: list[dict], output_schemas: dict[str, dict]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for command in command_specs:
        if command.get("mode") == "radar":
            for field, meaning in RADAR_OUTPUTS.items():
                if field not in seen:
                    rows.append((field, "typed", meaning))
                    seen.add(field)
            continue
        if command.get("mode") == "direct":
            for field, meaning in DIRECT_OUTPUTS.get(command.get("answer_contract"), {}).items():
                if field not in seen:
                    rows.append((field, "typed", meaning))
                    seen.add(field)
            continue
        for leaf in command.get("leaves", []):
            schema = output_schemas.get(leaf, {})
            fields = schema.get("field_types", {})
            if not fields:
                field = f"sections.{leaf}.answer"
                if field not in seen:
                    rows.append((field, "object|null", f"Endpoint-linked answer section for `{leaf}`; see evidence and limitations."))
                    seen.add(field)
                continue
            for field, field_type in fields.items():
                qualified = f"{leaf}.{field}"
                if qualified in seen:
                    continue
                meaning = field.replace("_", " ").capitalize() + "."
                rows.append((qualified, field_type, meaning))
                seen.add(qualified)
    return rows[:30]


def marketplace_skill_markdown(
    card: dict,
    commands: dict[tuple[str, str], dict],
    details: dict,
    endpoint_specs: dict,
    output_schemas: dict[str, dict],
) -> str:
    call_rows = []
    dependencies = set()
    requires_baseline = False
    for call in card["core_calls"]:
        command = commands[(call["group"], call["command"])]
        dependencies.update(command.get("leaves", []))
        dependencies.update(command.get("endpoint_ids", []))
        call_rows.append(
            f"{len(call_rows) + 1}. `{invocation(call['group'], command)}`"
        )
        requires_baseline = requires_baseline or "baseline" in command.get("requires", [])
    card_detail = details[card["name"]]
    command_specs = [commands[(call["group"], call["command"])] for call in card["core_calls"]]
    capabilities = "\n".join(f"- {item}" for item in card_detail["capabilities"])
    examples = "\n".join(f"- `{item}`" for item in card_detail["examples"])
    input_rows = _input_rows(card, command_specs, endpoint_specs)
    input_table = "\n".join(
        f"| `{parameter}` | {requirement} | `{default}` | {meaning} |"
        for parameter, requirement, default, meaning in input_rows
    ) or "| — | None | — | This card uses its declared defaults and accepts only operational controls. |"
    output_rows = _output_rows(command_specs, output_schemas)
    output_table = "\n".join(
        f"| `{field}` | `{field_type}` | {meaning} |"
        for field, field_type, meaning in output_rows
    )
    install_command = f"npx skills add {PUBLIC_SOURCE} --skill {card['name']}"
    call_text = "\n".join(call_rows)
    baseline_boundary = (
        "- This change-monitoring card requires a compatible caller baseline. A current feed is not a change alert.\n"
        if requires_baseline
        else ""
    )
    readiness_boundary = (
        "- Answer readiness: `ATOMIC_TYPED_PATH`; this card has a typed runtime answer and still preserves normal coverage and live-data limits.\n"
        if card["answer_readiness"] == "ATOMIC_TYPED_PATH"
        else "- Answer readiness: `ANALYTICAL_EVIDENCE_PATH`; keep it explicitly non-production until its analytical acceptance gate passes.\n"
    )
    flow_reference = (
        "\n\n## Flow reference\n\nRead [references/flow.md](references/flow.md) before running. It is the canonical sweep → gate → score → shortlist contract for this card.\n\n"
        if card["name"] in REFERENCE_SOURCES
        else "\n\n"
    )
    return f"""---
name: {card['name']}
description: {yaml_quote(card['description'] + ' Use when the trader asks: ' + card['question'])}
---

# {card['title']}

Answer this daily trader job: **{card['question']}**

This is a focused marketplace skill, not a generic Birdeye toolbox. Use only the calls needed below and keep the default horizon and filters unless the user overrides them.

## Installation

Learn the {card['title'].split(' ', 1)[-1]} skill.

From this repository, install the public package:

```bash
{install_command}
```

After installation, run `birdeye-cli doctor`. If `api_key_configured` is false, explain that `BIRDEYE_API_KEY` must be configured in the process environment. Never request a credential in prompt text or JSON input.

## Core capabilities

{capabilities}

## Just say to your agent

{examples}

## Inputs and filters

| Input | Requirement | Default | Meaning |
|---|---|---|---|
{input_table}

Explicit flags override values passed through `--input-json`, except inputs marked `Fixed`, which are enforced to preserve the card's identity. Reject credentials in both places. Preserve the user's stated window and thresholds instead of silently restoring defaults.

## Run

{call_text}

Use `--input-json` for endpoint-supported filters not exposed as flags. Preserve any explicit user time window, liquidity, market-cap, holder or activity thresholds.{flow_reference}## Output fields

The command returns the V3 envelope. These are the card-specific answer fields or endpoint-linked sections the agent must interpret:

| Field | Type | Meaning |
|---|---|---|
{output_table}

Do not strip `status`, `observed_at`, `answer`, `sections`, `summary`, `limitations` or endpoint-linked evidence from the runtime response.

## Response rules

1. Lead with the direct answer to the card's question.
2. Show the ranking basis or analysis window and the filters actually applied.
3. Include the few fields that let the trader verify the result; do not dump unrelated endpoint payloads.
4. State coverage, pagination, freshness, failed sections and material unknowns.
5. Treat rankings, wallet history and change signals as research evidence, never as guaranteed returns or an instruction to trade.

## Boundaries

- Category: `{card['category']}`; trader stage: `{card['stage']}`; difficulty: `{card['difficulty']}`.
{readiness_boundary}- Birdeye Data, Solana and read-only only.
{baseline_boundary}- Do not scrape Birdeye web pages or use third-party provider data. Use only `birdeye-cli` and its audited x402-eligible dependencies.
- Never sign, swap, launch, submit a transaction, or handle a private key.
- Internal dependencies: {', '.join(f'`{value}`' for value in sorted(dependencies))}.
{('- Known absence: ' + KNOWN_ABSENCES[card['name']]) if card['name'] in KNOWN_ABSENCES else ''}
"""


def marketplace_openai_yaml(card: dict) -> str:
    short = card["description"]
    if len(short) > 64:
        short = short[:61].rstrip() + "..."
    if len(short) < 25:
        short += " with Birdeye Data"
    prompt = f"Use ${card['name']} to answer: {card['question']}"
    return "\n".join(
        [
            "interface:",
            f"  display_name: {yaml_quote(card['title'])}",
            f"  short_description: {yaml_quote(short)}",
            f"  default_prompt: {yaml_quote(prompt)}",
            "",
        ]
    )


def main() -> None:
    document = json.loads(CATALOG_PATH.read_text())
    marketplace = json.loads(MARKETPLACE_PATH.read_text())
    details_document = json.loads(MARKETPLACE_DETAILS_PATH.read_text())
    details = details_document["skills"]
    endpoint_specs = json.loads((ROOT / "src/birdeye_intel/v2/endpoints.json").read_text())
    output_schemas: dict[str, dict] = {}
    for manifest_path in (
        ROOT / "src/birdeye_intel/v2/wave0_manifest.json",
        ROOT / "src/birdeye_intel/v2/wave1_manifest.json",
    ):
        for row in json.loads(manifest_path.read_text()).get("skills", []):
            output_schemas[row["slug"]] = row
    v2_catalog = json.loads(
        (ROOT / "src/birdeye_intel/v2/catalog.json").read_text()
    )
    v2_status = {item["slug"]: item["runtime_status"] for item in v2_catalog["skills"]}
    if CORE_OUTPUT.exists():
        shutil.rmtree(CORE_OUTPUT)
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    CORE_OUTPUT.mkdir(parents=True)
    OUTPUT.mkdir(parents=True)
    core_manifest = []
    commands = {}
    for skill in document["skills"]:
        folder = CORE_OUTPUT / skill["name"]
        (folder / "agents").mkdir(parents=True)
        (folder / "SKILL.md").write_text(skill_markdown(skill).rstrip() + "\n")
        (folder / "agents" / "openai.yaml").write_text(openai_yaml(skill))
        if skill["name"] in REFERENCE_SOURCES:
            (folder / "references").mkdir()
            shutil.copyfile(REFERENCE_SOURCES[skill["name"]], folder / "references" / "flow.md")
        core_manifest.append(
            {
                "name": skill["name"],
                "title": skill["title"],
                "command_count": len(skill["commands"]),
                "commands": [command["name"] for command in skill["commands"]],
            }
        )
        for command in skill["commands"]:
            command["_answer_readiness"] = (
                "ATOMIC_TYPED_PATH"
                if command["mode"] == "direct"
                or all(v2_status[leaf] == "READY_ATOMIC" for leaf in command.get("leaves", []))
                else "ANALYTICAL_EVIDENCE_PATH"
            )
            commands[(skill["name"].removeprefix("birdeye-"), command["name"])] = command
    manifest = []
    seen = set()
    expected_details = {card["name"] for card in marketplace["skills"]}
    if set(details) != expected_details:
        missing = sorted(expected_details - set(details))
        extra = sorted(set(details) - expected_details)
        raise ValueError(f"Marketplace detail coverage mismatch; missing={missing}, extra={extra}")
    for card in marketplace["skills"]:
        if card["name"] in seen:
            raise ValueError(f"Duplicate marketplace skill: {card['name']}")
        seen.add(card["name"])
        for call in card["core_calls"]:
            if (call["group"], call["command"]) not in commands:
                raise ValueError(f"Unknown marketplace core call: {call}")
        card["answer_readiness"] = (
            "ATOMIC_TYPED_PATH"
            if all(
                commands[(call["group"], call["command"])]["_answer_readiness"]
                == "ATOMIC_TYPED_PATH"
                for call in card["core_calls"]
            )
            else "ANALYTICAL_EVIDENCE_PATH"
        )
        folder = OUTPUT / card["name"]
        (folder / "agents").mkdir(parents=True)
        (folder / "SKILL.md").write_text(
            marketplace_skill_markdown(
                card, commands, details, endpoint_specs, output_schemas
            ).rstrip()
            + "\n"
        )
        (folder / "agents" / "openai.yaml").write_text(marketplace_openai_yaml(card))
        if card["name"] in REFERENCE_SOURCES:
            (folder / "references").mkdir()
            shutil.copyfile(REFERENCE_SOURCES[card["name"]], folder / "references" / "flow.md")
        manifest.append({
            "name": card["name"],
            "title": card["title"],
            "category": card["category"],
            "stage": card["stage"],
            "difficulty": card["difficulty"],
            "question": card["question"],
            "answer_readiness": card["answer_readiness"],
            "core_calls": card["core_calls"],
            "capability_count": len(details[card["name"]]["capabilities"]),
            "example_prompt_count": len(details[card["name"]]["examples"]),
        })
    (OUTPUT.parent / "core-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "3.0.0",
                "release": document["release"],
                "skill_count": len(core_manifest),
                "command_count": sum(item["command_count"] for item in core_manifest),
                "skills": core_manifest,
            },
            indent=2,
        )
        + "\n"
    )
    (OUTPUT.parent / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "release": document["release"],
                "skill_count": len(manifest),
                "core_command_count": sum(len(item["core_calls"]) for item in manifest),
                "skills": manifest,
            },
            indent=2,
        )
        + "\n"
    )
    with (OUTPUT.parent / "marketplace-catalog.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            lineterminator="\n",
            fieldnames=[
                "skill_name",
                "display_title",
                "trader_question",
                "description",
                "category",
                "stage",
                "difficulty",
                "answer_readiness",
                "core_calls",
                "core_capabilities",
                "example_prompts",
            ],
        )
        writer.writeheader()
        for item in manifest:
            writer.writerow(
                {
                    "skill_name": item["name"],
                    "display_title": item["title"],
                    "trader_question": item["question"],
                    "description": next(
                        card["description"]
                        for card in marketplace["skills"]
                        if card["name"] == item["name"]
                    ),
                    "category": item["category"],
                    "stage": item["stage"],
                    "difficulty": item["difficulty"],
                    "answer_readiness": item["answer_readiness"],
                    "core_calls": "; ".join(
                        f"{call['group']} {call['command']}" for call in item["core_calls"]
                    ),
                    "core_capabilities": "; ".join(
                        details[item["name"]]["capabilities"]
                    ),
                    "example_prompts": "; ".join(
                        details[item["name"]]["examples"]
                    ),
                }
            )


if __name__ == "__main__":
    main()
