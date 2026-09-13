"""Cost-aware intent routing; no execution route exists."""

from __future__ import annotations

import re


ROUTES = {
    "atomic_token_facts": [r"\b(price|metadata|symbol|token info)\b", r"\btop holders?\b", r"\bwho bought early\b"],
    "quick-token-condition-screen": [r"\bcheck .*token\b", r"\brisk conditions?\b"],
    "token-early-participant-analysis": [r"\banaly[sz]e early (buyers|participants)\b"],
    "token-holder-composition-analysis": [r"\b(holder concentration|holder composition|analy[sz]e holders?)\b"],
    "atomic_wallet_facts": [r"\b(show|list).*(wallet )?(pnl|activity|holdings)\b", r"\brecent sells?\b"],
    "participant-exit-destination-trace": [r"\b(where|destination).*(after|following).*(sell|exit|reduction)\b"],
    "wallet-liquidity-adjusted-copyability": [r"\b(copied performance|copyability|latency.*liquidity)\b"],
    "reserved_wallet_follow_assessment": [r"\bworth following\b"],
    "reserved_wallet_behavior_profile": [r"\b(trading style|take profit)\b"],
    "reserved_wallet_comparison": [r"\bcompare .*wallets?\b"],
    "baseline_required": [r"\bwhat changed\b"],
    "execution_boundary": [
        r"^(please\s+)?(buy|sell|swap)\b",
        r"\b(buy|sell|swap)\s+(this|that|the|my|token)",
        r"\bshould\s+i\s+(buy|sell|swap)\b",
        r"\b(copy trade|place (an )?order|sign (a )?transaction)\b",
    ],
}


def route_intent(text: str, *, has_baseline: bool = False) -> str:
    normalized = text.strip().lower()
    if any(re.search(pattern, normalized) for pattern in ROUTES["execution_boundary"]):
        return "execution_boundary"
    if any(re.search(pattern, normalized) for pattern in ROUTES["baseline_required"]):
        return "caller-baseline-delta" if has_baseline else "baseline_required"
    for route, patterns in ROUTES.items():
        if route in {"execution_boundary", "baseline_required"}:
            continue
        if any(re.search(pattern, normalized) for pattern in patterns):
            return route
    return "unsupported_or_clarify"
