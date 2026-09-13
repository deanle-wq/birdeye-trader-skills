"""Live orchestration over approved Birdeye endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any

from .adapters import (
    _data,
    _envelope,
    normalize_copyability,
    normalize_activity_round_trips,
    normalize_early,
    normalize_exit,
    normalize_historical_point,
    normalize_holders,
    normalize_quick,
)
from .analysis import (
    analyze_copyability,
    analyze_early_participants,
    analyze_exit_trace,
    analyze_holder_composition,
    analyze_quick_screen,
)
from .client import BirdeyeClient
from .core import IntelligenceError, Usage, decimal_string, ratio_percent, validate_address, validate_chain


class BirdeyeIntelligence:
    def __init__(self, client: BirdeyeClient) -> None:
        self.client = client

    def _optional(
        self,
        endpoint_id: str,
        usage: Usage,
        errors: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        try:
            return self.client.fetch(endpoint_id, usage=usage, **kwargs)
        except IntelligenceError as exc:
            errors.append(exc.as_dict())
            return None

    @staticmethod
    def _attach_errors(result: dict[str, Any], errors: list[dict[str, Any]]) -> dict[str, Any]:
        result["errors"].extend(errors)
        if errors and result["status"] == "complete":
            result["status"] = "partial"
        return result

    def quick_screen(
        self,
        token_address: str,
        *,
        chain: str = "solana",
        min_liquidity_usd: Any = "25000",
        max_top10_share_pct: Any = "50",
    ) -> dict[str, Any]:
        validate_chain(chain)
        validate_address(token_address, "token address")
        usage = Usage(5)
        errors: list[dict[str, Any]] = []
        responses: dict[str, Any] = {}
        responses["EP-009"] = self.client.fetch(
            "EP-009", usage=usage, params={"address": token_address}, chain=chain
        )
        if not isinstance(_data(responses["EP-009"]), dict) or not _data(responses["EP-009"]).get("symbol"):
            facts = normalize_quick(responses, token_address)
            return analyze_quick_screen(token_address, facts, chain=chain, usage=usage)
        calls: list[tuple[str, dict[str, Any]]] = [
            ("EP-010", {"params": {"address": token_address}}),
            ("EP-011", {"params": {"address": token_address, "ui_amount_mode": "scaled"}}),
            ("EP-025", {"body": {"addresses": [token_address]}}),
            ("EP-031", {"params": {"token_address": token_address, "mode": "top", "top_n": 10, "limit": 10}}),
        ]
        for endpoint_id, kwargs in calls:
            response = self._optional(endpoint_id, usage, errors, chain=chain, **kwargs)
            if response is not None:
                responses[endpoint_id] = response
        result = analyze_quick_screen(
            token_address,
            normalize_quick(responses, token_address),
            chain=chain,
            min_liquidity_usd=min_liquidity_usd,
            max_top10_share_pct=max_top10_share_pct,
            usage=usage,
        )
        return self._attach_errors(result, errors)

    def early_participants(
        self,
        token_address: str,
        *,
        early_window: tuple[int, int],
        chain: str = "solana",
        max_wallets: int = 5,
        max_pages: int = 2,
    ) -> dict[str, Any]:
        validate_chain(chain)
        validate_address(token_address, "token address")
        if early_window[1] <= early_window[0]:
            raise ValueError("early_window must be increasing")
        max_wallets = max(1, min(max_wallets, 20))
        max_pages = max(1, min(max_pages, 10))
        usage = Usage(40)
        errors: list[dict[str, Any]] = []
        responses: dict[str, Any] = {}
        buyers: list[dict[str, Any]] = []
        for page in range(max_pages):
            response = self._optional(
                "EP-038",
                usage,
                errors,
                params={"token_address": token_address, "offset": page * 100, "limit": 100},
                chain=chain,
            )
            if response is None:
                break
            if page == 0:
                responses["EP-038"] = response
            data = _data(response)
            page_buyers = data.get("buyers") if isinstance(data, dict) else []
            if not isinstance(page_buyers, list) or not page_buyers:
                break
            buyers.extend(item for item in page_buyers if isinstance(item, dict))
            if len(page_buyers) < 100:
                break
        if "EP-038" not in responses:
            responses["EP-038"] = {"envelope": {"success": True, "data": {"buyers": []}}}
        else:
            root = _data(responses["EP-038"])
            if isinstance(root, dict):
                root["buyers"] = buyers
                root["has_next"] = len(buyers) >= max_pages * 100

        normalized = normalize_early(responses, token_address)
        if not normalized["buyers"]:
            result = analyze_early_participants(
                token_address, normalized, early_window=early_window, chain=chain, usage=usage
            )
            return self._attach_errors(result, errors)

        base_calls: list[tuple[str, dict[str, Any]]] = [
            ("EP-029", {"params": {"address": token_address}}),
            ("EP-025", {"body": {"addresses": [token_address]}}),
            ("EP-033", {"params": {"token_address": token_address, "limit": 50, "offset": 0}}),
            ("EP-037", {"params": {"address": token_address, "time_frame": "30d", "limit": 10}}),
            ("EP-039", {"params": {"address": token_address, "after_time": early_window[0], "before_time": early_window[1], "limit": 100}}),
        ]
        for endpoint_id, kwargs in base_calls:
            response = self._optional(endpoint_id, usage, errors, chain=chain, **kwargs)
            if response is not None:
                responses[endpoint_id] = response
        selected = [b.get("wallet_address") for b in buyers[:max_wallets] if isinstance(b.get("wallet_address"), str)]
        wallet_pnl: dict[str, Any] = {}
        for wallet in selected:
            summary = self._optional(
                "EP-053", usage, errors, params={"wallet": wallet, "duration": "30d"}, chain=chain
            )
            details = self._optional(
                "EP-054",
                usage,
                errors,
                body={"wallet": wallet, "duration": "30d", "limit": 10, "offset": 0},
                chain=chain,
            )
            wallet_pnl[wallet] = {"summary": _data(summary), "details": _data(details)}
        if selected:
            funded = self._optional(
                "EP-062", usage, errors, body={"wallets": selected, "token_address": token_address}, chain=chain
            )
            if funded is not None:
                responses["EP-062"] = funded
        result = analyze_early_participants(
            token_address,
            normalize_early(responses, token_address, wallet_pnl=wallet_pnl),
            early_window=early_window,
            chain=chain,
            usage=usage,
        )
        return self._attach_errors(result, errors)

    def holder_composition(
        self,
        token_address: str,
        *,
        chain: str = "solana",
        max_pages: int = 2,
    ) -> dict[str, Any]:
        validate_chain(chain)
        validate_address(token_address, "token address")
        max_pages = max(1, min(max_pages, 5))
        usage = Usage(12)
        errors: list[dict[str, Any]] = []
        responses: dict[str, Any] = {}
        distribution_holders: list[dict[str, Any]] = []
        distribution_total = None
        for page in range(max_pages):
            response = self._optional(
                "EP-031",
                usage,
                errors,
                params={
                    "token_address": token_address,
                    "mode": "top",
                    "top_n": 100,
                    "offset": page * 50,
                    "limit": 50,
                },
                chain=chain,
            )
            if response is None:
                break
            if page == 0:
                responses["EP-031"] = response
            page_data = _data(response)
            page_holders = page_data.get("holders") if isinstance(page_data, dict) else []
            summary = page_data.get("summary") if isinstance(page_data, dict) else None
            if isinstance(summary, dict) and isinstance(summary.get("wallet_count"), int):
                distribution_total = summary["wallet_count"]
            if not isinstance(page_holders, list) or not page_holders:
                break
            distribution_holders.extend(item for item in page_holders if isinstance(item, dict))
            if len(page_holders) < 50 or (
                distribution_total is not None and len(distribution_holders) >= distribution_total
            ):
                break
        first_distribution = _data(responses.get("EP-031"))
        if isinstance(first_distribution, dict):
            first_distribution["holders"] = distribution_holders
        calls: list[tuple[str, dict[str, Any]]] = [
            ("EP-032", {"params": {"token_address": token_address}}),
            ("EP-033", {"params": {"token_address": token_address, "limit": 50, "offset": 0}}),
            ("EP-034", {"params": {"token_address": token_address, "count": 20}}),
            ("EP-035", {"params": {"token_address": token_address}}),
            ("EP-010", {"params": {"address": token_address}}),
            ("EP-025", {"body": {"addresses": [token_address]}}),
        ]
        for endpoint_id, kwargs in calls:
            response = self._optional(endpoint_id, usage, errors, chain=chain, **kwargs)
            if response is not None:
                responses[endpoint_id] = response
        facts = normalize_holders(responses, token_address)
        facts["pagination_complete"] = distribution_total is not None and len(distribution_holders) >= distribution_total
        result = analyze_holder_composition(token_address, facts, chain=chain, usage=usage)
        return self._attach_errors(result, errors)

    def exit_trace(
        self,
        wallet_address: str,
        token_address: str,
        *,
        lookback: tuple[int, int],
        forward_window_seconds: int = 86400,
        chain: str = "solana",
        max_pages: int = 2,
    ) -> dict[str, Any]:
        validate_chain(chain)
        validate_address(wallet_address, "wallet address")
        validate_address(token_address, "token address")
        if lookback[1] <= lookback[0]:
            raise ValueError("lookback must be increasing")
        max_pages = max(1, min(max_pages, 5))
        usage = Usage(30)
        errors: list[dict[str, Any]] = []
        responses: dict[str, Any] = {}
        calls: list[tuple[str, dict[str, Any]]] = [
            ("EP-054", {"body": {"wallet": wallet_address, "duration": "90d", "limit": 20, "offset": 0}}),
            ("EP-020", {"params": {"address": token_address}}),
            ("EP-011", {"params": {"address": token_address}}),
            ("EP-049", {"params": {"wallet": wallet_address, "limit": 20}}),
            ("EP-062", {"body": {"wallets": [wallet_address], "token_address": token_address}}),
            ("EP-025", {"body": {"addresses": [token_address]}}),
        ]
        for endpoint_id, kwargs in calls:
            response = self._optional(endpoint_id, usage, errors, chain=chain, **kwargs)
            if response is not None:
                responses[endpoint_id] = response
        family_complete: dict[str, bool] = {}
        for endpoint_id, base_params in (
            (
                "EP-048",
                {"address": wallet_address, "after_time": lookback[0], "limit": 100},
            ),
            (
                "EP-059",
                {
                    "address": wallet_address,
                    "token_address": token_address,
                    "time_from": lookback[0],
                    "time_to": lookback[1],
                    "limit": 100,
                },
            ),
        ):
            merged_items: list[dict[str, Any]] = []
            complete = False
            for page in range(max_pages):
                params = dict(base_params)
                params["offset"] = page * 100
                response = self._optional(
                    endpoint_id, usage, errors, params=params, chain=chain
                )
                if response is None:
                    break
                if page == 0:
                    responses[endpoint_id] = response
                data = _data(response)
                page_items = data.get("items") if isinstance(data, dict) else []
                if not isinstance(page_items, list):
                    break
                merged_items.extend(item for item in page_items if isinstance(item, dict))
                has_next = bool(isinstance(data, dict) and data.get("has_next"))
                if not has_next or len(page_items) < 100:
                    complete = True
                    break
            root = _data(responses.get(endpoint_id))
            if isinstance(root, dict):
                root["items"] = merged_items
                root["has_next"] = not complete
            family_complete[endpoint_id] = complete
        for endpoint_id, entity_key, entity_value in (
            ("EP-060", "wallet", wallet_address),
            ("EP-061", "token_address", token_address),
        ):
            merged_transfers: list[dict[str, Any]] = []
            cursor = None
            complete = False
            for page in range(max_pages):
                body = {entity_key: entity_value}
                if cursor:
                    body["cursor"] = cursor
                else:
                    body.update(
                        {
                            "time_from": lookback[0],
                            "time_to": lookback[1] + forward_window_seconds,
                            "limit": 100,
                        }
                    )
                response = self._optional(
                    endpoint_id, usage, errors, body=body, chain=chain
                )
                if response is None:
                    break
                if page == 0:
                    responses[endpoint_id] = response
                data = _data(response)
                if isinstance(data, list):
                    merged_transfers.extend(item for item in data if isinstance(item, dict))
                cursor = _envelope(response).get("next_cursor")
                if not cursor:
                    complete = True
                    break
            first_envelope = _envelope(responses.get(endpoint_id))
            if isinstance(first_envelope, dict):
                first_envelope["data"] = merged_transfers
                first_envelope["next_cursor"] = None if complete else cursor
            family_complete[endpoint_id] = complete
        facts = normalize_exit(
            responses, token_address, window_end=lookback[1] + forward_window_seconds
        )
        facts["pagination_complete"] = all(
            family_complete.get(endpoint_id, False)
            for endpoint_id in ("EP-048", "EP-059", "EP-060", "EP-061")
        )
        result = analyze_exit_trace(
            wallet_address,
            token_address,
            facts,
            lookback=lookback,
            forward_window_seconds=forward_window_seconds,
            chain=chain,
            usage=usage,
        )
        return self._attach_errors(result, errors)

    def copyability(
        self,
        wallet_address: str,
        *,
        lookback: tuple[int, int],
        latency_seconds: int,
        size_usd: Any,
        chain: str = "solana",
        token_cap: int = 5,
        activity_page_cap: int = 2,
        slippage_bps_override: Any | None = None,
    ) -> dict[str, Any]:
        validate_chain(chain)
        validate_address(wallet_address, "wallet address")
        if lookback[1] <= lookback[0]:
            raise ValueError("lookback must be increasing")
        token_cap = max(1, min(token_cap, 20))
        activity_page_cap = max(1, min(activity_page_cap, 10))
        usage = Usage(50)
        errors: list[dict[str, Any]] = []
        responses: dict[str, Any] = {}
        base_calls: list[tuple[str, dict[str, Any]]] = [
            ("EP-053", {"params": {"wallet": wallet_address, "duration": "90d"}}),
            ("EP-054", {"body": {"wallet": wallet_address, "duration": "90d", "limit": token_cap, "offset": 0}}),
            ("EP-055", {"params": {"wallet": wallet_address, "time_from": datetime.fromtimestamp(lookback[0], timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), "time_to": datetime.fromtimestamp(lookback[1], timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}}),
            ("EP-049", {"params": {"wallet": wallet_address, "limit": token_cap}}),
        ]
        for endpoint_id, kwargs in base_calls:
            response = self._optional(endpoint_id, usage, errors, chain=chain, **kwargs)
            if response is not None:
                responses[endpoint_id] = response
        activity_items: list[dict[str, Any]] = []
        activity_complete = False
        for page in range(activity_page_cap):
            activity_response = self._optional(
                "EP-048",
                usage,
                errors,
                params={
                    "address": wallet_address,
                    "after_time": lookback[0],
                    "offset": page * 100,
                    "limit": 100,
                },
                chain=chain,
            )
            if activity_response is None:
                break
            if page == 0:
                responses["EP-048"] = activity_response
            activity_data = _data(activity_response)
            page_items = activity_data.get("items") if isinstance(activity_data, dict) else []
            if not isinstance(page_items, list):
                break
            activity_items.extend(item for item in page_items if isinstance(item, dict))
            has_next = bool(isinstance(activity_data, dict) and activity_data.get("has_next"))
            if not has_next or len(page_items) < 100:
                activity_complete = True
                break
        activity_root = _data(responses.get("EP-048"))
        if isinstance(activity_root, dict):
            activity_root["items"] = activity_items
            activity_root["has_next"] = not activity_complete
        details = _data(responses.get("EP-054"))
        tokens = details.get("tokens") if isinstance(details, dict) else []
        addresses = [item.get("address") for item in tokens if isinstance(item, dict) and isinstance(item.get("address"), str)][:token_cap]
        liquidity_by_token: dict[str, Any] = {}
        if addresses:
            liquidity_response = self._optional(
                "EP-025", usage, errors, body={"addresses": addresses}, chain=chain
            )
            data = _data(liquidity_response)
            items = data.get("items") if isinstance(data, dict) else []
            for item in items if isinstance(items, list) else []:
                if isinstance(item, dict) and isinstance(item.get("token"), str):
                    liquidity_by_token[item["token"]] = item.get("exit_liquidity_usd")
        matched, matched_pagination_complete = normalize_activity_round_trips(
            responses.get("EP-048"), set(addresses)
        )
        trade_cap = 10
        selected_matches = matched[:trade_cap]
        now = int(time.time())
        for trade in selected_matches:
            trade["current_exit_liquidity_usd"] = decimal_string(
                liquidity_by_token.get(trade.get("token"))
            )
            if latency_seconds == 0:
                trade["entry_latency_move_pct"] = "0"
                trade["exit_latency_move_pct"] = "0"
                trade["history_valid"] = True
                continue
            requested_times = [
                trade.get("entry_time"),
                trade.get("entry_time") + latency_seconds if isinstance(trade.get("entry_time"), int) else None,
                trade.get("exit_time"),
                trade.get("exit_time") + latency_seconds if isinstance(trade.get("exit_time"), int) else None,
            ]
            if any(not isinstance(value, int) or value > now for value in requested_times):
                continue
            points = []
            for requested in requested_times:
                history_response = self._optional(
                    "EP-066",
                    usage,
                    errors,
                    params={"address": trade.get("token"), "unixtime": requested},
                    chain=chain,
                )
                points.append(
                    normalize_historical_point(history_response, requested)
                    if history_response is not None
                    else None
                )
                if usage.cap_reached:
                    break
            if len(points) == 4 and all(point is not None for point in points):
                entry_move = ratio_percent(points[1]["price"] - points[0]["price"], points[0]["price"])
                exit_move = ratio_percent(points[3]["price"] - points[2]["price"], points[2]["price"])
                trade["entry_latency_move_pct"] = decimal_string(entry_move, "0.0001")
                trade["exit_latency_move_pct"] = decimal_string(exit_move, "0.0001")
                trade["history_valid"] = entry_move is not None and exit_move is not None
            if usage.cap_reached:
                break
        if selected_matches:
            facts = {
                "trades": selected_matches,
                "reported_summary": details.get("summary") if isinstance(details, dict) else None,
                "history_complete": (
                    matched_pagination_complete
                    and len(matched) <= trade_cap
                    and all(trade.get("history_valid") for trade in selected_matches)
                ),
                "pagination_complete": matched_pagination_complete and len(matched) <= trade_cap,
            }
        else:
            facts = normalize_copyability(responses, liquidity_by_token=liquidity_by_token)
        result = analyze_copyability(
            wallet_address,
            facts,
            lookback=lookback,
            latency_seconds=latency_seconds,
            size_usd=size_usd,
            slippage_bps_override=slippage_bps_override,
            chain=chain,
            usage=usage,
        )
        return self._attach_errors(result, errors)
