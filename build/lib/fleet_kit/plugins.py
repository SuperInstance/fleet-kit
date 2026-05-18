"""
fleet_kit.plugins — Lightweight plugin discovery and runtime for fleet vessels.

Provides PluginRuntime for scanning, loading, and running plugins defined by
MANIFEST.md files throughout the fleet workspace.
"""

import json
import re
import yaml
from pathlib import Path
from typing import Optional


def scan_manifests(root_dir: str = "/home/ubuntu/.openclaw/workspace") -> list[dict]:
    """
    Recursively find all MANIFEST.md files under root_dir and parse them.

    Each manifest uses YAML frontmatter (--- delimited). Parses:
    name, family, version, provides, depends_on, ticks, io.

    Returns:
        List of dicts, each with 'file_path' and parsed manifest fields.
    """
    root = Path(root_dir)
    results = []

    for manifest_path in root.rglob("MANIFEST.md"):
        manifest_text = manifest_path.read_text()

        # Extract YAML frontmatter between --- markers
        if manifest_text.startswith("---"):
            parts = manifest_text.split("---", 2)
            if len(parts) >= 3:
                raw_yaml = parts[1]
                try:
                    parsed = yaml.safe_load(raw_yaml) or {}
                except yaml.YAMLError:
                    parsed = {}
                # Normalise provides
                if "provides" in parsed:
                    parsed["provides"] = _normalise_provides(parsed["provides"])
                # Normalise depends_on
                if "depends_on" in parsed:
                    parsed["depends_on"] = _normalise_depends(parsed["depends_on"])
                parsed["file_path"] = str(manifest_path)
                results.append(parsed)

    return results


def _normalise_provides(provides) -> list[dict]:
    """Coerce provides to a list of {tool_name: ...} dicts."""
    if not provides:
        return []
    if isinstance(provides[0], str):
        return [{"tool_name": p} for p in provides]
    return provides


def _normalise_depends(deps) -> list[dict]:
    """Coerce depends_on to a list of {service: ...} dicts."""
    if not deps:
        return []
    if isinstance(deps[0], str):
        return [{"service": d} for d in deps]
    return deps


class PluginRuntime:
    """
    Lightweight plugin loader driven by a parsed MANIFEST.md dict.

    Usage:
        manifests = scan_manifests()
        runtime = PluginRuntime(manifests[0])
        runtime.load_plugin("some_tool")
        runtime.list_plugins()
    """

    def __init__(self, manifest: dict):
        self.manifest = manifest
        self.name: str = manifest.get("name", "unknown")
        self.family: str = manifest.get("family", "unknown")
        self.version: str = manifest.get("version", "0.1.0")
        self._plugins: dict[str, dict] = {}
        for entry in manifest.get("provides", []):
            if isinstance(entry, dict):
                tool_name = entry.get("tool_name") or next(iter(entry.keys()), None)
                if tool_name:
                    if tool_name in entry:
                        # tool_name is a nested key → value is the metadata dict or scalar
                        sub = entry[tool_name]
                        meta = sub if isinstance(sub, dict) else {"description": sub}
                    else:
                        # tool_name + description are sibling fields
                        meta = {"description": entry.get("description", "")}
                    self._plugins[tool_name] = meta
            elif isinstance(entry, str):
                self._plugins[entry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_plugin(self, name: str) -> dict:
        """
        Locate and validate a named plugin/tool within this manifest.

        Returns plugin metadata dict or raises ValueError if not found.
        """
        if name not in self._plugins:
            raise ValueError(f"Plugin '{name}' not found in manifest '{self.name}'")
        meta = self._plugins[name].copy()
        meta["status"] = "loaded"
        meta["source"] = self.name
        return meta

    def list_plugins(self) -> list[dict]:
        """Return all plugins defined in this manifest."""
        return [
            {"tool_name": name, "description": meta.get("description", ""), "source": self.name}
            for name, meta in self._plugins.items()
        ]

    def get_dependency_graph(self) -> dict:
        """
        Build and return the dependency tree for this manifest.

        Returns {service_name: {service, port, required, reason, status}}.
        """
        graph = {}
        for dep in self.manifest.get("depends_on", []):
            if isinstance(dep, dict):
                svc = dep.get("service", "unknown")
                graph[svc] = {
                    "service": svc,
                    "port": dep.get("port", 0),
                    "required": dep.get("required", False),
                    "reason": dep.get("reason", ""),
                    "status": "available",
                }
            elif isinstance(dep, str):
                graph[dep] = {
                    "service": dep,
                    "port": 0,
                    "required": False,
                    "reason": "",
                    "status": "available",
                }
        return graph

    def run_plugin(self, name: str, context: dict = None) -> dict:
        """
        Execute a named plugin in the given context.

        Currently validates the plugin exists and returns metadata.
        Full execution requires the full Plugin class from plugin-runtime.py.
        """
        self.load_plugin(name)  # validates
        return {
            "plugin": name,
            "source": self.name,
            "family": self.family,
            "version": self.version,
            "manifest": str(self.manifest.get("file_path", "")),
            "context": context or {},
            "status": "validated",
        }