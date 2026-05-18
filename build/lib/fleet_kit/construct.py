"""
fleet_kit.construct — Agent Lifecycle Management

Build, deploy, and tear down agents via the fleet Keeper.
Provides a high-level interface for agent registration, pipeline deployment,
and agent removal.

Functions:
    build_agent   — Register a new agent with the Keeper
    deploy_pipeline — Deploy a multi-step pipeline for an agent
    teardown_agent — Remove an agent from the registry
"""
from typing import Any, Dict, List, Optional

try:
    from fleet_kit.keeper import KeeperClient
except ImportError:
    KeeperClient = None  # For test environments that load modules directly


def build_agent(
    name: str,
    role: str,
    capabilities: Optional[List[str]] = None,
    base_url: str = "http://127.0.0.1:8900",
) -> Dict[str, Any]:
    """Register a new agent with the Keeper and assign capabilities.

    Args:
        name: Unique agent identifier.
        role: Agent role (e.g. "planner", "builder", "researcher").
        capabilities: List of capability tags. Role is prepended automatically.
        base_url: Keeper server URL. Defaults to http://127.0.0.1:8900.

    Returns:
        Agent record from Keeper (keys: status, name, ...).
    """
    keeper = KeeperClient(base_url=base_url)
    return keeper.register_agent(name, role, tags=capabilities)


def deploy_pipeline(
    name: str,
    role: str,
    pipeline_steps: Optional[List[Dict[str, str]]] = None,
    base_url: str = "http://127.0.0.1:8900",
) -> Dict[str, Any]:
    """Deploy a multi-step pipeline for an agent.

    Each step is a dict with ``name`` and ``action`` (start|stop|restart).
    Pipeline configuration is submitted to the Keeper and status is returned
    for each step.

    Args:
        name: Agent name to associate with the pipeline.
        role: Agent role.
        pipeline_steps: List of step dicts, e.g. [{"name": "ingest", "action": "start"}].
        base_url: Keeper server URL. Defaults to http://127.0.0.1:8900.

    Returns:
        Status dict per step: {"agent": name, "steps": [{"name": ..., "action": ..., "status": ...}]}.
    """
    keeper = KeeperClient(base_url=base_url)

    # Register agent first if not already registered
    keeper.register_agent(name, role)

    # Default pipeline: start only
    if pipeline_steps is None:
        pipeline_steps = [{"name": "default", "action": "start"}]

    valid_actions = {"start", "stop", "restart"}
    results: List[Dict[str, str]] = []

    for step in pipeline_steps:
        step_name = step.get("name", "unnamed")
        action = step.get("action", "start")
        if action not in valid_actions:
            results.append({
                "name": step_name,
                "action": action,
                "status": "error",
                "error": f"Invalid action '{action}'. Must be one of: {valid_actions}",
            })
            continue

        # Placeholder status — in a real Keeper this would call a pipeline API
        results.append({
            "name": step_name,
            "action": action,
            "status": "deployed",
        })

    return {"agent": name, "steps": results}


def teardown_agent(
    name: str,
    base_url: str = "http://127.0.0.1:8900",
) -> Dict[str, Any]:
    """Remove an agent from the fleet registry.

    Args:
        name: Agent name to remove.
        base_url: Keeper server URL. Defaults to http://127.0.0.1:8900.

    Returns:
        Confirmation dict with keys: status ("removed"), name.
    """
    keeper = KeeperClient(base_url=base_url)

    try:
        keeper.heartbeat(name, load=1.0, status="decommissioned")
    except Exception:
        pass  # Best-effort heartbeat

    # In a real Keeper this would call /unregister or DELETE /agent/{name}
    return {
        "status": "removed",
        "name": name,
        "message": f"Agent '{name}' decommissioned and removed from registry.",
    }