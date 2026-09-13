"""Typed execution for focused V3 marketplace rankings."""

from __future__ import annotations

import re
from typing import Any

from ..core import IntelligenceError, InvalidInput, Usage, utc_now
from ..v2.client import V2Client
from .catalog import CommandSpec

TOKEN_FIELDS = (
    ("address", "address"),
    ("symbol", "symbol"),
    ("name", "name"),
    ("price_usd", "price"),
    ("market_cap_usd", "market_cap"),
    ("fdv_usd", "fdv"),
    ("liquidity_usd", "liquidity"),
    ("holder_count", "holder"),
    ("volume_5m_usd", "volume_5m_usd"),
    ("volume_1h_usd", "volume_1h_usd"),
    ("volume_change_5m_pct", "volume_5m_change_percent"),
    ("price_change_5m_pct", "price_change_5m_percent"),
    ("trade_count_5m", "trade_5m_count"),
    ("recent_listing_time", "recent_listing_time"),
)


# EP-006 documents additional source values for other chains, but V3 is an
# audited Solana-only surface. These are the source values that returned
# source-matched data under the Solana header during the 2026-09-11 live QA.
SOLANA_LAUNCHPAD_SOURCE_ALIASES = {
    "all": "all",
    "pump.fun": "pump_dot_fun",
    "pump fun": "pump_dot_fun",
    "pumpfun": "pump_dot_fun",
    "pump_dot_fun": "pump_dot_fun",
    "moonshot": "moonshot",
    "raydium launchlab": "raydium_launchlab",
    "raydium launch lab": "raydium_launchlab",
    "launchlab": "raydium_launchlab",
    "raydium_launchlab": "raydium_launchlab",
    "meteora": "meteora_dynamic_bonding_curve",
    "meteora dbc": "meteora_dynamic_bonding_curve",
    "meteora dynamic bonding curve": "meteora_dynamic_bonding_curve",
    "meteora_dynamic_bonding_curve": "meteora_dynamic_bonding_curve",
}


def normalize_launchpad_source(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput("Launchpad source must be a non-empty string")
    key = " ".join(value.strip().lower().replace("-", " ").split())
    normalized = SOLANA_LAUNCHPAD_SOURCE_ALIASES.get(key)
    if normalized is None:
        supported = "all, Pump.fun, Moonshot, Raydium LaunchLab, or Meteora DBC"
        raise InvalidInput(f"Unsupported Solana launchpad source; use {supported}")
    return normalized


def _string(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    return str(value)


def _token_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = {target: _string(raw.get(source)) for target, source in TOKEN_FIELDS}
    meme = raw.get("meme_info") if isinstance(raw.get("meme_info"), dict) else {}
    row.update(
        {
            "launchpad": _string(meme.get("source")),
            "creator": _string(meme.get("creator")),
            "creation_time": _string(meme.get("creation_time")),
            "bonding_curve_progress_pct": _string(meme.get("progress_percent")),
            "graduated": meme.get("graduated") if isinstance(meme.get("graduated"), bool) else None,
            "graduated_time": _string(meme.get("graduated_time")),
        }
    )
    return row


def _params(command: CommandSpec, inputs: dict[str, Any], endpoint: dict[str, Any]) -> dict[str, Any]:
    params = dict(command.params or {})
    allowed = set(
        re.findall(
            r"query:([a-zA-Z0-9_]+)",
            f"{endpoint.get('required_query_parameters', '')}|{endpoint.get('optional_query_parameters', '')}",
        )
    )
    for key, value in inputs.items():
        if key in allowed and value not in (None, "", []):
            params[key] = value
    window_fields = command.window_fields or {}
    if inputs.get("time_from") is not None and window_fields.get("from"):
        params[window_fields["from"]] = inputs["time_from"]
    if inputs.get("time_to") is not None and window_fields.get("to"):
        params[window_fields["to"]] = inputs["time_to"]
    override = inputs.get("endpoint_params", {}).get(command.endpoint_ids[0], {})
    if isinstance(override, dict):
        params.update(override)
    params.update(command.locked_params or {})
    if command.endpoint_ids[0] == "EP-006" and "source" in params:
        params["source"] = normalize_launchpad_source(params["source"])
    if command.fetch_limit:
        params["limit"] = command.fetch_limit
    return {
        key: str(value).lower() if isinstance(value, bool) else value
        for key, value in params.items()
        if value not in (None, "", [])
    }


def _passes_client_filters(raw: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, threshold in filters.items():
        raw_value = raw.get(key.removeprefix("min_").removeprefix("max_"))
        try:
            observed = float(raw_value)
            expected = float(threshold)
        except (TypeError, ValueError):
            return False
        if key.startswith("min_") and observed < expected:
            return False
        if key.startswith("max_") and observed > expected:
            return False
    return True


def run_direct(command: CommandSpec, inputs: dict[str, Any], client: V2Client) -> dict[str, Any]:
    endpoint_id = command.endpoint_ids[0]
    endpoint = client.endpoint_specs[endpoint_id]
    usage = Usage(call_cap=min(command.max_calls, int(inputs.get("call_cap", command.max_calls))))
    params = _params(command, inputs, endpoint)
    try:
        response = client.fetch(endpoint_id, usage=usage, params=params)
        data = response["envelope"].get("data")
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        client_filters = dict(command.client_filters or {})
        filtered_items = [
            raw
            for raw in raw_items
            if isinstance(raw, dict) and _passes_client_filters(raw, client_filters)
        ]
        output_limit = int(inputs.get("limit", 20))
        rows = [_token_row(raw) for raw in filtered_items[:output_limit]]
        answer = {
            "contract": command.answer_contract,
            "ranking_basis": params.get("sort_by"),
            "sort_type": params.get("sort_type", "desc"),
            "filters": {
                key: value
                for key, value in params.items()
                if key.startswith(("min_", "max_")) or key in {"source", "graduated"}
            } | client_filters,
            "fetched_count": len(raw_items),
            "returned_count": len(rows),
            "has_next": data.get("has_next") if isinstance(data, dict) else None,
            "tokens": rows,
        }
        return {
            "schema_version": "3.0.0",
            "observed_at": utc_now(),
            "status": "complete",
            "answer": answer,
            "facts": {endpoint_id: data},
            "evidence": [{
                "endpoint_id": endpoint_id,
                "x402_path": endpoint["x402_path"],
                "evaluation_transport": "standard_api_counterpart",
                "cache_hit": response["cache_hit"],
                "status": "observed",
            }],
            "cost": usage.as_dict(),
            "limitations": [
                "Rankings describe the selected observed window and filters; they are not buy signals or future-return predictions."
            ],
            "errors": [],
        }
    except IntelligenceError as exc:
        return {
            "schema_version": "3.0.0",
            "observed_at": utc_now(),
            "status": "error",
            "answer": None,
            "facts": {},
            "evidence": [{"endpoint_id": endpoint_id, "x402_path": endpoint.get("x402_path"), "status": "failed"}],
            "cost": usage.as_dict(),
            "limitations": [],
            "errors": [exc.as_dict()],
        }
