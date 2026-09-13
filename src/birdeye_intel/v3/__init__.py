"""Birdeye core-skill surface."""

SCHEMA_VERSION = "3.0.0"

from .catalog import CommandSpec, CoreCatalog, CoreSkillSpec

__all__ = ["CommandSpec", "CoreCatalog", "CoreSkillSpec"]
__version__ = "3.0.0rc1"
