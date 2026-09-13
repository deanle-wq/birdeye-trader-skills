"""V2 evaluation client generated from the endpoint allowlist."""

from __future__ import annotations

from decimal import Decimal
import json
from importlib.resources import files
import os
import random
import time
from typing import Any
from urllib.parse import urlencode

from ..client import BASE_URL, Transport, _default_transport
from ..core import (
    AuthenticationError,
    MemoryCache,
    RateLimited,
    UpstreamError,
    Usage,
    canonical_hash,
    validate_chain,
)


def load_endpoint_specs() -> dict[str, dict[str, Any]]:
    document = json.loads(files(__package__).joinpath("endpoints.json").read_text())
    if not isinstance(document, dict):
        raise ValueError("Invalid V2 endpoint asset")
    return document


def _json_safe_numbers(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe_numbers(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_json_safe_numbers(child) for child in value]
    return value


class V2Client:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 20.0,
        retries: int = 2,
        cache: MemoryCache | None = None,
        transport: Transport | None = None,
        endpoint_specs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("BIRDEYE_API_KEY") or os.getenv("API_KEY")
        self.timeout = timeout
        self.retries = max(0, min(retries, 2))
        self.cache = cache or MemoryCache()
        self.transport = transport or _default_transport
        self.endpoint_specs = endpoint_specs or load_endpoint_specs()

    def fetch(
        self,
        endpoint_id: str,
        *,
        usage: Usage,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        chain: str = "solana",
    ) -> dict[str, Any]:
        validate_chain(chain)
        spec = self.endpoint_specs.get(endpoint_id)
        if not spec or not spec.get("x402_eligible") or not spec.get("x402_path"):
            raise UpstreamError(
                "Endpoint is outside the Birdeye x402 surface allowed for V2 skills",
                endpoint_id=endpoint_id,
            )
        if not spec.get("approved"):
            raise UpstreamError("x402 endpoint is not allowlisted for V2 evaluation", endpoint_id=endpoint_id)
        if not self._api_key:
            raise AuthenticationError("Birdeye API key is not configured", endpoint_id=endpoint_id)
        params = {key: value for key, value in (params or {}).items() if value is not None}
        body = {key: value for key, value in (body or {}).items() if value is not None}
        cache_key = canonical_hash(
            {"endpoint_id": endpoint_id, "chain": chain, "params": params, "body": body}
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            usage.cache_hits += 1
            return {"endpoint_id": endpoint_id, "cache_hit": True, "envelope": cached}
        # Birdeye documents x402 routes as response-compatible with their
        # standard counterparts. Evaluation uses the API-key counterpart so QA
        # never signs or charges a payment; release eligibility still comes
        # exclusively from the audited x402 path above.
        url = f"{BASE_URL}{spec['standard_path']}"
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        payload = None
        headers = {
            "Accept": "application/json",
            "X-API-KEY": self._api_key,
            "x-chain": chain,
            "User-Agent": "birdeye-question-skills-v2/2.0.0rc1",
        }
        if spec["method"] == "POST":
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body, separators=(",", ":")).encode()
        attempt = 0
        while True:
            usage.preflight(endpoint_id)
            usage.add_cost(str(spec.get("cu") or "UNKNOWN"))
            try:
                status, raw, response_headers = self.transport(
                    spec["method"], url, headers, payload, self.timeout
                )
            except UpstreamError:
                if attempt >= self.retries:
                    raise
                attempt += 1
                usage.retries += 1
                time.sleep(min(0.1 * 2**attempt + random.random() * 0.05, 2.0))
                continue
            if status in {401, 403}:
                raise AuthenticationError("Birdeye authentication failed", endpoint_id=endpoint_id)
            retryable = status == 429 or 500 <= status <= 599
            if retryable and attempt < self.retries:
                attempt += 1
                usage.retries += 1
                retry_after = response_headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 0.1 * 2**attempt
                time.sleep(min(delay + random.random() * 0.05, 2.0))
                continue
            if status == 429:
                raise RateLimited("Birdeye rate limit reached", endpoint_id=endpoint_id)
            if status < 200 or status >= 300:
                raise UpstreamError(f"Birdeye request failed with HTTP {status}", endpoint_id=endpoint_id)
            try:
                envelope = _json_safe_numbers(json.loads(raw.decode(), parse_float=Decimal))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UpstreamError("Birdeye returned invalid JSON", endpoint_id=endpoint_id) from exc
            if not isinstance(envelope, dict) or envelope.get("success") is False:
                raise UpstreamError("Birdeye returned an unsuccessful envelope", endpoint_id=endpoint_id)
            usage.calls_succeeded += 1
            ttl = 3600 if "HISTOR" in spec.get("name", "").upper() else 15
            self.cache.set(cache_key, envelope, ttl)
            return {"endpoint_id": endpoint_id, "cache_hit": False, "envelope": envelope}
