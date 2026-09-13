"""Deterministic typed answer contracts for the V2 Wave 1 atomic skills."""

from __future__ import annotations

import json
from importlib.resources import files
import re
from typing import Any, Callable

from ..core import decimal
from .catalog import SkillSpec
from .wave0 import (
    ANSWER_SCHEMA_VERSION,
    FIELD_STATES,
    WAVE0_MANIFEST,
    _as_boolean,
    _as_decimal_string,
    _as_integer_string,
    _as_string,
    _path,
    _put,
    _quality,
    _set_freshness,
)


METHODOLOGY_VERSION = "wave1-x402-1.0.0"
INTEGER_RE = re.compile(r"^-?\d+$")
QUOTE_SYMBOLS = {"SOL", "WSOL", "USDC", "USDT", "USD", "PYUSD"}


def load_wave1_manifest() -> dict[str, Any]:
    document = json.loads(files(__package__).joinpath("wave1_manifest.json").read_text())
    if document.get("answer_schema_version") != ANSWER_SCHEMA_VERSION:
        raise ValueError("Unsupported Wave 1 answer schema")
    if document.get("methodology_version") != METHODOLOGY_VERSION:
        raise ValueError("Unsupported Wave 1 methodology")
    if document.get("skill_count") != len(document.get("skills", [])):
        raise ValueError("Wave 1 skill count mismatch")
    return document


WAVE1_MANIFEST = load_wave1_manifest()
WAVE1_BY_SLUG = {item["slug"]: item for item in WAVE1_MANIFEST["skills"]}
WAVE1_SLUGS = frozenset(WAVE1_BY_SLUG)
MODELS = {**WAVE0_MANIFEST.get("models", {}), **WAVE1_MANIFEST.get("models", {})}


def _value(value: Any, *keys: str) -> Any:
    if not isinstance(value, dict):
        return None
    for key in keys:
        if key in value:
            return value[key]
    return None


def _entity(spec: SkillSpec, inputs: dict[str, Any]) -> dict[str, str]:
    entity_type = WAVE1_BY_SLUG[spec.slug]["entity_type"]
    if entity_type == "token":
        address = str(inputs.get("token_address") or inputs.get("token") or "")
    elif entity_type == "wallet":
        wallets = inputs.get("wallet_addresses") or inputs.get("wallets") or []
        address = str(
            inputs.get("wallet_address")
            or inputs.get("wallet")
            or (wallets[0] if wallets else "")
        )
    elif entity_type == "pair":
        address = str(inputs.get("pair_address") or inputs.get("pool_address") or "")
    elif entity_type == "developer":
        address = str(
            inputs.get("developer_wallet_address")
            or inputs.get("wallet_address")
            or inputs.get("wallet")
            or ""
        )
    else:
        address = "solana-market"
    return {"type": entity_type, "address": address}


def _base(spec: SkillSpec, inputs: dict[str, Any], observed_at: str) -> dict[str, Any]:
    contract = WAVE1_BY_SLUG[spec.slug]
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
        "freshness": {
            "provider_timestamp": None,
            "age_seconds": None,
            "classification": "not_available",
        },
        "limitations": [],
        "errors": [],
        "production_accepted": False,
    }


def _put_value(
    answer: dict[str, Any],
    field: str,
    raw: Any,
    normalized: Any,
    endpoint_id: str,
    source_path: str,
    *,
    present: bool = True,
    quality: str | None = None,
    supporting_endpoint_ids: list[str] | None = None,
) -> None:
    _put(
        answer,
        field,
        raw,
        normalized,
        endpoint_id=endpoint_id,
        source_path=source_path,
        present=present,
        quality=quality,
    )
    if supporting_endpoint_ids:
        answer["evidence"][-1]["supporting_endpoint_ids"] = supporting_endpoint_ids


def _list(value: Any, key: str = "items") -> tuple[bool, list[Any]]:
    if isinstance(value, list):
        return True, value
    present, items = _path(value, key)
    return present, items if isinstance(items, list) else []


def _side(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "address": _as_string(_value(value, "address")),
        "symbol": _as_string(_value(value, "symbol")),
        "decimals": _as_integer_string(_value(value, "decimals")),
        "amount": _as_decimal_string(
            _value(value, "ui_change_amount", "uiChangeAmount", "ui_amount", "uiAmount", "amount")
        ),
        "price": _as_decimal_string(_value(value, "price", "nearest_price", "nearestPrice")),
        "type_swap": _as_string(_value(value, "type_swap", "typeSwap", "type")),
    }


def _wallet_direction(item: dict[str, Any], base: dict[str, Any] | None, quote: dict[str, Any] | None) -> str | None:
    explicit = _as_string(_value(item, "side", "direction"))
    if explicit and explicit.lower() in {"buy", "sell"}:
        return explicit.lower()
    tx_type = _as_string(_value(item, "tx_type", "txType"))
    if tx_type and tx_type.lower() in {"buy", "sell"}:
        return tx_type.lower()
    sides = [side for side in (base, quote) if isinstance(side, dict)]
    from_side = next((side for side in sides if side.get("type_swap") == "from"), None)
    to_side = next((side for side in sides if side.get("type_swap") == "to"), None)
    from_symbol = str((from_side or {}).get("symbol") or "").upper()
    to_symbol = str((to_side or {}).get("symbol") or "").upper()
    if from_symbol in QUOTE_SYMBOLS and to_symbol and to_symbol not in QUOTE_SYMBOLS:
        return "buy"
    if to_symbol in QUOTE_SYMBOLS and from_symbol and from_symbol not in QUOTE_SYMBOLS:
        return "sell"
    return None


def _trade_records(
    data: Any,
    endpoint_id: str,
    inputs: dict[str, Any],
    *,
    wallet: str | None = None,
) -> tuple[bool, list[Any], list[dict[str, Any]], bool | None]:
    present, raw_items = _list(data)
    time_from = int(inputs["time_from"]) if inputs.get("time_from") is not None else None
    time_to = int(inputs["time_to"]) if inputs.get("time_to") is not None else None
    trades: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        timestamp = _as_integer_string(_value(raw, "block_unix_time", "blockUnixTime", "time"))
        if timestamp is not None:
            if time_from is not None and int(timestamp) < time_from:
                continue
            if time_to is not None and int(timestamp) >= time_to:
                continue
        tx_hash = _as_string(_value(raw, "tx_hash", "txHash"))
        ins_index = _as_integer_string(_value(raw, "ins_index", "insIndex"))
        inner = _as_integer_string(_value(raw, "inner_ins_index", "innerInsIndex"))
        event_id = f"{tx_hash or endpoint_id}:{ins_index or index}:{inner or 'na'}"
        base = _side(_value(raw, "base", "from"))
        quote = _side(_value(raw, "quote", "to"))
        trades.append(
            {
                "event_id": event_id,
                "tx_hash": tx_hash,
                "block_unix_time": timestamp,
                "owner": _as_string(_value(raw, "owner")) or wallet,
                "source": _as_string(_value(raw, "source")),
                "direction": _wallet_direction(raw, base, quote),
                "tx_type": _as_string(_value(raw, "tx_type", "txType")),
                "volume": _as_decimal_string(_value(raw, "volume")),
                "volume_usd": _as_decimal_string(_value(raw, "volume_usd", "volumeUsd")),
                "base": base,
                "quote": quote,
                "pool_address": _as_string(_value(raw, "pool_id", "poolId")),
            }
        )
    trades.sort(
        key=lambda item: (
            -(int(item["block_unix_time"]) if item["block_unix_time"] else -1),
            item["event_id"],
        )
    )
    has_next = _as_boolean(_value(data, "has_next", "hasNext"))
    return present, raw_items, trades, has_next


