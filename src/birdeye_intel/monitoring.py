"""Caller-owned snapshot comparison; no persistence or scheduling."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from .core import BaselineRequired, InvalidInput, base_result, decimal, decimal_string, ratio_percent, set_coverage_confidence


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise InvalidInput("Snapshot observed_at must be an RFC3339 string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidInput("Snapshot observed_at is invalid") from exc


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            output.update(_flatten(child, path))
    else:
        output[prefix] = value
    return output


def compare_snapshots(
    baseline: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, Any]:
    if baseline is None:
        raise BaselineRequired("A compatible prior snapshot is required")
    for name, snapshot in (("baseline", baseline), ("current", current)):
        if not isinstance(snapshot, dict):
            raise InvalidInput(f"{name} snapshot must be an object")
        for key in ("schema_version", "methodology_version", "skill_slug", "chain", "entity", "observed_at", "facts"):
            if key not in snapshot:
                raise InvalidInput(f"{name} snapshot is missing {key}")
    for key in ("schema_version", "methodology_version", "skill_slug", "chain", "entity"):
        if baseline[key] != current[key]:
            raise InvalidInput(f"Snapshot {key} mismatch")
    if not str(baseline["schema_version"]).startswith("1."):
        raise InvalidInput("Snapshot schema major version is incompatible")
    baseline_time = _timestamp(baseline["observed_at"])
    current_time = _timestamp(current["observed_at"])
    if baseline_time >= current_time:
        raise InvalidInput("Baseline must be older than current observation")

    old = _flatten(baseline["facts"])
    new = _flatten(current["facts"])
    paths = sorted(set(old) | set(new))
    deltas = []
    comparable = 0
    for path in paths:
        if path not in old:
            deltas.append({"path": path, "state": "unknown_baseline", "baseline": None, "current": new[path]})
            continue
        if path not in new:
            deltas.append({"path": path, "state": "unknown_current", "baseline": old[path], "current": None})
            continue
        old_number = decimal(old[path])
        new_number = decimal(new[path])
        if old_number is not None and new_number is not None:
            comparable += 1
            absolute = new_number - old_number
            deltas.append(
                {
                    "path": path,
                    "state": "changed" if absolute != 0 else "unchanged",
                    "baseline": decimal_string(old_number),
                    "current": decimal_string(new_number),
                    "absolute_change": decimal_string(absolute),
                    "percentage_change": decimal_string(ratio_percent(absolute, old_number), "0.0001") if old_number != 0 else None,
                }
            )
        elif old[path] == new[path]:
            comparable += 1
            deltas.append({"path": path, "state": "unchanged", "baseline": old[path], "current": new[path]})
        else:
            comparable += 1
            deltas.append({"path": path, "state": "changed", "baseline": old[path], "current": new[path]})

    result = base_result(current["skill_slug"] + "-delta", "token", current["entity"], observed_at=current["observed_at"])
    result["facts"] = {"baseline_observed_at": baseline["observed_at"], "current_observed_at": current["observed_at"]}
    result["metrics"] = {"deltas": deltas, "changed_count": sum(item["state"] == "changed" for item in deltas)}
    result["summary"] = f"Compared {len(paths)} normalized fact paths against the caller-provided baseline."
    if comparable < len(paths):
        result["status"] = "partial"
        result["limitations"].append("Some facts were unavailable in either the baseline or current snapshot.")
    result["limitations"].append("Observed changes are descriptive and do not establish cause or direction.")
    set_coverage_confidence(
        result,
        required_available=comparable,
        required_total=max(1, len(paths)),
        endpoint_factor=Decimal("1"),
    )
    return result
