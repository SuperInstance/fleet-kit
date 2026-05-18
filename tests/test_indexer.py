"""Tests for indexer.py."""
import pytest
from pathlib import Path

from fleet_kit import indexer


class TestGenerateIndex:
    def test_empty_fleet_dir(self, tmp_path):
        empty = tmp_path / "fleet-empty"
        empty.mkdir()
        result = indexer.generate_index(str(empty))
        assert "# Fleet Index" in result
        assert "not found" in result.lower() or "no services" in result.lower()

    def test_single_subdir_services(self, tmp_path):
        fleet = tmp_path / "fleet"
        fleet.mkdir()
        subdir = fleet / "core"
        subdir.mkdir()
        (subdir / "keeper.py").write_text(
            '"""Fleet keeper service — monitors agent health."""\nprint("running")'
        )
        (subdir / "plato.py").write_text("\"\"\"PLATO knowledge graph interface.\"\"\"\n")

        result = indexer.generate_index(str(fleet))
        assert "# Fleet Index" in result
        assert "core" in result
        assert "keeper.py" in result
        assert "plato.py" in result

    def test_subdir_with_no_service_files_ignored(self, tmp_path):
        fleet = tmp_path / "fleet"
        fleet.mkdir()
        (fleet / "empty-dir").mkdir()
        (fleet / "docs.txt").write_text("Just a text file")

        subdir = fleet / "core"
        subdir.mkdir()
        (subdir / "service.py").write_text('"""Core service."""\n')

        result = indexer.generate_index(str(fleet))
        assert "# Fleet Index" in result
        assert "empty-dir" not in result
        assert "docs.txt" not in result
        assert "core" in result