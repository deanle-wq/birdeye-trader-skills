#!/usr/bin/env python3
"""Run sanitized live QA for every V3 command backed only by typed atomic leaves."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from v2_live_skill_smoke import (
    LAUNCH_TOKEN,
    MARKET_TOKEN,
    WSOL,
    bootstrap,
)

from birdeye_intel.v2.runtime import V2Runtime
from birdeye_intel.v3.catalog import CoreCatalog
from birdeye_intel.v3.cli import run_command


def main() -> None:
    key = os.getenv("BIRDEYE_API_KEY") or os.getenv("API_KEY")
    if not key:
        raise SystemExit("BIRDEYE_API_KEY or API_KEY is required")
    catalog = CoreCatalog()
    pair, wallets, creator = bootstrap(key)
    now = int(time.time())
    base_inputs = {
        "chain": "solana",
        "query": "SOL",
        "token_address": MARKET_TOKEN,
        "token_addresses": [MARKET_TOKEN, WSOL],
        "wallet_address": wallets[0],
        "wallet_addresses": wallets[:2] if len(wallets) >= 2 else wallets,
        "developer_wallet_address": creator,
        "pair_address": pair,
        "pair_addresses": [pair],
        "time_from": now - 86_400,
        "time_to": now,
        "before_time": now,
        "resolution": "1H",
        "unixtime": now - 3_600,
        "limit": 5,
    }
    runtime = V2Runtime()
    cases = []
    for skill in catalog.list():
        for command in skill.commands:
            statuses = (
                {"READY_ATOMIC_DIRECT"}
                if command.mode == "direct"
                else {"READY_DETERMINISTIC_RADAR"}
                if command.mode == "radar"
                else {
                    catalog.leaf_catalog.get(leaf).runtime_status for leaf in command.leaves
                }
            )
            if statuses not in ({"READY_ATOMIC"}, {"READY_ATOMIC_DIRECT"}, {"READY_DETERMINISTIC_RADAR"}):
                continue
            inputs = {**command.defaults, **base_inputs, "call_cap": command.max_calls}
            if command.default_lookback_seconds:
                inputs["time_from"] = now - command.default_lookback_seconds
            if command.name == "launch-stages":
                inputs["token_address"] = LAUNCH_TOKEN
                inputs["token_addresses"] = [LAUNCH_TOKEN]
            result = run_command(skill, command, inputs, runtime=runtime)
            error_codes = sorted(
                {
                    error.get("code", "unknown")
                    for section in result["sections"].values()
                    for error in section.get("errors", [])
                }
            )
            cases.append(
                {
                    "skill": skill.name,
                    "command": command.name,
                    "status": result["status"],
                    "section_statuses": result["summary"]["section_statuses"],
                    "sections_with_answers": result["summary"]["sections_with_answers"],
                    "calls_attempted": result["summary"]["calls_attempted"],
                    "calls_succeeded": result["summary"]["calls_succeeded"],
                    "error_codes": error_codes,
                }
            )
    counts = Counter(case["status"] for case in cases)
    failed = [case for case in cases if case["status"] != "complete"]
    document = {
        "schema_version": "3.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "standard_api_counterpart_live_qa",
        "credential_source": "process_environment_only",
        "credential_value_persisted": False,
        "entity_values_persisted": False,
        "x402_paid_requests": 0,
        "case_count": len(cases),
        "status_counts": dict(sorted(counts.items())),
        "gate": "PASS" if not failed else "FAIL",
        "cases": cases,
    }
    output = ROOT / "qa" / "v3" / "live-atomic-command-qa.json"
    output.write_text(json.dumps(document, indent=2) + "\n")
    print(json.dumps({
        "gate": document["gate"],
        "case_count": document["case_count"],
        "status_counts": document["status_counts"],
        "failed_cases": [{"skill": case["skill"], "command": case["command"], "error_codes": case["error_codes"]} for case in failed],
        "x402_paid_requests": 0,
    }, indent=2))
    raise SystemExit(0 if not failed else 1)


if __name__ == "__main__":
    main()
