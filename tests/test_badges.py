"""Tests for badges.py."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from fleet_kit import badges


class TestInjectBadge:
    def test_no_readme(self, tmp_path):
        result = badges.inject_badge(str(tmp_path))
        assert result["badge_added"] is False
        assert "No README" in result["reason"]

    def test_badge_already_present(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n\n![CI](https://github.com/SuperInstance/foo/actions/workflows/ci.yml/badge.svg)")
        result = badges.inject_badge(str(tmp_path))
        assert result["badge_added"] is False
        assert "already present" in result["reason"]

    def test_badge_added_after_heading(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\nSome description")
        result = badges.inject_badge(str(tmp_path))
        assert result["badge_added"] is True
        content = readme.read_text()
        assert "badge.svg" in content
        assert "# My Project" in content

    def test_no_heading_inserts_at_top(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("No heading here")
        result = badges.inject_badge(str(tmp_path))
        assert result["badge_added"] is True
        content = readme.read_text()
        assert content.startswith("![CI]")


class TestScanMissingBadges:
    def test_missing_badge_detected(self, tmp_path):
        # Create a fake repo with workflows but no badge
        repo = tmp_path / "my-repo"
        repo.mkdir()
        workflows = repo / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI")
        (repo / "README.md").write_text("# my-repo")

        missing = badges.scan_missing_badges(str(tmp_path))
        assert any(r["repo"] == "my-repo" for r in missing)

    def test_repo_without_workflows_ignored(self, tmp_path):
        repo = tmp_path / "no-ci-repo"
        repo.mkdir()
        (repo / "README.md").write_text("# no-ci-repo")

        missing = badges.scan_missing_badges(str(tmp_path))
        assert not any(r["repo"] == "no-ci-repo" for r in missing)

    def test_repo_with_badge_ignored(self, tmp_path):
        repo = tmp_path / "has-badge"
        repo.mkdir()
        workflows = repo / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI")
        (repo / "README.md").write_text(
            "![CI](https://github.com/SuperInstance/has-badge/actions/workflows/ci.yml/badge.svg)"
        )

        missing = badges.scan_missing_badges(str(tmp_path))
        assert not any(r["repo"] == "has-badge" for r in missing)