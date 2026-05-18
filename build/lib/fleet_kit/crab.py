"""
fleet_kit.crab — Agent shell orchestration for the fleet.

High-level wrappers around KeeperClient (register/heartbeat) and
PlatoClient (post tiles) for single agents and fleet-wide operations.

Example:
    # Single agent
    crab = Crab("oracle1", role="coordinator")
    crab.register()
    crab.say("All systems nominal.")
    print(crab.status())

    # Fleet manager
    fleet = Crabs()
    agents = fleet.list()
    scout = fleet.deploy_crab("scout-alpha", role="explorer")
"""
import os
import importlib.util
from typing import Any, Dict, List, Optional

__all__ = ["Crab", "Crabs"]


# ── Load sub-modules directly (avoid fleet_kit package dependencies) ────────

def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_KIT_DIR = os.path.dirname(os.path.abspath(__file__))
_plato_mod = _load_module("plato", f"{_KIT_DIR}/plato.py")
_keeper_mod = _load_module("keeper", f"{_KIT_DIR}/keeper.py")

PlatoClient = _plato_mod.PlatoClient
KeeperClient = _keeper_mod.KeeperClient


# ── Crab — Single Agent Shell ────────────────────────────────────────────────

class Crab:
    """A single agent shell backed by Keeper + PLATO.

    Args:
        name: Unique agent identifier.
        role: Agent role/archetype (e.g. "scout", "builder").
        base_url: Base URL for Keeper. Defaults to http://127.0.0.1:8900.
        keeper: Optional existing KeeperClient instance (used by Crabs to share a client).
        plato: Optional existing PlatoClient instance.
    """

    def __init__(
        self,
        name: str,
        role: str = "agent",
        base_url: str = "http://127.0.0.1:8900",
        keeper: Optional[KeeperClient] = None,
        plato: Optional[PlatoClient] = None,
    ) -> None:
        self.name = name
        self.role = role
        self.base_url = base_url
        self._keeper = keeper if keeper is not None else KeeperClient(base_url)
        self._plato = plato if plato is not None else PlatoClient()

    def register(self, capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        """Register this agent with the fleet Keeper.

        Args:
            capabilities: List of capability tags. Defaults to [role].

        Returns:
            Dict with keys: status, name.
        """
        if capabilities is None:
            capabilities = [self.role]
        return self._keeper.register(
            name=self.name,
            capabilities=capabilities,
            display_name=f"{self.name} ({self.role})",
        )

    def heart(self, load: float = 0.0, status: str = "active") -> Dict[str, Any]:
        """Send a heartbeat to the Keeper.

        Args:
            load: Agent load/score (0.0–1.0).
            status: Agent status string.

        Returns:
            Dict with keys: status, active_agents.
        """
        return self._keeper.heartbeat(self.name, load=load, status=status)

    def say(self, message: str, domain: str = "fleet-general", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Post a PLATO tile as this agent.

        Args:
            message: Tile answer content.
            domain: PLATO room/domain. Defaults to "fleet-general".
            tags: Optional list of tags.

        Returns:
            Dict with keys: status, room, tile_hash, etc.
        """
        question = f"Message from {self.name}"
        return self._plato.submit_tile(
            domain=domain,
            question=question,
            answer=message,
            tags=tags or [self.role, "fleet-comms"],
        )

    def status(self) -> Dict[str, Any]:
        """Return agent details from the Keeper.

        Returns:
            Agent record dict or {"error": "not found"}.
        """
        return self._keeper.get_agent(self.name)


# ── Crabs — Fleet Manager ───────────────────────────────────────────────────

class Crabs:
    """Fleet-wide crab manager. Manages multiple agent shells.

    Args:
        base_url: Base URL for Keeper. Defaults to http://127.0.0.1:8900.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8900") -> None:
        self.base_url = base_url
        self._keeper = KeeperClient(base_url)
        self._crabs: Dict[str, Crab] = {}

    def list(self, active_only: bool = False) -> List[Crab]:
        """Return all registered Crabs as Crab instances.

        Args:
            active_only: If True, return only active agents.

        Returns:
            List of Crab instances.
        """
        agents = self._keeper.agents(active_only=active_only)
        crabs = []
        for a in agents:
            name = a.get("name") or a.get("agent_id", "unknown")
            crab = Crab(name, base_url=self.base_url)
            self._crabs[name] = crab
            crabs.append(crab)
        return crabs

    def find(self, name: str) -> Optional[Crab]:
        """Find a registered Crab by name.

        Args:
            name: Agent name to look up.

        Returns:
            Crab instance if found, None otherwise.
        """
        # Check local cache first
        if name in self._crabs:
            return self._crabs[name]
        # Try Keeper lookup
        rec = self._keeper.get_agent(name)
        if "error" not in rec:
            crab = Crab(name, base_url=self.base_url)
            self._crabs[name] = crab
            return crab
        return None

    def deploy_crab(self, name: str, role: str = "agent", capabilities: Optional[List[str]] = None) -> Crab:
        """Register and return a new Crab.

        Args:
            name: Unique agent identifier for the new crab.
            role: Agent role/archetype.
            capabilities: Optional list of capability tags.

        Returns:
            The registered Crab instance.
        """
        crab = Crab(name, role=role, base_url=self.base_url, keeper=self._keeper)
        crab.register(capabilities=capabilities or [role])
        self._crabs[name] = crab
        return crab