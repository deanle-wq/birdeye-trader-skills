"""Deterministic multi-feed market radar for the Birdeye V3 skill surface."""

from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal
from typing import Any

from ..core import (
    AuthenticationError,
    CostCapReached,
    IntelligenceError,
    InvalidInput,
    RateLimited,
    Usage,
    decimal,
    decimal_string,
    utc_now,
)
from ..v2.client import V2Client
from .catalog import CommandSpec

METHODOLOGY_VERSION = "birdeye-market-radar-1.0.0"
MAX_OUTPUT_ROWS = 20
MAX_NEAR_MISSES = 5

SOURCE_PLAN = (
    ("volume_24h", "EP-002", {"sort_by": "volume_24h_usd", "sort_type": "desc"}),
    ("volume_1h", "EP-002", {"sort_by": "volume_1h_usd", "sort_type": "desc"}),
    ("volume_5m", "EP-002", {"sort_by": "volume_5m_usd", "sort_type": "desc"}),
    ("birdeye_trending", "EP-005", {"sort_by": "rank", "sort_type": "asc", "interval": "1h"}),
    ("smart_money", "EP-008", {"sort_by": "smart_traders_no", "sort_type": "desc", "interval": "1d", "trader_style": "all"}),
)

SCORE_WEIGHTS = {
    "volume_24h_rank": Decimal(14),
    "volume_1h_rank": Decimal(12),
    "volume_5m_rank": Decimal(10),
    "liquidity_depth": Decimal(14),
    "holder_depth": Decimal(10),
    "volume_acceleration_5m": Decimal(12),
    "trade_participation_5m": Decimal(10),
    "smart_money_confirmation": Decimal(10),
    "birdeye_trending_confirmation": Decimal(8),
}

FIELD_ALIASES = {
    "address": ("address", "token", "token_address"),
    "symbol": ("symbol",),
    "name": ("name",),
    "price_usd": ("price", "price_usd"),
    "market_cap_usd": ("market_cap", "marketcap", "market_cap_usd"),
    "liquidity_usd": ("liquidity", "liquidity_usd"),
    "holder_count": ("holder", "holder_count"),
    "volume_24h_usd": ("volume_24h_usd", "volume24hUSD", "volume_usd"),
    "volume_1h_usd": ("volume_1h_usd",),
    "volume_5m_usd": ("volume_5m_usd",),
    "volume_change_5m_pct": ("volume_5m_change_percent", "volume_change_5m_pct"),
    "price_change_5m_pct": ("price_change_5m_percent", "price_change_5m_pct"),
    "trade_count_5m": ("trade_5m_count", "trade_count_5m"),
    "recent_listing_time": ("recent_listing_time", "liquidityAddedAt"),
    "smart_trader_count": ("smart_traders_no", "smart_trader_count"),
    "net_flow_usd": ("net_flow", "net_flow_usd"),
}

BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]+")
MARKUP_RE = re.compile(r"[<>\[\]{}()`]+")


