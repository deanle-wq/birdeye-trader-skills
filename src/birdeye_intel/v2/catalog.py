"""Immutable V2 skill catalog, hierarchy navigation and intent routing."""

from __future__ import annotations

from dataclasses import dataclass
import json
from importlib.resources import files
import re
from typing import Any, Iterable
import unicodedata


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text.lower().replace("đ", "d")).encode("ascii", "ignore").decode()
    return " ".join(TOKEN_RE.findall(ascii_text))


@dataclass(frozen=True)
class SkillSpec:
    skill_id: str
    name: str
    slug: str
    public_package_name: str
    public_display_name: str
    question: str
    stage: str
    domain: str
    capability_path: str
    parent_capability_id: str
    skill_type: str
    difficulty: str
    state: str
    endpoint_ids: tuple[str, ...]
    readiness: str
    runtime_status: str
    answer_status: str
    unapproved_endpoint_ids: tuple[str, ...]
    non_x402_endpoint_ids: tuple[str, ...]
    scope_excluded_endpoint_ids: tuple[str, ...]
    x402_eligible: bool
    x402_endpoint_paths: tuple[str, ...]
    wave: str
    pricing_role: str
    pricing_drivers: tuple[str, ...]
    public_surface: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SkillSpec":
        return cls(
            **{
                **value,
                "endpoint_ids": tuple(value["endpoint_ids"]),
                "unapproved_endpoint_ids": tuple(value["unapproved_endpoint_ids"]),
                "non_x402_endpoint_ids": tuple(value["non_x402_endpoint_ids"]),
                "scope_excluded_endpoint_ids": tuple(value["scope_excluded_endpoint_ids"]),
                "x402_endpoint_paths": tuple(value["x402_endpoint_paths"]),
                "pricing_drivers": tuple(value["pricing_drivers"]),
            }
        )

    def as_dict(self) -> dict[str, Any]:
        value = dict(self.__dict__)
        value["endpoint_ids"] = list(self.endpoint_ids)
        value["unapproved_endpoint_ids"] = list(self.unapproved_endpoint_ids)
        value["non_x402_endpoint_ids"] = list(self.non_x402_endpoint_ids)
        value["scope_excluded_endpoint_ids"] = list(self.scope_excluded_endpoint_ids)
        value["x402_endpoint_paths"] = list(self.x402_endpoint_paths)
        value["pricing_drivers"] = list(self.pricing_drivers)
        return value


