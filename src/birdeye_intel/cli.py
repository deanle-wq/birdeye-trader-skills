"""Minimal read-only CLI adapter."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .client import BirdeyeClient
from .core import IntelligenceError
from .router import route_intent
from .workflows import BirdeyeIntelligence


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="birdeye-intel")
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Route an intent without making an API request")
    route.add_argument("text")
    route.add_argument("--has-baseline", action="store_true")

    quick = sub.add_parser("quick-screen")
    quick.add_argument("token")
    quick.add_argument("--min-liquidity-usd", default="25000")
    quick.add_argument("--max-top10-share-pct", default="50")

    early = sub.add_parser("early-participants")
    early.add_argument("token")
    early.add_argument("--time-from", type=int, required=True)
    early.add_argument("--time-to", type=int, required=True)
    early.add_argument("--max-wallets", type=int, default=5)
    early.add_argument("--max-pages", type=int, default=2)

    holder = sub.add_parser("holder-composition")
    holder.add_argument("token")
    holder.add_argument("--max-pages", type=int, default=2)

    exit_parser = sub.add_parser("exit-trace")
    exit_parser.add_argument("wallet")
    exit_parser.add_argument("token")
    exit_parser.add_argument("--time-from", type=int, required=True)
    exit_parser.add_argument("--time-to", type=int, required=True)
    exit_parser.add_argument("--forward-window-seconds", type=int, default=86400)
    exit_parser.add_argument("--max-pages", type=int, default=2)

    copy = sub.add_parser("copyability")
    copy.add_argument("wallet")
    copy.add_argument("--time-from", type=int, required=True)
    copy.add_argument("--time-to", type=int, required=True)
    copy.add_argument("--latency-seconds", type=int, required=True)
    copy.add_argument("--size-usd", required=True)
    copy.add_argument("--slippage-bps-override")
    copy.add_argument("--token-cap", type=int, default=5)
    copy.add_argument("--activity-page-cap", type=int, default=2)
    return parser


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "route":
        return {"route": route_intent(args.text, has_baseline=args.has_baseline)}
    intelligence = BirdeyeIntelligence(BirdeyeClient())
    if args.command == "quick-screen":
        return intelligence.quick_screen(
            args.token,
            min_liquidity_usd=args.min_liquidity_usd,
            max_top10_share_pct=args.max_top10_share_pct,
        )
    if args.command == "early-participants":
        return intelligence.early_participants(
            args.token,
            early_window=(args.time_from, args.time_to),
            max_wallets=args.max_wallets,
            max_pages=args.max_pages,
        )
    if args.command == "holder-composition":
        return intelligence.holder_composition(args.token, max_pages=args.max_pages)
    if args.command == "exit-trace":
        return intelligence.exit_trace(
            args.wallet,
            args.token,
            lookback=(args.time_from, args.time_to),
            forward_window_seconds=args.forward_window_seconds,
            max_pages=args.max_pages,
        )
    if args.command == "copyability":
        return intelligence.copyability(
            args.wallet,
            lookback=(args.time_from, args.time_to),
            latency_seconds=args.latency_seconds,
            size_usd=args.size_usd,
            slippage_bps_override=args.slippage_bps_override,
            token_cap=args.token_cap,
            activity_page_cap=args.activity_page_cap,
        )
    raise ValueError("Unsupported command")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _run(args)
    except IntelligenceError as exc:
        result = {"status": "error", "errors": [exc.as_dict()]}
    except (ValueError, TypeError) as exc:
        result = {
            "status": "error",
            "errors": [
                {
                    "code": "invalid_input",
                    "endpoint_id": None,
                    "retryable": False,
                    "message": str(exc),
                    "details": {},
                }
            ],
        }
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.get("status") != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())