def _first(raw: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = raw.get(name)
        if value not in (None, ""):
            return value
    return None


def _safe_text(value: Any, *, limit: int = 80) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    cleaned = " ".join(MARKUP_RE.sub(" ", CONTROL_RE.sub(" ", str(value))).split())
    return cleaned[:limit] or None


def _rows(data: Any, endpoint_id: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        return []
    preferred = "tokens" if endpoint_id == "EP-005" else "items"
    value = data.get(preferred)
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict) and isinstance(value.get("items"), list):
        return [row for row in value["items"] if isinstance(row, dict)]
    for value in data.values():
        if isinstance(value, list) and all(isinstance(row, dict) for row in value):
            return value
    return []


def _normalized_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = {field: _first(raw, aliases) for field, aliases in FIELD_ALIASES.items()}
    row["address"] = _safe_text(row["address"], limit=44)
    row["symbol"] = _safe_text(row["symbol"], limit=24)
    row["name"] = _safe_text(row["name"], limit=80)
    meme = raw.get("meme_info") if isinstance(raw.get("meme_info"), dict) else {}
    row["launchpad"] = _safe_text(meme.get("source"), limit=48)
    row["bonding_curve_progress_pct"] = meme.get("progress_percent")
    row["graduated"] = meme.get("graduated") if isinstance(meme.get("graduated"), bool) else None
    return row


def _merge_candidate(existing: dict[str, Any], observed: dict[str, Any]) -> None:
    for field, value in observed.items():
        if existing.get(field) in (None, "") and value not in (None, ""):
            existing[field] = value


def _numeric(value: Any) -> Decimal | None:
    number = decimal(value)
    if number is None or not number.is_finite():
        return None
    return number


def _percentile(value: Decimal | None, values: list[Decimal], *, positive_only: bool = False) -> Decimal | None:
    if value is None:
        return None
    if positive_only and value <= 0:
        return Decimal(0)
    population = [item for item in values if not positive_only or item > 0]
    if not population:
        return Decimal(0) if positive_only else None
    return Decimal(sum(item <= value for item in population)) / Decimal(len(population))


def _rank_fraction(rank: int | None, count: int, source_available: bool) -> Decimal | None:
    if not source_available:
        return None
    if rank is None:
        return Decimal(0)
    if count <= 1:
        return Decimal(1)
    value = Decimal(1) - (Decimal(rank - 1) / Decimal(count - 1))
    return max(Decimal(0), min(Decimal(1), value))


def _component(value: Decimal | None, weight: Decimal) -> str | None:
    return decimal_string(value * weight, "0.01") if value is not None else None


def _baseline_addresses(baseline: Any) -> set[str] | None:
    if baseline is None:
        return None
    if not isinstance(baseline, dict):
        raise InvalidInput("baseline must be a JSON object")
    source: Any = baseline.get("listed_addresses")
    if source is None:
        source = baseline.get("tokens")
    if source is None and isinstance(baseline.get("answer"), dict):
        source = baseline["answer"].get("tokens")
    if not isinstance(source, list):
        raise InvalidInput("baseline must contain listed_addresses or tokens as an array")
    addresses: set[str] = set()
    for item in source:
        value = item.get("address") if isinstance(item, dict) else item
        if isinstance(value, str) and BASE58_RE.fullmatch(value):
            addresses.add(value)
        else:
            raise InvalidInput("baseline contains an invalid Solana token address")
    return addresses


def _blocked_section(endpoint_id: str, reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "endpoint_id": endpoint_id,
        "returned_count": 0,
        "reason": reason,
        "errors": [],
    }


def run_market_radar(command: CommandSpec, inputs: dict[str, Any], client: V2Client) -> dict[str, Any]:
    """Run a deterministic sweep → gate → score → shortlist flow with Birdeye data."""

    baseline_addresses = _baseline_addresses(inputs.get("baseline"))
    try:
        call_cap = min(command.max_calls, int(inputs.get("call_cap", command.max_calls)))
        output_limit = int(inputs.get("limit", 10))
        score_floor = Decimal(str(inputs.get("score_floor", 60)))
        min_score_coverage = Decimal(str(inputs.get("min_score_coverage", 70)))
        time_from = int(inputs["time_from"])
        time_to = int(inputs["time_to"])
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise InvalidInput("Radar limits, score thresholds and time window must be numeric") from exc
    if call_cap < 1:
        raise InvalidInput("call_cap must be a positive integer")
    if output_limit < 1 or output_limit > MAX_OUTPUT_ROWS:
        raise InvalidInput(f"limit must be between 1 and {MAX_OUTPUT_ROWS}")
    if not score_floor.is_finite() or not Decimal(0) <= score_floor <= Decimal(100):
        raise InvalidInput("score_floor must be between 0 and 100")
    if not min_score_coverage.is_finite() or not Decimal(0) <= min_score_coverage <= Decimal(100):
        raise InvalidInput("min_score_coverage must be between 0 and 100")
    if time_from >= time_to:
        raise InvalidInput("time_from must be earlier than time_to")
    min_market_cap = _numeric(inputs.get("min_market_cap", 500_000))
    min_liquidity = _numeric(inputs.get("min_liquidity", 100_000))
    min_holder = _numeric(inputs.get("min_holder"))
    if min_market_cap is None or min_market_cap < 0 or min_liquidity is None or min_liquidity < 0:
        raise InvalidInput("min_market_cap and min_liquidity must be non-negative numbers")

    fetch_limit = max(1, min(int(command.fetch_limit or 50), 50))
    usage = Usage(call_cap=call_cap)
    sections: dict[str, dict[str, Any]] = {}
    evidence: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    source_rows: dict[str, list[dict[str, Any]]] = {}
    stop_reason: str | None = None

    for source_name, endpoint_id, source_params in SOURCE_PLAN:
        if stop_reason:
            sections[source_name] = _blocked_section(endpoint_id, stop_reason)
            continue
        if usage.calls_attempted >= call_cap:
            stop_reason = "command_call_cap_reached"
            sections[source_name] = _blocked_section(endpoint_id, stop_reason)
            continue
        params = dict(source_params)
        params["limit"] = min(fetch_limit, 20) if endpoint_id == "EP-008" else fetch_limit
        if endpoint_id == "EP-002":
            params.update(
                {
                    "min_market_cap": decimal_string(min_market_cap),
                    "min_liquidity": decimal_string(min_liquidity),
                    "min_recent_listing_time": time_from,
                    "max_recent_listing_time": time_to,
                }
            )
            if min_holder is not None:
                params["min_holder"] = decimal_string(min_holder)
        try:
            response = client.fetch(endpoint_id, usage=usage, params=params)
            data = response.get("envelope", {}).get("data")
            rows = _rows(data, endpoint_id)
            source_rows[source_name] = rows
            status = "complete" if rows else "empty"
            sections[source_name] = {
                "status": status,
                "endpoint_id": endpoint_id,
                "returned_count": len(rows),
                "sort_by": params.get("sort_by"),
                "errors": [],
            }
            evidence.append(
                {
                    "source": source_name,
                    "endpoint_id": endpoint_id,
                    "x402_path": client.endpoint_specs[endpoint_id]["x402_path"],
                    "evaluation_transport": "standard_api_counterpart",
                    "cache_hit": bool(response.get("cache_hit")),
                    "status": "observed",
                }
            )
            if source_name == "volume_24h" and not rows:
                stop_reason = "primary_24h_candidate_feed_empty"
        except IntelligenceError as exc:
            error = exc.as_dict()
            errors.append(error)
            sections[source_name] = {
                "status": "error",
                "endpoint_id": endpoint_id,
                "returned_count": 0,
                "errors": [error],
            }
            evidence.append(
                {
                    "source": source_name,
                    "endpoint_id": endpoint_id,
                    "x402_path": client.endpoint_specs[endpoint_id].get("x402_path"),
                    "evaluation_transport": "standard_api_counterpart",
                    "cache_hit": False,
                    "status": "failed",
                }
            )
            if isinstance(exc, AuthenticationError):
                stop_reason = "authentication_required"
            elif isinstance(exc, RateLimited):
                stop_reason = "upstream_rate_limit_reached"
            elif isinstance(exc, CostCapReached):
                stop_reason = "command_call_cap_reached"

    candidates: dict[str, dict[str, Any]] = {}
    raw_candidate_count = 0
    candidate_sources = ("volume_24h", "volume_1h", "volume_5m")
    for source_name in candidate_sources:
        rows = source_rows.get(source_name, [])
        raw_candidate_count += len(rows)
        for rank, raw in enumerate(rows, start=1):
            observed = _normalized_row(raw)
            address = observed.get("address")
            if not address:
                continue
            candidate = candidates.setdefault(
                address,
                {"address": address, "source_ranks": {}, "source_feeds": []},
            )
            _merge_candidate(candidate, observed)
            candidate["source_ranks"][source_name] = rank
            if source_name not in candidate["source_feeds"]:
                candidate["source_feeds"].append(source_name)

    for source_name in ("birdeye_trending", "smart_money"):
        for rank, raw in enumerate(source_rows.get(source_name, []), start=1):
            observed = _normalized_row(raw)
            address = observed.get("address")
            candidate = candidates.get(address)
            if candidate is None:
                continue
            _merge_candidate(candidate, observed)
            candidate["source_ranks"][source_name] = rank
            if source_name not in candidate["source_feeds"]:
                candidate["source_feeds"].append(source_name)

    rejection_counts: Counter[str] = Counter()
    eligible: list[dict[str, Any]] = []
    for candidate in candidates.values():
        address = candidate.get("address")
        market_cap = _numeric(candidate.get("market_cap_usd"))
        liquidity = _numeric(candidate.get("liquidity_usd"))
        listing_time = _numeric(candidate.get("recent_listing_time"))
        holder_count = _numeric(candidate.get("holder_count"))
        reasons = []
        if not isinstance(address, str) or not BASE58_RE.fullmatch(address):
            reasons.append("invalid_address")
        if market_cap is None:
            reasons.append("missing_market_cap")
        elif market_cap < min_market_cap:
            reasons.append("market_cap_below_floor")
        if liquidity is None:
            reasons.append("missing_liquidity")
        elif liquidity < min_liquidity:
            reasons.append("liquidity_below_floor")
        if listing_time is None:
            reasons.append("unknown_age")
        elif not Decimal(time_from) <= listing_time <= Decimal(time_to):
            reasons.append("outside_age_window")
        if min_holder is not None:
            if holder_count is None:
                reasons.append("missing_holder_count")
            elif holder_count < min_holder:
                reasons.append("holder_count_below_floor")
        if reasons:
            rejection_counts.update(reasons)
            continue
        eligible.append(candidate)

    numeric_populations = {
        field: [number for candidate in eligible if (number := _numeric(candidate.get(field))) is not None]
        for field in ("liquidity_usd", "holder_count", "volume_change_5m_pct", "trade_count_5m")
    }
    source_available = {name: name in source_rows for name, _, _ in SOURCE_PLAN}
    source_counts = {name: len(source_rows.get(name, [])) for name, _, _ in SOURCE_PLAN}
    scored: list[dict[str, Any]] = []
    for candidate in eligible:
        ranks = candidate["source_ranks"]
        fractions = {
            "volume_24h_rank": _rank_fraction(ranks.get("volume_24h"), source_counts["volume_24h"], source_available["volume_24h"]),
            "volume_1h_rank": _rank_fraction(ranks.get("volume_1h"), source_counts["volume_1h"], source_available["volume_1h"]),
            "volume_5m_rank": _rank_fraction(ranks.get("volume_5m"), source_counts["volume_5m"], source_available["volume_5m"]),
            "liquidity_depth": _percentile(_numeric(candidate.get("liquidity_usd")), numeric_populations["liquidity_usd"]),
            "holder_depth": _percentile(_numeric(candidate.get("holder_count")), numeric_populations["holder_count"]),
            "volume_acceleration_5m": _percentile(_numeric(candidate.get("volume_change_5m_pct")), numeric_populations["volume_change_5m_pct"], positive_only=True),
            "trade_participation_5m": _percentile(_numeric(candidate.get("trade_count_5m")), numeric_populations["trade_count_5m"]),
            "smart_money_confirmation": _rank_fraction(ranks.get("smart_money"), source_counts["smart_money"], source_available["smart_money"]),
            "birdeye_trending_confirmation": _rank_fraction(ranks.get("birdeye_trending"), source_counts["birdeye_trending"], source_available["birdeye_trending"]),
        }
        components = {name: _component(value, SCORE_WEIGHTS[name]) for name, value in fractions.items()}
        observed_weight = sum(SCORE_WEIGHTS[name] for name, value in fractions.items() if value is not None)
        score = sum((value or Decimal(0)) * SCORE_WEIGHTS[name] for name, value in fractions.items())
        coverage = observed_weight
        missing_fields = [
            field
            for field in ("holder_count", "volume_change_5m_pct", "trade_count_5m")
            if _numeric(candidate.get(field)) is None
        ]
        scored.append(
            {
                "address": candidate["address"],
                "symbol": candidate.get("symbol"),
                "name": candidate.get("name"),
                "score": decimal_string(score, "0.01"),
                "score_coverage_pct": decimal_string(coverage, "0.01"),
                "source_feeds": sorted(candidate["source_feeds"]),
                "source_ranks": dict(sorted(ranks.items())),
                "score_components": components,
                "market_cap_usd": decimal_string(candidate.get("market_cap_usd")),
                "liquidity_usd": decimal_string(candidate.get("liquidity_usd")),
                "holder_count": decimal_string(candidate.get("holder_count")),
                "volume_24h_usd": decimal_string(candidate.get("volume_24h_usd")),
                "volume_1h_usd": decimal_string(candidate.get("volume_1h_usd")),
                "volume_5m_usd": decimal_string(candidate.get("volume_5m_usd")),
                "volume_change_5m_pct": decimal_string(candidate.get("volume_change_5m_pct")),
                "trade_count_5m": decimal_string(candidate.get("trade_count_5m")),
                "recent_listing_time": decimal_string(candidate.get("recent_listing_time")),
                "launchpad": candidate.get("launchpad"),
                "bonding_curve_progress_pct": decimal_string(candidate.get("bonding_curve_progress_pct")),
                "graduated": candidate.get("graduated"),
                "smart_trader_count": decimal_string(candidate.get("smart_trader_count")),
                "net_flow_usd": decimal_string(candidate.get("net_flow_usd")),
                "missing_fields": missing_fields,
                "security_check": "not_run",
            }
        )

    scored.sort(
        key=lambda item: (
            -float(item["score"] or 0),
            -float(item["liquidity_usd"] or 0),
            item["address"],
        )
    )
    passed = [
        item
        for item in scored
        if Decimal(item["score"] or "0") >= score_floor
        and Decimal(item["score_coverage_pct"] or "0") >= min_score_coverage
    ]
    listed = passed[:output_limit]
    listed_addresses = {item["address"] for item in listed}
    passed_addresses = {item["address"] for item in passed}
    for rank, item in enumerate(listed, start=1):
        item["rank"] = rank
    near_misses = [item for item in scored if item["address"] not in listed_addresses][:MAX_NEAR_MISSES]
    for item in near_misses:
        item["miss_reason"] = (
            "outside_result_limit"
            if item["address"] in passed_addresses
            else "score_coverage_below_floor"
            if Decimal(item["score_coverage_pct"] or "0") < min_score_coverage
            else "score_below_floor"
        )

    current_addresses = {item["address"] for item in listed}
    changes = None
    if baseline_addresses is not None:
        changes = {
            "new": sorted(current_addresses - baseline_addresses),
            "stayed": sorted(current_addresses & baseline_addresses),
            "dropped": sorted(baseline_addresses - current_addresses),
        }

    successful_sources = sum(section["status"] in {"complete", "empty"} for section in sections.values())
    failed_sources = sum(section["status"] == "error" for section in sections.values())
    blocked_sources = sum(section["status"] == "blocked" for section in sections.values())
    policy_skips_only = blocked_sources and all(
        section.get("reason") == "primary_24h_candidate_feed_empty"
        for section in sections.values()
        if section["status"] == "blocked"
    )
    status = (
        "error"
        if not successful_sources
        else "partial"
        if failed_sources or (blocked_sources and not policy_skips_only)
        else "complete"
    )
    answer = {
        "contract": "curated-market-radar-v1",
        "methodology_version": METHODOLOGY_VERSION,
        "policy": {
            "chain": "solana",
            "time_from": time_from,
            "time_to": time_to,
            "min_market_cap_usd": decimal_string(min_market_cap),
            "min_liquidity_usd": decimal_string(min_liquidity),
            "min_holder_count": decimal_string(min_holder),
            "score_floor": decimal_string(score_floor),
            "min_score_coverage_pct": decimal_string(min_score_coverage),
            "max_results": output_limit,
            "fetch_limit_per_source": fetch_limit,
            "no_padding": True,
            "security_gate": "not_available_in_bounded_sweep",
        },
        "score_weights": {name: decimal_string(value) for name, value in SCORE_WEIGHTS.items()},
        "funnel": {
            "raw_candidates": raw_candidate_count,
            "unique_candidates": len(candidates),
            "eligible_after_hard_gates": len(eligible),
            "rejected_by_hard_gates": len(candidates) - len(eligible),
            "passed_score_floor": len(passed),
            "listed": len(listed),
            "near_misses_shown": len(near_misses),
            "rejection_counts": dict(sorted(rejection_counts.items())),
        },
        "tokens": listed,
        "near_misses": near_misses,
        "empty_sources": sorted(name for name, section in sections.items() if section["status"] == "empty"),
        "changes": changes,
    }
    limitations = [
        "This is a deterministic research shortlist, not a buy list or future-return prediction.",
        "The bounded sweep does not call token-security endpoints per candidate; every listed token keeps security_check=not_run and should go through token due diligence before deeper use.",
        "Feed absence means absent from the bounded returned cohort, not absent from the entire Solana market.",
    ]
    if failed_sources or (blocked_sources and not policy_skips_only):
        limitations.append("One or more sources failed or were skipped; scores preserve missing components and the result is partial.")
    if not listed:
        limitations.append("No candidate cleared both the score and score-coverage floors; the list was not padded.")
    return {
        "schema_version": "3.0.0",
        "observed_at": utc_now(),
        "status": status,
        "answer": answer,
        "sections": sections,
        "evidence": evidence,
        "cost": usage.as_dict(),
        "limitations": limitations,
        "errors": errors,
    }
