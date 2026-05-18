"""
Tests for fleet_kit.plugins — PluginRuntime and scan_manifests.
"""

import importlib.util
import sys
from pathlib import Path

# Load plugins.py directly to bypass any broken fleet_kit/__init__.py imports
_plugins_path = Path(__file__).parent.parent / "fleet_kit" / "plugins.py"
_spec = importlib.util.spec_from_file_location("fleet_kit.plugins", _plugins_path)
_plugins_mod = importlib.util.module_from_spec(_spec)
sys.modules["fleet_kit.plugins"] = _plugins_mod
_spec.loader.exec_module(_plugins_mod)

scan_manifests = _plugins_mod.scan_manifests
PluginRuntime = _plugins_mod.PluginRuntime

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────

MANIFEST_MINIMAL = """---
name: bordercollie
family: doc
version: 0.1.0
summary: bordercollie — fleet vessel
provides:
  - tool_name: bordercollie_read
    description: Read documentation
depends_on:
  - service: plato
    port: 8847
    required: false
    reason: Optional PLATO integration
---"""


def make_manifest_dir(parent: Path, content: str = MANIFEST_MINIMAL) -> Path:
    mdir = parent / "bordercollie"
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "MANIFEST.md").write_text(content)
    return mdir


# ── Tests ───────────────────────────────────────────────────────────────────

class TestPluginRuntime:
    """Tests for PluginRuntime class."""

    def test_init(self):
        manifest = {
            "name": "bordercollie",
            "family": "doc",
            "version": "0.1.0",
            "provides": [{"tool_name": "bordercollie_read", "description": "Read docs"}],
        }
        runtime = PluginRuntime(manifest)
        assert runtime.name == "bordercollie"
        assert runtime.family == "doc"
        assert runtime.version == "0.1.0"

    def test_init_with_string_provides(self):
        """Provides as a list of tool name strings is normalised to dicts."""
        manifest = {
            "name": "bordercollie",
            "provides": ["bordercollie_read", "bordercollie_build"],
        }
        runtime = PluginRuntime(manifest)
        plugins = runtime.list_plugins()
        names = {p["tool_name"] for p in plugins}
        assert "bordercollie_read" in names
        assert "bordercollie_build" in names

    def test_list_plugins(self):
        manifest = {
            "name": "bordercollie",
            "provides": [
                {"tool_name": "bordercollie_read", "description": "Read docs"},
                {"tool_name": "bordercollie_build", "description": "Build"},
            ],
        }
        runtime = PluginRuntime(manifest)
        plugins = runtime.list_plugins()
        assert len(plugins) == 2
        names = {p["tool_name"] for p in plugins}
        assert "bordercollie_read" in names
        assert "bordercollie_build" in names

    def test_list_plugins_descriptions(self):
        manifest = {
            "name": "bordercollie",
            "provides": [{"tool_name": "bordercollie_read", "description": "Read the docs"}],
        }
        runtime = PluginRuntime(manifest)
        plugins = runtime.list_plugins()
        assert plugins[0]["description"] == "Read the docs"

    def test_load_plugin_valid(self):
        manifest = {
            "name": "bordercollie",
            "provides": [{"tool_name": "bordercollie_read", "description": "Read docs"}],
        }
        runtime = PluginRuntime(manifest)
        result = runtime.load_plugin("bordercollie_read")
        assert result["status"] == "loaded"
        assert result["source"] == "bordercollie"

    def test_load_plugin_not_found(self):
        manifest = {
            "name": "bordercollie",
            "provides": [],
        }
        runtime = PluginRuntime(manifest)
        with pytest.raises(ValueError, match="not found"):
            runtime.load_plugin("nonexistent_tool")

    def test_get_dependency_graph(self):
        manifest = {
            "name": "some-vessel",
            "depends_on": [
                {"service": "plato", "port": 8847, "required": True, "reason": "Knowledge"},
                {"service": "keeper", "port": 8900, "required": False, "reason": "Auth"},
            ],
        }
        runtime = PluginRuntime(manifest)
        graph = runtime.get_dependency_graph()
        assert "plato" in graph
        assert graph["plato"]["port"] == 8847
        assert graph["plato"]["required"] is True
        assert "keeper" in graph
        assert graph["keeper"]["required"] is False

    def test_get_dependency_graph_string_deps(self):
        """depends_on as list of service name strings is normalised."""
        manifest = {
            "name": "bordercollie",
            "depends_on": ["plato", "keeper"],
        }
        runtime = PluginRuntime(manifest)
        graph = runtime.get_dependency_graph()
        assert "plato" in graph
        assert "keeper" in graph

    def test_run_plugin(self):
        manifest = {
            "name": "bordercollie",
            "family": "doc",
            "version": "0.1.0",
            "file_path": "/tmp/bordercollie/MANIFEST.md",
            "provides": [{"tool_name": "bordercollie_read"}],
        }
        runtime = PluginRuntime(manifest)
        result = runtime.run_plugin("bordercollie_read", {"key": "val"})
        assert result["status"] == "validated"
        assert result["plugin"] == "bordercollie_read"
        assert result["source"] == "bordercollie"
        assert result["context"] == {"key": "val"}

    def test_run_plugin_passes_context(self):
        manifest = {
            "name": "bordercollie",
            "provides": [{"tool_name": "bordercollie_read"}],
        }
        runtime = PluginRuntime(manifest)
        result = runtime.run_plugin("bordercollie_read", {"foo": "bar"})
        assert result["context"]["foo"] == "bar"

    def test_run_plugin_unknown_raises(self):
        manifest = {"name": "bordercollie", "provides": []}
        runtime = PluginRuntime(manifest)
        with pytest.raises(ValueError, match="not found"):
            runtime.run_plugin("unknown")


