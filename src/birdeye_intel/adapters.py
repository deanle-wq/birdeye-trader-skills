"""Endpoint-specific normalization. No analytical verdicts live here."""

from __future__ import annotations

from typing import Any

from .core import decimal, decimal_string


def _envelope(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {}
    candidate = response.get("envelope", response)
    return candidate if isinstance(candidate, dict) else {}


def _data(response: Any) -> Any:
    return _envelope(response).get("data")


def normalize_quick(responses: dict[str, Any], token: str) -> dict[str, Any]:
    identity = _data(responses.get("EP-009"))
    security = _data(responses.get("EP-010"))
    market = _data(responses.get("EP-011"))
    liquidity_root = _data(responses.get("EP-025"))
    distribution = _data(responses.get("EP-031"))

    liquidity_item: dict[str, Any] | None = None
    if isinstance(liquidity_root, dict):
        items = liquidity_root.get("items")
        if isinstance(items, list):
            liquidity_item = next(
                (item for item in items if isinstance(item, dict) and item.get("token") == token),
                next((item for item in items if isinstance(item, dict)), None),
            )

    summary = distribution.get("summary") if isinstance(distribution, dict) else None
    holders = distribution.get("holders") if isinstance(distribution, dict) else None
    top10_share = None
    if isinstance(summary, dict):
        top10_share = summary.get("percent_of_supply")
    if top10_share is None and isinstance(security, dict):
        top10_share = security.get("top10HolderPercent")

    return {
        "identity": identity if isinstance(identity, dict) else None,
        "security": security if isinstance(security, dict) else None,
        "market": {
            "price_usd": decimal_string(market.get("price")) if isinstance(market, dict) else None,
            "market_cap_usd": decimal_string(market.get("market_cap")) if isinstance(market, dict) else None,
            "liquidity_usd": decimal_string(market.get("liquidity")) if isinstance(market, dict) else None,
            "holder_count": market.get("holder") if isinstance(market, dict) else None,
        }
        if isinstance(market, dict)
        else None,
        "liquidity": {
            "liquidity_usd": decimal_string(liquidity_item.get("liquidity_usd")),
            "exit_liquidity_usd": decimal_string(liquidity_item.get("exit_liquidity_usd")),
            "stable_liquidity_usd": decimal_string(liquidity_item.get("stable_liquidity_usd")),
            "price_usd": decimal_string(liquidity_item.get("price")),
        }
        if isinstance(liquidity_item, dict)
        else None,
        "distribution": {
            "wallet_count": summary.get("wallet_count") if isinstance(summary, dict) else None,
            "total_holding": str(summary.get("total_holding")) if isinstance(summary, dict) and summary.get("total_holding") is not None else None,
            "top10_share_pct": decimal_string(top10_share),
            "holders": holders if isinstance(holders, list) else [],
        }
        if isinstance(distribution, dict)
        else None,
    }

def normalize_early(
    responses: dict[str, Any],
    token: str,
    *,
    wallet_pnl: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = _data(responses.get("EP-038"))
    raw_buyers = root.get("buyers") if isinstance(root, dict) else None
    buyers: list[dict[str, Any]] = []
    for raw in raw_buyers if isinstance(raw_buyers, list) else []:
        if not isinstance(raw, dict):
            continue
        wallet = raw.get("wallet_address")
        pnl = (wallet_pnl or {}).get(wallet, {}) if isinstance(wallet, str) else {}
        buyers.append(
            {
                "wallet": wallet,
                "first_buy_time": raw.get("block_unix_time"),
                "acquired_amount": str(raw.get("initial_holding")) if raw.get("initial_holding") is not None else None,
                "current_amount": str(raw.get("current_holding")) if raw.get("current_holding") is not None else None,
                "acquired_usd": decimal_string(raw.get("first_buy_volume_usd")),
                "total_buy_usd": decimal_string(raw.get("total_buy_volume_usd")),
                "position_status": raw.get("position_status"),
                "tags": raw.get("tags") if isinstance(raw.get("tags"), list) else [],
                "funder": None,
                "pnl_available": bool(pnl),
                "pnl": pnl,
            }
        )
    creation = _data(responses.get("EP-029"))
    liquidity = normalize_quick({"EP-025": responses.get("EP-025")}, token).get("liquidity")
    return {
        "buyers": buyers,
        "creation": creation if isinstance(creation, dict) else None,
        "liquidity": liquidity,
        "page_summary": root.get("page_summary") if isinstance(root, dict) else None,
        "pagination_complete": not bool(root and root.get("has_next")),
    }


def normalize_holders(responses: dict[str, Any], token: str) -> dict[str, Any]:
    distribution = _data(responses.get("EP-031"))
    profile = _data(responses.get("EP-032"))
    positions = _data(responses.get("EP-033"))
    summary = distribution.get("summary") if isinstance(distribution, dict) else None
    holders_raw = distribution.get("holders") if isinstance(distribution, dict) else None
    holders = []
    for raw in holders_raw if isinstance(holders_raw, list) else []:
        if isinstance(raw, dict):
            holders.append(
                {
                    "wallet": raw.get("wallet"),
                    "amount": str(raw.get("holding")) if raw.get("holding") is not None else None,
                    "share_pct": decimal_string(raw.get("percent_of_supply")),
                }
            )
    tags: dict[str, str | None] = {}
    for raw in profile.get("tags", []) if isinstance(profile, dict) else []:
        if isinstance(raw, dict) and isinstance(raw.get("tag"), str):
            tags[raw["tag"]] = decimal_string(raw.get("percent_of_supply"))
    denominator = None
    direct_share = None
    if isinstance(summary, dict):
        denominator = str(summary.get("total_holding")) if summary.get("total_holding") is not None else None
        direct_share = decimal_string(summary.get("percent_of_supply"))
    return {
        "token": token,
        "denominator": denominator,
        "denominator_name": "EP-031 summary.total_holding",
        "direct_sample_share_pct": direct_share,
        "holders": holders,
        "tags": tags,
        "positions_available": isinstance(positions, list),
        "pagination_complete": True,
        "security": _data(responses.get("EP-010")),
        "liquidity": normalize_quick({"EP-025": responses.get("EP-025")}, token).get("liquidity"),
    }


def normalize_exit(
    responses: dict[str, Any],
    token: str,
    *,
    window_end: int,
) -> dict[str, Any]:
    changes_root = _data(responses.get("EP-059"))
    changes = changes_root.get("items") if isinstance(changes_root, dict) else []
    trades_root = _data(responses.get("EP-048"))
    trades = trades_root.get("items") if isinstance(trades_root, dict) else []
    sell_by_hash: dict[str, Any] = {}
    for trade in trades if isinstance(trades, list) else []:
        if not isinstance(trade, dict):
            continue
        tx_hash = trade.get("tx_hash")
        addresses = {
            (trade.get("base") or {}).get("address") if isinstance(trade.get("base"), dict) else None,
            (trade.get("quote") or {}).get("address") if isinstance(trade.get("quote"), dict) else None,
        }
        if token in addresses and isinstance(tx_hash, str):
            sell_by_hash[tx_hash] = trade.get("volume_usd")
    events = []
    for index, raw in enumerate(changes if isinstance(changes, list) else []):
        if not isinstance(raw, dict):
            continue
        token_info = raw.get("token_info") if isinstance(raw.get("token_info"), dict) else {}
        if token_info.get("address") != token and raw.get("address") != token:
            continue
        before = decimal(raw.get("pre_balance"))
        after = decimal(raw.get("post_balance"))
        if before is None or after is None or after >= before:
            continue
        tx_hash = raw.get("tx_hash")
        events.append(
            {
                "event_id": f"balance-leg-{index}",
                "tx_hash": tx_hash,
                "timestamp": raw.get("block_unix_time") or raw.get("time"),
                "position_before": decimal_string(before),
                "position_after": decimal_string(after),
                "sell_usd": decimal_string(sell_by_hash.get(tx_hash)),
            }
        )
    transfers = _data(responses.get("EP-060"))
    destinations = []
    for index, raw in enumerate(transfers if isinstance(transfers, list) else []):
        if not isinstance(raw, dict):
            continue
        timestamp = raw.get("unix_time") or raw.get("time")
        if isinstance(timestamp, (int, float)) and timestamp <= window_end:
            destinations.append(
                {
                    "event_id": f"transfer-{index}",
                    "timestamp": int(timestamp),
                    "category": "external_wallet_transfer",
                    "target": raw.get("to_address"),
                    "token": raw.get("token_address"),
                    "value_usd": decimal_string(raw.get("value")),
                    "tx_hash": raw.get("tx_hash"),
                }
            )
    return {
        "events": events,
        "destinations": destinations,
        "pagination_complete": not bool(
            isinstance(trades_root, dict) and trades_root.get("has_next")
        ),
    }


def normalize_copyability(
    responses: dict[str, Any],
    *,
    liquidity_by_token: dict[str, Any] | None = None,
) -> dict[str, Any]:
    details = _data(responses.get("EP-054"))
    raw_tokens = details.get("tokens") if isinstance(details, dict) else None
    trades = []
    for raw in raw_tokens if isinstance(raw_tokens, list) else []:
        if not isinstance(raw, dict):
            continue
        pricing = raw.get("pricing") if isinstance(raw.get("pricing"), dict) else {}
        quantity = raw.get("quantity") if isinstance(raw.get("quantity"), dict) else {}
        counts = raw.get("counts") if isinstance(raw.get("counts"), dict) else {}
        token = raw.get("address")
        liquidity = (liquidity_by_token or {}).get(token)
        trades.append(
            {
                "token": token,
                "symbol": raw.get("symbol"),
                "closed": bool(counts.get("total_buy") and counts.get("total_sell")),
                "observed_entry_price": decimal_string(pricing.get("avg_buy_cost")),
                "observed_exit_price": decimal_string(pricing.get("avg_sell_cost")),
                "observed_bought_amount": str(quantity.get("total_bought_amount")) if quantity.get("total_bought_amount") is not None else None,
                "observed_sold_amount": str(quantity.get("total_sold_amount")) if quantity.get("total_sold_amount") is not None else None,
                "last_trade_time": raw.get("last_trade_unix_time"),
                "current_exit_liquidity_usd": decimal_string(liquidity),
                "entry_latency_move_pct": None,
                "exit_latency_move_pct": None,
                "history_valid": False,
                "source_granularity": "token_aggregate",
            }
        )
    return {
        "trades": trades,
        "reported_summary": details.get("summary") if isinstance(details, dict) else None,
        "history_complete": False,
        "pagination_complete": False,
    }


def normalize_activity_round_trips(
    response: Any,
    allowed_tokens: set[str],
) -> tuple[list[dict[str, Any]], bool]:
    """FIFO-match token legs from wallet activity without inferring unsupported fills."""
    root = _data(response)
    raw_items = root.get("items") if isinstance(root, dict) else []
    items = sorted(
        (item for item in raw_items if isinstance(item, dict)),
        key=lambda item: item.get("block_unix_time") or 0,
    )
    lots: dict[str, list[dict[str, Any]]] = {token: [] for token in allowed_tokens}
    matched: list[dict[str, Any]] = []
    for item in items:
        timestamp = item.get("block_unix_time")
        if not isinstance(timestamp, int):
            continue
        for leg_name in ("base", "quote"):
            leg = item.get(leg_name)
            if not isinstance(leg, dict):
                continue
            token = leg.get("address")
            if token not in allowed_tokens:
                continue
            direction = leg.get("type_swap")
            amount = decimal(leg.get("ui_change_amount"))
            price = decimal(leg.get("price"))
            if amount is None or price is None or price <= 0:
                continue
            amount = abs(amount)
            if amount == 0:
                continue
            if direction == "to":
                lots[token].append({"amount": amount, "price": price, "timestamp": timestamp})
                continue
            if direction != "from":
                continue
            remaining = amount
            while remaining > 0 and lots[token]:
                lot = lots[token][0]
                used = min(remaining, lot["amount"])
                matched.append(
                    {
                        "token": token,
                        "closed": True,
                        "observed_entry_price": decimal_string(lot["price"]),
                        "observed_exit_price": decimal_string(price),
                        "observed_amount": decimal_string(used),
                        "entry_time": lot["timestamp"],
                        "exit_time": timestamp,
                        "entry_latency_move_pct": None,
                        "exit_latency_move_pct": None,
                        "history_valid": False,
                        "source_granularity": "fifo_activity_leg",
                    }
                )
                lot["amount"] -= used
                remaining -= used
                if lot["amount"] == 0:
                    lots[token].pop(0)
    pagination_complete = not bool(isinstance(root, dict) and root.get("has_next"))
    return matched, pagination_complete


def normalize_historical_point(
    response: Any,
    requested_time: int,
    *,
    maximum_gap_seconds: int = 120,
) -> dict[str, Any] | None:
    data = _data(response)
    if not isinstance(data, dict):
        return None
    timestamp = data.get("updateUnixTime")
    price = decimal(data.get("value"))
    if not isinstance(timestamp, int) or price is None or price <= 0:
        return None
    if timestamp > requested_time or requested_time - timestamp > maximum_gap_seconds:
        return None
    return {"timestamp": timestamp, "price": price}
