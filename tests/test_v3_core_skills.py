from __future__ import annotations

import csv
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from birdeye_intel.core import AuthenticationError, RateLimited
from birdeye_intel.v3.catalog import CoreCatalog
from birdeye_intel.v3.cli import execute, parser
from birdeye_intel.v3.direct import SOLANA_LAUNCHPAD_SOURCE_ALIASES

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = "11111111111111111111111111111111"


class FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.client = None

    def run(self, leaf: str, inputs: dict) -> dict:
        self.calls.append((leaf, inputs))
        return {
            "status": "complete",
            "answer": {"leaf": leaf},
            "cost": {"calls_attempted": 1, "calls_succeeded": 1},
            "limitations": [],
        }


class FakeClient:
    def __init__(self, endpoint_specs: dict) -> None:
        self.endpoint_specs = endpoint_specs
        self.calls: list[tuple[str, dict]] = []

    def fetch(self, endpoint_id: str, *, usage, params=None, body=None) -> dict:
        usage.preflight(endpoint_id)
        usage.calls_succeeded += 1
        self.calls.append((endpoint_id, dict(params or {})))
        return {
            "cache_hit": False,
            "envelope": {
                "data": {
                    "has_next": False,
                    "items": [
                        {
                            "address": ADDRESS,
                            "symbol": "TEST",
                            "name": "Test Token",
                            "price": "1.25",
                            "market_cap": "100000",
                            "liquidity": "25000",
                            "holder": 500,
                            "volume_5m_usd": "12345",
                            "trade_5m_count": 91,
                            "meme_info": {
                                "source": "pump_dot_fun",
                                "progress_percent": "88.5",
                                "graduated": False,
                            },
                        }
                    ],
                }
            },
        }


class FakeDirectRuntime:
    def __init__(self, endpoint_specs: dict) -> None:
        self.client = FakeClient(endpoint_specs)


class FakeRadarClient:
    def __init__(self, endpoint_specs: dict, *, empty_primary: bool = False, rate_limit_on: str | None = None, auth_fail: bool = False) -> None:
        self.endpoint_specs = endpoint_specs
        self.calls: list[tuple[str, dict]] = []
        self.empty_primary = empty_primary
        self.rate_limit_on = rate_limit_on
        self.auth_fail = auth_fail

    @staticmethod
    def _candidate(address: str, symbol: str, *, now: int, market_cap: int, liquidity: int, holder: int) -> dict:
        return {
            "address": address,
            "symbol": symbol,
            "name": f"{symbol} token",
            "price": "1",
            "market_cap": market_cap,
            "liquidity": liquidity,
            "holder": holder,
            "volume_24h_usd": market_cap // 2,
            "volume_1h_usd": market_cap // 20,
            "volume_5m_usd": market_cap // 100,
            "volume_5m_change_percent": holder,
            "trade_5m_count": holder // 2,
            "recent_listing_time": now - 3_600,
            "meme_info": {"source": "pump_dot_fun", "progress_percent": "75"},
        }

    def fetch(self, endpoint_id: str, *, usage, params=None, body=None) -> dict:
        if self.auth_fail:
            self.calls.append((endpoint_id, dict(params or {})))
            raise AuthenticationError("test missing key", endpoint_id=endpoint_id)
        usage.preflight(endpoint_id)
        params = dict(params or {})
        self.calls.append((endpoint_id, params))
        if params.get("sort_by") == self.rate_limit_on:
            raise RateLimited("test rate limit", endpoint_id=endpoint_id)
        usage.calls_succeeded += 1
        now = int(params.get("max_recent_listing_time", 2_000_000_000))
        best = self._candidate("2" * 32, "GOOD\x00\nTOKEN", now=now, market_cap=2_000_000, liquidity=500_000, holder=1_000)
        second = self._candidate("3" * 32, "SECOND", now=now, market_cap=1_000_000, liquidity=200_000, holder=500)
        unknown_age = self._candidate("4" * 32, "UNKNOWN", now=now, market_cap=900_000, liquidity=150_000, holder=300)
        unknown_age.pop("recent_listing_time")
        if endpoint_id == "EP-002":
            if params["sort_by"] == "volume_24h_usd":
                rows = [] if self.empty_primary else [best, second, unknown_age]
            else:
                rows = [best]
            data = {"items": rows, "has_next": False}
        elif endpoint_id == "EP-005":
            data = {"tokens": [{"address": best["address"], "symbol": best["symbol"]}]}
        else:
            data = [{"token": best["address"], "smart_traders_no": 12, "net_flow": 50000}]
        return {"cache_hit": False, "envelope": {"success": True, "data": data}}


