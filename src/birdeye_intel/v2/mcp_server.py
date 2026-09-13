"""Generic MCP discovery and execution surface for the V2 question catalog."""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from ..core import IntelligenceError
from .catalog import Catalog
from .runtime import V2Runtime


TOOLS = [
    {"name": "birdeye-v2-list-skills", "description": "List one-question Birdeye skills by trader stage, domain or runtime status.", "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"stage": {"type": "string"}, "domain": {"type": "string"}, "runtime_status": {"type": "string"}}}},
    {"name": "birdeye-v2-describe-skill", "description": "Describe one V2 question, hierarchy path, dependencies, difficulty and pricing drivers.", "inputSchema": {"type": "object", "additionalProperties": False, "required": ["skill"], "properties": {"skill": {"type": "string"}}}},
    {"name": "birdeye-v2-route-question", "description": "Route a user question to the closest specific V2 skills without API calls.", "inputSchema": {"type": "object", "additionalProperties": False, "required": ["question"], "properties": {"question": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}}}},
    {"name": "birdeye-v2-run-skill", "description": "Run one evaluation V2 question contract and return its bounded Birdeye evidence plus a typed answer where implemented.", "inputSchema": {"type": "object", "additionalProperties": False, "required": ["skill", "inputs"], "properties": {"skill": {"type": "string"}, "inputs": {"type": "object"}}}},
]


def call_tool(name: str, arguments: dict[str, Any], *, runtime_factory: Callable[[], V2Runtime] = V2Runtime) -> dict[str, Any]:
    runtime = runtime_factory()
    if name == "birdeye-v2-list-skills":
        skills = runtime.catalog.list(stage=arguments.get("stage"), domain=arguments.get("domain"), runtime_status=arguments.get("runtime_status"))
        return {"schema_version": "2.0.0", "count": len(skills), "skills": [skill.as_dict() for skill in skills]}
    if name == "birdeye-v2-describe-skill":
        return {"schema_version": "2.0.0", "skill": runtime.catalog.get(arguments["skill"]).as_dict()}
    if name == "birdeye-v2-route-question":
        return {"schema_version": "2.0.0", "matches": runtime.catalog.route(arguments["question"], limit=arguments.get("limit", 5))}
    if name == "birdeye-v2-run-skill":
        return runtime.run(arguments["skill"], arguments["inputs"])
    raise ValueError("Unknown V2 tool")


def handle_message(message: dict[str, Any], *, runtime_factory: Callable[[], V2Runtime] = V2Runtime) -> dict[str, Any] | None:
    request_id = message.get("id")
    if request_id is None:
        return None
    method = message.get("method")
    if method == "initialize":
        result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "birdeye-question-skills-v2", "version": "2.0.0rc1"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}
        try:
            structured = call_tool(params.get("name", ""), params.get("arguments") or {}, runtime_factory=runtime_factory)
            result = {"content": [{"type": "text", "text": json.dumps(structured, ensure_ascii=False, sort_keys=True)}], "structuredContent": structured, "isError": structured.get("status") == "error"}
        except (IntelligenceError, KeyError, ValueError, TypeError) as exc:
            error = exc.as_dict() if isinstance(exc, IntelligenceError) else {"code": "invalid_input", "message": str(exc), "retryable": False, "endpoint_id": None, "details": {}}
            structured = {"schema_version": "2.0.0", "status": "error", "errors": [error]}
            result = {"content": [{"type": "text", "text": json.dumps(structured, ensure_ascii=False, sort_keys=True)}], "structuredContent": structured, "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> int:
    for line in sys.stdin:
        try:
            response = handle_message(json.loads(line))
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
