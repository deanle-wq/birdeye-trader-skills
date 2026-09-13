"""CLI for V2 catalog discovery, routing and bounded execution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from ..core import IntelligenceError
from .catalog import Catalog
from .runtime import V2Runtime


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="birdeye-intel-v2")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    listing = commands.add_parser("list")
    listing.add_argument("--stage")
    listing.add_argument("--domain")
    listing.add_argument("--runtime-status")
    describe = commands.add_parser("describe")
    describe.add_argument("skill")
    route = commands.add_parser("route")
    route.add_argument("text")
    route.add_argument("--limit", type=int, default=5)
    run = commands.add_parser("run")
    run.add_argument("skill")
    run.add_argument("--input-json", default="{}")
    hierarchy = commands.add_parser("hierarchy")
    hierarchy.add_argument("--stage")
    return root


def execute(args: argparse.Namespace) -> dict[str, Any]:
    catalog = Catalog()
    if args.command == "doctor":
        return {
            "schema_version": "2.0.0",
            "status": "ok",
            "runtime": "birdeye-intel-v2",
            "release_status": "evaluation-only-not-production-ready",
            "endpoint_surface_policy": "BIRDEYE_X402_ONLY",
            "catalog_skill_count": len(catalog),
            "public_package_count": len({skill.public_package_name for skill in catalog.list()}),
            "api_key_configured": bool(os.environ.get("BIRDEYE_API_KEY")),
            "credential_source": "process_environment_only",
            "credential_value_exposed": False,
        }
    if args.command == "list":
        skills = catalog.list(stage=args.stage, domain=args.domain, runtime_status=args.runtime_status)
        return {"schema_version": "2.0.0", "count": len(skills), "skills": [skill.as_dict() for skill in skills]}
    if args.command == "describe":
        return {"schema_version": "2.0.0", "skill": catalog.get(args.skill).as_dict()}
    if args.command == "route":
        return {"schema_version": "2.0.0", "matches": catalog.route(args.text, limit=args.limit)}
    if args.command == "hierarchy":
        tree = catalog.hierarchy()
        return {"schema_version": "2.0.0", "hierarchy": {args.stage.upper(): tree.get(args.stage.upper(), {})} if args.stage else tree}
    if args.command == "run":
        inputs = json.loads(args.input_json)
        if not isinstance(inputs, dict):
            raise ValueError("--input-json must be a JSON object")
        return V2Runtime(catalog=catalog).run(args.skill, inputs)
    raise ValueError("Unsupported V2 command")


def main(argv: list[str] | None = None) -> int:
    try:
        result = execute(parser().parse_args(argv))
    except (IntelligenceError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        error = exc.as_dict() if isinstance(exc, IntelligenceError) else {"code": "invalid_input", "message": str(exc), "retryable": False, "endpoint_id": None, "details": {}}
        result = {"schema_version": "2.0.0", "status": "error", "errors": [error]}
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 2 if result.get("status") == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