class FakeRadarRuntime:
    def __init__(self, endpoint_specs: dict, *, empty_primary: bool = False, rate_limit_on: str | None = None, auth_fail: bool = False) -> None:
        self.client = FakeRadarClient(
            endpoint_specs,
            empty_primary=empty_primary,
            rate_limit_on=rate_limit_on,
            auth_fail=auth_fail,
        )


class V3CoreSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = CoreCatalog()

    def test_core_surface_has_twelve_packages_and_sixty_five_commands(self) -> None:
        self.assertEqual(len(self.catalog), 12)
        self.assertEqual(self.catalog.command_count, 65)
        self.assertEqual(len({skill.name for skill in self.catalog.list()}), 12)
        self.assertEqual(len({skill.group for skill in self.catalog.list()}), 12)
        self.assertNotIn("birdeye-entry-check", {skill.name for skill in self.catalog.list()})

    def test_every_dependency_is_approved_x402_and_never_scope_excluded(self) -> None:
        unique_endpoints: set[str] = set()
        unique_leaves: set[str] = set()
        for skill in self.catalog.list():
            for command in skill.commands:
                for leaf_name in command.leaves:
                    leaf = self.catalog.leaf_catalog.get(leaf_name)
                    unique_leaves.add(leaf_name)
                    unique_endpoints.update(leaf.endpoint_ids)
                    self.assertTrue(leaf.x402_eligible, (skill.name, command.name, leaf_name))
                    self.assertEqual(leaf.unapproved_endpoint_ids, ())
                    self.assertEqual(leaf.non_x402_endpoint_ids, ())
                    self.assertEqual(leaf.scope_excluded_endpoint_ids, ())
                    self.assertEqual(len(leaf.endpoint_ids), len(leaf.x402_endpoint_paths))
        self.assertEqual(len(unique_leaves), 62)
        self.assertEqual(len(unique_endpoints), 27)
        audit = json.loads((ROOT / "qa/v2/x402-eligibility-audit.json").read_text())
        excluded = {item["endpoint_id"] for item in audit["scope_exclusions"]}
        self.assertFalse(unique_endpoints & excluded)

    def test_generated_packages_match_catalog_and_have_agent_metadata(self) -> None:
        root = ROOT / "core-skills"
        folders = {path.name for path in root.iterdir() if path.is_dir()}
        self.assertEqual(folders, {skill.name for skill in self.catalog.list()})
        for skill in self.catalog.list():
            skill_md = (root / skill.name / "SKILL.md").read_text()
            metadata = (root / skill.name / "agents" / "openai.yaml").read_text()
            self.assertRegex(skill_md, rf"(?m)^name: {re.escape(skill.name)}$")
            self.assertIn("birdeye-cli doctor", skill_md)
            self.assertIn("audited Solana Birdeye x402 allowlist", skill_md)
            self.assertIn("must not sign, swap, launch, submit a transaction", skill_md)
            self.assertIn(f"${skill.name}", metadata)
            for command in skill.commands:
                self.assertIn(f"`{command.name}`", skill_md)
                self.assertIn(command.question, skill_md)

    def test_marketplace_has_forty_seven_specific_daily_job_packages(self) -> None:
        marketplace = json.loads((ROOT / "src/birdeye_intel/v3/marketplace.json").read_text())
        details = json.loads(
            (ROOT / "src/birdeye_intel/v3/marketplace_details.json").read_text()
        )["skills"]
        cards = marketplace["skills"]
        self.assertEqual(len(cards), 47)
        self.assertEqual(len({card["name"] for card in cards}), 47)
        self.assertEqual(set(details), {card["name"] for card in cards})
        root = ROOT / "skills"
        self.assertEqual(
            {path.name for path in root.iterdir() if path.is_dir()},
            {card["name"] for card in cards},
        )
        self.assertIn("birdeye-5-minute-trending-tokens", {card["name"] for card in cards})
        self.assertIn("birdeye-pumpfun-trending-tokens", {card["name"] for card in cards})
        self.assertIn("birdeye-pumpfun-new-tokens", {card["name"] for card in cards})
        self.assertIn("birdeye-launchpad-trending-tokens", {card["name"] for card in cards})
        self.assertIn("birdeye-launchpad-new-tokens", {card["name"] for card in cards})
        self.assertIn("birdeye-market-radar", {card["name"] for card in cards})
        self.assertNotIn("birdeye-pre-trade-data-check", {card["name"] for card in cards})
        self.assertNotIn("Decision Support", {card["category"] for card in cards})
        for card in cards:
            text = (root / card["name"] / "SKILL.md").read_text()
            metadata = (root / card["name"] / "agents/openai.yaml").read_text()
            self.assertIn(card["question"], text)
            self.assertIn(f"name: {card['name']}", text)
            self.assertIn(f"${card['name']}", metadata)
            self.assertIn("## Installation", text)
            self.assertIn("## Core capabilities", text)
            self.assertIn("## Just say to your agent", text)
            self.assertIn("## Inputs and filters", text)
            self.assertIn("## Output fields", text)
            self.assertIn("## Boundaries", text)
            self.assertIn(
                f"npx skills add https://github.com/deanle-wq/birdeye-trader-skills --skill {card['name']}",
                text,
            )
            self.assertGreaterEqual(len(details[card["name"]]["capabilities"]), 3)
            self.assertGreaterEqual(len(details[card["name"]]["examples"]), 2)
            for capability in details[card["name"]]["capabilities"]:
                self.assertIn(capability, text)
            for example in details[card["name"]]["examples"]:
                self.assertIn(example, text)
            for call in card["core_calls"]:
                self.catalog.resolve(call["group"], call["command"])

    def test_marketplace_contracts_do_not_overclaim_unavailable_fields(self) -> None:
        root = ROOT / "skills"
        expected_disclosures = {
            "birdeye-migrated-token-screener": ("bundle-rate", "fresh-wallet-rate", "top-10 concentration"),
            "birdeye-token-basic-info": ("rat-wallet", "bundle", "sniper-wallet", "KOL-buyer"),
            "birdeye-top-holders": ("cost basis", "holder P&L", "wallet tags", "funding source"),
            "birdeye-holder-distribution-analysis": ("explicitly excluded", "not x402-supported"),
            "birdeye-wallet-trade-history": ("not current wallet holdings", "not used"),
            "birdeye-selected-kol-wallet-activity": ("caller must provide", "complete KOL universe"),
        }
        for skill_name, phrases in expected_disclosures.items():
            text = (root / skill_name / "SKILL.md").read_text()
            for phrase in phrases:
                self.assertIn(phrase.lower(), text.lower(), (skill_name, phrase))

    def test_marketplace_catalog_exports_detail_contract(self) -> None:
        with (ROOT / "marketplace-catalog.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 47)
        for row in rows:
            self.assertTrue(row["core_capabilities"].strip(), row["skill_name"])
            self.assertTrue(row["example_prompts"].strip(), row["skill_name"])
            self.assertGreaterEqual(row["core_capabilities"].count("; "), 2)
            self.assertGreaterEqual(row["example_prompts"].count("; "), 1)

    def test_manifests_follow_domain_skill_packaging(self) -> None:
        for relative in (
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
            ".cursor-plugin/plugin.json",
        ):
            document = json.loads((ROOT / relative).read_text())
            expected = ["./skills/"] if ".cursor-plugin" in relative else "./skills/"
            self.assertEqual(document["skills"], expected)
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["skill_count"], 47)
        core_manifest = json.loads((ROOT / "core-manifest.json").read_text())
        self.assertEqual(core_manifest["skill_count"], 12)
        self.assertEqual(core_manifest["command_count"], 65)
        with (ROOT / "marketplace-catalog.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 47)
        self.assertEqual(len({row["skill_name"] for row in rows}), 47)

    def test_cli_doctor_never_exposes_key(self) -> None:
        with patch.dict("os.environ", {"BIRDEYE_API_KEY": "secret-value"}, clear=False):
            result = execute(parser(self.catalog).parse_args(["doctor"]), catalog=self.catalog)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["core_skill_count"], 12)
        self.assertEqual(result["command_count"], 65)
        self.assertTrue(result["api_key_configured"])
        self.assertFalse(result["transaction_execution"])
        self.assertNotIn("secret-value", json.dumps(result))

    def test_leaf_command_runs_one_private_dependency(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            ["token", "security", "--address", ADDRESS]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["skill"], "birdeye-token")
        self.assertEqual([call[0] for call in runtime.calls], ["token-security-check"])
        self.assertEqual(runtime.calls[0][1]["token_address"], ADDRESS)

    def test_composite_command_runs_declared_dependencies_and_lookback(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            ["wallet-analysis", "run", "--address", ADDRESS]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000)
        command = self.catalog.get("wallet-analysis").command("run")
        self.assertEqual([call[0] for call in runtime.calls], list(command.leaves))
        self.assertEqual(runtime.calls[0][1]["time_to"], 2_000_000_000)
        self.assertEqual(runtime.calls[0][1]["time_from"], 2_000_000_000 - 2_592_000)
        self.assertEqual(result["summary"]["section_count"], len(command.leaves))

    def test_command_level_call_cap_stops_composite_fanout(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            ["token-dd", "run", "--address", ADDRESS, "--call-cap", "2"]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(len(runtime.calls), 2)
        self.assertEqual(result["summary"]["calls_attempted"], 2)
        self.assertEqual(result["summary"]["call_cap"], 2)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(
            any(section["status"] == "blocked" for section in result["sections"].values())
        )

    def test_five_minute_trending_has_a_typed_direct_answer(self) -> None:
        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market", "trending-5m", "--min-liquidity", "20000", "--limit", "5"]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["answer"]["ranking_basis"], "volume_5m_usd")
        self.assertEqual(result["answer"]["filters"]["min_liquidity"], 20000.0)
        self.assertEqual(result["answer"]["tokens"][0]["volume_5m_usd"], "12345")
        self.assertEqual(runtime.client.calls[0][0], "EP-002")

    def test_market_radar_runs_sweep_gate_score_and_no_padding_flow(self) -> None:
        runtime = FakeRadarRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(["market-radar", "run"])
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        answer = result["answer"]
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["summary"]["calls_attempted"], 5)
        self.assertEqual(answer["methodology_version"], "birdeye-market-radar-1.0.0")
        self.assertEqual(answer["funnel"]["unique_candidates"], 3)
        self.assertEqual(answer["funnel"]["eligible_after_hard_gates"], 2)
        self.assertEqual(answer["funnel"]["rejected_by_hard_gates"], 1)
        self.assertEqual(answer["funnel"]["rejection_counts"]["unknown_age"], 1)
        self.assertEqual(answer["funnel"]["listed"], 1)
        self.assertEqual(len(answer["tokens"]), 1)
        self.assertEqual(answer["tokens"][0]["address"], "2" * 32)
        self.assertEqual(answer["tokens"][0]["symbol"], "GOOD TOKEN")
        self.assertEqual(answer["tokens"][0]["security_check"], "not_run")
        self.assertEqual(len(answer["near_misses"]), 1)
        self.assertTrue(answer["policy"]["no_padding"])
        self.assertEqual(sum(map(int, answer["score_weights"].values())), 100)

    def test_market_radar_primary_empty_stops_after_one_call(self) -> None:
        runtime = FakeRadarRuntime(self.catalog.endpoint_specs, empty_primary=True)
        args = parser(self.catalog).parse_args(["market-radar", "run"])
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["summary"]["calls_attempted"], 1)
        self.assertEqual(result["answer"]["tokens"], [])
        self.assertEqual(result["sections"]["volume_1h"]["reason"], "primary_24h_candidate_feed_empty")

    def test_market_radar_stops_on_call_cap_and_rate_limit(self) -> None:
        runtime = FakeRadarRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market-radar", "run", "--call-cap", "2"]
        )
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(runtime.client.calls), 2)
        self.assertEqual(result["sections"]["volume_5m"]["reason"], "command_call_cap_reached")

        runtime = FakeRadarRuntime(
            self.catalog.endpoint_specs, rate_limit_on="volume_1h_usd"
        )
        args = parser(self.catalog).parse_args(["market-radar", "run"])
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(runtime.client.calls), 2)
        self.assertEqual(result["sections"]["volume_5m"]["reason"], "upstream_rate_limit_reached")

        runtime = FakeRadarRuntime(self.catalog.endpoint_specs, auth_fail=True)
        args = parser(self.catalog).parse_args(["market-radar", "run"])
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["summary"]["calls_attempted"], 0)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["sections"]["volume_1h"]["reason"], "authentication_required")

    def test_market_radar_rejects_bad_baseline_before_network(self) -> None:
        runtime = FakeRadarRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market-radar", "run", "--baseline-json", '{"tokens":["bad"]}']
        )
        with self.assertRaisesRegex(Exception, "invalid Solana token address"):
            execute(
                args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
            )
        self.assertEqual(runtime.client.calls, [])

    def test_market_radar_applies_score_floor_before_limit_and_tracks_baseline(self) -> None:
        runtime = FakeRadarRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            [
                "market-radar",
                "run",
                "--limit",
                "10",
                "--score-floor",
                "95",
                "--baseline-json",
                json.dumps({"listed_addresses": ["3" * 32, "5" * 32]}),
            ]
        )
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertLessEqual(len(result["answer"]["tokens"]), 10)
        self.assertEqual(result["answer"]["changes"]["new"], ["2" * 32])
        self.assertEqual(result["answer"]["changes"]["dropped"], ["3" * 32, "5" * 32])

    def test_market_radar_reference_is_packaged_for_agent_execution(self) -> None:
        for root in (ROOT / "core-skills", ROOT / "skills"):
            skill = root / "birdeye-market-radar"
            self.assertTrue((skill / "references/flow.md").is_file())
            text = (skill / "SKILL.md").read_text()
            self.assertIn("references/flow.md", text)
            flow = (skill / "references/flow.md").read_text()
            self.assertIn("sweep", flow.lower())
            self.assertIn("never pad", flow.lower())

    def test_pumpfun_new_tokens_maps_default_window_to_creation_time(self) -> None:
        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(["market", "pumpfun-new"])
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "complete")
        _, params = runtime.client.calls[0]
        self.assertEqual(params["source"], "pump_dot_fun")
        self.assertEqual(params["min_creation_time"], 2_000_000_000 - 86_400)
        self.assertEqual(params["max_creation_time"], 2_000_000_000)

    def test_generic_launchpad_cards_normalize_human_source_names(self) -> None:
        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market", "launchpad-trending", "--source", "Raydium LaunchLab"]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(runtime.client.calls[0][1]["source"], "raydium_launchlab")

        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market", "launchpad-new", "--source", "Meteora DBC"]
        )
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "complete")
        _, params = runtime.client.calls[0]
        self.assertEqual(params["source"], "meteora_dynamic_bonding_curve")
        self.assertEqual(params["min_creation_time"], 2_000_000_000 - 86_400)

    def test_generic_launchpad_cards_reject_non_solana_sources_before_network(self) -> None:
        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market", "launchpad-trending", "--source", "four.meme"]
        )
        with self.assertRaisesRegex(Exception, "Unsupported Solana launchpad source"):
            execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(runtime.client.calls, [])

    def test_launchpad_live_qa_and_runtime_allowlist_stay_aligned(self) -> None:
        qa = json.loads((ROOT / "qa/v3/launchpad-source-qa.json").read_text())
        accepted = {row["source"] for row in qa["accepted_sources"]}
        rejected = {row["source"] for row in qa["rejected_sources"]}
        self.assertEqual(qa["gate"], "PASS")
        self.assertEqual(accepted, set(SOLANA_LAUNCHPAD_SOURCE_ALIASES.values()))
        self.assertFalse(accepted & rejected)
        self.assertTrue(all(row["runtime_policy"] == "REJECT_BEFORE_NETWORK" for row in qa["rejected_sources"]))

    def test_focused_launchpad_cards_keep_identity_defining_filters_locked(self) -> None:
        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market", "pumpfun-trending", "--source", "all"]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(runtime.client.calls[0][1]["source"], "pump_dot_fun")

        runtime = FakeDirectRuntime(self.catalog.endpoint_specs)
        args = parser(self.catalog).parse_args(
            ["market", "migrated", "--graduated", "false"]
        )
        result = execute(
            args, catalog=self.catalog, runtime=runtime, now=lambda: 2_000_000_000
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(runtime.client.calls[0][1]["graduated"], "true")

    def test_monitor_rejects_missing_baseline_before_network(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            ["monitor", "bonding-curve", "--address", ADDRESS]
        )
        with self.assertRaisesRegex(Exception, "baseline"):
            execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(runtime.calls, [])

    def test_monitor_accepts_json_baseline(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            [
                "monitor",
                "bonding-curve",
                "--address",
                ADDRESS,
                "--baseline-json",
                '{"progress_percent":"50"}',
            ]
        )
        result = execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(runtime.calls[0][1]["baseline"]["progress_percent"], "50")

    def test_wallet_comparison_requires_two_addresses_before_network(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            ["wallet", "compare", "--wallets", ADDRESS]
        )
        with self.assertRaisesRegex(Exception, "at least two"):
            execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(runtime.calls, [])

    def test_credentials_are_rejected_from_json_input(self) -> None:
        runtime = FakeRuntime()
        args = parser(self.catalog).parse_args(
            [
                "market",
                "trending",
                "--input-json",
                '{"api_key":"do-not-accept"}',
            ]
        )
        with self.assertRaisesRegex(Exception, "Credentials"):
            execute(args, catalog=self.catalog, runtime=runtime)
        self.assertEqual(runtime.calls, [])


if __name__ == "__main__":
    unittest.main()
