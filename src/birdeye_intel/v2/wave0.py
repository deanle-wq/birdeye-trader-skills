"""Deterministic typed answer contracts for the frozen V2 Wave 0 skills."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from importlib.resources import files
import re
from typing import Any, Callable

from ..core import decimal, decimal_string
from .catalog import SkillSpec


ANSWER_SCHEMA_VERSION = "2.1.0"
METHODOLOGY_VERSION = "wave0-x402-1.0.0"
INTEGER_RE = re.compile(r"^-?\d+$")
FIELD_STATES = {"observed", "zero", "empty", "missing", "null", "invalid"}
RESOLUTION_SECONDS = {
    "1s": 1,
    "15s": 15,
    "30s": 30,
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1H": 3600,
    "2H": 7200,
    "4H": 14_400,
    "6H": 21_600,
    "8H": 28_800,
    "12H": 43_200,
    "1D": 86_400,
    "3D": 259_200,
    "1W": 604_800,
}


def load_wave0_manifest() -> dict[str, Any]:
    document = json.loads(files(__package__).joinpath("wave0_manifest.json").read_text())
    if document.get("answer_schema_version") != ANSWER_SCHEMA_VERSION:
        raise ValueError("Unsupported Wave 0 answer schema")
    if document.get("skill_count") != len(document.get("skills", [])):
        raise ValueError("Wave 0 skill count mismatch")
    return document


WAVE0_MANIFEST = load_wave0_manifest()
WAVE0_BY_SLUG = {item["slug"]: item for item in WAVE0_MANIFEST["skills"]}
WAVE0_SLUGS = frozenset(WAVE0_BY_SLUG)


def _path(data: Any, dotted: str) -> tuple[bool, Any]:
    value = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _first_path(data: Any, *paths: str) -> tuple[bool, Any, str]:
    for path in paths:
        present, value = _path(data, path)
        if present:
            return True, value, path
    return False, None, paths[0]


def _as_decimal_string(value: Any) -> str | None:
    return decimal_string(value)


def _as_integer_string(value: Any) -> str | None:
    number = decimal(value)
    if number is None or not number.is_finite() or number != number.to_integral_value():
        return None
    return decimal_string(number)


def _as_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _as_object(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _quality(present: bool, raw: Any, normalized: Any) -> str:
    if not present:
        return "missing"
    if raw is None:
        return "null"
    if raw in ([], {}, ""):
        return "empty"
    if normalized is None:
        return "invalid"
    if normalized in (0, "0"):
        return "zero"
    return "observed"


def _entity(spec: SkillSpec, inputs: dict[str, Any]) -> dict[str, str]:
    contract = WAVE0_BY_SLUG[spec.slug]
    entity_type = contract["entity_type"]
    if entity_type == "token":
        address = str(inputs.get("token_address") or inputs.get("token") or "")
    elif entity_type == "wallet":
        address = str(inputs.get("wallet_address") or inputs.get("wallet") or "")
    else:
        address = "solana"
    return {"type": entity_type, "address": address}


def _base(spec: SkillSpec, inputs: dict[str, Any], observed_at: str) -> dict[str, Any]:
    contract = WAVE0_BY_SLUG[spec.slug]
    return {
        "schema_version": ANSWER_SCHEMA_VERSION,
        "methodology_version": METHODOLOGY_VERSION,
        "skill_id": spec.skill_id,
        "skill": spec.slug,
        "question": spec.question,
        "chain": "solana",
        "entity": _entity(spec, inputs),
        "observed_at": observed_at,
        "status": "insufficient_data",
        "fields": {},
        "field_states": {},
        "evidence": [],
        "coverage": {},
        "pagination": {"model": contract["pagination"], "complete": None},
        "freshness": {"provider_timestamp": None, "age_seconds": None, "classification": "not_available"},
        "limitations": [],
        "errors": [],
        "production_accepted": False,
    }


def _put(
    answer: dict[str, Any],
    field: str,
    raw: Any,
    normalized: Any,
    *,
    endpoint_id: str,
    source_path: str,
    present: bool = True,
    quality: str | None = None,
) -> None:
    state = quality or _quality(present, raw, normalized)
    answer["fields"][field] = normalized
    answer["field_states"][field] = state
    answer["evidence"].append(
        {
            "field": field,
            "endpoint_id": endpoint_id,
            "source_path": source_path,
            "quality": state,
        }
    )


def _simple(
    answer: dict[str, Any],
    data: Any,
    endpoint_id: str,
    mapping: dict[str, tuple[str, Callable[[Any], Any]]],
) -> None:
    for field, (source_path, converter) in mapping.items():
        present, raw = _path(data, source_path)
        _put(
            answer,
            field,
            raw,
            converter(raw),
            endpoint_id=endpoint_id,
            source_path=f"data.{source_path}",
            present=present,
        )


def _set_freshness(answer: dict[str, Any], timestamp: Any) -> None:
    if timestamp is None:
        return
    provider_unix: int | None = None
    provider_value: str | None = None
    number = _as_integer_string(timestamp)
    if number is not None:
        provider_unix = int(number)
        provider_value = number
    elif isinstance(timestamp, str):
        provider_value = timestamp
        try:
            normalized = timestamp.replace("Z", "+00:00")
            fractional = re.fullmatch(
                r"(?P<prefix>.+\.)(?P<fraction>\d+)(?P<timezone>[+-]\d{2}:\d{2})",
                normalized,
            )
            if fractional and len(fractional.group("fraction")) > 6:
                normalized = (
                    f"{fractional.group('prefix')}"
                    f"{fractional.group('fraction')[:6]}"
                    f"{fractional.group('timezone')}"
                )
            provider_unix = int(datetime.fromisoformat(normalized).timestamp())
        except ValueError:
            provider_unix = None
    age: int | None = None
    if provider_unix is not None:
        try:
            observed = datetime.fromisoformat(answer["observed_at"].replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            age = int(observed.timestamp()) - provider_unix
        except ValueError:
            age = None
    answer["freshness"] = {
        "provider_timestamp": provider_value,
        "age_seconds": age,
        "classification": "timestamp_provided" if provider_unix is not None else "timestamp_unparseable",
    }


def _normalize_identity(answer: dict[str, Any], facts: dict[str, Any]) -> None:
    _simple(
        answer,
        facts.get("EP-009"),
        "EP-009",
        {
            "canonical_address": ("address", _as_string),
            "decimals": ("decimals", _as_integer_string),
            "name": ("name", _as_string),
            "symbol": ("symbol", _as_string),
        },
    )


def _normalize_metadata(answer: dict[str, Any], facts: dict[str, Any]) -> None:
    _simple(
        answer,
        facts.get("EP-009"),
        "EP-009",
        {
            "canonical_address": ("address", _as_string),
            "decimals": ("decimals", _as_integer_string),
            "extensions": ("extensions", _as_object),
            "logo_uri": ("logo_uri", _as_string),
            "name": ("name", _as_string),
            "symbol": ("symbol", _as_string),
        },
    )


def _normalize_valuation(answer: dict[str, Any], facts: dict[str, Any]) -> None:
    _simple(
        answer,
        facts.get("EP-011"),
        "EP-011",
        {
            "canonical_address": ("address", _as_string),
            "circulating_supply": ("circulating_supply", _as_decimal_string),
            "fdv_usd": ("fdv", _as_decimal_string),
            "holder_count": ("holder", _as_integer_string),
            "liquidity_usd": ("liquidity", _as_decimal_string),
            "market_cap_usd": ("market_cap", _as_decimal_string),
            "price_usd": ("price", _as_decimal_string),
            "total_supply": ("total_supply", _as_decimal_string),
        },
    )


def _normalize_liquidity(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    _simple(
        answer,
        facts.get("EP-011"),
        "EP-011",
        {
            "token_address": ("address", _as_string),
            "liquidity_usd": ("liquidity", _as_decimal_string),
            "price_usd": ("price", _as_decimal_string),
        },
    )
    answer["limitations"].append("This is indexed token liquidity context, not an executable route or slippage quote.")


def _normalize_price(answer: dict[str, Any], facts: dict[str, Any]) -> None:
    data = facts.get("EP-020")
    _simple(
        answer,
        data,
        "EP-020",
        {
            "is_scaled_ui_token": ("isScaledUiToken", _as_boolean),
            "price_change_24h_pct": ("priceChange24h", _as_decimal_string),
            "price_native": ("priceInNative", _as_decimal_string),
            "price_usd": ("value", _as_decimal_string),
            "provider_update_human": ("updateHumanTime", _as_string),
            "provider_update_unix": ("updateUnixTime", _as_integer_string),
        },
    )
    _, timestamp = _path(data, "updateUnixTime")
    _set_freshness(answer, timestamp)


def _normalize_market_activity(answer: dict[str, Any], facts: dict[str, Any]) -> None:
    data = facts.get("EP-013")
    mapping = {
        "buy_count_1h": ("buy_1h", _as_integer_string),
        "buy_count_24h": ("buy_24h", _as_integer_string),
        "last_trade_unix": ("last_trade_unix_time", _as_integer_string),
        "price_usd": ("price", _as_decimal_string),
        "sell_count_1h": ("sell_1h", _as_integer_string),
        "sell_count_24h": ("sell_24h", _as_integer_string),
        "trade_count_1h": ("trade_1h", _as_integer_string),
        "trade_count_24h": ("trade_24h", _as_integer_string),
        "unique_wallet_count_1h": ("unique_wallet_1h", _as_integer_string),
        "unique_wallet_count_24h": ("unique_wallet_24h", _as_integer_string),
        "volume_1h_usd": ("volume_1h_usd", _as_decimal_string),
    }
    _simple(answer, data, "EP-013", mapping)
    present, raw, path = _first_path(data, "volume_24h_usd", "volume_24h")
    _put(
        answer,
        "volume_24h_usd",
        raw,
        _as_decimal_string(raw),
        endpoint_id="EP-013",
        source_path=f"data.{path}",
        present=present,
    )
    _, timestamp = _path(data, "last_trade_unix_time")
    _set_freshness(answer, timestamp)


def _token_side(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "address": _as_string(value.get("address")),
        "symbol": _as_string(value.get("symbol")),
        "decimals": _as_integer_string(value.get("decimals")),
    }


def _normalize_markets(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-019")
    present, raw_items = _path(data, "items")
    items = raw_items if isinstance(raw_items, list) else []
    markets = []
    for item in items:
        if not isinstance(item, dict):
            continue
        markets.append(
            {
                "pool_address": _as_string(item.get("address")),
                "name": _as_string(item.get("name")),
                "dex": _as_string(item.get("source")),
                "base_token": _token_side(item.get("base")),
                "quote_token": _token_side(item.get("quote")),
                "liquidity_usd": _as_decimal_string(item.get("liquidity")),
                "price_usd": _as_decimal_string(item.get("price")),
                "volume_24h_usd": _as_decimal_string(item.get("volume24h")),
                "trade_count_24h": _as_integer_string(item.get("trade24h")),
                "unique_wallet_count_24h": _as_integer_string(item.get("uniqueWallet24h")),
                "created_at": _as_string(item.get("createdAt")),
            }
        )
    source_quality = _quality(present, raw_items, markets)
    _put(answer, "markets", raw_items, markets, endpoint_id="EP-019", source_path="data.items", present=present, quality=source_quality)
    _put(answer, "ordering", "liquidity desc", "liquidity_desc", endpoint_id="EP-019", source_path="request.sort_by/request.sort_type")
    _put(answer, "returned_count", len(markets), len(markets), endpoint_id="EP-019", source_path="derived:data.items.length")
    total_present, total_raw = _path(data, "total")
    total = _as_integer_string(total_raw)
    _put(answer, "total", total_raw, total, endpoint_id="EP-019", source_path="data.total", present=total_present)
    offset = int(inputs.get("offset", 0))
    limit = int(inputs.get("limit", 20))
    total_int = int(total) if total is not None else None
    has_next = total_int is not None and offset + len(markets) < total_int
    answer["pagination"] = {
        "model": "offset-limit",
        "offset": offset,
        "limit": limit,
        "returned": len(markets),
        "total": total,
        "has_next": has_next if total_int is not None else None,
        "complete": not has_next if total_int is not None else len(markets) < limit,
    }


def _candle_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item:
            return item[key]
    return None


def _normalize_kline(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-023")
    present, raw_items = _path(data, "items")
    items = raw_items if isinstance(raw_items, list) else []
    time_from = int(inputs["time_from"]) if inputs.get("time_from") is not None else None
    time_to = int(inputs["time_to"]) if inputs.get("time_to") is not None else None
    candles = []
    skipped = 0
    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        timestamp = _as_integer_string(_candle_value(item, "unix_time", "time", "timestamp"))
        if timestamp is None:
            skipped += 1
            continue
        timestamp_int = int(timestamp)
        if time_from is not None and timestamp_int < time_from:
            continue
        if time_to is not None and timestamp_int >= time_to:
            continue
        candles.append(
            {
                "unix_time": timestamp,
                "open": _as_decimal_string(_candle_value(item, "o", "open")),
                "high": _as_decimal_string(_candle_value(item, "h", "high")),
                "low": _as_decimal_string(_candle_value(item, "l", "low")),
                "close": _as_decimal_string(_candle_value(item, "c", "close")),
                "volume": _as_decimal_string(_candle_value(item, "v", "volume")),
            }
        )
    candles.sort(key=lambda item: int(item["unix_time"]))
    source_quality = _quality(present, raw_items, candles)
    _put(answer, "candles", raw_items, candles, endpoint_id="EP-023", source_path="data.items", present=present, quality=source_quality)
    resolution = str(inputs.get("resolution", "1H"))
    _put(answer, "resolution", resolution, resolution, endpoint_id="EP-023", source_path="request.type")
    _put(answer, "time_from", time_from, _as_integer_string(time_from), endpoint_id="EP-023", source_path="request.time_from", present=time_from is not None)
    _put(answer, "time_to", time_to, _as_integer_string(time_to), endpoint_id="EP-023", source_path="request.time_to", present=time_to is not None)
    _put(answer, "returned_count", len(candles), len(candles), endpoint_id="EP-023", source_path="derived:filtered_items.length")
    seconds = RESOLUTION_SECONDS.get(resolution)
    slots = max(0, (time_to - time_from) // seconds) if seconds and time_from is not None and time_to is not None else None
    gaps = max(0, slots - len(candles)) if slots is not None else None
    _put(answer, "requested_slot_estimate", slots, slots, endpoint_id="EP-023", source_path="derived:window/resolution", present=slots is not None)
    _put(answer, "gap_count_estimate", gaps, gaps, endpoint_id="EP-023", source_path="derived:requested_slots-returned", present=gaps is not None)
    answer["pagination"] = {"model": "not-applicable-provider-cap-5000", "record_cap": 5000, "complete": slots is not None and gaps == 0}
    if skipped:
        answer["limitations"].append(f"Skipped {skipped} malformed candle records without a usable timestamp.")
    if gaps:
        answer["limitations"].append("Candle gaps are preserved; missing slots are not zero-filled.")
    if candles:
        _set_freshness(answer, candles[-1]["unix_time"])


def _normalize_holdings(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-049")
    present, raw_items = _path(data, "items")
    items = raw_items if isinstance(raw_items, list) else []
    holdings = []
    for item in items:
        if not isinstance(item, dict):
            continue
        holdings.append(
            {
                "token_address": _as_string(item.get("address")),
                "symbol": _as_string(item.get("symbol")),
                "name": _as_string(item.get("name")),
                "decimals": _as_integer_string(item.get("decimals")),
                "amount": _as_decimal_string(item.get("amount")),
                "balance_raw": _as_integer_string(item.get("balance")),
                "price_usd": _as_decimal_string(item.get("price")),
                "value_usd": _as_decimal_string(item.get("value")),
                "network": _as_string(item.get("network")),
            }
        )
    source_quality = _quality(present, raw_items, holdings)
    mapping = {
        "currency": ("currency", _as_string),
        "current_timestamp": ("current_timestamp", _as_string),
        "total_value_usd": ("total_value", _as_decimal_string),
        "wallet_address": ("wallet", _as_string),
    }
    _simple(answer, data, "EP-049", mapping)
    _put(answer, "holdings", raw_items, holdings, endpoint_id="EP-049", source_path="data.items", present=present, quality=source_quality)
    _put(answer, "returned_count", len(holdings), len(holdings), endpoint_id="EP-049", source_path="derived:data.items.length")
    offset = int(inputs.get("offset", 0))
    limit = int(inputs.get("limit", 100))
    total_present, total_raw = _first_path(data, "total", "total_count")[:2]
    total = _as_integer_string(total_raw)
    total_int = int(total) if total is not None else None
    has_next = total_int is not None and offset + len(holdings) < total_int
    answer["pagination"] = {
        "model": "offset-limit",
        "offset": offset,
        "limit": limit,
        "returned": len(holdings),
        "total": total,
        "has_next": has_next if total_int is not None else None,
        "complete": not has_next if total_int is not None else len(holdings) < limit,
    }
    _, timestamp = _path(data, "current_timestamp")
    _set_freshness(answer, timestamp)
    answer["limitations"].append("Portfolio coverage depends on Birdeye indexing and supported asset classes.")


def _normalize_numeric_object(
    value: Any,
    fields: dict[str, Callable[[Any], Any]],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {key: converter(value.get(key)) for key, converter in fields.items()}


def _normalize_pnl(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-053")
    present, summary = _path(data, "summary")
    counts_present, counts_raw = _path(summary, "counts")
    cashflow_present, cashflow_raw = _path(summary, "cashflow_usd")
    pnl_present, pnl_raw = _path(summary, "pnl")
    unique_present, unique_raw = _path(summary, "unique_tokens")
    counts = _normalize_numeric_object(
        counts_raw,
        {
            "total_buy": _as_integer_string,
            "total_loss": _as_integer_string,
            "total_sell": _as_integer_string,
            "total_trade": _as_integer_string,
            "total_win": _as_integer_string,
            "win_rate": _as_decimal_string,
        },
    )
    cashflow = _normalize_numeric_object(
        cashflow_raw,
        {
            "current_value": _as_decimal_string,
            "total_invested": _as_decimal_string,
            "total_sold": _as_decimal_string,
        },
    )
    pnl = _normalize_numeric_object(
        pnl_raw,
        {
            "avg_profit_per_trade_usd": _as_decimal_string,
            "realized_profit_percent": _as_decimal_string,
            "realized_profit_usd": _as_decimal_string,
            "total_usd": _as_decimal_string,
            "unrealized_usd": _as_decimal_string,
        },
    )
    duration = str(inputs.get("duration", "all"))
    scope = str(inputs.get("position_scope", "duration_only"))
    _put(answer, "duration", duration, duration, endpoint_id="EP-053", source_path="request.duration")
    _put(answer, "position_scope", scope, scope, endpoint_id="EP-053", source_path="request.position_scope")
    _put(answer, "unique_token_count", unique_raw, _as_integer_string(unique_raw), endpoint_id="EP-053", source_path="data.summary.unique_tokens", present=present and unique_present)
    _put(answer, "counts", counts_raw, counts, endpoint_id="EP-053", source_path="data.summary.counts", present=present and counts_present)
    _put(answer, "cashflow", cashflow_raw, cashflow, endpoint_id="EP-053", source_path="data.summary.cashflow_usd", present=present and cashflow_present)
    _put(answer, "pnl", pnl_raw, pnl, endpoint_id="EP-053", source_path="data.summary.pnl", present=present and pnl_present)
    answer["limitations"].append("Reported wallet PnL may be incomplete where protocol trade history is not fully backfilled.")


def _trade_side(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "address": _as_string(value.get("address")),
        "symbol": _as_string(value.get("symbol")),
        "decimals": _as_integer_string(value.get("decimals")),
        "amount": _as_decimal_string(value.get("ui_change_amount", value.get("ui_amount"))),
        "price": _as_decimal_string(value.get("price")),
        "type_swap": _as_string(value.get("type_swap")),
    }


def _normalize_wallet_trades(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-048")
    present, raw_items = _path(data, "items")
    items = raw_items if isinstance(raw_items, list) else []
    time_from = int(inputs["time_from"]) if inputs.get("time_from") is not None else None
    time_to = int(inputs["time_to"]) if inputs.get("time_to") is not None else None
    trades = []
    filtered_after = 0
    malformed = 0
    for item in items:
        if not isinstance(item, dict):
            malformed += 1
            continue
        timestamp = _as_integer_string(item.get("block_unix_time"))
        if timestamp is None:
            malformed += 1
            continue
        timestamp_int = int(timestamp)
        if time_from is not None and timestamp_int < time_from:
            continue
        if time_to is not None and timestamp_int >= time_to:
            filtered_after += 1
            continue
        tx_hash = _as_string(item.get("tx_hash"))
        ins_index = _as_integer_string(item.get("ins_index"))
        inner = _as_integer_string(item.get("inner_ins_index"))
        event_id = f"{tx_hash or 'unknown'}:{ins_index or 'na'}:{inner or 'na'}"
        trades.append(
            {
                "event_id": event_id,
                "tx_hash": tx_hash,
                "block_number": _as_integer_string(item.get("block_number")),
                "block_unix_time": timestamp,
                "owner": _as_string(item.get("owner")),
                "source": _as_string(item.get("source")),
                "tx_type": _as_string(item.get("tx_type")),
                "volume": _as_decimal_string(item.get("volume")),
                "volume_usd": _as_decimal_string(item.get("volume_usd")),
                "base": _trade_side(item.get("base")),
                "quote": _trade_side(item.get("quote")),
            }
        )
    trades.sort(key=lambda item: (-int(item["block_unix_time"]), item["event_id"]))
    source_quality = _quality(present, raw_items, trades)
    _put(answer, "trades", raw_items, trades, endpoint_id="EP-048", source_path="data.items", present=present, quality=source_quality)
    _put(answer, "returned_count", len(trades), len(trades), endpoint_id="EP-048", source_path="derived:closed_window_items.length")
    _put(answer, "time_from", time_from, _as_integer_string(time_from), endpoint_id="EP-048", source_path="request.after_time", present=time_from is not None)
    _put(answer, "time_to", time_to, _as_integer_string(time_to), endpoint_id="EP-048", source_path="client_filter:block_unix_time<time_to", present=time_to is not None)
    _put(answer, "filtered_out_after_time_to", filtered_after, filtered_after, endpoint_id="EP-048", source_path="derived:filtered_after_time_to")
    has_next_present, has_next_raw = _path(data, "has_next")
    has_next = _as_boolean(has_next_raw)
    complete = has_next is False
    _put(answer, "closed_window_complete", complete, complete, endpoint_id="EP-048", source_path="derived:provider_has_next_and_client_filter")
    answer["pagination"] = {
        "model": "offset-limit-one-sided-time-seek",
        "offset": int(inputs.get("offset", 0)),
        "limit": int(inputs.get("limit", 100)),
        "returned_before_filter": len(items),
        "returned_after_filter": len(trades),
        "has_next": has_next if has_next_present else None,
        "complete": complete,
    }
    if malformed:
        answer["limitations"].append(f"Skipped {malformed} malformed trade records without a usable timestamp.")
    if not complete:
        answer["limitations"].append("Closed-window completeness is conditional because EP-048 uses one-sided time seek and may require additional pages.")
    answer["limitations"].append("Multiple indexed legs sharing a transaction hash are preserved as separate events.")
    if trades:
        _set_freshness(answer, trades[0]["block_unix_time"])


def _normalize_index(answer: dict[str, Any], facts: dict[str, Any]) -> None:
    _simple(
        answer,
        facts.get("EP-045"),
        "EP-045",
        {"latest_indexed_block": ("block_number", _as_integer_string)},
    )
    answer["limitations"].append("Latest indexed block alone does not establish wall-clock lag without a comparable chain timestamp.")


NORMALIZERS: dict[str, Callable[..., None]] = {
    "token-identity-resolver": _normalize_identity,
    "token-metadata": _normalize_metadata,
    "token-valuation-snapshot": _normalize_valuation,
    "token-liquidity-snapshot": _normalize_liquidity,
    "current-token-price": _normalize_price,
    "token-market-activity": _normalize_market_activity,
    "token-markets-and-pools": _normalize_markets,
    "token-kline-data": _normalize_kline,
    "wallet-current-holdings": _normalize_holdings,
    "wallet-pnl-stats": _normalize_pnl,
    "wallet-trade-history": _normalize_wallet_trades,
    "index-freshness": _normalize_index,
}


def _finish(
    answer: dict[str, Any],
    contract: dict[str, Any],
    errors: list[dict[str, Any]],
    facts: dict[str, Any],
) -> None:
    required = contract["required_fields"]
    available_states = {"observed", "zero", "empty"}
    available = sum(answer["field_states"].get(field) in available_states for field in required)
    missing = [field for field in required if answer["field_states"].get(field) == "missing"]
    null = [field for field in required if answer["field_states"].get(field) == "null"]
    invalid = [field for field in required if answer["field_states"].get(field) == "invalid"]
    empty = [field for field in required if answer["field_states"].get(field) == "empty"]
    answer["coverage"] = {
        "required_fields_available": available,
        "required_fields_total": len(required),
        "missing_fields": missing,
        "null_fields": null,
        "invalid_fields": invalid,
        "empty_fields": empty,
    }
    endpoint_observed = any(endpoint_id in facts for endpoint_id in contract["endpoint_ids"])
    if errors and not endpoint_observed:
        answer["status"] = "error"
    elif available == 0:
        answer["status"] = "insufficient_data"
    elif available < len(required):
        answer["status"] = "partial"
    elif empty:
        answer["status"] = "empty"
    else:
        answer["status"] = "complete"
    if answer["status"] in {"complete", "empty"} and answer["pagination"].get("complete") is False:
        answer["status"] = "partial"
        answer["limitations"].append(
            "The returned page or requested time window is not complete; follow pagination before treating this answer as exhaustive."
        )
    answer["errors"] = list(errors)


def normalize_wave0_answer(
    spec: SkillSpec,
    inputs: dict[str, Any],
    facts: dict[str, Any],
    *,
    observed_at: str,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if spec.slug not in WAVE0_BY_SLUG:
        return None
    answer = _base(spec, inputs, observed_at)
    normalizer = NORMALIZERS[spec.slug]
    if spec.slug in {
        "token-liquidity-snapshot",
        "token-markets-and-pools",
        "token-kline-data",
        "wallet-current-holdings",
        "wallet-pnl-stats",
        "wallet-trade-history",
    }:
        normalizer(answer, facts, inputs)
    else:
        normalizer(answer, facts)
    _finish(answer, WAVE0_BY_SLUG[spec.slug], list(errors or []), facts)
    validation_errors = validate_wave0_answer(answer)
    if validation_errors:
        raise ValueError(f"Wave 0 answer contract violation for {spec.slug}: {'; '.join(validation_errors)}")
    return answer


def _type_valid(value: Any, type_name: str) -> bool:
    nullable = type_name.endswith("|null")
    base = type_name[:-5] if nullable else type_name
    if value is None:
        return nullable
    if base == "string":
        return isinstance(value, str)
    if base == "integer-string":
        return isinstance(value, str) and bool(INTEGER_RE.fullmatch(value))
    if base == "decimal-string":
        number = decimal(value)
        return isinstance(value, str) and number is not None and number.is_finite()
    if base == "boolean":
        return isinstance(value, bool)
    if base == "object":
        return isinstance(value, dict)
    if base.startswith("array[") and base.endswith("]"):
        item_type = base[6:-1]
        return isinstance(value, list) and all(_type_valid(item, item_type) for item in value)
    if base == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    model = WAVE0_MANIFEST.get("models", {}).get(base)
    if isinstance(model, dict):
        return (
            isinstance(value, dict)
            and set(value) == set(model)
            and all(_type_valid(value[field], field_type) for field, field_type in model.items())
        )
    return False


def validate_wave0_answer(answer: Any) -> list[str]:
    if not isinstance(answer, dict):
        return ["answer must be an object"]
    slug = answer.get("skill")
    contract = WAVE0_BY_SLUG.get(slug)
    if contract is None:
        return ["skill is not in the frozen Wave 0 manifest"]
    errors: list[str] = []
    if answer.get("schema_version") != ANSWER_SCHEMA_VERSION:
        errors.append("invalid schema_version")
    if answer.get("methodology_version") != METHODOLOGY_VERSION:
        errors.append("invalid methodology_version")
    if answer.get("skill_id") != contract["skill_id"]:
        errors.append("skill_id does not match manifest")
    if answer.get("production_accepted") is not False:
        errors.append("Wave 0 answer must not claim production acceptance")
    if answer.get("chain") != "solana":
        errors.append("chain must be solana")
    entity = answer.get("entity")
    if not isinstance(entity, dict) or entity.get("type") != contract["entity_type"] or not isinstance(entity.get("address"), str):
        errors.append("entity does not match manifest")
    if not isinstance(answer.get("observed_at"), str):
        errors.append("observed_at must be a string")
    fields = answer.get("fields")
    if not isinstance(fields, dict):
        errors.append("fields must be an object")
        return errors
    expected = set(contract["field_types"])
    if set(fields) != expected:
        errors.append("field set does not match manifest")
    for field, type_name in contract["field_types"].items():
        if field in fields and not _type_valid(fields[field], type_name):
            errors.append(f"{field} must be {type_name}")
    if answer.get("status") not in {"complete", "partial", "empty", "insufficient_data", "error"}:
        errors.append("invalid answer status")
    evidence = answer.get("evidence")
    if (
        not isinstance(evidence, list)
        or len(evidence) != len(expected)
        or {item.get("field") for item in evidence if isinstance(item, dict)} != expected
    ):
        errors.append("evidence must cover every contract field")
    else:
        for item in evidence:
            if (
                not isinstance(item, dict)
                or item.get("endpoint_id") not in contract["endpoint_ids"]
                or not isinstance(item.get("source_path"), str)
                or item.get("quality") not in FIELD_STATES
            ):
                errors.append("evidence contains an invalid provenance record")
                break
    states = answer.get("field_states")
    if (
        not isinstance(states, dict)
        or set(states) != expected
        or any(value not in FIELD_STATES for value in states.values())
    ):
        errors.append("field_states must classify every contract field")
    elif isinstance(evidence, list) and len(evidence) == len(expected):
        evidence_states = {
            item.get("field"): item.get("quality")
            for item in evidence
            if isinstance(item, dict)
        }
        if any(evidence_states.get(field) != state for field, state in states.items()):
            errors.append("field_states and evidence quality must agree")
    if not isinstance(answer.get("coverage"), dict):
        errors.append("coverage must be an object")
    if not isinstance(answer.get("pagination"), dict):
        errors.append("pagination must be an object")
    if not isinstance(answer.get("freshness"), dict):
        errors.append("freshness must be an object")
    if not isinstance(answer.get("limitations"), list) or not isinstance(answer.get("errors"), list):
        errors.append("limitations and errors must be arrays")
    return errors
