"""Validated core-skill catalog backed by audited V2 leaves."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from ..v2.catalog import Catalog as LeafCatalog

NAME_RE = re.compile(r"^birdeye-[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMAND_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class CommandSpec:
    name: str
    question: str
    mode: str
    leaves: tuple[str, ...]
    endpoint_ids: tuple[str, ...]
    entity: str
    requires: tuple[str, ...]
    defaults: dict[str, Any]
    max_calls: int
    default_lookback_seconds: int | None = None
    params: dict[str, Any] | None = None
    locked_params: dict[str, Any] | None = None
    window_fields: dict[str, str] | None = None
    answer_contract: str | None = None
    client_filters: dict[str, Any] | None = None
    fetch_limit: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CommandSpec:
        return cls(
            name=value["name"],
            question=value["question"],
            mode=value["mode"],
            leaves=tuple(value["leaves"]),
            endpoint_ids=tuple(value.get("endpoint_ids", [])),
            entity=value["entity"],
            requires=tuple(value.get("requires", [])),
            defaults=dict(value.get("defaults", {})),
            max_calls=int(value["max_calls"]),
            default_lookback_seconds=value.get("default_lookback_seconds"),
            params=dict(value.get("params", {})),
            locked_params=dict(value.get("locked_params", {})),
            window_fields=dict(value.get("window_fields", {})),
            answer_contract=value.get("answer_contract"),
            client_filters=dict(value.get("client_filters", {})),
            fetch_limit=value.get("fetch_limit"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "leaves": list(self.leaves),
            "endpoint_ids": list(self.endpoint_ids),
            "requires": list(self.requires),
            "defaults": dict(self.defaults),
        }


@dataclass(frozen=True)
class CoreSkillSpec:
    name: str
    title: str
    description: str
    default_prompt: str
    playbook: tuple[str, ...]
    commands: tuple[CommandSpec, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CoreSkillSpec:
        return cls(
            name=value["name"],
            title=value["title"],
            description=value["description"],
            default_prompt=value["default_prompt"],
            playbook=tuple(value["playbook"]),
            commands=tuple(CommandSpec.from_dict(item) for item in value["commands"]),
        )

    @property
    def group(self) -> str:
        return self.name.removeprefix("birdeye-")

    def command(self, name: str) -> CommandSpec:
        for item in self.commands:
            if item.name == name:
                return item
        raise KeyError(f"Unknown command for {self.name}: {name}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "group": self.group,
            "title": self.title,
            "description": self.description,
            "default_prompt": self.default_prompt,
            "playbook": list(self.playbook),
            "commands": [command.as_dict() for command in self.commands],
        }


class CoreCatalog:
    """Load and cross-check the V3 public surface against the V2 endpoint audit."""

    def __init__(
        self,
        skills: Iterable[CoreSkillSpec] | None = None,
        leaf_catalog: LeafCatalog | None = None,
    ) -> None:
        self.leaf_catalog = leaf_catalog or LeafCatalog()
        self.endpoint_specs = json.loads(
            files("birdeye_intel.v2").joinpath("endpoints.json").read_text()
        )
        if skills is None:
            document = json.loads(files(__package__).joinpath("catalog.json").read_text())
            if document.get("schema_version") != "3.0.0":
                raise ValueError("Unsupported V3 catalog schema")
            self.release = document["release"]
            self.runtime_boundary = document["runtime_boundary"]
            skills = [CoreSkillSpec.from_dict(item) for item in document["skills"]]
        else:
            self.release = "custom"
            self.runtime_boundary = "read-only Solana Birdeye Data"
        self._skills = tuple(skills)
        self._by_name = {skill.name: skill for skill in self._skills}
        self._by_group = {skill.group: skill for skill in self._skills}
        if len(self._by_name) != len(self._skills) or len(self._by_group) != len(self._skills):
            raise ValueError("Duplicate V3 skill name or CLI group")
        self._validate()

    def _validate(self) -> None:
        for skill in self._skills:
            if not NAME_RE.fullmatch(skill.name):
                raise ValueError(f"Invalid V3 skill name: {skill.name}")
            seen: set[str] = set()
            for command in skill.commands:
                if not COMMAND_RE.fullmatch(command.name) or command.name in seen:
                    raise ValueError(f"Invalid or duplicate command: {skill.name}/{command.name}")
                seen.add(command.name)
                if command.mode not in {"leaf", "composite", "direct", "radar"}:
                    raise ValueError(f"Invalid command mode: {skill.name}/{command.name}")
                if command.mode == "leaf" and len(command.leaves) != 1:
                    raise ValueError(f"Leaf command must own one leaf: {skill.name}/{command.name}")
                if command.mode == "direct" and (command.leaves or not command.endpoint_ids):
                    raise ValueError(f"Direct command must own endpoints, not leaves: {skill.name}/{command.name}")
                if command.mode == "radar" and (command.leaves or not command.endpoint_ids):
                    raise ValueError(f"Radar command must own endpoints, not leaves: {skill.name}/{command.name}")
                if command.mode not in {"direct", "radar"} and command.endpoint_ids:
                    raise ValueError(f"Only direct or radar commands may own endpoints: {skill.name}/{command.name}")
                if (not command.leaves and not command.endpoint_ids) or command.max_calls < 1:
                    raise ValueError(f"Empty or unbounded command: {skill.name}/{command.name}")
                estimated_calls = 0
                for leaf_name in command.leaves:
                    leaf = self.leaf_catalog.get(leaf_name)
                    if (
                        not leaf.x402_eligible
                        or leaf.unapproved_endpoint_ids
                        or leaf.non_x402_endpoint_ids
                        or leaf.scope_excluded_endpoint_ids
                    ):
                        raise ValueError(
                            f"V3 command references an ineligible leaf: {skill.name}/{command.name}/{leaf_name}"
                        )
                    estimated_calls += len(leaf.endpoint_ids)
                for endpoint_id in command.endpoint_ids:
                    endpoint = self.endpoint_specs.get(endpoint_id)
                    if not endpoint or not endpoint.get("x402_eligible") or not endpoint.get("approved"):
                        raise ValueError(
                            f"V3 command references an ineligible endpoint: {skill.name}/{command.name}/{endpoint_id}"
                        )
                    estimated_calls += 1
                if estimated_calls > command.max_calls:
                    raise ValueError(
                        f"Call budget is below dependency count: {skill.name}/{command.name}"
                    )

    def get(self, identifier: str) -> CoreSkillSpec:
        key = identifier.strip().lower()
        try:
            return self._by_name.get(key) or self._by_group[key]
        except KeyError as exc:
            raise KeyError(f"Unknown Birdeye core skill: {identifier}") from exc

    def resolve(self, group: str, command: str) -> tuple[CoreSkillSpec, CommandSpec]:
        skill = self.get(group)
        return skill, skill.command(command)

    def list(self) -> list[CoreSkillSpec]:
        return list(self._skills)

    @property
    def command_count(self) -> int:
        return sum(len(skill.commands) for skill in self._skills)

    def __len__(self) -> int:
        return len(self._skills)
