#!/usr/bin/env python3
"""Live-smoke every READY_ATOMIC V2 skill without persisting entity data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from birdeye_intel.v2.catalog import Catalog
from birdeye_intel.v2.runtime import V2Runtime
from birdeye_intel.v2.wave0 import WAVE0_SLUGS, validate_wave0_answer
from birdeye_intel.v2.wave1 import WAVE1_SLUGS, validate_wave1_answer


BASE_URL = "https://public-api.birdeye.so"
WSOL = "So11111111111111111111111111111111111111112"
MARKET_TOKEN = "J3Dhvhga7QwgLWUGn43caDJtaoUTkDLmiMGqstS2Dw8A"
LAUNCH_TOKEN = "HHuLN58RAJoyNxwYte8NdEyV7dhQzDCLXDmTraHspump"
SENSITIVE_EXCERPT_KEY_PARTS = (
    "address",
    "wallet",
    "hash",
    "owner",
    "creator",
    "pool",
    "logo",
    "uri",
    "authority",
)
ON_CHAIN_IDENTIFIER_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,88}$")


def get(path: str, params: dict[str, Any], key: str) -> dict[str, Any]:
    request = Request(
        f"{BASE_URL}{path}?{urlencode(params)}",
        headers={"X-API-KEY": key, "x-chain": "solana", "Accept": "application/json"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
        return json.loads(response.read())


def bootstrap(key: str) -> tuple[str, list[str], str]:
    market = get(
        "/defi/v2/markets",
        {"address": MARKET_TOKEN, "sort_type": "desc", "sort_by": "liquidity", "limit": 1},
        key,
    )
    pair = market["data"]["items"][0]["address"]
    traders = get(
        "/defi/v2/tokens/top_traders",
        {"address": MARKET_TOKEN, "time_frame": "30d", "sort_type": "desc", "sort_by": "volume", "limit": 2},
        key,
    )
    wallets = list(
        dict.fromkeys(
            item["owner"]
            for item in traders["data"]["items"]
            if isinstance(item, dict) and item.get("owner")
        )
    )
    launch_detail = get(
        "/defi/v3/token/meme/detail/single",
        {"address": LAUNCH_TOKEN},
        key,
    )
    creator = launch_detail.get("data", {}).get("meme_info", {}).get("creator")
    if not wallets or not creator:
        raise RuntimeError("Live bootstrap did not return the required wallet fixtures")
    return pair, wallets, creator


def shape(value: Any, depth: int = 0) -> Any:
    if depth >= 3:
        return type(value).__name__
    if isinstance(value, dict):
        return {key: shape(child, depth + 1) for key, child in sorted(value.items())[:30]}
    if isinstance(value, list):
        return [shape(value[0], depth + 1)] if value else []
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def sanitized_answer_excerpt(answer: Any, depth: int = 0) -> Any:
    """Keep user-visible live values while removing on-chain identifiers."""
    if depth >= 5:
        return "[depth-limited]"
    if isinstance(answer, dict):
        return {
            key: sanitized_answer_excerpt(value, depth + 1)
            for key, value in answer.items()
            if key != "event_id"
            and not any(part in key.lower() for part in SENSITIVE_EXCERPT_KEY_PARTS)
        }
    if isinstance(answer, list):
        return [sanitized_answer_excerpt(value, depth + 1) for value in answer[:3]]
    if isinstance(answer, str) and ON_CHAIN_IDENTIFIER_RE.fullmatch(answer):
        return "[redacted-on-chain-identifier]"
    return answer


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--skill", action="append", help="Optional skill slug filter")
    args = parser.parse_args()
    key = os.getenv("BIRDEYE_API_KEY") or os.getenv("API_KEY")
    if not key:
        raise SystemExit("BIRDEYE_API_KEY or API_KEY is required")
    pair, wallets, creator = bootstrap(key)
    wallet = wallets[0]
    now = int(time.time())
    base_inputs = {
        "chain": "solana",
        "query": "SOL",
        "token_address": MARKET_TOKEN,
        "token_addresses": [MARKET_TOKEN, WSOL],
        "wallet_address": wallet,
        "wallet_addresses": [wallet],
        "pair_address": pair,
        "pair_addresses": [pair],
        "time_from": now - 86_400,
        "time_to": now,
        "before_time": now,
        "developer_wallet_address": creator,
        "resolution": "1H",
        "unixtime": now - 3_600,
        "call_cap": 10,
    }
    runtime = V2Runtime()
    results = []
    skills = Catalog().list(runtime_status="READY_ATOMIC")
    selected = set(args.skill or [])
    known = {skill.slug for skill in skills}
    unknown = selected - known
    if unknown:
        raise SystemExit(f"Unknown or non-atomic skill filters: {', '.join(sorted(unknown))}")
    if selected:
        skills = [skill for skill in skills if skill.slug in selected]
    for skill in skills:
        inputs = dict(base_inputs)
        if skill.slug in {
            "token-identity-resolver",
            "token-metadata",
            "token-valuation-snapshot",
            "current-token-price",
            "token-market-activity",
            "token-kline-data",
        }:
            inputs["token_address"] = WSOL
            inputs["token_addresses"] = [WSOL]
        if skill.slug == "bonding-curve-token-stages":
            inputs["token_address"] = LAUNCH_TOKEN
            inputs["token_addresses"] = [LAUNCH_TOKEN]
        if skill.slug in {"top-token-traders", "top-trader-performance"}:
            inputs["time_frame"] = "30d"
        if skill.slug == "kol-trades":
            inputs["wallet_addresses"] = wallets[:2]
        if skill.slug == "token-transfers":
            inputs["token_address"] = WSOL
            inputs["token_addresses"] = [WSOL]
        result = runtime.run(skill.slug, inputs)
        answer = result.get("answer")
        answer_contract_errors = (
            validate_wave0_answer(answer)
            if skill.slug in WAVE0_SLUGS
            else validate_wave1_answer(answer)
            if skill.slug in WAVE1_SLUGS
            else []
        )
        answer_status = answer.get("status") if isinstance(answer, dict) else None
        canonical_answer_expected = skill.slug in WAVE0_SLUGS | WAVE1_SLUGS
        canonical_answer_present = isinstance(answer, dict)
        evidence_passed = (
            result["status"] == "complete"
            and result.get("completeness", {}).get("endpoints_succeeded")
            == len(skill.endpoint_ids)
            and not result.get("errors")
        )
        user_answer_passed = (
            canonical_answer_present
            and not answer_contract_errors
            and answer_status in {"complete", "partial", "empty"}
        )
        passed = evidence_passed and (
            not canonical_answer_expected or user_answer_passed
        )
        results.append(
            {
                "skill_id": skill.skill_id,
                "slug": skill.slug,
                "passed": passed,
                "evidence_passed": evidence_passed,
                "status": result["status"],
                "canonical_answer_expected": canonical_answer_expected,
                "canonical_answer_present": canonical_answer_present,
                "user_answer_passed": user_answer_passed,
                "answer_status": answer_status,
                "answer_schema_version": answer.get("schema_version") if isinstance(answer, dict) else None,
                "answer_contract_errors": answer_contract_errors,
                "answer_field_states": answer.get("field_states") if isinstance(answer, dict) else None,
                "answer_field_shapes": shape(answer.get("fields")) if isinstance(answer, dict) else None,
                "answer_freshness": {
                    "classification": answer.get("freshness", {}).get("classification"),
                    "age_seconds": answer.get("freshness", {}).get("age_seconds"),
                } if isinstance(answer, dict) else None,
                "answer_pagination": answer.get("pagination") if isinstance(answer, dict) else None,
                "answer_coverage": answer.get("coverage") if isinstance(answer, dict) else None,
                "user_answer_excerpt": {
                    "status": answer_status,
                    "fields": sanitized_answer_excerpt(answer.get("fields")),
                    "coverage": answer.get("coverage"),
                    "pagination": answer.get("pagination"),
                    "limitations": answer.get("limitations", [])[:3],
                } if isinstance(answer, dict) else None,
                "evidence": result["evidence"],
                "completeness": result["completeness"],
                "cost": result["cost"],
                "fact_shapes": {endpoint_id: shape(value) for endpoint_id, value in result["facts"].items() if endpoint_id.startswith("EP-")},
                "errors": result["errors"],
            }
        )
        time.sleep(0.1)
    report = {
        "schema_version": "2.0.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "Birdeye standard API counterparts for x402-eligible routes through V2 runtime",
        "endpoint_surface_policy": "BIRDEYE_X402_ONLY",
        "evaluation_transport": "API-key standard counterpart; no x402 payment or eligibility expansion",
        "sanitization": "API keys, headers, raw facts, wallet addresses, pair addresses and transaction identifiers are omitted.",
        "fixtures": {
            "wallet_fingerprint": hashlib.sha256(wallet.encode()).hexdigest()[:12],
            "wallet_fixture_count": len(wallets[:2]),
            "pair_fingerprint": hashlib.sha256(pair.encode()).hexdigest()[:12],
            "public_token_roles": ["market token", "launch token", "wrapped native token"],
        },
        "x402_paid_requests": 0,
        "skill_count": len(results),
        "passed": sum(result["passed"] for result in results),
        "failed": sum(not result["passed"] for result in results),
        "evidence_passed": sum(result["evidence_passed"] for result in results),
        "evidence_failed": sum(not result["evidence_passed"] for result in results),
        "canonical_answer_expected": sum(
            result["canonical_answer_expected"] for result in results
        ),
        "canonical_answer_present": sum(
            result["canonical_answer_present"] for result in results
        ),
        "user_answer_passed": sum(result["user_answer_passed"] for result in results),
        "answer_status_counts": {
            status: sum(result["answer_status"] == status for result in results)
            for status in ("complete", "partial", "empty", "insufficient_data", "error")
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "skill_count",
                    "evidence_passed",
                    "evidence_failed",
                    "canonical_answer_expected",
                    "user_answer_passed",
                )
            },
            sort_keys=True,
        )
    )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
