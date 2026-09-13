#!/usr/bin/env python3
"""Generate a reproducible V3 package, dependency and readiness audit."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from birdeye_intel.v3.catalog import CoreCatalog


def main() -> None:
    catalog = CoreCatalog()
    marketplace = json.loads(
        (ROOT / "src/birdeye_intel/v3/marketplace.json").read_text()
    )
    detail_document = json.loads(
        (ROOT / "src/birdeye_intel/v3/marketplace_details.json").read_text()
    )
    details = detail_document["skills"]
    excluded_document = json.loads((ROOT / "qa/v2/x402-eligibility-audit.json").read_text())
    excluded_ids = {row["endpoint_id"] for row in excluded_document["scope_exclusions"]}
    unique_leaves = {
        leaf_name: catalog.leaf_catalog.get(leaf_name)
        for skill in catalog.list()
        for command in skill.commands
        for leaf_name in command.leaves
    }
    endpoint_ids = sorted(
        {endpoint_id for leaf in unique_leaves.values() for endpoint_id in leaf.endpoint_ids}
        | {
            endpoint_id
            for skill in catalog.list()
            for command in skill.commands
            for endpoint_id in command.endpoint_ids
        }
    )
    command_rows = []
    for skill in catalog.list():
        for command in skill.commands:
            statuses = (
                ["READY_ATOMIC_DIRECT"]
                if command.mode == "direct"
                else ["READY_DETERMINISTIC_RADAR"]
                if command.mode == "radar"
                else sorted(
                    {catalog.leaf_catalog.get(leaf).runtime_status for leaf in command.leaves}
                )
            )
            command_rows.append(
                {
                    "skill": skill.name,
                    "command": command.name,
                    "question": command.question,
                    "mode": command.mode,
                    "leaf_count": len(command.leaves),
                    "leaf_runtime_statuses": statuses,
                    "answer_readiness": (
                        "ATOMIC_TYPED_PATH"
                        if statuses in (["READY_ATOMIC"], ["READY_ATOMIC_DIRECT"], ["READY_DETERMINISTIC_RADAR"])
                        else "REQUIRES_ANALYTICAL_ACCEPTANCE"
                    ),
                    "max_calls": command.max_calls,
                }
            )
    package_root = ROOT / "skills"
    folders = sorted(path.name for path in package_root.iterdir() if path.is_dir())
    expected_folders = sorted(card["name"] for card in marketplace["skills"])
    core_folders = sorted(
        path.name for path in (ROOT / "core-skills").iterdir() if path.is_dir()
    )
    expected_core_folders = sorted(skill.name for skill in catalog.list())
    violations = []
    if folders != expected_folders:
        violations.append("Generated package folders do not match the V3 catalog")
    if core_folders != expected_core_folders:
        violations.append("Generated core folders do not match the V3 core catalog")
    if excluded_ids & set(endpoint_ids):
        violations.append("An explicitly excluded endpoint is active in V3")
    expected_detail_names = {card["name"] for card in marketplace["skills"]}
    if set(details) != expected_detail_names:
        violations.append("Marketplace detail contracts do not exactly cover public skills")
    detail_rows = []
    required_headings = (
        "## Installation",
        "## Core capabilities",
        "## Just say to your agent",
        "## Inputs and filters",
        "## Output fields",
        "## Boundaries",
    )
    for card in marketplace["skills"]:
        detail = details.get(card["name"], {})
        generated = (ROOT / "skills" / card["name"] / "SKILL.md").read_text()
        missing_sections = [heading for heading in required_headings if heading not in generated]
        row = {
            "skill": card["name"],
            "capability_count": len(detail.get("capabilities", [])),
            "example_prompt_count": len(detail.get("examples", [])),
            "missing_sections": missing_sections,
            "installation_targets_exact_skill": (
                f"npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill {card['name']}"
                in generated
            ),
        }
        row["gate"] = (
            "PASS"
            if row["capability_count"] >= 3
            and row["example_prompt_count"] >= 2
            and not missing_sections
            and row["installation_targets_exact_skill"]
            else "FAIL"
        )
        if row["gate"] != "PASS":
            violations.append(f"Incomplete marketplace detail contract: {card['name']}")
        detail_rows.append(row)
    for leaf_name, leaf in unique_leaves.items():
        if not leaf.x402_eligible or leaf.unapproved_endpoint_ids or leaf.non_x402_endpoint_ids:
            violations.append(f"Ineligible dependency: {leaf_name}")
    readiness = Counter(leaf.runtime_status for leaf in unique_leaves.values())
    command_readiness = Counter(row["answer_readiness"] for row in command_rows)
    command_lookup = {
        (skill.group, command.name): command
        for skill in catalog.list()
        for command in skill.commands
    }
    marketplace_readiness = Counter()
    for card in marketplace["skills"]:
        atomic = True
        for call in card["core_calls"]:
            command = command_lookup[(call["group"], call["command"])]
            if command.mode in {"direct", "radar"}:
                continue
            if any(
                catalog.leaf_catalog.get(leaf).runtime_status != "READY_ATOMIC"
                for leaf in command.leaves
            ):
                atomic = False
        marketplace_readiness[
            "ATOMIC_TYPED_PATH" if atomic else "ANALYTICAL_EVIDENCE_PATH"
        ] += 1
    report = {
        "schema_version": "3.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "release": catalog.release,
        "package_gate": "PASS" if not violations else "FAIL",
        "production_answer_gate": (
            "BLOCKED" if command_readiness["REQUIRES_ANALYTICAL_ACCEPTANCE"] else "PASS"
        ),
        "core_skill_count": len(catalog),
        "command_count": catalog.command_count,
        "marketplace_skill_count": len(marketplace["skills"]),
        "marketplace_detail_benchmark": detail_document["benchmark"],
        "marketplace_detail_gate": (
            "PASS" if detail_rows and all(row["gate"] == "PASS" for row in detail_rows) else "FAIL"
        ),
        "marketplace_detail_rows": detail_rows,
        "unique_internal_leaf_count": len(unique_leaves),
        "unique_endpoint_count": len(endpoint_ids),
        "endpoint_ids": endpoint_ids,
        "scope_excluded_endpoint_overlap": sorted(excluded_ids & set(endpoint_ids)),
        "leaf_runtime_status_counts": dict(sorted(readiness.items())),
        "command_answer_readiness_counts": dict(sorted(command_readiness.items())),
        "marketplace_answer_readiness_counts": dict(sorted(marketplace_readiness.items())),
        "generated_package_folders": folders,
        "generated_core_folders": core_folders,
        "violations": violations,
        "commands": command_rows,
    }
    output = ROOT / "qa" / "v3" / "core-surface-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in (
        "package_gate",
        "production_answer_gate",
        "core_skill_count",
        "command_count",
        "marketplace_skill_count",
        "marketplace_detail_gate",
        "unique_internal_leaf_count",
        "unique_endpoint_count",
        "scope_excluded_endpoint_overlap",
        "violations",
    )}, indent=2))
    raise SystemExit(0 if report["package_gate"] == "PASS" else 1)


if __name__ == "__main__":
    main()
