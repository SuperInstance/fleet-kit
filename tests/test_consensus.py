"""
Tests for fleet_kit.consensus module.
"""

import math
import struct
import sys
import os

# Ensure the fleet_kit package root is on the path
_fleet_kit_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _fleet_kit_root not in sys.path:
    sys.path.insert(0, _fleet_kit_root)

# Pre-populate sys.modules so fleet_kit is available before loading consensus.py directly.
# This avoids triggering fleet_kit/__init__.py (which imports missing submodules).
import importlib
import types

# Create a minimal fleet_kit module stub so ConsensusTile's dataclass field() works
_fleet_kit_mod = types.ModuleType("fleet_kit")
_fleet_kit_mod.__path__ = [os.path.join(_fleet_kit_root, "fleet_kit")]
_fleet_kit_mod.__package__ = "fleet_kit"
sys.modules.setdefault("fleet_kit", _fleet_kit_mod)

# Now load consensus.py as fleet_kit.consensus
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "fleet_kit.consensus",
    os.path.join(_fleet_kit_root, "fleet_kit", "consensus.py"),
)
assert _spec is not None and _spec.loader is not None
_consensus_mod = importlib.util.module_from_spec(_spec)
sys.modules["fleet_kit.consensus"] = _consensus_mod
_spec.loader.exec_module(_consensus_mod)

# Alias into local namespace
HolonomyMatrix = _consensus_mod.HolonomyMatrix
ConsensusTile = _consensus_mod.ConsensusTile
ConsensusResult = _consensus_mod.ConsensusResult
check_consensus = _consensus_mod.check_consensus
quick_check = _consensus_mod.quick_check


class TestHolonomyMatrix:
    def test_identity(self):
        I = HolonomyMatrix.identity()
        assert I.is_identity()
        assert I.deviation() == 0.0

    def test_from_axis_angle(self):
        # 90-degree rotation around Z axis
        H = HolonomyMatrix.from_axis_angle([0, 0, 1], math.pi / 2)
        assert H.deviation() > 0.0
        # cos(pi/2)=0, sin(pi/2)=1
        assert abs(H.data[0][0] - 0.0) < 1e-6
        assert abs(H.data[0][1] - (-1.0)) < 1e-6
        assert abs(H.data[1][0] - 1.0) < 1e-6
        assert abs(H.data[1][1] - 0.0) < 1e-6

    def test_multiply(self):
        H1 = HolonomyMatrix.identity()
        H2 = HolonomyMatrix.from_axis_angle([0, 0, 1], math.pi / 4)
        H3 = H1.multiply(H2)
        # I * H2 == H2
        assert H3.deviation() == H2.deviation()

    def test_deviation(self):
        I = HolonomyMatrix.identity()
        assert I.deviation() == 0.0
        H = HolonomyMatrix.from_axis_angle([1, 0, 0], math.pi)
        assert H.deviation() > 0.0

    def test_is_identity_tolerance(self):
        I = HolonomyMatrix.identity()
        assert I.is_identity(tolerance=1e-6)
        assert I.is_identity(tolerance=1e-3)
        H = HolonomyMatrix.from_axis_angle([0, 0, 1], 0.001)
        assert H.is_identity(tolerance=1e-2)
        assert not H.is_identity(tolerance=1e-8)

    def test_to_bytes_roundtrip(self):
        H = HolonomyMatrix.from_axis_angle([1, 2, 3], 0.5)
        data = H.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) == 72  # 9 * 8
        H2 = HolonomyMatrix.from_bytes(data)
        for i in range(3):
            for j in range(3):
                assert abs(H2.data[i][j] - H.data[i][j]) < 1e-9


class TestCheckConsensus:
    def test_empty_tiles(self):
        result = check_consensus([])
        assert result.consistent
        assert result.deviation == 0.0
        assert result.faulty_tile is None
        assert result.cycle_infos == []

    def test_single_tile_no_cycle(self):
        H = HolonomyMatrix.identity()
        tile = ConsensusTile(id=1, holonomy=H, tags=["a"])
        result = check_consensus([tile])
        assert result.consistent
        assert result.deviation == 0.0

    def test_identity_tiles_consistent(self):
        """Two identity tiles with overlapping tags form a cycle and are consistent."""
        tiles = [
            ConsensusTile(id=0, holonomy=HolonomyMatrix.identity(), tags=["a", "b"]),
            ConsensusTile(id=1, holonomy=HolonomyMatrix.identity(), tags=["b", "c"]),
        ]
        result = check_consensus(tiles)
        assert result.consistent
        assert result.faulty_tile is None

    def test_quick_check(self):
        """quick_check returns a valid ConsensusResult."""
        result = quick_check(tile_count=5, avg_cycle_length=4)
        assert isinstance(result, ConsensusResult)
        assert hasattr(result, "consistent")
        assert hasattr(result, "deviation")
        assert hasattr(result, "faulty_tile")
        assert hasattr(result, "cycle_infos")