class Test_scan_manifests:
    """Integration tests for scan_manifests with real temp directories."""

    def test_finds_manifest(self, tmp_path):
        make_manifest_dir(tmp_path)
        results = scan_manifests(str(tmp_path))
        assert len(results) == 1
        assert results[0]["name"] == "bordercollie"
        assert results[0]["family"] == "doc"
        assert "bordercollie" in results[0]["file_path"]

    def test_finds_multiple_manifests(self, tmp_path):
        make_manifest_dir(tmp_path, MANIFEST_MINIMAL)
        sub = tmp_path / "lucerne"
        sub.mkdir()
        (sub / "MANIFEST.md").write_text(MANIFEST_MINIMAL.replace("bordercollie", "lucerne"))
        results = scan_manifests(str(tmp_path))
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert "bordercollie" in names
        assert "lucerne" in names

    def test_ignores_non_manifest_files(self, tmp_path):
        vessel = tmp_path / "vessel"
        vessel.mkdir()
        (vessel / "README.md").write_text("# Readme")
        (vessel / "MANIFEST.md").write_text(MANIFEST_MINIMAL)
        results = scan_manifests(str(tmp_path))
        assert len(results) == 1

    def test_empty_when_no_manifests(self, tmp_path):
        results = scan_manifests(str(tmp_path))
        assert results == []

    def test_provides_normalised(self, tmp_path):
        make_manifest_dir(tmp_path)
        results = scan_manifests(str(tmp_path))
        provides = results[0].get("provides", [])
        tool_names = [p["tool_name"] if isinstance(p, dict) else p for p in provides]
        assert "bordercollie_read" in tool_names

    def test_depends_on_normalised(self, tmp_path):
        make_manifest_dir(tmp_path)
        results = scan_manifests(str(tmp_path))
        deps = results[0].get("depends_on", [])
        assert len(deps) == 1
        assert deps[0].get("service") == "plato"

    def test_file_path_recorded(self, tmp_path):
        make_manifest_dir(tmp_path)
        results = scan_manifests(str(tmp_path))
        assert "file_path" in results[0]
        assert results[0]["file_path"].endswith("bordercollie/MANIFEST.md")