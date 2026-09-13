"""Bounded evidence runtime for one-question V2 skill contracts."""

from __future__ import annotations

from copy import deepcopy
import json
from importlib.resources import files
import re
from typing import Any

from ..core import BaselineRequired, InvalidInput, IntelligenceError, Usage, utc_now, validate_address
from .catalog import Catalog, SkillSpec
from .client import V2Client
from .wave0 import normalize_wave0_answer
from .wave1 import normalize_wave1_answer


PAIR_ENDPOINTS = {"EP-017", "EP-018", "EP-028", "EP-047", "EP-075"}
WALLET_ADDRESS_ENDPOINTS = {"EP-048", "EP-059"}
NO_ENTITY_ENDPOINTS = {"EP-002", "EP-003", "EP-004", "EP-005", "EP-006", "EP-008", "EP-044", "EP-045", "EP-065", "EP-077", "EP-079"}
MAX_KOL_WALLET_FANOUT = 5

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "EP-001": {"sort_by": "volume_24h_usd", "sort_type": "desc", "chain": "solana", "target": "token", "search_mode": "fuzzy", "search_by": "symbol", "limit": 10},
    "EP-002": {"sort_by": "liquidity", "sort_type": "desc", "limit": 20},
    "EP-003": {"sort_by": "liquidity", "sort_type": "desc", "limit": 100},
    "EP-004": {"limit": 10, "meme_platform_enabled": "true"},
    "EP-005": {"sort_by": "rank", "sort_type": "asc", "interval": "24h", "limit": 20},
    "EP-006": {"sort_by": "progress_percent", "sort_type": "desc", "source": "all", "limit": 20},
    "EP-008": {"interval": "1d", "trader_style": "all", "sort_by": "smart_traders_no", "sort_type": "desc", "limit": 20},
    "EP-019": {"sort_type": "desc", "sort_by": "liquidity", "limit": 20},
    "EP-026": {"resolution": "4h", "direction": "back", "count": 50},
    "EP-027": {"resolution": "4h", "direction": "back", "count": 50},
    "EP-028": {"direction": "back", "count": 50},
    "EP-031": {"mode": "top", "top_n": 10, "include_list": "true", "limit": 50},
    "EP-032": {"interval": "1h", "include_zero_balance": "true"},
    "EP-033": {"sort_by": "amount", "order_type": "desc", "include_zero_balance": "true", "limit": 50},
    "EP-034": {"chart_type": "1h", "mode": "padding", "percent_mode": "beginning", "count": 20},
    "EP-035": {"chart_type": "1d"},
    "EP-037": {"time_frame": "24h", "sort_type": "desc", "sort_by": "volume", "limit": 10},
    "EP-038": {"offset": 0, "limit": 70},
    "EP-039": {"offset": 0, "limit": 100, "sort_by": "block_unix_time", "sort_type": "desc", "tx_type": "swap"},
    "EP-040": {"volume_type": "usd", "sort_type": "desc", "sort_by": "block_unix_time", "limit": 100},
    "EP-041": {"sort_by": "block_time", "sort_type": "desc", "type": "all", "limit": 100},
    "EP-042": {"time_frame": "24h"},
    "EP-043": {"time_frame": "24h"},
    "EP-044": {"offset": 0, "limit": 100, "tx_type": "swap"},
    "EP-046": {"offset": 0, "limit": 100, "tx_type": "swap"},
    "EP-047": {"offset": 0, "limit": 50, "tx_type": "swap"},
    "EP-049": {"sort_type": "desc", "sort_by": "value", "limit": 100},
    "EP-050": {"sort_type": "desc", "count": 30, "direction": "back", "type": "1d"},
    "EP-051": {"sort_type": "desc", "type": "1d", "limit": 100, "offset": 0},
    "EP-053": {"duration": "all", "position_scope": "duration_only"},
    "EP-057": {},
    "EP-066": {},
    "EP-067": {"address_type": "token", "type": "1H"},
    "EP-077": {"offset": 0, "limit": 100, "sort_by": "block_unix_time", "sort_type": "desc", "tx_type": "swap"},
    "EP-079": {"type": "1W", "sort_by": "PnL", "sort_type": "desc", "offset": 0, "limit": 10},
}


