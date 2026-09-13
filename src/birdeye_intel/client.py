"""Allowlisted Birdeye Data API client with cache, retries, and call budgets."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import random
import time
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .core import (
    AuthenticationError,
    MemoryCache,
    RateLimited,
    UpstreamError,
    Usage,
    canonical_hash,
    validate_chain,
)

BASE_URL = "https://public-api.birdeye.so"


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    cu: str
    ttl: int


ENDPOINTS: dict[str, Endpoint] = {
    "EP-009": Endpoint("GET", "/defi/v3/token/meta-data/single", "5", 3600),
    "EP-010": Endpoint("GET", "/defi/token_security", "40", 300),
    "EP-011": Endpoint("GET", "/defi/v3/token/market-data", "12", 15),
    "EP-020": Endpoint("GET", "/defi/price", "3", 15),
    "EP-023": Endpoint("GET", "/defi/v3/ohlcv", "D23", 3600),
    "EP-025": Endpoint("POST", "/defi/v3/liquidity/latest/token", "U25", 15),
    "EP-029": Endpoint("GET", "/defi/token_creation_info", "50", 3600),
    "EP-031": Endpoint("GET", "/holder/v1/distribution", "35", 60),
    "EP-032": Endpoint("GET", "/token/v1/holder-profile", "35", 60),
    "EP-033": Endpoint("GET", "/token/v1/holder-positions", "50", 60),
    "EP-034": Endpoint("GET", "/token/v1/holder/chart", "25", 60),
    "EP-035": Endpoint("GET", "/token/v1/chart/tag-holdings", "U35", 60),
    "EP-037": Endpoint("GET", "/defi/v2/tokens/top_traders", "30", 60),
    "EP-038": Endpoint("GET", "/token/v1/first-buyers", "U38", 60),
    "EP-039": Endpoint("GET", "/defi/v3/token/txs", "15", 15),
    "EP-048": Endpoint("GET", "/trader/txs/seek_by_time", "10", 15),
    "EP-049": Endpoint("GET", "/wallet/v2/current-net-worth", "40", 60),
    "EP-053": Endpoint("GET", "/wallet/v2/pnl/summary", "30", 60),
    "EP-054": Endpoint("POST", "/wallet/v2/pnl/details", "40", 60),
    "EP-055": Endpoint("GET", "/wallet/v2/pnl/chart", "U55", 60),
    "EP-059": Endpoint("GET", "/wallet/v2/balance-change", "10", 15),
    "EP-060": Endpoint("POST", "/wallet/v2/transfer", "10", 15),
    "EP-061": Endpoint("POST", "/token/v1/transfer", "10", 15),
    "EP-062": Endpoint("POST", "/wallet/v2/tx/first-funded", "UB", 300),
    "EP-066": Endpoint("GET", "/defi/historical_price_unix", "6", 3600),
}

Transport = Callable[[str, str, dict[str, str], Optional[bytes], float], tuple[int, bytes, dict[str, str]]]


def _default_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: bytes | None,
    timeout: float,
) -> tuple[int, bytes, dict[str, str]]:
    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed allowlisted host
            return response.status, response.read(), dict(response.headers.items())
    except HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())
    except URLError as exc:
        raise UpstreamError("Birdeye transport failed") from exc


class BirdeyeClient:
    """A read-only client. It exposes no transaction or signing methods."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 15.0,
        retries: int = 2,
        cache: MemoryCache | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("BIRDEYE_API_KEY") or os.getenv("API_KEY")
        self.timeout = timeout
        self.retries = max(0, min(retries, 2))
        self.cache = cache or MemoryCache()
        self.transport = transport or _default_transport

    def fetch(
        self,
        endpoint_id: str,
        *,
        usage: Usage,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        chain: str = "solana",
        cache_ttl: int | None = None,
    ) -> dict[str, Any]:
        validate_chain(chain)
        endpoint = ENDPOINTS.get(endpoint_id)
        if endpoint is None:
            raise UpstreamError("Endpoint is not approved for build", endpoint_id=endpoint_id)
        if not self._api_key:
            raise AuthenticationError("Birdeye API key is not configured", endpoint_id=endpoint_id)

        params = {k: v for k, v in (params or {}).items() if v is not None}
        request_body = body or {}
        cache_key = canonical_hash(
            {"endpoint_id": endpoint_id, "chain": chain, "params": params, "body": request_body}
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            usage.cache_hits += 1
            return {"envelope": cached, "cache_hit": True, "endpoint_id": endpoint_id}

        url = f"{BASE_URL}{endpoint.path}"
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        payload = None
        headers = {
            "Accept": "application/json",
            "X-API-KEY": self._api_key,
            "x-chain": chain,
            "User-Agent": "birdeye-trader-intelligence/0.1.0",
        }
        if endpoint.method == "POST":
            payload = json.dumps(request_body, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"

        attempt = 0
        while True:
            usage.preflight(endpoint_id)
            usage.add_cost(endpoint.cu)
            try:
                status, raw, response_headers = self.transport(
                    endpoint.method, url, headers, payload, self.timeout
                )
            except UpstreamError:
                if attempt < self.retries:
                    attempt += 1
                    usage.retries += 1
                    time.sleep(min(0.1 * 2**attempt + random.random() * 0.05, 2.0))
                    continue
                raise
            if status in (401, 403):
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
                envelope = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise UpstreamError("Birdeye returned invalid JSON", endpoint_id=endpoint_id) from exc
            if not isinstance(envelope, dict):
                raise UpstreamError("Birdeye returned an invalid response envelope", endpoint_id=endpoint_id)
            if envelope.get("success") is False:
                raise UpstreamError("Birdeye returned an unsuccessful response", endpoint_id=endpoint_id)
            usage.calls_succeeded += 1
            ttl = endpoint.ttl if cache_ttl is None else max(0, min(cache_ttl, endpoint.ttl))
            self.cache.set(cache_key, envelope, ttl)
            return {"envelope": envelope, "cache_hit": False, "endpoint_id": endpoint_id}
