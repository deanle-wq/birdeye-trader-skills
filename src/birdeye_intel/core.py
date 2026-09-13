"""Shared validation, decimal, budget, cache, and result helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
import re
import time
from typing import Any

SCHEMA_VERSION = "1.0.0"
METHODOLOGY_VERSION = "1.0.0"
BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class IntelligenceError(Exception):
    """Base sanitized application error."""

    code = "upstream_error"
    retryable = False

    def __init__(self, message: str, *, endpoint_id: str | None = None) -> None:
        super().__init__(message)
        self.endpoint_id = endpoint_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "endpoint_id": self.endpoint_id,
            "retryable": self.retryable,
            "message": str(self),
            "details": {},
        }


class InvalidInput(IntelligenceError):
    code = "invalid_input"


class UnsupportedChain(IntelligenceError):
    code = "unsupported_chain"


class CostCapReached(IntelligenceError):
    code = "cost_cap_reached"


class AuthenticationError(IntelligenceError):
    code = "authentication_error"


class RateLimited(IntelligenceError):
    code = "rate_limited"
    retryable = True


class UpstreamError(IntelligenceError):
    code = "upstream_error"


class BaselineRequired(IntelligenceError):
    code = "baseline_required"


def decimal(value: Any, *, default: Decimal | None = None) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def decimal_string(value: Decimal | Any, places: str | None = None) -> str | None:
    number = decimal(value)
    if number is None or not number.is_finite():
        return None
    if places is not None:
        number = number.quantize(Decimal(places), rounding=ROUND_HALF_UP)
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def ratio_percent(numerator: Any, denominator: Any) -> Decimal | None:
    n = decimal(numerator)
    d = decimal(denominator)
    if n is None or d is None or d <= 0:
        return None
    return n / d * Decimal("100")


def validate_chain(chain: str) -> str:
    if chain.lower() != "solana":
        raise UnsupportedChain("Only audited Solana mode is available")
    return "solana"


def validate_address(address: str, label: str = "address") -> str:
    if not isinstance(address, str) or not BASE58_RE.fullmatch(address):
        raise InvalidInput(f"Invalid Solana {label}")
    return address


def validate_positive(value: Any, label: str) -> Decimal:
    number = decimal(value)
    if number is None or number <= 0:
        raise InvalidInput(f"{label} must be positive")
    return number


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class Usage:
    call_cap: int
    calls_attempted: int = 0
    calls_succeeded: int = 0
    cache_hits: int = 0
    retries: int = 0
    known_cu: Decimal = Decimal("0")
    unknown_cu_variables: set[str] = field(default_factory=set)
    cap_reached: bool = False
    omitted_expansions: list[str] = field(default_factory=list)
    started: float = field(default_factory=time.monotonic)

    def preflight(self, endpoint_id: str) -> None:
        if self.calls_attempted >= self.call_cap:
            self.cap_reached = True
            self.omitted_expansions.append(endpoint_id)
            raise CostCapReached("Call cap reached before next request", endpoint_id=endpoint_id)
        self.calls_attempted += 1

    def add_cost(self, cu: str) -> None:
        number = decimal(cu)
        if number is None:
            self.unknown_cu_variables.add(cu)
        else:
            self.known_cu += number

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls_attempted": self.calls_attempted,
            "calls_succeeded": self.calls_succeeded,
            "cache_hits": self.cache_hits,
            "retries": self.retries,
            "known_cu": decimal_string(self.known_cu),
            "unknown_cu_variables": sorted(self.unknown_cu_variables),
            "call_cap": self.call_cap,
            "cap_reached": self.cap_reached,
            "omitted_expansions": list(self.omitted_expansions),
            "elapsed_ms": int((time.monotonic() - self.started) * 1000),
        }


class MemoryCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires, value = item
        if expires <= time.monotonic():
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self._items[key] = (time.monotonic() + max(0, ttl_seconds), value)


def condition(
    code: str,
    state: str,
    *,
    value: str | None = None,
    unit: str = "text",
    threshold_id: str | None = None,
    evidence_ids: list[str] | None = None,
    description: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "state": state,
        "observed_value": value,
        "unit": unit,
        "threshold_id": threshold_id,
        "evidence_ids": evidence_ids or [],
        "description": description,
    }

def threshold(
    threshold_id: str,
    value: Any,
    unit: str,
    source: str,
    *,
    override: bool,
    sensitivity: str,
) -> dict[str, Any]:
    return {
        "threshold_id": threshold_id,
        "value": decimal_string(value),
        "unit": unit,
        "class": "user_configurable",
        "source": "caller_override" if override else source,
        "is_override": override,
        "sensitivity": sensitivity,
    }


def base_result(
    skill: str,
    entity_type: str,
    address: str,
    *,
    status: str = "complete",
    observed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "skill": skill,
        "status": status,
        "chain": "solana",
        "entity": {"type": entity_type, "address": address},
        "observed_at": observed_at or utc_now(),
        "summary": "",
        "facts": {},
        "metrics": {},
        "conditions": [],
        "thresholds": [],
        "evidence": [],
        "coverage": {},
        "confidence": {},
        "cost": Usage(0).as_dict(),
        "limitations": [],
        "errors": [],
        "snapshot": None,
    }


def set_coverage_confidence(
    result: dict[str, Any],
    *,
    required_available: int,
    required_total: int,
    optional_available: int = 0,
    optional_total: int = 0,
    endpoint_factor: Decimal = Decimal("0.85"),
    history_factor: Decimal = Decimal("1"),
    pagination_complete: bool = True,
    truncated: bool = False,
) -> None:
    coverage = Decimal(required_available) / Decimal(required_total) if required_total else Decimal("0")
    confidence = coverage * endpoint_factor * history_factor
    result["coverage"] = {
        "required_facts_available": required_available,
        "required_facts_total": required_total,
        "optional_facts_available": optional_available,
        "optional_facts_total": optional_total,
        "history_window_complete": history_factor == Decimal("1"),
        "pagination_complete": pagination_complete,
        "truncated_by_cap": truncated,
    }
    result["confidence"] = {
        "value": float(confidence.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "required_fact_coverage": float(coverage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "endpoint_reliability_factor": float(endpoint_factor),
        "history_coverage_factor": float(history_factor),
        "meaning": "evidence completeness, not predictive certainty",
    }