class V2Runtime:
    def __init__(self, client: V2Client | None = None, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or Catalog()
        self.client = client or V2Client()
        self.endpoint_specs = json.loads(files(__package__).joinpath("endpoints.json").read_text())

    @staticmethod
    def _blocked(spec: SkillSpec, reason: str) -> dict[str, Any]:
        return {
            "schema_version": "2.0.0",
            "skill_id": spec.skill_id,
            "skill": spec.slug,
            "question": spec.question,
            "status": "blocked",
            "reason": reason,
            "runtime_status": spec.runtime_status,
            "unapproved_endpoint_ids": list(spec.unapproved_endpoint_ids),
            "non_x402_endpoint_ids": list(spec.non_x402_endpoint_ids),
            "scope_excluded_endpoint_ids": list(spec.scope_excluded_endpoint_ids),
            "x402_eligible": spec.x402_eligible,
            "facts": {},
            "evidence": [],
            "completeness": {"state": "not_started", "endpoints_succeeded": 0, "endpoints_required": len(spec.endpoint_ids)},
            "cost": Usage(0).as_dict(),
            "limitations": ["No network request was made."],
            "errors": [],
        }

    @staticmethod
    def _validate_inputs(spec: SkillSpec, inputs: dict[str, Any]) -> None:
        if str(inputs.get("chain", "solana")).lower() != "solana":
            raise InvalidInput("V2 release candidate supports audited Solana mode only")
        time_from = inputs.get("time_from")
        time_to = inputs.get("time_to")
        if time_from is not None and time_to is not None and int(time_from) >= int(time_to):
            raise InvalidInput("time_from must be earlier than time_to")
        if spec.state == "CALLER_BASELINE" and not isinstance(inputs.get("baseline"), dict):
            raise BaselineRequired("This monitor requires a caller-supplied baseline")
        forbidden = {key.lower() for key in inputs if "api_key" in key.lower() or "authorization" in key.lower()}
        if forbidden:
            raise InvalidInput("Credentials cannot be passed in skill input")

    @staticmethod
    def _entity_values(inputs: dict[str, Any]) -> tuple[str | None, str | None, list[str], list[str]]:
        token = inputs.get("token_address") or inputs.get("token")
        pair = inputs.get("pair_address") or inputs.get("pool_address")
        wallet = (
            inputs.get("wallet_address")
            or inputs.get("wallet")
            or inputs.get("developer_wallet_address")
        )
        raw_tokens = inputs.get("token_addresses") or ([token] if token else [])
        raw_wallets = inputs.get("wallet_addresses") or inputs.get("wallets") or ([wallet] if wallet else [])
        tokens = [raw_tokens] if isinstance(raw_tokens, str) else list(raw_tokens)
        wallets = [raw_wallets] if isinstance(raw_wallets, str) else list(raw_wallets)
        for value in tokens:
            validate_address(str(value), "token address")
        if pair:
            validate_address(str(pair), "pair address")
        for value in wallets:
            validate_address(str(value), "wallet address")
        return str(token) if token else None, str(pair) if pair else None, [str(v) for v in tokens], [str(v) for v in wallets]

    def _request_for(self, endpoint_id: str, inputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        token, pair, tokens, wallets = self._entity_values(inputs)
        wallet = wallets[0] if wallets else None
        spec = self.endpoint_specs[endpoint_id]
        params = deepcopy(DEFAULT_PARAMS.get(endpoint_id, {}))
        body: dict[str, Any] = {}
        if endpoint_id == "EP-001":
            params["keyword"] = inputs.get("query") or inputs.get("symbol") or token
        elif endpoint_id == "EP-006" and (
            inputs.get("developer_wallet_address") or inputs.get("wallet_address")
        ):
            params["creator"] = inputs.get("developer_wallet_address") or inputs.get("wallet_address")
        elif endpoint_id in PAIR_ENDPOINTS:
            if endpoint_id == "EP-018":
                params["list_address"] = ",".join(inputs.get("pair_addresses") or ([pair] if pair else []))
            else:
                params["address"] = pair
        elif endpoint_id in WALLET_ADDRESS_ENDPOINTS:
            params["address"] = wallet
        elif endpoint_id not in NO_ENTITY_ENDPOINTS:
            required = spec.get("required_query_parameters", "")
            if "query:wallet " in required:
                params["wallet"] = wallet
            if "query:wallets " in required:
                params["wallets"] = ",".join(wallets)
            if "query:token_address " in required:
                params["token_address"] = token
            if "query:list_address " in required:
                params["list_address"] = ",".join(tokens)
            if "query:address " in required:
                params["address"] = token
        allowed_query = set(
            re.findall(
                r"query:([a-zA-Z_]+)",
                f"{spec.get('required_query_parameters', '')}|{spec.get('optional_query_parameters', '')}",
            )
        )
        for key in (
            "time_from",
            "time_to",
            "offset",
            "limit",
            "interval",
            "duration",
            "time_frame",
            "sort_by",
            "sort_type",
            "tx_type",
            "min_volume",
            "max_volume",
            "source",
            "graduated",
            "min_creation_time",
            "max_creation_time",
            "min_percent",
            "max_percent",
            "top_n",
            "mode",
            "address_type",
        ):
            if key in inputs and key in allowed_query:
                params[key] = inputs[key]
        if endpoint_id == "EP-039" and inputs.get("time_from") is not None and inputs.get("time_to") is not None:
            params["after_time"] = inputs["time_from"]
            params["before_time"] = inputs["time_to"]
        elif endpoint_id in {"EP-046", "EP-047"}:
            if inputs.get("before_time") is not None:
                params["before_time"] = inputs["before_time"]
            elif inputs.get("time_from") is not None:
                params["after_time"] = inputs["time_from"]
        elif endpoint_id == "EP-048" and inputs.get("time_from") is not None:
            params["after_time"] = inputs["time_from"]
        if endpoint_id == "EP-023":
            params.update({"address": token, "type": inputs.get("resolution", "1H"), "time_from": inputs.get("time_from"), "time_to": inputs.get("time_to")})
        elif endpoint_id == "EP-066":
            params["unixtime"] = inputs.get("unixtime", inputs.get("time_to"))
        elif endpoint_id == "EP-025":
            body = {"addresses": tokens}
        elif endpoint_id == "EP-022":
            body = {"list_address": ",".join(tokens)}
        elif endpoint_id == "EP-036":
            body = {"wallets": wallets, "token_address": token}
        elif endpoint_id == "EP-052":
            body = {"wallets": wallets}
        elif endpoint_id == "EP-054":
            body = {"wallet": wallet, "token_addresses": tokens or None, "duration": inputs.get("duration", "90d"), "position_scope": inputs.get("position_scope", "duration_only"), "limit": inputs.get("limit", 100), "offset": inputs.get("offset", 0)}
        elif endpoint_id == "EP-060":
            body = {"wallet": wallet, "token_address": token, "time_from": inputs.get("time_from"), "time_to": inputs.get("time_to"), "limit": inputs.get("limit", 100)}
        elif endpoint_id == "EP-061":
            body = {"token_address": token, "time_from": inputs.get("time_from"), "time_to": inputs.get("time_to"), "limit": inputs.get("limit", 100)}
        elif endpoint_id == "EP-062":
            body = {"wallets": wallets, "token_address": token}
        elif endpoint_id == "EP-063":
            body = {"wallet": wallet, "token_addresses": tokens}
        elif endpoint_id == "EP-078":
            body = {"token_address": token, "time_from": inputs.get("time_from"), "time_to": inputs.get("time_to")}
        endpoint_params = inputs.get("endpoint_params", {})
        endpoint_bodies = inputs.get("endpoint_bodies", {})
        if isinstance(endpoint_params, dict) and isinstance(endpoint_params.get(endpoint_id), dict):
            params.update(endpoint_params[endpoint_id])
        if isinstance(endpoint_bodies, dict) and isinstance(endpoint_bodies.get(endpoint_id), dict):
            body.update(endpoint_bodies[endpoint_id])
        params = {key: value for key, value in params.items() if value not in (None, "", [])}
        body = {key: value for key, value in body.items() if value not in (None, "", [])}
        required_query = re.findall(r"query:([a-zA-Z_]+)", spec.get("required_query_parameters", ""))
        missing_query = [key for key in required_query if key not in params]
        required_body = re.findall(r"(?:^|\|)([a-zA-Z_]+)\*?:", spec.get("request_body_schema", ""))
        missing_body = [key for key in required_body if "*" in spec.get("request_body_schema", "").split(key, 1)[1][:2] and key not in body]
        if missing_query:
            raise InvalidInput(f"{endpoint_id} requires input for: {', '.join(missing_query)}")
        if missing_body:
            raise InvalidInput(f"{endpoint_id} requires body input for: {', '.join(missing_body)}")
        return params, body

    def run(self, identifier: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        spec = self.catalog.get(identifier)
        inputs = dict(inputs or {})
        if spec.runtime_status.startswith("BLOCKED_"):
            return self._blocked(spec, spec.runtime_status.lower())
        if not spec.x402_eligible:
            return self._blocked(spec, "blocked_x402_unavailable")
        self._validate_inputs(spec, inputs)
        input_wallets: list[str] = []
        if spec.slug == "kol-trades":
            _, _, _, input_wallets = self._entity_values(inputs)
            input_wallets = list(dict.fromkeys(input_wallets))
            if len(input_wallets) > MAX_KOL_WALLET_FANOUT:
                raise InvalidInput(
                    f"kol-trades accepts at most {MAX_KOL_WALLET_FANOUT} wallets per bounded run"
                )
        requested_cap = inputs.get("call_cap")
        call_cap = max(len(spec.endpoint_ids) + 1, 10) if requested_cap is None else max(1, min(int(requested_cap), 20))
        usage = Usage(call_cap=call_cap)
        evidence: list[dict[str, Any]] = []
        facts: dict[str, Any] = {"baseline": inputs.get("baseline")}
        limitations: list[str] = []
        errors: list[dict[str, Any]] = []
        for endpoint_id in spec.endpoint_ids:
            try:
                if endpoint_id == "EP-048" and spec.slug == "kol-trades" and input_wallets:
                    wallet_facts: list[dict[str, Any]] = []
                    cache_hits: list[bool] = []
                    wallet_errors: list[dict[str, Any]] = []
                    for wallet_index, wallet_address in enumerate(input_wallets):
                        fanout_inputs = {
                            **inputs,
                            "wallet_address": wallet_address,
                            "wallet_addresses": [wallet_address],
                        }
                        try:
                            params, body = self._request_for(endpoint_id, fanout_inputs)
                            response = self.client.fetch(
                                endpoint_id, usage=usage, params=params, body=body
                            )
                            wallet_facts.append(
                                {
                                    "wallet": wallet_address,
                                    "data": response["envelope"].get("data"),
                                }
                            )
                            cache_hits.append(bool(response["cache_hit"]))
                        except IntelligenceError as exc:
                            wallet_errors.append({**exc.as_dict(), "wallet_index": wallet_index})
                    if wallet_facts:
                        facts[endpoint_id] = {
                            "wallets": wallet_facts,
                            "requested_count": len(input_wallets),
                        }
                    errors.extend(wallet_errors)
                    evidence.append(
                        {
                            "endpoint_id": endpoint_id,
                            "x402_path": self.endpoint_specs[endpoint_id]["x402_path"],
                            "evaluation_transport": "standard_api_counterpart",
                            "cache_hit": bool(cache_hits) and all(cache_hits),
                            "status": (
                                "observed"
                                if len(wallet_facts) == len(input_wallets)
                                else "partial"
                                if wallet_facts
                                else "failed"
                            ),
                            "call_count": len(input_wallets),
                            "wallets_queried": len(wallet_facts),
                        }
                    )
                    continue
                params, body = self._request_for(endpoint_id, inputs)
                response = self.client.fetch(endpoint_id, usage=usage, params=params, body=body)
                facts[endpoint_id] = response["envelope"].get("data")
                evidence.append(
                    {
                        "endpoint_id": endpoint_id,
                        "x402_path": self.endpoint_specs[endpoint_id]["x402_path"],
                        "evaluation_transport": "standard_api_counterpart",
                        "cache_hit": response["cache_hit"],
                        "status": "observed",
                    }
                )
            except IntelligenceError as exc:
                errors.append(exc.as_dict())
                evidence.append(
                    {
                        "endpoint_id": endpoint_id,
                        "x402_path": self.endpoint_specs[endpoint_id].get("x402_path"),
                        "evaluation_transport": "standard_api_counterpart",
                        "cache_hit": False,
                        "status": "failed",
                    }
                )
        succeeded = sum(item["status"] == "observed" for item in evidence)
        if spec.skill_type not in {"ATOMIC_QUERY", "UTILITY"}:
            limitations.append("The package instructions must derive the named answer from this bounded evidence; endpoint payloads alone are not a recommendation.")
        if spec.runtime_status == "EVIDENCE_ONLY_CONDITIONAL":
            limitations.append("This skill uses an explicitly labeled proxy or incomplete observable and must preserve that label.")
        evidence_only = spec.runtime_status.startswith("EVIDENCE_ONLY_")
        if evidence_only:
            limitations.append(
                "The evidence recipe ran, but the named analytical answer is not release-ready until its derivation has forward-test and human-review evidence."
            )
        status = (
            "evidence_only"
            if evidence_only and succeeded == len(spec.endpoint_ids) and not errors
            else "complete"
            if succeeded == len(spec.endpoint_ids) and not errors
            else "partial"
            if succeeded or any(endpoint_id in facts for endpoint_id in spec.endpoint_ids)
            else "error"
        )
        observed_at = utc_now()
        answer = normalize_wave0_answer(
            spec,
            inputs,
            facts,
            observed_at=observed_at,
            errors=errors,
        )
        if answer is None:
            answer = normalize_wave1_answer(
                spec,
                inputs,
                facts,
                observed_at=observed_at,
                errors=errors,
            )
        return {
            "schema_version": "2.0.0",
            "observed_at": observed_at,
            "skill_id": spec.skill_id,
            "skill": spec.slug,
            "question": spec.question,
            "capability_path": spec.capability_path,
            "status": status,
            "runtime_status": spec.runtime_status,
            "answer_status": spec.answer_status,
            "answer": answer,
            "facts": facts,
            "evidence": evidence,
            "completeness": {"state": status, "endpoints_succeeded": succeeded, "endpoints_required": len(spec.endpoint_ids)},
            "cost": usage.as_dict(),
            "pricing": {"role": spec.pricing_role, "drivers": list(spec.pricing_drivers), "difficulty": spec.difficulty},
            "limitations": limitations,
            "errors": errors,
        }
