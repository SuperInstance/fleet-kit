"""
fleet_kit.keeper — Client for the fleet Keeper service (port 8900).

Handles agent registration, heartbeats, and fleet discovery.
No external dependencies — uses urllib only.

Example:
    keeper = KeeperClient()
    keeper.register("my-agent", ["coding", "research"])
    keeper.heartbeat("my-agent")
"""
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

__all__ = ["KeeperClient"]


class KeeperClient:
    """Client for the fleet Keeper service at localhost:8900.

    Args:
        base_url: Base URL of the Keeper server. Defaults to http://127.0.0.1:8900.

    Attributes:
        base_url: Base URL of the Keeper server.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8900") -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> Dict[str, Any]:
        """Make a GET request to the Keeper server."""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to the Keeper server."""
        url = f"{self.base_url}{path}"
        body = json.dumps(data, default=str).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    # ── Agent Lifecycle ────────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        capabilities: Optional[List[str]] = None,
        display_name: Optional[str] = None,
        endpoint: str = "",
    ) -> Dict[str, Any]:
        """Register an agent with the fleet Keeper.

        Args:
            name: Unique agent identifier.
            capabilities: List of capability tags (e.g. ["coding", "research"]).
            display_name: Human-readable name.
            endpoint: Agent's HTTP endpoint (optional).

        Returns:
            Dict with keys: status ("registered"|"updated"), name.
        """
        payload: Dict[str, Any] = {
            "name": name,
            "capabilities": capabilities or [],
            "endpoint": endpoint,
        }
        if display_name:
            payload["display_name"] = display_name
        return self._post("/register", payload)

    def register_agent(self, name: str, role: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Register a new agent (or update if already registered).

        Alias for ``register(name, [role] + (tags or []))`` for convenience.

        Args:
            name: Unique agent name / agent_id.
            role: Agent role (e.g. "planner", "builder", "researcher").
            tags: Optional list of string tags.

        Returns:
            Dict with keys: status ("registered" | "updated"), name.
        """
        return self.register(name, [role] + (tags or []))

    def heartbeat(self, name: str, load: float = 0.0, status: str = "active") -> Dict[str, Any]:
        """Send a heartbeat to the Keeper.

        Args:
            name: Agent name.
            load: Current load/score (0.0–1.0).
            status: Agent status string.

        Returns:
            Dict with keys: status ("ack"|"error"), active_agents.
        """
        return self._post("/heartbeat", {"name": name, "load": load, "status": status})

    def status(self) -> Dict[str, Any]:
        """Return Keeper service status and fleet summary.

        Returns:
            Dict with keys: status, agents_registered, agents_active, uptime, etc.
        """
        return self._get("/status")

    # ── Discovery ──────────────────────────────────────────────────────────────

    def agents(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List registered agents.

        Args:
            active_only: If True, return only active agents.

        Returns:
            List of agent dicts.
        """
        path = "/agents/active" if active_only else "/agents"
        return self._get(path)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return all registered agents.

        Returns:
            List of agent dicts.
        """
        return self.agents()

    def get_agent(self, name: str) -> Dict[str, Any]:
        """Get details for a specific agent.

        Args:
            name: Agent name.

        Returns:
            Agent record dict or {"error": "not found"}.
        """
        return self._get(f"/agent/{name}")

    def agents_active(self) -> int:
        """Return the count of currently active (non-stale) agents.

        Returns:
            Integer count of active agents.
        """
        return self.status().get("agents_active", 0)

    def discover(self, capability: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover agents by capability via beacon discovery.

        Args:
            capability: Capability tag to filter by (optional).

        Returns:
            List of beacon signals from matching agents.
        """
        path = f"/discover?capability={capability}" if capability else "/discover"
        return self._get(path)

    def match(self, capabilities: List[str]) -> List[Dict[str, Any]]:
        """Match agents against a list of capabilities.

        Args:
            capabilities: List of capability tags.

        Returns:
            List of matching agents with match scores.
        """
        caps = ",".join(capabilities)
        return self._get(f"/match?capabilities={caps}")

    def proximity(self, capability: Optional[str] = None) -> List[Dict[str, Any]]:
        """Score active agents by proximity to a capability.

        Args:
            capability: Capability tag (optional).

        Returns:
            List of agents with proximity scores.
        """
        path = f"/proximity?capability={capability}" if capability else "/proximity"
        return self._get(path)