def _launch_rows(data: Any) -> tuple[bool, list[Any], list[dict[str, Any]], Any]:
    present, raw_items = _list(data)
    container = data
    if isinstance(data, dict) and isinstance(data.get("items"), dict):
        container = data["items"]
        present, raw_items = _list(container)
    rows = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        meme = raw.get("meme_info") if isinstance(raw.get("meme_info"), dict) else {}
        rows.append(
            {
                "address": _as_string(_value(raw, "address")),
                "symbol": _as_string(_value(raw, "symbol")),
                "name": _as_string(_value(raw, "name")),
                "creator": _as_string(_value(meme, "creator")),
                "source": _as_string(_value(meme, "source")),
                "progress_percent": _as_decimal_string(_value(meme, "progress_percent")),
                "graduated": _as_boolean(_value(meme, "graduated")),
                "creation_time": _as_integer_string(_value(meme, "creation_time")),
                "graduated_time": _as_integer_string(_value(meme, "graduated_time")),
                "market_cap_usd": _as_decimal_string(_value(raw, "market_cap")),
                "liquidity_usd": _as_decimal_string(_value(raw, "liquidity")),
                "price_usd": _as_decimal_string(_value(raw, "price")),
            }
        )
    total = _value(container, "total")
    return present, raw_items, rows, total


