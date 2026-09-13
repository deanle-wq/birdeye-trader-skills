"""Pure, deterministic workflow calculations over normalized Birdeye facts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .core import (
    Usage,
    base_result,
    canonical_hash,
    condition,
    decimal,
    decimal_string,
    ratio_percent,
    set_coverage_confidence,
    threshold,
    utc_now,
    validate_address,
    validate_chain,
    validate_positive,
)


def _evidence(endpoint_id: str, evidence_type: str, field: str, value: Any, entity: str) -> dict[str, Any]:
    quality = "observed"
    if value is None:
        quality = "null"
    elif value == [] or value == {}:
        quality = "empty"
    elif value in (0, "0"):
        quality = "zero"
    return {
        "evidence_id": f"{endpoint_id.lower()}-{field.replace('.', '-')}",
        "type": evidence_type,
        "endpoint_id": endpoint_id,
        "source_path": field,
        "observed_at": utc_now(),
        "entity": entity,
        "field_path": field,
        "value": value,
        "unit": "text",
        "tx_hash": None,
        "event_timestamp": None,
        "quality": quality,
    }


def _apply_usage(result: dict[str, Any], usage: Usage | dict[str, Any] | None) -> None:
    if isinstance(usage, Usage):
        result["cost"] = usage.as_dict()
    elif isinstance(usage, dict):
        result["cost"] = usage


def analyze_quick_screen(
    token_address: str,
    facts: dict[str, Any],
    *,
    chain: str = "solana",
    min_liquidity_usd: Any = "25000",
    max_top10_share_pct: Any = "50",
    thresholds_overridden: bool = False,
    usage: Usage | dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_chain(chain)
    validate_address(token_address, "token address")
    min_liquidity = validate_positive(min_liquidity_usd, "min_liquidity_usd")
    max_top10 = validate_positive(max_top10_share_pct, "max_top10_share_pct")
    result = base_result("quick-token-condition-screen", "token", token_address)

    identity = facts.get("identity")
    security = facts.get("security")
    market = facts.get("market")
    liquidity = facts.get("liquidity")
    distribution = facts.get("distribution")
    result["facts"] = {
        "identity": identity,
        "security": security,
        "market": market,
        "liquidity": liquidity,
        "distribution": distribution,
    }
    result["evidence"] = [
        _evidence("EP-009", "identity", "data", identity, token_address),
        _evidence("EP-010", "security", "data", security, token_address),
        _evidence("EP-011", "market", "data", market, token_address),
        _evidence("EP-025", "liquidity", "data.items", liquidity, token_address),
        _evidence("EP-031", "holder", "data.summary", distribution, token_address),
    ]

    required_available = sum(value is not None for value in (identity, market, liquidity))
    optional_available = sum(value is not None for value in (security, distribution))
    if identity is None:
        result["status"] = "insufficient_data"
        result["summary"] = "No supported token identity was available for the supplied address."
        result["limitations"].append("The address may be valid on Solana without being an indexed token.")
    elif market is None or liquidity is None:
        result["status"] = "insufficient_data"
        result["summary"] = "Token identity was observed, but required current market or liquidity facts were unavailable."
    elif optional_available < 2:
        result["status"] = "partial"
        result["summary"] = "Current token conditions were observed with incomplete security or holder evidence."
    else:
        result["summary"] = "Current token, security, market, liquidity, holder and completeness conditions were observed."

    market_cap = decimal(market.get("market_cap_usd")) if isinstance(market, dict) else None
    liquidity_usd = decimal(liquidity.get("liquidity_usd")) if isinstance(liquidity, dict) else None
    top10 = decimal(distribution.get("top10_share_pct")) if isinstance(distribution, dict) else None
    liquidity_ratio = ratio_percent(liquidity_usd, market_cap)
    result["metrics"] = {
        "liquidity_to_market_cap_pct": decimal_string(liquidity_ratio, "0.0001"),
        "data_completeness_pct": decimal_string(
            Decimal(required_available + optional_available) / Decimal("5") * Decimal("100"), "0.01"
        ),
    }
    result["thresholds"] = [
        threshold(
            "min_liquidity_usd",
            min_liquidity,
            "usd",
            "methodology_1.0.0_heuristic",
            override=thresholds_overridden,
            sensitivity="Condition changes when observed liquidity crosses this value.",
        ),
        threshold(
            "max_top10_share_pct",
            max_top10,
            "percent",
            "methodology_1.0.0_heuristic",
            override=thresholds_overridden,
            sensitivity="Condition changes when observed top-10 share crosses this value.",
        ),
    ]
    liquidity_state = "unknown" if liquidity_usd is None else ("observed" if liquidity_usd < min_liquidity else "not_observed")
    top10_state = "unknown" if top10 is None else ("observed" if top10 > max_top10 else "not_observed")
    authority_values = []
    if isinstance(security, dict):
        authority_values = [security.get(key) for key in ("freezeAuthority", "mintAuthority", "metaplexUpdateAuthority")]
    authority_state = "unknown" if not authority_values or all(v is None for v in authority_values) else "observed"
    result["conditions"] = [
        condition(
            "authority_condition_observed",
            authority_state,
            description="At least one supported authority field is present; this does not establish intent.",
        ),
        condition(
            "liquidity_below_configured_context",
            liquidity_state,
            value=decimal_string(liquidity_usd),
            unit="usd",
            threshold_id="min_liquidity_usd",
            description="Current liquidity is compared with the disclosed caller/default context.",
        ),
        condition(
            "top10_share_above_configured_context",
            top10_state,
            value=decimal_string(top10),
            unit="percent",
            threshold_id="max_top10_share_pct",
            description="Observed top-10 share is compared with the disclosed caller/default context.",
        ),
        condition(
            "security_data_incomplete",
            "observed" if security is None or authority_state == "unknown" else "not_observed",
            description="Expected security fields are missing or null.",
        ),
        condition(
            "holder_data_incomplete",
            "observed" if distribution is None or top10 is None else "not_observed",
            description="Holder distribution or its share denominator is unavailable.",
        ),
    ]
    result["limitations"].extend(
        [
            "Current conditions do not establish legitimacy, future performance, or executable price impact.",
            "Security and holder fields can be null or incompletely indexed.",
        ]
    )
    set_coverage_confidence(
        result,
        required_available=required_available,
        required_total=3,
        optional_available=optional_available,
        optional_total=2,
        endpoint_factor=Decimal("0.85"),
    )
    snapshot_payload = {
        "schema_version": "1.0.0",
        "methodology_version": "1.0.0",
        "skill_slug": result["skill"],
        "chain": "solana",
        "entity": token_address,
        "observed_at": result["observed_at"],
        "facts": result["facts"],
        "coverage": result["coverage"],
        "source_endpoint_ids": ["EP-009", "EP-010", "EP-011", "EP-025", "EP-031"],
    }
    snapshot_payload["content_hash"] = canonical_hash(snapshot_payload)
    result["snapshot"] = snapshot_payload
    _apply_usage(result, usage)
    return result


def analyze_early_participants(
    token_address: str,
    facts: dict[str, Any],
    *,
    early_window: tuple[int, int],
    chain: str = "solana",
    retained_position_pct: Any = "5",
    large_entry_share_pct: Any = "20",
    usage: Usage | dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_chain(chain)
    validate_address(token_address, "token address")
    if not isinstance(early_window, tuple) or len(early_window) != 2 or early_window[1] <= early_window[0]:
        raise ValueError("early_window must contain increasing Unix-second bounds")
    retained_threshold = validate_positive(retained_position_pct, "retained_position_pct")
    large_threshold = validate_positive(large_entry_share_pct, "large_entry_share_pct")
    result = base_result("token-early-participant-analysis", "token", token_address)
    buyers = facts.get("buyers") if isinstance(facts.get("buyers"), list) else []
    result["facts"] = {"participants": buyers, "creation": facts.get("creation"), "liquidity": facts.get("liquidity")}
    result["thresholds"] = [
        threshold("retained_position_pct", retained_threshold, "percent", "methodology_1.0.0_heuristic", override=False, sensitivity="Changes retained/reduced segment counts."),
        threshold("large_entry_share_pct", large_threshold, "percent", "methodology_1.0.0_heuristic", override=False, sensitivity="Changes large-entry observation count."),
    ]
    if not buyers:
        result["status"] = "insufficient_data"
        result["summary"] = "No indexed first-buyer records were available for the requested token/window."
        result["limitations"].append("Empty enumeration is not evidence that no early participants existed.")
        set_coverage_confidence(result, required_available=0, required_total=2, endpoint_factor=Decimal("0.85"))
        _apply_usage(result, usage)
        return result

    total_usd = sum((decimal(b.get("acquired_usd"), default=Decimal("0")) or Decimal("0")) for b in buyers)
    sorted_usd = sorted((decimal(b.get("acquired_usd"), default=Decimal("0")) or Decimal("0") for b in buyers), reverse=True)
    top5 = sum(sorted_usd[:5], Decimal("0"))
    segments = {"retained_observed": 0, "reduced_observed": 0, "fully_reduced_observed": 0, "position_unknown": 0, "large_early_entry_observed": 0}
    position_evidence = 0
    funders: dict[str, int] = {}
    for buyer in buyers:
        acquired = decimal(buyer.get("acquired_amount"))
        current = decimal(buyer.get("current_amount"))
        share = ratio_percent(buyer.get("acquired_usd"), total_usd)
        if share is not None and share > large_threshold:
            segments["large_early_entry_observed"] += 1
        if acquired is None or acquired <= 0 or current is None:
            segments["position_unknown"] += 1
        else:
            position_evidence += 1
            retained = current / acquired * Decimal("100")
            if current == 0:
                segments["fully_reduced_observed"] += 1
            elif retained >= retained_threshold:
                segments["retained_observed"] += 1
            else:
                segments["reduced_observed"] += 1
        funder = buyer.get("funder")
        if isinstance(funder, str):
            funders[funder] = funders.get(funder, 0) + 1
    shared_funder_count = sum(count for count in funders.values() if count > 1)
    result["metrics"] = {
        "participant_count": len(buyers),
        "sampled_early_buy_usd": decimal_string(total_usd, "0.01"),
        "top5_entry_concentration_pct": decimal_string(ratio_percent(top5, total_usd), "0.0001"),
        "sample_churn_pct": decimal_string(ratio_percent(segments["fully_reduced_observed"], position_evidence), "0.0001"),
        "funding_overlap_pct": decimal_string(ratio_percent(shared_funder_count, len(buyers)), "0.0001") if funders else None,
        "segments": segments,
    }
    result["summary"] = f"Observed {len(buyers)} indexed early participants; position evidence was available for {position_evidence}."
    optional_available = sum(bool(facts.get(key)) for key in ("creation", "liquidity")) + sum(bool(b.get("pnl_available")) for b in buyers)
    pnl_evidence = sum(bool(b.get("pnl_available")) for b in buyers)
    if position_evidence < len(buyers) or pnl_evidence < len(buyers) or not facts.get("pagination_complete", True):
        result["status"] = "partial"
    result["limitations"].extend(
        [
            "First-buyer coverage depends on Birdeye indexing and launch-source coverage.",
            "Shared funding, timing, profit, tags, or retention do not establish common ownership or intent.",
            "Current positions can include transfers and activity outside the early window.",
            "Participant PnL coverage can be incomplete across protocols or capped enrichment.",
        ]
    )
    set_coverage_confidence(
        result,
        required_available=1 + int(position_evidence > 0),
        required_total=2,
        optional_available=optional_available,
        optional_total=2 + len(buyers),
        endpoint_factor=Decimal("0.85"),
        pagination_complete=bool(facts.get("pagination_complete", True)),
        truncated=not bool(facts.get("pagination_complete", True)),
    )
    result["evidence"] = [_evidence("EP-038", "trade", "data.buyers", buyers, token_address)]
    _apply_usage(result, usage)
    return result


def analyze_holder_composition(
    token_address: str,
    facts: dict[str, Any],
    *,
    chain: str = "solana",
    max_top10_share_pct: Any = "50",
    max_single_holder_share_pct: Any = "20",
    usage: Usage | dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_chain(chain)
    validate_address(token_address, "token address")
    max_top10 = validate_positive(max_top10_share_pct, "max_top10_share_pct")
    max_single = validate_positive(max_single_holder_share_pct, "max_single_holder_share_pct")
    result = base_result("token-holder-composition-analysis", "token", token_address)
    denominator = decimal(facts.get("denominator"))
    holders = facts.get("holders") if isinstance(facts.get("holders"), list) else []
    tags = facts.get("tags") if isinstance(facts.get("tags"), dict) else {}
    result["facts"] = {
        "denominator": decimal_string(denominator),
        "denominator_name": facts.get("denominator_name"),
        "sampled_holder_count": len(holders),
        "tags": tags,
        "liquidity": facts.get("liquidity"),
        "security": facts.get("security"),
    }
    result["thresholds"] = [
        threshold("max_top10_share_pct", max_top10, "percent", "methodology_1.0.0_heuristic", override=False, sensitivity="Changes the top-10 condition."),
        threshold("max_single_holder_share_pct", max_single, "percent", "methodology_1.0.0_heuristic", override=False, sensitivity="Changes the single-holder condition."),
    ]
    if denominator is None or denominator <= 0 or not holders:
        result["status"] = "insufficient_data"
        result["summary"] = "A usable holder denominator and sampled holder set were not both available."
        result["limitations"].append("Concentration is omitted when its denominator is missing or non-positive.")
        set_coverage_confidence(result, required_available=0, required_total=2, endpoint_factor=Decimal("0.85"))
        _apply_usage(result, usage)
        return result
    ordered = sorted(
        holders,
        key=lambda h: decimal(h.get("amount"), default=Decimal("0")) or Decimal("0"),
        reverse=True,
    )
    direct_shares = [decimal(h.get("share_pct")) for h in ordered]
    if all(value is not None for value in direct_shares):
        shares = [value for value in direct_shares if value is not None]
        top1 = shares[0]
        top10 = sum(shares[:10], Decimal("0"))
        topn = sum(shares, Decimal("0"))
        share_method = "provider_percent_of_supply"
    else:
        amounts = [decimal(h.get("amount"), default=Decimal("0")) or Decimal("0") for h in ordered]
        top1 = ratio_percent(amounts[0], denominator)
        top10 = ratio_percent(sum(amounts[:10], Decimal("0")), denominator)
        topn = ratio_percent(sum(amounts, Decimal("0")), denominator)
        share_method = "amount_over_disclosed_denominator"
    direct = decimal(facts.get("direct_sample_share_pct"))
    tolerance_ok = None if direct is None or topn is None else abs(direct - topn) <= Decimal("0.001")
    tag_metrics = {key: decimal_string(value, "0.0001") for key, value in tags.items()}
    result["metrics"] = {
        "top1_share_pct": decimal_string(top1, "0.0001"),
        "top10_share_pct": decimal_string(top10, "0.0001"),
        "topN_share_pct": decimal_string(topn, "0.0001"),
        "supported_tag_share_pct": tag_metrics,
        "direct_derived_within_tolerance": tolerance_ok,
        "share_method": share_method,
    }
    result["conditions"] = [
        condition("top10_share_above_configured_context", "observed" if top10 and top10 > max_top10 else "not_observed", value=decimal_string(top10), unit="percent", threshold_id="max_top10_share_pct", description="Observed top-10 concentration exceeds the configured context."),
        condition("single_holder_above_configured_context", "observed" if top1 and top1 > max_single else "not_observed", value=decimal_string(top1), unit="percent", threshold_id="max_single_holder_share_pct", description="Observed largest-holder share exceeds the configured context."),
        condition("supported_tag_activity_observed", "observed" if any((decimal(v) or Decimal("0")) > 0 for v in tags.values()) else "not_observed", description="At least one Birdeye-supported holder tag has a positive observed share; this does not establish identity or intent."),
    ]
    result["summary"] = f"Calculated holder composition for {len(holders)} sampled holders using the disclosed denominator."
    pagination_complete = bool(facts.get("pagination_complete", True))
    if not pagination_complete or tolerance_ok is False:
        result["status"] = "partial"
    result["limitations"].extend(
        [
            "Concentration depends on the disclosed denominator and any provider-side exclusions.",
            "Holder tags and charts can be incompletely backfilled.",
            "Address categories do not establish common control or future action.",
        ]
    )
    set_coverage_confidence(
        result,
        required_available=2,
        required_total=2,
        optional_available=sum(bool(v) for v in (tags, facts.get("liquidity"), facts.get("security"))),
        optional_total=3,
        endpoint_factor=Decimal("0.85"),
        pagination_complete=pagination_complete,
        truncated=not pagination_complete,
    )
    result["evidence"] = [_evidence("EP-031", "holder", "data.holders", holders, token_address)]
    _apply_usage(result, usage)
    return result


def analyze_exit_trace(
    wallet_address: str,
    token_address: str,
    facts: dict[str, Any],
    *,
    lookback: tuple[int, int],
    minimum_exit_pct: Any = "20",
    minimum_exit_usd: Any = "1000",
    forward_window_seconds: int = 86400,
    chain: str = "solana",
    usage: Usage | dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_chain(chain)
    validate_address(wallet_address, "wallet address")
    validate_address(token_address, "token address")
    if lookback[1] <= lookback[0] or forward_window_seconds <= 0 or forward_window_seconds > 604800:
        raise ValueError("Invalid lookback or forward window")
    min_pct = validate_positive(minimum_exit_pct, "minimum_exit_pct")
    min_usd = validate_positive(minimum_exit_usd, "minimum_exit_usd")
    result = base_result("participant-exit-destination-trace", "wallet", wallet_address)
    events = facts.get("events") if isinstance(facts.get("events"), list) else []
    destinations = facts.get("destinations") if isinstance(facts.get("destinations"), list) else []
    qualified = []
    observed_sells = []
    for event in events:
        before = decimal(event.get("position_before"))
        after = decimal(event.get("position_after"))
        sell_usd = decimal(event.get("sell_usd"))
        reduction = None if before is None or after is None else max(Decimal("0"), before - after)
        reduction_pct = ratio_percent(reduction, before)
        normalized = dict(event)
        normalized["reduction_amount"] = decimal_string(reduction)
        normalized["reduction_pct"] = decimal_string(reduction_pct, "0.0001")
        if reduction_pct is not None and sell_usd is not None and reduction_pct >= min_pct and sell_usd >= min_usd:
            qualified.append(normalized)
        else:
            observed_sells.append(normalized)
    if not events:
        result["status"] = "insufficient_data"
        result["summary"] = "No supported position-reduction events were available in the bounded window."
        result["facts"] = {"qualifying_reductions": [], "other_observed_reductions": []}
        pagination_complete = bool(facts.get("pagination_complete", True))
        set_coverage_confidence(
            result,
            required_available=0,
            required_total=2,
            endpoint_factor=Decimal("0.85"),
            history_factor=Decimal("0.5"),
            pagination_complete=pagination_complete,
            truncated=not pagination_complete,
        )
        _apply_usage(result, usage)
        return result
    matched_destinations = []
    for destination in destinations:
        timestamp = destination.get("timestamp")
        if not isinstance(timestamp, int):
            continue
        if any(event.get("timestamp") < timestamp <= event.get("timestamp") + forward_window_seconds for event in qualified if isinstance(event.get("timestamp"), int)):
            matched_destinations.append(destination)
    result["facts"] = {
        "qualifying_reductions": qualified,
        "other_observed_reductions": observed_sells,
        "subsequent_destination_evidence": matched_destinations,
        "unattributed_destination_count": max(0, len(destinations) - len(matched_destinations)),
    }
    result["metrics"] = {
        "qualifying_reduction_count": len(qualified),
        "destination_evidence_count": len(matched_destinations),
    }
    result["thresholds"] = [
        threshold("minimum_exit_pct", min_pct, "percent", "methodology_1.0.0_heuristic", override=False, sensitivity="Changes which observed reductions qualify."),
        threshold("minimum_exit_usd", min_usd, "usd", "methodology_1.0.0_heuristic", override=False, sensitivity="Changes which observed reductions qualify."),
    ]
    if not qualified:
        result["status"] = "insufficient_data"
        result["summary"] = "Observed reductions did not meet both disclosed qualification thresholds."
    elif not matched_destinations or not facts.get("pagination_complete", True):
        result["status"] = "partial"
        result["summary"] = f"Observed {len(qualified)} qualifying reduction events; subsequent destination evidence was incomplete or unavailable."
    else:
        result["summary"] = f"Observed {len(qualified)} qualifying reduction events and {len(matched_destinations)} temporally subsequent destination records."
    result["limitations"].extend(
        [
            "Temporal ordering does not prove that observed proceeds funded later activity.",
            "Transfer destinations and address ownership remain unknown without direct supported evidence.",
            "Position denominators can be incomplete when earlier or unsupported activity is missing.",
            "Current liquidity is context and is not historical event liquidity.",
        ]
    )
    set_coverage_confidence(
        result,
        required_available=int(bool(events)) + int(bool(qualified)),
        required_total=2,
        optional_available=int(bool(matched_destinations)),
        optional_total=1,
        endpoint_factor=Decimal("0.85"),
        history_factor=Decimal("0.75") if not facts.get("pagination_complete", True) else Decimal("1"),
        pagination_complete=bool(facts.get("pagination_complete", True)),
        truncated=not bool(facts.get("pagination_complete", True)),
    )
    result["evidence"] = [_evidence("EP-059", "trade", "data.items", events, wallet_address), _evidence("EP-060", "transfer", "data", matched_destinations, wallet_address)]
    _apply_usage(result, usage)
    return result


def analyze_copyability(
    wallet_address: str,
    facts: dict[str, Any],
    *,
    lookback: tuple[int, int],
    latency_seconds: int,
    size_usd: Any,
    fee_bps: Any = "30",
    slippage_bps_override: Any | None = None,
    chain: str = "solana",
    usage: Usage | dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_chain(chain)
    validate_address(wallet_address, "wallet address")
    if lookback[1] <= lookback[0] or latency_seconds < 0:
        raise ValueError("Invalid lookback or latency_seconds")
    size = validate_positive(size_usd, "size_usd")
    fee = decimal(fee_bps)
    if fee is None or fee < 0:
        raise ValueError("fee_bps must be non-negative")
    override = decimal(slippage_bps_override) if slippage_bps_override is not None else None
    if override is not None and override < 0:
        raise ValueError("slippage_bps_override must be non-negative")
    result = base_result("wallet-liquidity-adjusted-copyability", "wallet", wallet_address)
    trades = facts.get("trades") if isinstance(facts.get("trades"), list) else []
    eligible = []
    excluded = []
    for trade in trades:
        entry = decimal(trade.get("observed_entry_price"))
        exit_price = decimal(trade.get("observed_exit_price"))
        liquidity = decimal(trade.get("current_exit_liquidity_usd"))
        if not trade.get("closed"):
            excluded.append({"token": trade.get("token"), "reason": "open_or_unmatched"})
            continue
        if entry is None or entry <= 0 or exit_price is None or exit_price < 0:
            excluded.append({"token": trade.get("token"), "reason": "invalid_price"})
            continue
        if override is None and (liquidity is None or liquidity <= 0):
            excluded.append({"token": trade.get("token"), "reason": "liquidity_unavailable"})
            continue
        slippage = override if override is not None else min(Decimal("10000"), size / liquidity * Decimal("10000"))
        entry_move = decimal(trade.get("entry_latency_move_pct"))
        exit_move = decimal(trade.get("exit_latency_move_pct"))
        history_valid = bool(trade.get("history_valid"))
        if latency_seconds > 0 and (entry_move is None or exit_move is None or not history_valid):
            excluded.append({"token": trade.get("token"), "reason": "latency_history_unavailable"})
            continue
        entry_move = entry_move or Decimal("0")
        exit_move = exit_move or Decimal("0")
        adjusted_entry = entry * (Decimal("1") + entry_move / Decimal("100") + slippage / Decimal("10000"))
        adjusted_exit = max(Decimal("0"), exit_price * (Decimal("1") + exit_move / Decimal("100") - slippage / Decimal("10000")))
        if adjusted_entry <= 0:
            excluded.append({"token": trade.get("token"), "reason": "adjusted_entry_non_positive"})
            continue
        quantity = size / adjusted_entry
        entry_fee = size * fee / Decimal("10000")
        exit_notional = quantity * adjusted_exit
        exit_fee = exit_notional * fee / Decimal("10000")
        pnl = exit_notional - size - entry_fee - exit_fee
        eligible.append(
            {
                "token": trade.get("token"),
                "source_granularity": trade.get("source_granularity", "trade"),
                "slippage_bps": decimal_string(slippage, "0.0001"),
                "adjusted_entry_price": decimal_string(adjusted_entry, "0.00000001"),
                "adjusted_exit_price": decimal_string(adjusted_exit, "0.00000001"),
                "scenario_quantity": decimal_string(quantity),
                "adjusted_pnl_usd": decimal_string(pnl, "0.01"),
                "adjusted_return_pct": decimal_string(ratio_percent(pnl, size), "0.0001"),
            }
        )
    result["facts"] = {
        "reported_summary": facts.get("reported_summary"),
        "eligible_scenarios": eligible,
        "excluded_trades": excluded,
    }
    aggregate_pnl = sum((decimal(item["adjusted_pnl_usd"], default=Decimal("0")) or Decimal("0")) for item in eligible)
    result["metrics"] = {
        "observed_trade_records": len(trades),
        "eligible_trade_count": len(eligible),
        "excluded_trade_count": len(excluded),
        "aggregate_adjusted_pnl_usd": decimal_string(aggregate_pnl, "0.01") if eligible else None,
        "latency_seconds": latency_seconds,
        "size_usd": decimal_string(size, "0.01"),
        "fee_bps": decimal_string(fee, "0.0001"),
    }
    if not eligible:
        result["status"] = "insufficient_data"
        result["summary"] = "No supported closed observations had all required price, liquidity and latency-history inputs."
    elif any(item["reason"] != "open_or_unmatched" for item in excluded) or not facts.get("history_complete", False) or not facts.get("pagination_complete", False):
        result["status"] = "partial"
        result["summary"] = f"Calculated disclosed scenarios for {len(eligible)} supported closed observations; {len(excluded)} records were excluded."
    else:
        result["summary"] = f"Calculated disclosed size, fee, liquidity and latency scenarios for {len(eligible)} closed observations."
    result["limitations"].extend(
        [
            "This is a sensitivity analysis, not an exact backtest, executable quote, or prediction.",
            "Current liquidity is a disclosed proxy when historical liquidity is unavailable.",
            "Protocol history, fills, priority fees, failed transactions, MEV and capital overlap can be incomplete.",
            "The result does not establish that future replication is possible or profitable.",
        ]
    )
    set_coverage_confidence(
        result,
        required_available=int(bool(trades)) + int(bool(eligible)),
        required_total=2,
        optional_available=0,
        optional_total=1,
        endpoint_factor=Decimal("0.85"),
        history_factor=Decimal("1") if facts.get("history_complete") else Decimal("0.5"),
        pagination_complete=bool(facts.get("pagination_complete", False)),
        truncated=not bool(facts.get("pagination_complete", False)),
    )
    result["evidence"] = [_evidence("EP-054", "wallet", "data.tokens", trades, wallet_address)]
    _apply_usage(result, usage)
    return result
