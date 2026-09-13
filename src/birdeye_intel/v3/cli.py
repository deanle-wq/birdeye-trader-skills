"""One shared CLI for the Birdeye V3 domain and analysis skills."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable

from ..core import BaselineRequired, IntelligenceError, InvalidInput, utc_now
from ..v2.runtime import V2Runtime
from .catalog import CommandSpec, CoreCatalog, CoreSkillSpec
from .direct import run_direct
from .radar import run_market_radar


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--address", help="Primary token, wallet, developer or pair address")
    parser.add_argument("--token", dest="token_address")
    parser.add_argument("--wallet", dest="wallet_address")
    parser.add_argument("--wallets", dest="wallet_addresses", help="Comma-separated wallet addresses")
    parser.add_argument("--developer", dest="developer_wallet_address")
    parser.add_argument("--pair", dest="pair_address")
    parser.add_argument("--time-from", type=int)
    parser.add_argument("--time-to", type=int)
    parser.add_argument("--interval")
    parser.add_argument("--resolution")
    parser.add_argument("--time-frame")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sort-by")
    parser.add_argument("--sort-type", choices=("asc", "desc"))
    parser.add_argument("--source")
    parser.add_argument("--graduated", choices=("true", "false"))
    parser.add_argument("--min-liquidity", type=float)
    parser.add_argument("--max-liquidity", type=float)
    parser.add_argument("--min-market-cap", type=float)
    parser.add_argument("--max-market-cap", type=float)
    parser.add_argument("--min-holder", type=int)
    parser.add_argument("--min-volume-5m-usd", type=float)
    parser.add_argument("--min-volume-1h-usd", type=float)
    parser.add_argument("--min-volume-5m-change-percent", type=float)
    parser.add_argument("--min-price-change-5m-percent", type=float)
    parser.add_argument("--min-trade-5m-count", type=int)
    parser.add_argument("--min-progress-percent", type=float)
    parser.add_argument("--max-progress-percent", type=float)
    parser.add_argument("--score-floor", type=float)
    parser.add_argument("--min-score-coverage", type=float)
    parser.add_argument("--size-usd")
    parser.add_argument("--latency-seconds", type=int)
    parser.add_argument("--baseline-json")
    parser.add_argument("--input-json", default="{}")
    parser.add_argument("--call-cap", type=int)
    parser.add_argument("--pretty", action="store_true")


def parser(catalog: CoreCatalog | None = None) -> argparse.ArgumentParser:
    catalog = catalog or CoreCatalog()
    root = argparse.ArgumentParser(
        prog="birdeye-cli",
        description="Read-only Birdeye Data skills for Solana trader research.",
    )
    commands = root.add_subparsers(dest="root_command", required=True)
    commands.add_parser("doctor", help="Check configuration without exposing credentials")
    listing = commands.add_parser("catalog", help="List core skills or inspect one package")
    listing.add_argument("skill", nargs="?")
    for skill in catalog.list():
        group = commands.add_parser(skill.group, help=skill.description)
        actions = group.add_subparsers(dest="action", required=True)
        for command in skill.commands:
            action = actions.add_parser(command.name, help=command.question)
            _add_run_arguments(action)
    return root


def _json_object(raw: str, label: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise InvalidInput(f"{label} must be a JSON object")
    return value


def _parse_inputs(
    args: argparse.Namespace,
    command: CommandSpec,
    *,
    now: Callable[[], int],
) -> dict[str, Any]:
    inputs = _json_object(args.input_json, "--input-json")
    forbidden = [key for key in inputs if "api_key" in key.lower() or "authorization" in key.lower()]
    if forbidden:
        raise InvalidInput("Credentials cannot be passed in command input")
    explicit = {
        "token_address": args.token_address,
        "wallet_address": args.wallet_address,
        "developer_wallet_address": args.developer_wallet_address,
        "pair_address": args.pair_address,
        "time_from": args.time_from,
        "time_to": args.time_to,
        "interval": args.interval,
        "resolution": args.resolution,
        "time_frame": args.time_frame,
        "limit": args.limit,
        "sort_by": args.sort_by,
        "sort_type": args.sort_type,
        "source": args.source,
        "graduated": ({"true": True, "false": False}.get(args.graduated) if args.graduated else None),
        "min_liquidity": args.min_liquidity,
        "max_liquidity": args.max_liquidity,
        "min_market_cap": args.min_market_cap,
        "max_market_cap": args.max_market_cap,
        "min_holder": args.min_holder,
        "min_volume_5m_usd": args.min_volume_5m_usd,
        "min_volume_1h_usd": args.min_volume_1h_usd,
        "min_volume_5m_change_percent": args.min_volume_5m_change_percent,
        "min_price_change_5m_percent": args.min_price_change_5m_percent,
        "min_trade_5m_count": args.min_trade_5m_count,
        "min_progress_percent": args.min_progress_percent,
        "max_progress_percent": args.max_progress_percent,
        "score_floor": args.score_floor,
        "min_score_coverage": args.min_score_coverage,
        "size_usd": args.size_usd,
        "latency_seconds": args.latency_seconds,
        "call_cap": args.call_cap,
    }
    inputs = {**command.defaults, **inputs, **{key: value for key, value in explicit.items() if value is not None}}
    if args.wallet_addresses:
        inputs["wallet_addresses"] = [item.strip() for item in args.wallet_addresses.split(",") if item.strip()]
    if args.baseline_json:
        inputs["baseline"] = _json_object(args.baseline_json, "--baseline-json")
    if args.address:
        address_fields = {
            "token": "token_address",
            "wallet": "wallet_address",
            "wallets": "wallet_addresses",
            "developer": "developer_wallet_address",
            "pair": "pair_address",
        }
        field = address_fields.get(command.entity)
        if field == "wallet_addresses":
            inputs.setdefault(field, [args.address])
        elif field:
            inputs.setdefault(field, args.address)
        else:
            raise InvalidInput("--address is ambiguous for this command; use --token, --wallet or --pair")
    if command.default_lookback_seconds:
        end = int(inputs.get("time_to") or now())
        inputs.setdefault("time_to", end)
        inputs.setdefault("time_from", end - command.default_lookback_seconds)
    if "baseline" in command.requires and not isinstance(inputs.get("baseline"), dict):
        raise BaselineRequired("This monitor requires --baseline-json or a baseline object in --input-json")
    missing = [field for field in command.requires if inputs.get(field) in (None, "", [])]
    if missing:
        raise InvalidInput(f"Missing required input: {', '.join(missing)}")
    if "wallet_addresses" in command.requires and len(inputs.get("wallet_addresses", [])) < 2:
        if command.entity != "wallets" or command.name in {"kol"}:
            pass
        else:
            raise InvalidInput("This command requires at least two wallet addresses")
    inputs.setdefault("chain", "solana")
    return inputs


def _usage_value(result: dict[str, Any], key: str) -> int:
    value = result.get("cost", {}).get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _aggregate_status(results: list[dict[str, Any]]) -> str:
    statuses = [str(result.get("status", "error")) for result in results]
    if statuses and all(status == "complete" for status in statuses):
        return "complete"
    if statuses and all(status in {"complete", "evidence_only"} for status in statuses):
        return "evidence_only"
    if statuses and all(status in {"error", "blocked"} for status in statuses):
        return "error"
    return "partial"


def run_command(
    skill: CoreSkillSpec,
    command: CommandSpec,
    inputs: dict[str, Any],
    *,
    runtime: V2Runtime | None = None,
) -> dict[str, Any]:
    runtime = runtime or V2Runtime()
    if command.mode == "radar":
        result = run_market_radar(command, inputs, runtime.client)
        sections = result.get("sections", {})
        section_answers = sum(
            section.get("status") in {"complete", "empty"}
            for section in sections.values()
        )
        return {
            "schema_version": "3.0.0",
            "observed_at": result["observed_at"],
            "skill": skill.name,
            "command": command.name,
            "question": command.question,
            "mode": command.mode,
            "status": result["status"],
            "answer": result.get("answer"),
            "sections": sections,
            "summary": {
                "section_count": len(sections),
                "sections_with_answers": section_answers,
                "section_statuses": {
                    name: section.get("status") for name, section in sections.items()
                },
                "calls_attempted": _usage_value(result, "calls_attempted"),
                "calls_succeeded": _usage_value(result, "calls_succeeded"),
                "call_cap": result.get("cost", {}).get("call_cap"),
                "max_calls": command.max_calls,
            },
            "limitations": result.get("limitations", []),
            "errors": result.get("errors", []),
        }
    if command.mode == "direct":
        sections = {
            command.endpoint_ids[0]: run_direct(command, inputs, runtime.client)
        }
        results = list(sections.values())
        result = results[0]
        return {
            "schema_version": "3.0.0",
            "observed_at": utc_now(),
            "skill": skill.name,
            "command": command.name,
            "question": command.question,
            "mode": command.mode,
            "status": result["status"],
            "answer": result.get("answer"),
            "sections": sections,
            "summary": {
                "section_count": 1,
                "sections_with_answers": int(result.get("answer") is not None),
                "section_statuses": {command.endpoint_ids[0]: result["status"]},
                "calls_attempted": _usage_value(result, "calls_attempted"),
                "calls_succeeded": _usage_value(result, "calls_succeeded"),
                "call_cap": min(command.max_calls, int(inputs.get("call_cap", command.max_calls))),
                "max_calls": command.max_calls,
            },
            "limitations": result.get("limitations", []),
            "errors": result.get("errors", []),
        }
    sections: dict[str, Any] = {}
    requested_cap = inputs.get("call_cap", command.max_calls)
    try:
        call_cap = min(command.max_calls, int(requested_cap))
    except (TypeError, ValueError) as exc:
        raise InvalidInput("call_cap must be a positive integer") from exc
    if call_cap < 1:
        raise InvalidInput("call_cap must be a positive integer")
    calls_attempted = 0
    for leaf in command.leaves:
        remaining = call_cap - calls_attempted
        if remaining <= 0:
            sections[leaf] = {
                "status": "blocked",
                "answer": None,
                "cost": {"calls_attempted": 0, "calls_succeeded": 0},
                "limitations": ["Skipped because the command-level call cap was reached."],
                "errors": [
                    {
                        "code": "cost_cap_reached",
                        "message": "Command-level call cap reached before this section",
                        "retryable": False,
                        "endpoint_id": None,
                        "details": {},
                    }
                ],
            }
            continue
        leaf_inputs = {**inputs, "call_cap": remaining}
        sections[leaf] = runtime.run(leaf, leaf_inputs)
        calls_attempted += _usage_value(sections[leaf], "calls_attempted")
    results = list(sections.values())
    calls_succeeded = sum(_usage_value(result, "calls_succeeded") for result in results)
    limitations: list[str] = []
    for result in results:
        for limitation in result.get("limitations", []):
            if limitation not in limitations:
                limitations.append(limitation)
    if calls_attempted >= call_cap and any(result.get("status") == "blocked" for result in results):
        limitations.append("The command stopped at its call cap; remaining sections were not queried.")
    section_answers = {
        name: result.get("answer")
        for name, result in sections.items()
        if result.get("answer") is not None
    }
    answer = results[0].get("answer") if len(results) == 1 else (section_answers or None)
    return {
        "schema_version": "3.0.0",
        "observed_at": utc_now(),
        "skill": skill.name,
        "command": command.name,
        "question": command.question,
        "mode": command.mode,
        "status": _aggregate_status(results),
        "answer": answer,
        "sections": sections,
        "summary": {
            "section_count": len(results),
            "sections_with_answers": len(section_answers),
            "section_statuses": {name: result.get("status") for name, result in sections.items()},
            "calls_attempted": calls_attempted,
            "calls_succeeded": calls_succeeded,
            "call_cap": call_cap,
            "max_calls": command.max_calls,
        },
        "limitations": limitations,
    }


def execute(
    args: argparse.Namespace,
    *,
    catalog: CoreCatalog | None = None,
    runtime: V2Runtime | None = None,
    now: Callable[[], int] | None = None,
) -> dict[str, Any]:
    catalog = catalog or CoreCatalog()
    if args.root_command == "doctor":
        return {
            "schema_version": "3.0.0",
            "status": "ok",
            "runtime": "birdeye-cli",
            "release": catalog.release,
            "runtime_boundary": catalog.runtime_boundary,
            "endpoint_surface_policy": "BIRDEYE_X402_ALLOWLIST_ONLY",
            "core_skill_count": len(catalog),
            "command_count": catalog.command_count,
            "legacy_leaf_count": len(catalog.leaf_catalog),
            "api_key_configured": bool(os.getenv("BIRDEYE_API_KEY") or os.getenv("API_KEY")),
            "credential_source": "process_environment_only",
            "credential_value_exposed": False,
            "transaction_execution": False,
        }
    if args.root_command == "catalog":
        if args.skill:
            return {"schema_version": "3.0.0", "skill": catalog.get(args.skill).as_dict()}
        return {
            "schema_version": "3.0.0",
            "core_skill_count": len(catalog),
            "command_count": catalog.command_count,
            "skills": [skill.as_dict() for skill in catalog.list()],
        }
    skill, command = catalog.resolve(args.root_command, args.action)
    effective_now = now or (lambda: int(datetime.now(timezone.utc).timestamp()))
    inputs = _parse_inputs(args, command, now=effective_now)
    return run_command(skill, command, inputs, runtime=runtime)


def main(argv: list[str] | None = None) -> int:
    args: argparse.Namespace | None = None
    try:
        catalog = CoreCatalog()
        args = parser(catalog).parse_args(argv)
        result = execute(args, catalog=catalog)
    except (IntelligenceError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        error = exc.as_dict() if isinstance(exc, IntelligenceError) else {
            "code": "invalid_input",
            "message": str(exc),
            "retryable": False,
            "endpoint_id": None,
            "details": {},
        }
        result = {"schema_version": "3.0.0", "status": "error", "errors": [error]}
    pretty = bool(getattr(args, "pretty", False))
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True, indent=2 if pretty else None)
    sys.stdout.write("\n")
    return 2 if result.get("status") == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
