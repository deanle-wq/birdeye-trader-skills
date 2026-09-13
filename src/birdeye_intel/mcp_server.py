"""Small stdio MCP adapter over the shared intelligence core."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .client import BirdeyeClient
from .core import IntelligenceError
from .workflows import BirdeyeIntelligence

TOOLS = [
    {
        "name": "quick-token-condition-screen",
        "description": "Inspect current Solana token conditions with evidence; no recommendation or execution.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["token_address"],
            "properties": {
                "token_address": {"type": "string"},
                "min_liquidity_usd": {"type": ["string", "number"], "default": "25000"},
                "max_top10_share_pct": {"type": ["string", "number"], "default": "50"},
            },
        },
    },
    {
        "name": "token-early-participant-analysis",
        "description": "Analyze indexed Solana early participants under wallet/page cost caps.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["token_address", "time_from", "time_to"],
            "properties": {
                "token_address": {"type": "string"},
                "time_from": {"type": "integer", "minimum": 1},
                "time_to": {"type": "integer", "minimum": 1},
                "max_wallets": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 10, "default": 2},
            },
        },
    },
    {
        "name": "token-holder-composition-analysis",
        "description": "Explain Solana holder shares, tags, denominator and completeness.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["token_address"],
            "properties": {
                "token_address": {"type": "string"},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 5, "default": 2},
            },
        },
    },
    {
        "name": "participant-exit-destination-trace",
        "description": "Trace observed Solana reductions and temporally subsequent destinations without causal claims.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["wallet_address", "token_address", "time_from", "time_to"],
            "properties": {
                "wallet_address": {"type": "string"},
                "token_address": {"type": "string"},
                "time_from": {"type": "integer", "minimum": 1},
                "time_to": {"type": "integer", "minimum": 1},
                "forward_window_seconds": {"type": "integer", "minimum": 1, "maximum": 604800, "default": 86400},
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 5, "default": 2},
            },
        },
    },
    {
        "name": "wallet-liquidity-adjusted-copyability",
        "description": "Model Solana wallet replication sensitivity under disclosed size, fee, liquidity and latency assumptions.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["wallet_address", "time_from", "time_to", "latency_seconds", "size_usd"],
            "properties": {
                "wallet_address": {"type": "string"},
                "time_from": {"type": "integer", "minimum": 1},
                "time_to": {"type": "integer", "minimum": 1},
                "latency_seconds": {"type": "integer", "minimum": 0},
                "size_usd": {"type": ["string", "number"]},
                "slippage_bps_override": {"type": ["string", "number", "null"]},
                "token_cap": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                "activity_page_cap": {"type": "integer", "minimum": 1, "maximum": 10, "default": 2},
            },
        },
    },
]


def _service() -> BirdeyeIntelligence:
    return BirdeyeIntelligence(BirdeyeClient())


def _call_tool(service: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "quick-token-condition-screen":
        return service.quick_screen(
            arguments["token_address"],
            min_liquidity_usd=arguments.get("min_liquidity_usd", "25000"),
            max_top10_share_pct=arguments.get("max_top10_share_pct", "50"),
        )
    if name == "token-early-participant-analysis":
        return service.early_participants(
            arguments["token_address"],
            early_window=(arguments["time_from"], arguments["time_to"]),
            max_wallets=arguments.get("max_wallets", 5),
            max_pages=arguments.get("max_pages", 2),
        )
    if name == "token-holder-composition-analysis":
        return service.holder_composition(
            arguments["token_address"], max_pages=arguments.get("max_pages", 2)
        )
    if name == "participant-exit-destination-trace":
        return service.exit_trace(
            arguments["wallet_address"],
            arguments["token_address"],
            lookback=(arguments["time_from"], arguments["time_to"]),
            forward_window_seconds=arguments.get("forward_window_seconds", 86400),
            max_pages=arguments.get("max_pages", 2),
        )
    if name == "wallet-liquidity-adjusted-copyability":
        return service.copyability(
            arguments["wallet_address"],
            lookback=(arguments["time_from"], arguments["time_to"]),
            latency_seconds=arguments["latency_seconds"],
            size_usd=arguments["size_usd"],
            slippage_bps_override=arguments.get("slippage_bps_override"),
            token_cap=arguments.get("token_cap", 5),
            activity_page_cap=arguments.get("activity_page_cap", 2),
        )
    raise ValueError("Unknown tool")


def handle_message(
    message: dict[str, Any],
    *,
    service_factory: Callable[[], Any] = _service,
) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    if request_id is None:
        return None
    if method == "initialize":
        result = {
            "protocolVersion": "2025-03-26",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "birdeye-trader-intelligence", "version": "0.1.0rc1"},
        }
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            structured = _call_tool(
                service_factory(), params.get("name"), params.get("arguments") or {}
            )
            result = {
                "content": [
                    {"type": "text", "text": json.dumps(structured, ensure_ascii=False, sort_keys=True)}
                ],
                "structuredContent": structured,
                "isError": structured.get("status") == "error",
            }
        except (IntelligenceError, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, IntelligenceError):
                error = exc.as_dict()
            else:
                error = {
                    "code": "invalid_input",
                    "endpoint_id": None,
                    "retryable": False,
                    "message": str(exc),
                    "details": {},
                }
            structured = {"status": "error", "errors": [error]}
            result = {
                "content": [
                    {"type": "text", "text": json.dumps(structured, ensure_ascii=False, sort_keys=True)}
                ],
                "structuredContent": structured,
                "isError": True,
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method not found"},
        }
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> int:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = handle_message(message)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
