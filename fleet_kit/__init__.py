"""
fleet-kit — modular toolkit from the Oracle1 fleet workspace.

Import what you need:
    from fleet_kit.plato import PlatoClient
    from fleet_kit.consensus import check_consensus
    from fleet_kit.models import ask
    from fleet_kit.badges import inject_badge
"""

# ── Plato ────────────────────────────────────────────────────────────────────
from .plato import PlatoClient

# ── Services ─────────────────────────────────────────────────────────────────
from .services import TileGate, RoomManager, run_server

# ── Consensus ────────────────────────────────────────────────────────────────
from .consensus import HolonomyMatrix, ConsensusTile, ConsensusResult
from .consensus import check_consensus, quick_check

# ── Models / Model Router ────────────────────────────────────────────────────
from .models import FleetModelClient, ModelResponse

# ── Matrix ───────────────────────────────────────────────────────────────────
from .matrix import MatrixClient

# ── Crab Shell ──────────────────────────────────────────────────────────────
from .crab import Crab, Crabs

# ── Construct ───────────────────────────────────────────────────────────────
from .construct import build_agent, deploy_pipeline, teardown_agent

# ── Plugins ─────────────────────────────────────────────────────────────────
from .plugins import PluginRuntime, scan_manifests

# ── Keeper ──────────────────────────────────────────────────────────────────
from .keeper import KeeperClient

# ── Audit ───────────────────────────────────────────────────────────────────
from .audits import RepoAuditor

# ── Badges ──────────────────────────────────────────────────────────────────
from .badges import inject_badge, scan_missing_badges

# ── Indexer ─────────────────────────────────────────────────────────────────
from .indexer import generate_index

# ── Utils ───────────────────────────────────────────────────────────────────
from .utils import load_key, sign_data

__all__ = [
    # Plato
    "PlatoClient",
    # Services
    "TileGate", "RoomManager", "run_server",
    # Consensus
    "HolonomyMatrix", "ConsensusTile", "ConsensusResult",
    "check_consensus", "quick_check",
    # Models
    "FleetModelClient", "ModelResponse",
    # Matrix
    "MatrixClient",
    # Crab
    "Crab", "Crabs",
    # Construct
    "build_agent", "deploy_pipeline", "teardown_agent",
    # Plugins
    "PluginRuntime", "scan_manifests",
    # Keeper
    "KeeperClient",
    # Audit
    "RepoAuditor",
    # Badges
    "inject_badge", "scan_missing_badges",
    # Indexer
    "generate_index",
    # Utils
    "load_key", "sign_data",
]

__version__ = "0.1.0"
