"""Dependency-free validation for the frozen common result contract."""

from __future__ import annotations

from typing import Any

REQUIRED_KEYS = {
    "schema_version",
    "methodology_version",
    "skill",
    "status",
    "chain",
    "entity",
    "observed_at",
    "summary",
    "facts",
    "metrics",
    "conditions",
    "thresholds",
    "evidence",
    "coverage",
    "confidence",
    "cost",
    "limitations",
    "errors",
    "snapshot",
}
STATUSES = {"complete", "partial", "insufficient_data", "error"}
QUALITIES = {"observed", "derived", "missing", "null", "empty", "zero", "unsupported", "error"}


def validate_result(result: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["result must be an object"]
    missing = sorted(REQUIRED_KEYS - set(result))
    if missing:
        errors.append(f"missing keys: {','.join(missing)}")
    if result.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if result.get("methodology_version") != "1.0.0":
        errors.append("methodology_version must be 1.0.0")
    if result.get("status") not in STATUSES:
        errors.append("invalid status")
    if result.get("chain") != "solana":
        errors.append("chain must be solana")
    entity = result.get("entity")
    if not isinstance(entity, dict) or entity.get("type") not in {"token", "wallet"} or not isinstance(entity.get("address"), str):
        errors.append("invalid entity")
    if not isinstance(result.get("summary"), str):
        errors.append("summary must be a string")
    for key in ("facts", "metrics", "coverage", "confidence", "cost"):
        if not isinstance(result.get(key), dict):
            errors.append(f"{key} must be an object")
    for key in ("conditions", "thresholds", "evidence", "limitations", "errors"):
        if not isinstance(result.get(key), list):
            errors.append(f"{key} must be an array")
    confidence = result.get("confidence")
    if isinstance(confidence, dict) and "value" in confidence:
        value = confidence.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
            errors.append("confidence.value must be in [0,1]")
    for index, evidence in enumerate(result.get("evidence", [])):
        if not isinstance(evidence, dict):
            errors.append(f"evidence[{index}] must be an object")
            continue
        if evidence.get("quality") not in QUALITIES:
            errors.append(f"evidence[{index}] has invalid quality")
        if not isinstance(evidence.get("endpoint_id"), str):
            errors.append(f"evidence[{index}] missing endpoint_id")
    for index, error in enumerate(result.get("errors", [])):
        if not isinstance(error, dict) or not isinstance(error.get("code"), str):
            errors.append(f"errors[{index}] invalid")
    return errors