def _normalize_trending(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-005")
    present, raw_items = _list(data, "tokens")
    tokens = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        tokens.append(
            {
                "address": _as_string(raw.get("address")),
                "symbol": _as_string(raw.get("symbol")),
                "name": _as_string(raw.get("name")),
                "decimals": _as_integer_string(raw.get("decimals")),
                "rank": _as_integer_string(raw.get("rank")),
                "price_usd": _as_decimal_string(raw.get("price")),
                "liquidity_usd": _as_decimal_string(raw.get("liquidity")),
                "market_cap_usd": _as_decimal_string(raw.get("marketcap")),
                "fdv_usd": _as_decimal_string(raw.get("fdv")),
                "volume_24h_usd": _as_decimal_string(raw.get("volume24hUSD")),
                "price_change_24h_pct": _as_decimal_string(raw.get("price24hChangePercent")),
                "volume_change_24h_pct": _as_decimal_string(raw.get("volume24hChangePercent")),
                "logo_uri": _as_string(raw.get("logoURI")),
            }
        )
    _put_value(answer, "tokens", raw_items, tokens, "EP-005", "data.tokens", present=present, quality=_quality(present, raw_items, tokens))
    _put_value(answer, "returned_count", len(tokens), len(tokens), "EP-005", "derived:data.tokens.length")
    total = _value(data, "total")
    _put_value(answer, "total", total, _as_integer_string(total), "EP-005", "data.total", present=total is not None)
    interval = str(inputs.get("interval", "24h"))
    ordering = f"{inputs.get('sort_by', 'rank')}_{inputs.get('sort_type', 'asc')}"
    _put_value(answer, "interval", interval, interval, "EP-005", "request.interval")
    _put_value(answer, "ordering", ordering, ordering, "EP-005", "request.sort_by/request.sort_type")
    update = _value(data, "updateUnixTime")
    _put_value(answer, "provider_update_unix", update, _as_integer_string(update), "EP-005", "data.updateUnixTime", present=update is not None)
    _set_freshness(answer, update)
    total_int = int(total) if _as_integer_string(total) is not None else None
    answer["pagination"] = {"model": "offset-limit", "returned": len(tokens), "total": _as_integer_string(total), "complete": total_int is not None and len(tokens) >= total_int}


def _normalize_new_tokens(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-004")
    present, raw_items = _list(data)
    tokens = [
        {
            "address": _as_string(raw.get("address")),
            "symbol": _as_string(raw.get("symbol")),
            "name": _as_string(raw.get("name")),
            "decimals": _as_integer_string(raw.get("decimals")),
            "liquidity_usd": _as_decimal_string(raw.get("liquidity")),
            "listed_at": _as_string(raw.get("liquidityAddedAt")),
            "source": _as_string(raw.get("source")),
            "logo_uri": _as_string(raw.get("logoURI")),
        }
        for raw in raw_items
        if isinstance(raw, dict)
    ]
    limit = int(inputs.get("limit", 10))
    _put_value(answer, "tokens", raw_items, tokens, "EP-004", "data.items", present=present, quality=_quality(present, raw_items, tokens))
    _put_value(answer, "returned_count", len(tokens), len(tokens), "EP-004", "derived:data.items.length")
    _put_value(answer, "limit", limit, limit, "EP-004", "request.limit")
    answer["pagination"] = {"model": "limit", "limit": limit, "returned": len(tokens), "complete": len(tokens) < limit}


def _normalize_bonding(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items, tokens, _ = _launch_rows(facts.get("EP-006"))
    detail_data = facts.get("EP-007")
    meme = detail_data.get("meme_info") if isinstance(detail_data, dict) and isinstance(detail_data.get("meme_info"), dict) else {}
    detail = {
        "address": _as_string(_value(detail_data, "address")),
        "creator": _as_string(_value(meme, "creator")),
        "source": _as_string(_value(meme, "source")),
        "progress_percent": _as_decimal_string(_value(meme, "progress_percent")),
        "graduated": _as_boolean(_value(meme, "graduated")),
        "creation_time": _as_integer_string(_value(meme, "creation_time")),
        "graduated_time": _as_integer_string(_value(meme, "graduated_time")),
    } if isinstance(detail_data, dict) else None
    has_next = _as_boolean(_value(facts.get("EP-006"), "has_next"))
    graduated_count = _as_integer_string(_value(facts.get("EP-006"), "graduated"))
    if graduated_count is None and isinstance(facts.get("EP-006"), dict):
        graduated_count = _as_integer_string(_value(facts["EP-006"].get("items"), "graduated"))
    _put_value(answer, "tokens", raw_items, tokens, "EP-006", "data.items", present=present, quality=_quality(present, raw_items, tokens))
    _put_value(answer, "returned_count", len(tokens), len(tokens), "EP-006", "derived:data.items.length")
    _put_value(answer, "has_next", has_next, has_next, "EP-006", "data.has_next", present=has_next is not None)
    _put_value(answer, "graduated_count", graduated_count, graduated_count, "EP-006", "data.items.graduated", present=graduated_count is not None)
    _put_value(answer, "requested_token_detail", detail_data, detail, "EP-007", "data.meme_info", present=isinstance(detail_data, dict), quality=_quality(isinstance(detail_data, dict), detail_data, detail))
    answer["pagination"] = {"model": "offset-limit", "has_next": has_next, "returned": len(tokens), "complete": has_next is False}
    answer["limitations"].append("Stage labels reflect indexed launchpad fields; they are not a prediction of graduation or future trading outcome.")


def _normalize_smart_money(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items = _list(facts.get("EP-008"))
    tokens = [
        {
            "token_address": _as_string(raw.get("token")),
            "symbol": _as_string(raw.get("symbol")),
            "name": _as_string(raw.get("name")),
            "trader_style": _as_string(raw.get("trader_style")),
            "smart_trader_count": _as_integer_string(raw.get("smart_traders_no")),
            "price_usd": _as_decimal_string(raw.get("price")),
            "liquidity_usd": _as_decimal_string(raw.get("liquidity")),
            "market_cap_usd": _as_decimal_string(raw.get("market_cap")),
            "net_flow_usd": _as_decimal_string(raw.get("net_flow")),
            "volume_usd": _as_decimal_string(raw.get("volume_usd")),
            "volume_buy_usd": _as_decimal_string(raw.get("volume_buy_usd")),
            "volume_sell_usd": _as_decimal_string(raw.get("volume_sell_usd")),
            "price_change_pct": _as_decimal_string(raw.get("price_change_percent")),
        }
        for raw in raw_items
        if isinstance(raw, dict)
    ]
    interval = str(inputs.get("interval", "1d"))
    style = str(inputs.get("trader_style", "all"))
    ordering = f"{inputs.get('sort_by', 'smart_traders_no')}_{inputs.get('sort_type', 'desc')}"
    _put_value(answer, "tokens", raw_items, tokens, "EP-008", "data", present=present, quality=_quality(present, raw_items, tokens))
    _put_value(answer, "returned_count", len(tokens), len(tokens), "EP-008", "derived:data.length")
    _put_value(answer, "interval", interval, interval, "EP-008", "request.interval")
    _put_value(answer, "trader_style", style, style, "EP-008", "request.trader_style")
    _put_value(answer, "ordering", ordering, ordering, "EP-008", "request.sort_by/request.sort_type")
    answer["pagination"] = {"model": "offset-limit", "returned": len(tokens), "complete": len(tokens) < int(inputs.get("limit", 20))}
    answer["limitations"].append("Birdeye smart-money labels are provider feed labels, not identity certainty or a recommendation.")


def _normalize_recent_market(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    merged: list[dict[str, Any]] = []
    feeds: dict[str, int] = {}
    has_next_values: list[bool] = []
    for endpoint_id in ("EP-044", "EP-077"):
        _, _, trades, has_next = _trade_records(facts.get(endpoint_id), endpoint_id, inputs)
        feeds[endpoint_id] = len(trades)
        merged.extend(trades)
        if has_next is not None:
            has_next_values.append(has_next)
    unique = {trade["event_id"]: trade for trade in merged}
    trades = sorted(unique.values(), key=lambda item: (-(int(item["block_unix_time"] or 0)), item["event_id"]))
    duplicate_count = len(merged) - len(trades)
    has_next = any(has_next_values) if has_next_values else None
    _put_value(answer, "trades", merged, trades, "EP-044", "derived:EP-044+EP-077", quality=_quality(True, merged, trades), supporting_endpoint_ids=["EP-044", "EP-077"])
    _put_value(answer, "returned_count", len(trades), len(trades), "EP-044", "derived:deduplicated.length", supporting_endpoint_ids=["EP-044", "EP-077"])
    _put_value(answer, "duplicate_count", duplicate_count, duplicate_count, "EP-044", "derived:merged-deduplicated", supporting_endpoint_ids=["EP-044", "EP-077"])
    _put_value(answer, "source_feeds", feeds, feeds, "EP-044", "derived:per-endpoint-counts", supporting_endpoint_ids=["EP-044", "EP-077"])
    _put_value(answer, "has_next", has_next, has_next, "EP-044", "derived:any-provider-has-next", present=has_next is not None, supporting_endpoint_ids=["EP-044", "EP-077"])
    answer["pagination"] = {"model": "offset-limit", "has_next": has_next, "complete": has_next is False}
    if trades:
        _set_freshness(answer, trades[0]["block_unix_time"])


def _normalize_trader_rank(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items = _list(facts.get("EP-079"))
    traders = [
        {
            "wallet": _as_string(raw.get("address")),
            "network": _as_string(raw.get("network")),
            "pnl_usd": _as_decimal_string(raw.get("pnl")),
            "realized_pnl_usd": _as_decimal_string(raw.get("realized_pnl")),
            "unrealized_pnl_usd": _as_decimal_string(raw.get("unrealized_pnl")),
            "trade_count": _as_integer_string(raw.get("trade_count")),
            "volume_usd": _as_decimal_string(raw.get("volume")),
        }
        for raw in raw_items
        if isinstance(raw, dict)
    ]
    period = str(inputs.get("type", "1W"))
    ordering = f"{inputs.get('sort_by', 'PnL')}_{inputs.get('sort_type', 'desc')}"
    _put_value(answer, "traders", raw_items, traders, "EP-079", "data.items", present=present, quality=_quality(present, raw_items, traders))
    _put_value(answer, "returned_count", len(traders), len(traders), "EP-079", "derived:data.items.length")
    _put_value(answer, "period", period, period, "EP-079", "request.type")
    _put_value(answer, "ordering", ordering, ordering, "EP-079", "request.sort_by/request.sort_type")
    answer["pagination"] = {"model": "offset-limit", "returned": len(traders), "complete": len(traders) < int(inputs.get("limit", 10))}
    answer["limitations"].append("Leaderboard PnL fields are provider-reported indexed observations, not guaranteed total wallet performance.")


def _normalize_security(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-010")
    mapping: dict[str, tuple[str, Callable[[Any], Any]]] = {
        "creator_address": ("creatorAddress", _as_string),
        "freeze_authority": ("freezeAuthority", _as_string),
        "freezeable": ("freezeable", _as_boolean),
        "is_token_2022": ("isToken2022", _as_boolean),
        "jupiter_strict_list": ("jupStrictList", _as_boolean),
        "mutable_metadata": ("mutableMetadata", _as_boolean),
        "non_transferable": ("nonTransferable", _as_boolean),
        "top10_holder_percent": ("top10HolderPercent", _as_decimal_string),
        "top10_user_percent": ("top10UserPercent", _as_decimal_string),
        "total_supply": ("totalSupply", _as_decimal_string),
    }
    for field, (source, converter) in mapping.items():
        raw = _value(data, source)
        _put_value(answer, field, raw, converter(raw), "EP-010", f"data.{source}", present=isinstance(data, dict) and source in data)
    answer["limitations"].append("This answer reports observable authority/security fields and does not produce a safe/rug verdict.")


def _normalize_creation(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-029")
    mapping: dict[str, tuple[str, Callable[[Any], Any]]] = {
        "token_address": ("tokenAddress", _as_string),
        "creator": ("creator", _as_string),
        "owner": ("owner", _as_string),
        "transaction_hash": ("txHash", _as_string),
        "block_unix_time": ("blockUnixTime", _as_integer_string),
        "block_human_time": ("blockHumanTime", _as_string),
        "slot": ("slot", _as_integer_string),
        "decimals": ("decimals", _as_integer_string),
    }
    for field, (source, converter) in mapping.items():
        raw = _value(data, source)
        _put_value(answer, field, raw, converter(raw), "EP-029", f"data.{source}", present=isinstance(data, dict) and source in data)
    _set_freshness(answer, _value(data, "blockUnixTime"))


def _normalize_historical_price(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-066")
    requested = inputs.get("unixtime", inputs.get("time_to"))
    provider = _value(data, "updateUnixTime")
    requested_int = int(requested) if requested is not None else None
    provider_str = _as_integer_string(provider)
    lag = requested_int - int(provider_str) if requested_int is not None and provider_str is not None else None
    values = {
        "requested_unix_time": (requested, _as_integer_string(requested), "request.unixtime", requested is not None),
        "provider_update_unix": (provider, provider_str, "data.updateUnixTime", provider is not None),
        "price_usd": (_value(data, "value"), _as_decimal_string(_value(data, "value")), "data.value", isinstance(data, dict) and "value" in data),
        "price_change_24h_pct": (_value(data, "priceChange24h"), _as_decimal_string(_value(data, "priceChange24h")), "data.priceChange24h", isinstance(data, dict) and "priceChange24h" in data),
        "is_scaled_ui_token": (_value(data, "isScaledUiToken"), _as_boolean(_value(data, "isScaledUiToken")), "data.isScaledUiToken", isinstance(data, dict) and "isScaledUiToken" in data),
        "provider_lag_seconds": (lag, lag, "derived:requested-provider", lag is not None),
    }
    for field, (raw, normalized, source, present) in values.items():
        _put_value(answer, field, raw, normalized, "EP-066", source, present=present)
    _set_freshness(answer, provider)
    if lag is not None and lag < 0:
        answer["limitations"].append("Provider timestamp is later than the requested time; do not treat a future-clamped point as historical event evidence.")
    else:
        answer["limitations"].append("Historical point lookup may return the nearest prior indexed observation rather than an exact-timestamp trade.")


def _holder_rows(data: Any) -> tuple[bool, list[Any], list[dict[str, Any]]]:
    present, raw_items = _list(data, "holders")
    holders = [
        {
            "rank": rank,
            "wallet": _as_string(raw.get("wallet")),
            "holding": _as_decimal_string(raw.get("holding")),
            "percent_of_supply": _as_decimal_string(raw.get("percent_of_supply")),
        }
        for rank, raw in enumerate(raw_items, start=1)
        if isinstance(raw, dict)
    ]
    return present, raw_items, holders


def _holder_summary(data: Any) -> dict[str, Any] | None:
    summary = data.get("summary") if isinstance(data, dict) else None
    if not isinstance(summary, dict):
        return None
    return {
        "total_holding": _as_decimal_string(summary.get("total_holding")),
        "percent_of_supply": _as_decimal_string(summary.get("percent_of_supply")),
        "wallet_count": _as_integer_string(summary.get("wallet_count")),
    }


def _normalize_holder_distribution(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-031")
    present, raw_items, holders = _holder_rows(data)
    summary = _holder_summary(data)
    _put_value(answer, "token_address", _value(data, "token_address"), _as_string(_value(data, "token_address")), "EP-031", "data.token_address", present=isinstance(data, dict) and "token_address" in data)
    _put_value(answer, "mode", _value(data, "mode"), _as_string(_value(data, "mode")), "EP-031", "data.mode", present=isinstance(data, dict) and "mode" in data)
    _put_value(answer, "holders", raw_items, holders, "EP-031", "data.holders", present=present, quality=_quality(present, raw_items, holders))
    _put_value(answer, "summary", _value(data, "summary"), summary, "EP-031", "data.summary", present=summary is not None)
    _put_value(answer, "returned_count", len(holders), len(holders), "EP-031", "derived:data.holders.length")
    wallet_count = summary.get("wallet_count") if summary else None
    total = int(wallet_count) if wallet_count is not None else None
    offset = int(inputs.get("offset", 0))
    answer["pagination"] = {"model": "offset-limit", "offset": offset, "returned": len(holders), "total": wallet_count, "complete": total is not None and offset + len(holders) >= total}
    answer["limitations"].append("Holder distribution reflects the requested address type and indexed denominator; known program/system exclusions are not inferred unless supplied.")


def _normalize_holder_positions(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-031")
    present, raw_items, holders = _holder_rows(data)
    _put_value(answer, "token_address", _value(data, "token_address"), _as_string(_value(data, "token_address")), "EP-031", "data.token_address", present=isinstance(data, dict) and "token_address" in data)
    _put_value(answer, "ranked_holders", raw_items, holders, "EP-031", "data.holders", present=present, quality=_quality(present, raw_items, holders))
    _put_value(answer, "returned_count", len(holders), len(holders), "EP-031", "derived:data.holders.length")
    ordering = "holding_desc"
    _put_value(answer, "ordering", ordering, ordering, "EP-031", "request.mode=top")
    summary = _holder_summary(data)
    total = int(summary["wallet_count"]) if summary and summary.get("wallet_count") else None
    offset = int(inputs.get("offset", 0))
    answer["pagination"] = {"model": "offset-limit", "offset": offset, "returned": len(holders), "total": str(total) if total is not None else None, "complete": total is not None and offset + len(holders) >= total}
    answer["limitations"].append("This ranks balances for the supplied token; it is not a cross-token wallet position portfolio.")


def _top_traders(data: Any) -> tuple[bool, list[Any], list[dict[str, Any]]]:
    present, raw_items = _list(data)
    traders = [
        {
            "rank": rank,
            "wallet": _as_string(raw.get("owner")),
            "tags": [tag for tag in raw.get("tags", []) if isinstance(tag, str)],
            "trade_count": _as_integer_string(raw.get("trade")),
            "buy_count": _as_integer_string(raw.get("tradeBuy")),
            "sell_count": _as_integer_string(raw.get("tradeSell")),
            "total_pnl_usd": _as_decimal_string(raw.get("totalPnl")),
            "realized_pnl_usd": _as_decimal_string(raw.get("realizedPnl")),
            "unrealized_pnl_usd": _as_decimal_string(raw.get("unrealizedPnl")),
            "volume_usd": _as_decimal_string(raw.get("volumeUsd")),
            "volume_buy_usd": _as_decimal_string(raw.get("volumeBuyUSD")),
            "volume_sell_usd": _as_decimal_string(raw.get("volumeSellUSD")),
        }
        for rank, raw in enumerate(raw_items, start=1)
        if isinstance(raw, dict)
    ]
    return present, raw_items, traders


def _normalize_top_traders(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items, traders = _top_traders(facts.get("EP-037"))
    frame = str(inputs.get("time_frame", "24h"))
    ordering = f"{inputs.get('sort_by', 'volume')}_{inputs.get('sort_type', 'desc')}"
    _put_value(answer, "traders", raw_items, traders, "EP-037", "data.items", present=present, quality=_quality(present, raw_items, traders))
    _put_value(answer, "returned_count", len(traders), len(traders), "EP-037", "derived:data.items.length")
    _put_value(answer, "time_frame", frame, frame, "EP-037", "request.time_frame")
    _put_value(answer, "ordering", ordering, ordering, "EP-037", "request.sort_by/request.sort_type")
    answer["pagination"] = {"model": "offset-limit", "offset": int(inputs.get("offset", 0)), "returned": len(traders), "complete": len(traders) < int(inputs.get("limit", 10))}
    answer["limitations"].append("Top-trader and performance fields are scoped to this token, selected window and provider ordering.")


def _normalize_token_trade_feed(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items, trades, has_next = _trade_records(facts.get("EP-039"), "EP-039", inputs)
    time_from = inputs.get("time_from")
    time_to = inputs.get("time_to")
    complete = has_next is False and time_from is not None and time_to is not None
    _put_value(answer, "trades", raw_items, trades, "EP-039", "data.items", present=present, quality=_quality(present, raw_items, trades))
    _put_value(answer, "returned_count", len(trades), len(trades), "EP-039", "derived:filtered.length")
    _put_value(answer, "time_from", time_from, _as_integer_string(time_from), "EP-039", "request.after_time", present=time_from is not None)
    _put_value(answer, "time_to", time_to, _as_integer_string(time_to), "EP-039", "request.before_time", present=time_to is not None)
    _put_value(answer, "has_next", has_next, has_next, "EP-039", "data.has_next", present=has_next is not None)
    _put_value(answer, "closed_window_complete", complete, complete, "EP-039", "derived:paired-time-and-has-next")
    answer["pagination"] = {"model": "offset-limit-paired-time", "has_next": has_next, "complete": complete}
    if trades:
        _set_freshness(answer, trades[0]["block_unix_time"])


def _normalize_large_trades(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items, trades, has_next = _trade_records(facts.get("EP-040"), "EP-040", inputs)
    threshold = inputs.get("min_volume")
    ordering = f"{inputs.get('sort_by', 'block_unix_time')}_{inputs.get('sort_type', 'desc')}"
    _put_value(answer, "trades", raw_items, trades, "EP-040", "data.items", present=present, quality=_quality(present, raw_items, trades))
    _put_value(answer, "returned_count", len(trades), len(trades), "EP-040", "derived:data.items.length")
    _put_value(answer, "min_volume_usd", threshold, _as_decimal_string(threshold), "EP-040", "request.min_volume", present=threshold is not None)
    _put_value(answer, "has_next", has_next, has_next, "EP-040", "data.has_next", present=has_next is not None)
    _put_value(answer, "ordering", ordering, ordering, "EP-040", "request.sort_by/request.sort_type")
    answer["pagination"] = {"model": "offset-limit", "has_next": has_next, "complete": has_next is False}


def _normalize_mint_burn(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items = _list(facts.get("EP-041"))
    events = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        tx_hash = _as_string(raw.get("tx_hash"))
        slot = _as_integer_string(raw.get("slot"))
        events.append(
            {
                "event_id": f"{tx_hash or 'EP-041'}:{slot or index}",
                "tx_hash": tx_hash,
                "block_unix_time": _as_integer_string(raw.get("block_time")),
                "slot": slot,
                "event_type": _as_string(raw.get("common_type")),
                "amount_raw": _as_decimal_string(raw.get("amount")),
                "amount_ui": _as_decimal_string(raw.get("ui_amount_string", raw.get("ui_amount"))),
                "decimals": _as_integer_string(raw.get("decimals")),
                "token_address": _as_string(raw.get("mint")),
            }
        )
    event_type = str(inputs.get("type", "all"))
    _put_value(answer, "events", raw_items, events, "EP-041", "data.items", present=present, quality=_quality(present, raw_items, events))
    _put_value(answer, "returned_count", len(events), len(events), "EP-041", "derived:data.items.length")
    _put_value(answer, "event_type_filter", event_type, event_type, "EP-041", "request.type")
    answer["pagination"] = {"model": "limit", "returned": len(events), "complete": len(events) < int(inputs.get("limit", 100))}
    if events:
        _set_freshness(answer, events[0]["block_unix_time"])


def _normalize_first_buyers(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    data = facts.get("EP-046")
    present, raw_items = _list(data)
    candidates = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        direction = _as_string(_value(raw, "side"))
        if direction and direction.lower() != "buy":
            continue
        token_side = _value(raw, "to", "quote")
        candidates.append(
            {
                "rank": 0,
                "wallet": _as_string(raw.get("owner")),
                "block_unix_time": _as_integer_string(_value(raw, "blockUnixTime", "block_unix_time")),
                "tx_hash": _as_string(_value(raw, "txHash", "tx_hash")),
                "source": _as_string(raw.get("source")),
                "pool_address": _as_string(_value(raw, "poolId", "pool_id")),
                "token_price_usd": _as_decimal_string(_value(raw, "tokenPrice", "token_price")),
                "token_amount": _as_decimal_string(_value(token_side, "uiChangeAmount", "ui_change_amount", "uiAmount", "ui_amount")),
                "direction": direction.lower() if direction else None,
            }
        )
    candidates.sort(key=lambda item: int(item["block_unix_time"] or 0))
    for rank, item in enumerate(candidates, start=1):
        item["rank"] = rank
    has_next = _as_boolean(_value(data, "hasNext", "has_next"))
    exhaustive = has_next is False
    before_time = inputs.get("before_time")
    _put_value(answer, "buyers", raw_items, candidates, "EP-046", "data.items[side=buy]", present=present, quality=_quality(present, raw_items, candidates))
    _put_value(answer, "returned_count", len(candidates), len(candidates), "EP-046", "derived:buy-candidates.length")
    _put_value(answer, "before_time", before_time, _as_integer_string(before_time), "EP-046", "request.before_time", present=before_time is not None)
    _put_value(answer, "has_next", has_next, has_next, "EP-046", "data.hasNext", present=has_next is not None)
    _put_value(answer, "page_is_exhaustive", exhaustive, exhaustive, "EP-046", "derived:provider-has-next")
    answer["pagination"] = {"model": "offset-limit-one-sided-time-seek", "has_next": has_next, "complete": exhaustive}
    answer["limitations"].append("Earliest means earliest buy in the bounded returned coverage; it is not exhaustive while additional pages exist.")


def _wallet_fact_sets(facts: dict[str, Any], inputs: dict[str, Any]) -> list[tuple[str | None, Any]]:
    data = facts.get("EP-048")
    if isinstance(data, dict) and isinstance(data.get("wallets"), list):
        return [
            (str(item.get("wallet")) if item.get("wallet") else None, item.get("data"))
            for item in data["wallets"]
            if isinstance(item, dict)
        ]
    wallet = inputs.get("wallet_address") or inputs.get("wallet")
    return [(str(wallet) if wallet else None, data)]


def _wallet_trades(facts: dict[str, Any], inputs: dict[str, Any]) -> tuple[list[Any], list[dict[str, Any]], list[bool | None]]:
    raw: list[Any] = []
    trades: list[dict[str, Any]] = []
    pages: list[bool | None] = []
    for wallet, data in _wallet_fact_sets(facts, inputs):
        _, items, rows, has_next = _trade_records(data, "EP-048", inputs, wallet=wallet)
        raw.extend(items)
        trades.extend(rows)
        pages.append(has_next)
    trades.sort(key=lambda item: (-(int(item["block_unix_time"] or 0)), item["event_id"]))
    return raw, trades, pages


def _normalize_traded_tokens(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    raw, trades, pages = _wallet_trades(facts, inputs)
    tokens: dict[str, dict[str, Any]] = {}
    for trade in trades:
        direction = trade.get("direction")
        sides = [side for side in (trade.get("base"), trade.get("quote")) if isinstance(side, dict)]
        for side in sides:
            symbol = str(side.get("symbol") or "").upper()
            if symbol in QUOTE_SYMBOLS:
                continue
            key = str(side.get("address") or symbol)
            if not key:
                continue
            item = tokens.setdefault(
                key,
                {
                    "token_address": side.get("address"),
                    "symbol": side.get("symbol"),
                    "buy_count": 0,
                    "sell_count": 0,
                    "unknown_count": 0,
                    "first_seen_unix": trade.get("block_unix_time"),
                    "last_seen_unix": trade.get("block_unix_time"),
                },
            )
            item[f"{direction}_count" if direction in {"buy", "sell"} else "unknown_count"] += 1
            timestamps = [value for value in (item["first_seen_unix"], item["last_seen_unix"], trade.get("block_unix_time")) if value]
            if timestamps:
                item["first_seen_unix"] = min(timestamps, key=int)
                item["last_seen_unix"] = max(timestamps, key=int)
    rows = sorted(tokens.values(), key=lambda item: (-(int(item["last_seen_unix"] or 0)), str(item["token_address"])))
    complete = all(value is False for value in pages) and bool(pages)
    time_from = inputs.get("time_from")
    time_to = inputs.get("time_to")
    _put_value(answer, "tokens", raw, rows, "EP-048", "derived:distinct-non-quote-traded-tokens", quality=_quality(True, raw, rows))
    _put_value(answer, "trade_count", len(trades), len(trades), "EP-048", "derived:filtered-trades.length")
    _put_value(answer, "time_from", time_from, _as_integer_string(time_from), "EP-048", "request.after_time", present=time_from is not None)
    _put_value(answer, "time_to", time_to, _as_integer_string(time_to), "EP-048", "client_filter:time_to", present=time_to is not None)
    _put_value(answer, "closed_window_complete", complete, complete, "EP-048", "derived:all-pages-complete")
    answer["pagination"] = {"model": "offset-limit-one-sided-time-seek", "complete": complete}
    answer["limitations"].append("This reports tokens observed in indexed wallet trades, not current wallet holdings or balances.")


def _pool_side(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        "address": _as_string(value.get("address")),
        "symbol": _as_string(value.get("symbol")),
        "decimals": _as_integer_string(value.get("decimals")),
    }


def _normalize_pool_check(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    token_data = facts.get("EP-009")
    pool = facts.get("EP-017")
    token_address = _as_string(_value(token_data, "address")) or _as_string(inputs.get("token_address"))
    pool_address = _as_string(_value(pool, "address"))
    base = _pool_side(_value(pool, "base"))
    quote = _pool_side(_value(pool, "quote"))
    matched = None
    if token_address and base and token_address == base.get("address"):
        matched = "base"
    elif token_address and quote and token_address == quote.get("address"):
        matched = "quote"
    matches = matched is not None if token_address and base and quote else None
    fields = {
        "token_address": (token_address, token_address, "EP-009", "data.address", token_address is not None),
        "pool_address": (pool_address, pool_address, "EP-017", "data.address", pool_address is not None),
        "base_token": (_value(pool, "base"), base, "EP-017", "data.base", base is not None),
        "quote_token": (_value(pool, "quote"), quote, "EP-017", "data.quote", quote is not None),
        "matched_side": (matched, matched, "EP-017", "derived:token-address-match", matched is not None),
        "token_matches_pool": (matches, matches, "EP-017", "derived:base-or-quote-match", matches is not None),
        "dex": (_value(pool, "source"), _as_string(_value(pool, "source")), "EP-017", "data.source", isinstance(pool, dict) and "source" in pool),
        "liquidity_usd": (_value(pool, "liquidity"), _as_decimal_string(_value(pool, "liquidity")), "EP-017", "data.liquidity", isinstance(pool, dict) and "liquidity" in pool),
    }
    for field, (raw, normalized, endpoint, source, present) in fields.items():
        _put_value(answer, field, raw, normalized, endpoint, source, present=present)
    answer["limitations"].append("Identity consistency does not verify pool safety, executable liquidity, or route quality.")


def _normalize_token_activity(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    _, raw, trades, has_next = _trade_records(facts.get("EP-039"), "EP-039", inputs)
    buy = sum(item["direction"] == "buy" for item in trades)
    sell = sum(item["direction"] == "sell" for item in trades)
    unknown = len(trades) - buy - sell
    complete = has_next is False and inputs.get("time_from") is not None and inputs.get("time_to") is not None
    _put_value(answer, "trades", raw, trades, "EP-039", "data.items", quality=_quality(True, raw, trades))
    _put_value(answer, "buy_count", buy, buy, "EP-039", "derived:direction=buy")
    _put_value(answer, "sell_count", sell, sell, "EP-039", "derived:direction=sell")
    _put_value(answer, "unknown_count", unknown, unknown, "EP-039", "derived:direction=unknown")
    _put_value(answer, "time_from", inputs.get("time_from"), _as_integer_string(inputs.get("time_from")), "EP-039", "request.after_time", present=inputs.get("time_from") is not None)
    _put_value(answer, "time_to", inputs.get("time_to"), _as_integer_string(inputs.get("time_to")), "EP-039", "request.before_time", present=inputs.get("time_to") is not None)
    _put_value(answer, "closed_window_complete", complete, complete, "EP-039", "derived:paired-time-and-has-next")
    answer["pagination"] = {"model": "offset-limit-paired-time", "has_next": has_next, "complete": complete}


def _normalize_wallet_sells(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    raw, trades, pages = _wallet_trades(facts, inputs)
    sells = [trade for trade in trades if trade.get("direction") == "sell"]
    complete = all(value is False for value in pages) and bool(pages)
    method = "provider buy/sell side, then non-quote from/to inference; ambiguous swaps excluded"
    _put_value(answer, "sells", raw, sells, "EP-048", "derived:direction=sell", quality=_quality(True, raw, sells))
    _put_value(answer, "returned_count", len(sells), len(sells), "EP-048", "derived:sells.length")
    _put_value(answer, "time_from", inputs.get("time_from"), _as_integer_string(inputs.get("time_from")), "EP-048", "request.after_time", present=inputs.get("time_from") is not None)
    _put_value(answer, "time_to", inputs.get("time_to"), _as_integer_string(inputs.get("time_to")), "EP-048", "client_filter:time_to", present=inputs.get("time_to") is not None)
    _put_value(answer, "classification_method", method, method, "EP-048", "derived:direction-method")
    _put_value(answer, "closed_window_complete", complete, complete, "EP-048", "derived:all-pages-complete")
    answer["pagination"] = {"model": "offset-limit-one-sided-time-seek", "complete": complete}
    if len(sells) < len(trades):
        answer["limitations"].append("Ambiguous swaps and observed buys are excluded from the sell feed rather than guessed.")


def _normalize_transfers(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items = _list(facts.get("EP-061"))
    transfers = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        tx_hash = _as_string(raw.get("tx_hash"))
        timestamp = _as_integer_string(raw.get("unix_time"))
        info = raw.get("token_info") if isinstance(raw.get("token_info"), dict) else {}
        transfers.append(
            {
                "event_id": f"{tx_hash or 'EP-061'}:{timestamp or index}:{index}",
                "tx_hash": tx_hash,
                "block_unix_time": timestamp,
                "from_wallet": _as_string(raw.get("from_address")),
                "to_wallet": _as_string(raw.get("to_address")),
                "token_address": _as_string(raw.get("token_address")),
                "symbol": _as_string(info.get("symbol")),
                "amount_raw": _as_decimal_string(raw.get("amount")),
                "amount_ui": _as_decimal_string(raw.get("ui_amount")),
                "price_usd": _as_decimal_string(raw.get("price")),
                "value_usd": _as_decimal_string(raw.get("value")),
                "action": _as_string(raw.get("action")),
            }
        )
    total = _value(facts.get("EP-078"), "total")
    limit = int(inputs.get("limit", 100))
    page_complete = len(transfers) < limit
    _put_value(answer, "transfers", raw_items, transfers, "EP-061", "data", present=present, quality=_quality(present, raw_items, transfers))
    _put_value(answer, "returned_count", len(transfers), len(transfers), "EP-061", "derived:data.length")
    _put_value(answer, "provider_total", total, _as_integer_string(total), "EP-078", "data.total", present=total is not None)
    _put_value(answer, "time_from", inputs.get("time_from"), _as_integer_string(inputs.get("time_from")), "EP-061", "request.time_from", present=inputs.get("time_from") is not None)
    _put_value(answer, "time_to", inputs.get("time_to"), _as_integer_string(inputs.get("time_to")), "EP-061", "request.time_to", present=inputs.get("time_to") is not None)
    _put_value(answer, "page_complete", page_complete, page_complete, "EP-061", "derived:returned<limit")
    answer["pagination"] = {"model": "cursor", "returned": len(transfers), "complete": page_complete}
    answer["limitations"].append("Transfer total and returned page are reported separately; cursor metadata is not fabricated when absent from the normalized payload.")


def _normalize_kol(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    raw, trades, pages = _wallet_trades(facts, inputs)
    requested_wallets = inputs.get("wallet_addresses") or inputs.get("wallets") or []
    if not requested_wallets and (inputs.get("wallet_address") or inputs.get("wallet")):
        requested_wallets = [inputs.get("wallet_address") or inputs.get("wallet")]
    if isinstance(requested_wallets, str):
        requested_wallets = [requested_wallets]
    requested_wallets = list(dict.fromkeys(requested_wallets))
    queried = len(_wallet_fact_sets(facts, inputs))
    coverage_complete = queried == len(requested_wallets) and all(value is False for value in pages)
    _put_value(answer, "trades", raw, trades, "EP-048", "derived:wallet-fanout", quality=_quality(True, raw, trades))
    _put_value(answer, "wallets_requested", len(requested_wallets), len(requested_wallets), "EP-048", "request.wallet_addresses.length")
    _put_value(answer, "wallets_queried", queried, queried, "EP-048", "derived:wallet-fanout.length")
    _put_value(answer, "time_from", inputs.get("time_from"), _as_integer_string(inputs.get("time_from")), "EP-048", "request.after_time", present=inputs.get("time_from") is not None)
    _put_value(answer, "time_to", inputs.get("time_to"), _as_integer_string(inputs.get("time_to")), "EP-048", "client_filter:time_to", present=inputs.get("time_to") is not None)
    _put_value(answer, "coverage_complete", coverage_complete, coverage_complete, "EP-048", "derived:wallet-and-page-coverage")
    answer["pagination"] = {"model": "wallet-fanout-offset-limit", "wallets_requested": len(requested_wallets), "wallets_queried": queried, "complete": coverage_complete}
    answer["limitations"].append("KOL identity is caller-supplied; Birdeye trade evidence does not verify that label.")


def _normalize_post_exit(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    raw, trades, pages = _wallet_trades(facts, inputs)
    exit_time = inputs.get("exit_unix_time", inputs.get("time_from"))
    complete = all(value is False for value in pages) and bool(pages)
    _put_value(answer, "trades", raw, trades, "EP-048", "derived:trades-after-exit", quality=_quality(True, raw, trades))
    _put_value(answer, "returned_count", len(trades), len(trades), "EP-048", "derived:filtered.length")
    _put_value(answer, "exit_unix_time", exit_time, _as_integer_string(exit_time), "EP-048", "request.after_time", present=exit_time is not None)
    _put_value(answer, "time_to", inputs.get("time_to"), _as_integer_string(inputs.get("time_to")), "EP-048", "client_filter:time_to", present=inputs.get("time_to") is not None)
    _put_value(answer, "closed_window_complete", complete, complete, "EP-048", "derived:all-pages-complete")
    answer["pagination"] = {"model": "offset-limit-one-sided-time-seek", "complete": complete}
    answer["limitations"].append("Temporal sequence after the selected exit does not establish causation or rotation intent.")


def _normalize_developer_tokens(answer: dict[str, Any], facts: dict[str, Any], inputs: dict[str, Any]) -> None:
    present, raw_items, tokens, total = _launch_rows(facts.get("EP-006"))
    developer = inputs.get("developer_wallet_address") or inputs.get("wallet_address") or inputs.get("wallet")
    has_next = _as_boolean(_value(facts.get("EP-006"), "has_next"))
    _put_value(answer, "developer_wallet", developer, _as_string(developer), "EP-006", "request.creator", present=developer is not None)
    _put_value(answer, "tokens", raw_items, tokens, "EP-006", "data.items", present=present, quality=_quality(present, raw_items, tokens))
    _put_value(answer, "returned_count", len(tokens), len(tokens), "EP-006", "derived:data.items.length")
    _put_value(answer, "total", total, _as_integer_string(total), "EP-006", "data.total", present=total is not None)
    _put_value(answer, "has_next", has_next, has_next, "EP-006", "data.has_next", present=has_next is not None)
    answer["pagination"] = {"model": "offset-limit", "has_next": has_next, "complete": has_next is False}
    answer["limitations"].append("This covers Birdeye-indexed launchpad tokens for the supplied creator filter, not every token ever associated with the wallet.")


NORMALIZERS: dict[str, Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None]] = {
    "trending-tokens": _normalize_trending,
    "newly-listed-tokens": _normalize_new_tokens,
    "bonding-curve-token-stages": _normalize_bonding,
    "smart-money-token-feed": _normalize_smart_money,
    "recent-market-activity": _normalize_recent_market,
    "trader-gainers-losers": _normalize_trader_rank,
    "token-security-check": _normalize_security,
    "token-creation-evidence": _normalize_creation,
    "historical-price-at-time": _normalize_historical_price,
    "holder-distribution": _normalize_holder_distribution,
    "holder-positions": _normalize_holder_positions,
    "top-token-traders": _normalize_top_traders,
    "token-trade-feed": _normalize_token_trade_feed,
    "large-token-trades": _normalize_large_trades,
    "mint-burn-activity": _normalize_mint_burn,
    "first-buyers": _normalize_first_buyers,
    "top-trader-performance": _normalize_top_traders,
    "wallet-current-holdings": _normalize_traded_tokens,
    "token-pool-verification": _normalize_pool_check,
    "token-activity-feed": _normalize_token_activity,
    "wallet-sell-feed": _normalize_wallet_sells,
    "token-transfers": _normalize_transfers,
    "kol-trades": _normalize_kol,
    "post-exit-activity": _normalize_post_exit,
    "developer-created-tokens": _normalize_developer_tokens,
}


def _finish(answer: dict[str, Any], contract: dict[str, Any], errors: list[dict[str, Any]], facts: dict[str, Any]) -> None:
    required = contract["required_fields"]
    available_states = {"observed", "zero", "empty"}
    available = sum(answer["field_states"].get(field) in available_states for field in required)
    empty = [field for field in required if answer["field_states"].get(field) == "empty"]
    answer["coverage"] = {
        "required_fields_available": available,
        "required_fields_total": len(required),
        "missing_fields": [field for field in required if answer["field_states"].get(field) == "missing"],
        "null_fields": [field for field in required if answer["field_states"].get(field) == "null"],
        "invalid_fields": [field for field in required if answer["field_states"].get(field) == "invalid"],
        "empty_fields": empty,
    }
    endpoint_observed = any(endpoint_id in facts for endpoint_id in contract["endpoint_ids"])
    if errors and not endpoint_observed:
        answer["status"] = "error"
    elif not endpoint_observed:
        answer["status"] = "insufficient_data"
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
        answer["limitations"].append("The bounded response is not exhaustive; follow the declared pagination model before treating it as complete.")
    answer["errors"] = list(errors)


def normalize_wave1_answer(
    spec: SkillSpec,
    inputs: dict[str, Any],
    facts: dict[str, Any],
    *,
    observed_at: str,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if spec.slug not in WAVE1_BY_SLUG:
        return None
    answer = _base(spec, inputs, observed_at)
    NORMALIZERS[spec.slug](answer, facts, inputs)
    _finish(answer, WAVE1_BY_SLUG[spec.slug], list(errors or []), facts)
    validation_errors = validate_wave1_answer(answer)
    if validation_errors:
        raise ValueError(f"Wave 1 answer contract violation for {spec.slug}: {'; '.join(validation_errors)}")
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
    if base == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if base == "object":
        return isinstance(value, dict)
    if base.startswith("array[") and base.endswith("]"):
        child = base[6:-1]
        return isinstance(value, list) and all(_type_valid(item, child) for item in value)
    model = MODELS.get(base)
    return bool(
        isinstance(model, dict)
        and isinstance(value, dict)
        and set(value) == set(model)
        and all(_type_valid(value[field], child_type) for field, child_type in model.items())
    )


def validate_wave1_answer(answer: Any) -> list[str]:
    if not isinstance(answer, dict):
        return ["answer must be an object"]
    contract = WAVE1_BY_SLUG.get(answer.get("skill"))
    if contract is None:
        return ["skill is not in the frozen Wave 1 manifest"]
    errors: list[str] = []
    if answer.get("schema_version") != ANSWER_SCHEMA_VERSION:
        errors.append("invalid schema_version")
    if answer.get("methodology_version") != METHODOLOGY_VERSION:
        errors.append("invalid methodology_version")
    if answer.get("skill_id") != contract["skill_id"]:
        errors.append("skill_id does not match manifest")
    if answer.get("production_accepted") is not False:
        errors.append("Wave 1 answer must not claim production acceptance")
    if answer.get("chain") != "solana":
        errors.append("chain must be solana")
    entity = answer.get("entity")
    if not isinstance(entity, dict) or entity.get("type") != contract["entity_type"] or not isinstance(entity.get("address"), str):
        errors.append("entity does not match manifest")
    fields = answer.get("fields")
    if not isinstance(fields, dict):
        return errors + ["fields must be an object"]
    expected = set(contract["field_types"])
    if set(fields) != expected:
        errors.append("field set does not match manifest")
    for field, type_name in contract["field_types"].items():
        if field in fields and not _type_valid(fields[field], type_name):
            errors.append(f"{field} must be {type_name}")
    if answer.get("status") not in {"complete", "partial", "empty", "insufficient_data", "error"}:
        errors.append("invalid answer status")
    evidence = answer.get("evidence")
    if not isinstance(evidence, list) or len(evidence) != len(expected) or {item.get("field") for item in evidence if isinstance(item, dict)} != expected:
        errors.append("evidence must cover every contract field")
    else:
        for item in evidence:
            supporting = item.get("supporting_endpoint_ids", [])
            if (
                not isinstance(item, dict)
                or item.get("endpoint_id") not in contract["endpoint_ids"]
                or not isinstance(item.get("source_path"), str)
                or item.get("quality") not in FIELD_STATES
                or not isinstance(supporting, list)
                or not set(supporting) <= set(contract["endpoint_ids"])
            ):
                errors.append("evidence contains an invalid provenance record")
                break
    states = answer.get("field_states")
    if not isinstance(states, dict) or set(states) != expected or any(value not in FIELD_STATES for value in states.values()):
        errors.append("field_states must classify every contract field")
    elif isinstance(evidence, list) and len(evidence) == len(expected):
        evidence_states = {item.get("field"): item.get("quality") for item in evidence if isinstance(item, dict)}
        if any(evidence_states.get(field) != state for field, state in states.items()):
            errors.append("field_states and evidence quality must agree")
    for key in ("coverage", "pagination", "freshness"):
        if not isinstance(answer.get(key), dict):
            errors.append(f"{key} must be an object")
    if not isinstance(answer.get("limitations"), list) or not isinstance(answer.get("errors"), list):
        errors.append("limitations and errors must be arrays")
    if not isinstance(answer.get("observed_at"), str):
        errors.append("observed_at must be a string")
    return errors