class Catalog:
    """Validated read-only catalog with open-depth capability paths."""

    def __init__(self, skills: Iterable[SkillSpec] | None = None) -> None:
        if skills is None:
            document = json.loads(files(__package__).joinpath("catalog.json").read_text())
            public_document = json.loads(files(__package__).joinpath("public_names.json").read_text())
            if document.get("schema_version") != "2.0.0":
                raise ValueError("Unsupported V2 catalog schema")
            if public_document.get("schema_version") != "1.0.0":
                raise ValueError("Unsupported V2 public-name schema")
            public_by_slug = {
                item["internal_slug"]: item for item in public_document["skills"]
            }
            if set(public_by_slug) != {item["slug"] for item in document["skills"]}:
                raise ValueError("V2 public-name map does not match the catalog")
            skills = [
                SkillSpec.from_dict(
                    {
                        **item,
                        "public_package_name": public_by_slug[item["slug"]]["public_package_name"],
                        "public_display_name": public_by_slug[item["slug"]]["public_display_name"],
                    }
                )
                for item in document["skills"]
            ]
        self._skills = tuple(skills)
        self._by_id = {skill.skill_id.lower(): skill for skill in self._skills}
        self._by_slug = {skill.slug.lower(): skill for skill in self._skills}
        self._by_public_name = {
            skill.public_package_name.lower(): skill for skill in self._skills
        }
        if (
            len(self._by_id) != len(self._skills)
            or len(self._by_slug) != len(self._skills)
            or len(self._by_public_name) != len(self._skills)
        ):
            raise ValueError("Duplicate V2 skill ID, internal slug or public package name")
        if len({skill.question.lower() for skill in self._skills}) != len(self._skills):
            raise ValueError("Duplicate V2 primary question")
        for skill in self._skills:
            if not re.fullmatch(r"birdeye-[a-z0-9]+(?:-[a-z0-9]+)*", skill.public_package_name):
                raise ValueError(f"Invalid public package name for {skill.skill_id}")
            if len(skill.public_package_name) > 64:
                raise ValueError(f"Public package name is too long for {skill.skill_id}")
            if skill.capability_path.split("/")[-1] != skill.slug:
                raise ValueError(f"Capability path mismatch for {skill.skill_id}")
            if skill.x402_eligible != (bool(skill.endpoint_ids) and not skill.non_x402_endpoint_ids):
                raise ValueError(f"x402 eligibility mismatch for {skill.skill_id}")
            if not set(skill.scope_excluded_endpoint_ids) <= set(skill.non_x402_endpoint_ids):
                raise ValueError(f"x402 scope exclusion mismatch for {skill.skill_id}")
            if skill.x402_eligible and len(skill.x402_endpoint_paths) != len(skill.endpoint_ids):
                raise ValueError(f"x402 path coverage mismatch for {skill.skill_id}")

    def get(self, identifier: str) -> SkillSpec:
        key = identifier.strip().lower()
        try:
            return self._by_id.get(key) or self._by_slug.get(key) or self._by_public_name[key]
        except KeyError as exc:
            raise KeyError(f"Unknown V2 skill: {identifier}") from exc

    def list(
        self,
        *,
        stage: str | None = None,
        domain: str | None = None,
        runtime_status: str | None = None,
    ) -> list[SkillSpec]:
        return [
            skill
            for skill in self._skills
            if (stage is None or skill.stage == stage.upper())
            and (domain is None or skill.domain == domain)
            and (runtime_status is None or skill.runtime_status == runtime_status.upper())
        ]

    def hierarchy(self) -> dict[str, dict[str, list[dict[str, str]]]]:
        tree: dict[str, dict[str, list[dict[str, str]]]] = {}
        for skill in self._skills:
            tree.setdefault(skill.stage, {}).setdefault(skill.domain, []).append(
                {
                    "skill_id": skill.skill_id,
                    "slug": skill.slug,
                    "public_package_name": skill.public_package_name,
                    "question": skill.question,
                }
            )
        return tree

    def route(self, text: str, *, limit: int = 5) -> list[dict[str, Any]]:
        normalized = _normalize(text)
        query_tokens = set(normalized.split())
        if not query_tokens:
            return []
        execution_patterns = (
            r"\b(buy|swap|ape)\s+(this|the|it|token)\b",
            r"\b(sell)\s+(this|the|it|token)\b",
            r"\b(execute|submit|sign|place)\b.*\b(transaction|swap|order)\b",
            r"\b(mua|ban|swap)\s+(token|coin|con nay)\b",
        )
        if any(re.search(pattern, normalized) for pattern in execution_patterns):
            return []
        if normalized in {"what changed", "what changed since baseline", "monitor changes", "co gi thay doi"}:
            return []
        if normalized in {"show holdings", "wallet holdings", "show wallet holdings"}:
            return []
        if re.search(
            r"\b(wallet|address)\b.*\b(hold|holds|holding|holdings|portfolio)\b",
            normalized,
        ) and not re.search(r"\b(change|delta|baseline|trade|traded|trading)\b", normalized):
            # The current approved x402 surface does not expose a complete
            # wallet-holdings observable. Do not silently route that question
            # to traded-token history.
            return []

        # High-signal jobs are routed before lexical similarity. These rules are
        # deliberately narrow: each maps a trader question to one owned leaf.
        intent_rules: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("developer-created-tokens", (r"\b(tokens?|coins?)\b.*\b(dev|developer|creator)\b.*\b(create|created|launch)", r"\bdev\b.*\btao\b.*\btoken")),
            ("developer-launch-track-record", (r"\b(dev|developer|creator)\b.*\b(track record|performance|win rate|outcomes?)\b",)),
            ("wallet-cohort-comparison", (r"\bcompare\b.*\b(wallet )?cohorts?\b", r"\bso sanh\b.*\bnhom vi\b")),
            ("wallet-comparison", (r"\bcompare\b.*\bwallets?\b", r"\bwallets?\b.*\b(win ?rate|pnl|performance)\b", r"\bso sanh\b.*\bvi\b")),
            ("latency-adjusted-copyability", (r"\b(copy|copied|copying)\b.*\b(delay|latency|return|performance)\b", r"\bif i copied\b", r"\bcopy\b.*\b(cham|tre)\b")),
            ("liquidity-adjusted-copyability", (r"\b(copy|copying)\b.*\b(liquidity|slippage|position size|size)\b", r"\bcopy\b.*\bthanh khoan\b")),
            ("wallet-observation-fit", (r"\b(wallet|address)\b.*\b(worth|should i)\b.*\b(follow|following|observe|observing|track|tracking|monitor|monitoring)\b", r"\bvi\b.*\bdang\b.*\btheo doi\b")),
            ("wallet-trading-style", (r"\bwallet\b.*\b(trading )?style\b", r"\bhow does (this|the) wallet trade\b", r"\bphong cach\b.*\bvi\b")),
            ("take-profit-pattern", (r"\b(take profit|takes profit|profit taking)\b", r"\bchot loi\b")),
            ("loss-cut-pattern", (r"\b(cut loss|cuts losses|stop loss)\b", r"\bcat lo\b")),
            ("wallet-current-holdings", (r"\b(wallet|address)\b.*\b(tokens?|coins?)\b.*\b(trade|traded|trading)\b", r"\btraded token(s)?\b", r"\bvi\b.*\bda giao dich\b")),
            ("wallet-pnl-delta", (r"\bwallet\b.*\b(pnl|p&l)\b.*\b(change|delta|baseline)\b",)),
            ("wallet-position-delta", (r"\bwallet\b.*\b(exposure|position|holdings?)\b.*\b(change|delta|baseline)\b",)),
            ("bonding-curve-progress-delta", (r"\b(bonding curve|curve)\b.*\b(progress|change|delta)\b",)),
            ("graduation-status-delta", (r"\b(graduat|launch status)\w*\b.*\b(change|changed|status)\b",)),
            ("trending-tokens", (r"\b(trending|hot|most active)\b.*\b(tokens?|coins?)\b", r"\btoken\b.*\btrend\w*\b")),
        )
        priority: dict[str, tuple[int, list[str]]] = {}
        for order, (slug, patterns) in enumerate(intent_rules):
            matched = [pattern for pattern in patterns if re.search(pattern, normalized)]
            if matched:
                priority[slug] = (10_000 - order, matched)

        scored: list[tuple[int, SkillSpec, list[str]]] = []
        for skill in self._skills:
            fields = {
                "question": set(TOKEN_RE.findall(skill.question.lower())),
                "name": set(TOKEN_RE.findall(skill.name.lower())),
                "path": set(TOKEN_RE.findall(skill.capability_path.lower())),
            }
            matches = sorted(query_tokens & set().union(*fields.values()))
            score = len(query_tokens & fields["question"]) * 4
            score += len(query_tokens & fields["name"]) * 3
            score += len(query_tokens & fields["path"])
            if skill.slug in priority:
                intent_score, patterns = priority[skill.slug]
                score += intent_score
                matches = sorted(set(matches + [f"intent:{pattern}" for pattern in patterns]))
            if score:
                scored.append((score, skill, matches))
        scored.sort(key=lambda item: (-item[0], item[1].difficulty, item[1].skill_id))
        return [
            {
                "skill_id": skill.skill_id,
                "slug": skill.slug,
                "public_package_name": skill.public_package_name,
                "name": skill.name,
                "question": skill.question,
                "capability_path": skill.capability_path,
                "runtime_status": skill.runtime_status,
                "score": score,
                "matched_terms": matches,
            }
            for score, skill, matches in scored[: max(1, min(limit, 20))]
        ]

    def __len__(self) -> int:
        return len(self._skills)
