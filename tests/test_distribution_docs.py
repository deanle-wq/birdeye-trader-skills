from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".csv", ".py", ".toml", ".example"}


class DistributionDocumentationTests(unittest.TestCase):
    def test_public_repository_excludes_internal_release_artifacts(self) -> None:
        forbidden = ("qa", "core-skills", "core-manifest.json", "scripts")
        present = []
        for name in forbidden:
            path = ROOT / name
            if path.is_file() or (path.is_dir() and any(item.is_file() for item in path.rglob("*"))):
                present.append(name)
        self.assertEqual(present, [])

    def test_installation_surface_is_complete(self) -> None:
        required = (
            "README.md",
            "docs/INSTALL.md",
            "docs/TROUBLESHOOTING.md",
            ".codex/INSTALL.md",
            ".opencode/INSTALL.md",
        )
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

        readme = (ROOT / "README.md").read_text()
        for invariant in (
            "Quick start for AI agents",
            "Install Birdeye CLI",
            "Configure your API key privately",
            "Verify setup",
            "Try it with natural language",
            "Update",
            "Troubleshooting",
            "Safety and product boundaries",
        ):
            self.assertIn(invariant, readme)

    def test_local_markdown_links_resolve(self) -> None:
        markdown_files = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
        pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
        missing: list[str] = []
        for document in markdown_files:
            for target in pattern.findall(document.read_text()):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                path = target.split("#", 1)[0]
                if path and not (document.parent / path).resolve().exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_public_text_does_not_name_a_competitor(self) -> None:
        blocked_name = "g" + "mgn"
        violations: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.suffix not in TEXT_SUFFIXES:
                continue
            if blocked_name in path.read_text(errors="ignore").lower():
                violations.append(str(path.relative_to(ROOT)))
        self.assertEqual(violations, [])

    def test_every_public_skill_has_an_entrypoint_and_agent_metadata(self) -> None:
        package_dirs = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.assertTrue(package_dirs)
        incomplete = [
            path.name
            for path in package_dirs
            if not (path / "SKILL.md").is_file() or not (path / "agents/openai.yaml").is_file()
        ]
        self.assertEqual(incomplete, [])


if __name__ == "__main__":
    unittest.main()
