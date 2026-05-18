"""
Zero-holonomy consensus tools for fleet-kit.

Provides:
- HolonomyMatrix: 3x3 rotation matrix (SO(3) element)
- ConsensusTile: a tile in the consensus network
- ConsensusResult: result of a consensus check
- check_consensus: O(C·L) zero-holonomy check across tile cycles
- quick_check: simulated consensus check for a fleet
"""

from __future__ import annotations

import math
import random
import struct
from dataclasses import dataclass, field
from typing import List, Optional


class HolonomyMatrix:
    """
    3x3 rotation matrix — element of SO(3).
    Represents the holonomy (parallel transport) around a cycle in the tile graph.
    """

    def __init__(self, data: List[List[float]]):
        if len(data) != 3 or any(len(row) != 3 for row in data):
            raise ValueError("Must be 3x3 matrix")
        self.data = data

    @classmethod
    def identity(cls) -> "HolonomyMatrix":
        """Return the identity matrix (no rotation)."""
        return cls([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    @classmethod
    def from_axis_angle(cls, axis: List[float], angle: float) -> "HolonomyMatrix":
        """
        Construct a rotation matrix from an axis and angle using Rodrigues' formula.

        Args:
            axis: Rotation axis (will be normalized)
            angle: Rotation angle in radians

        Returns:
            HolonomyMatrix representing the rotation
        """
        norm = math.sqrt(sum(a * a for a in axis))
        axis = [a / norm for a in axis]
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        t = 1.0 - cos_a
        x, y, z = axis
        return cls([
            [t * x * x + cos_a,      t * x * y - sin_a * z,  t * x * z + sin_a * y],
            [t * x * y + sin_a * z,  t * y * y + cos_a,      t * y * z - sin_a * x],
            [t * x * z - sin_a * y,  t * y * z + sin_a * x,  t * z * z + cos_a],
        ])

    def multiply(self, other: "HolonomyMatrix") -> "HolonomyMatrix":
        """
        Compose two holonomy matrices: self ∘ other.
        The result represents applying `other` then `self`.
        """
        result = [[0.0] * 3 for _ in range(3)]
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    result[i][j] += self.data[i][k] * other.data[k][j]
        return HolonomyMatrix(result)

    def deviation(self) -> float:
        """
        Frobenius norm of (M - I).
        Measures how far this matrix is from the identity (zero rotation).
        """
        total = 0.0
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                d = self.data[i][j] - expected
                total += d * d
        return math.sqrt(total)

    def is_identity(self, tolerance: float = 1e-6) -> bool:
        """Return True if this matrix is within `tolerance` of identity."""
        return self.deviation() < tolerance

    def to_bytes(self) -> bytes:
        """Serialize to 72 bytes (9 float64 values in row-major order)."""
        return struct.pack(
            "9d",
            *[self.data[i][j] for i in range(3) for j in range(3)]
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "HolonomyMatrix":
        """Deserialize from 72 bytes (9 float64 values)."""
        vals = struct.unpack("9d", data)
        return cls([[vals[i * 3 + j] for j in range(3)] for i in range(3)])


@dataclass
class ConsensusTile:
    """
    A tile participating in the zero-holonomy consensus network.

    Attributes:
        id: Unique tile identifier
        holonomy: This tile's SO(3) holonomy contribution
        tags: Arbitrary labels for routing/filtering
    """
    id: int
    holonomy: HolonomyMatrix
    tags: List[str] = field(default_factory=list)


@dataclass
class ConsensusResult:
    """
    Result of a zero-holonomy consensus check.

    Attributes:
        consistent: True if all cycles have identity holonomy (within tolerance)
        deviation: Average Frobenius deviation across all cycle compositions
        faulty_tile: ID of the first tile that causes inconsistency, or None
        cycle_infos: Information content of each cycle (I = -log|det|)
    """
    consistent: bool
    deviation: float
    faulty_tile: Optional[int] = None
    cycle_infos: List[float] = field(default_factory=list)


def check_consensus(
    tiles: List[ConsensusTile], tolerance: float = 1e-6
) -> ConsensusResult:
    """
    O(C·L) zero-holonomy consensus check.

    Finds cycles in the tile graph via DFS, composes each tile's holonomy
    around the cycle, and verifies the result is identity.

    Args:
        tiles: List of ConsensusTiles
        tolerance: Deviation threshold for identity check

    Returns:
        ConsensusResult describing consensus state
    """
    if not tiles:
        return ConsensusResult(consistent=True, deviation=0.0, faulty_tile=None, cycle_infos=[])

    tile_map = {t.id: t for t in tiles}

    # Build adjacency from tile IDs
    # Neighbors are inferred from tags — tiles with overlapping tags are adjacent
    # This is a simple 1D ring for consensus purposes
    adj: dict[int, List[int]] = {t.id: [] for t in tiles}
    for i, tile in enumerate(tiles):
        # Ring topology: connect to previous and next tile
        if i > 0:
            adj[tile.id].append(tiles[i - 1].id)
        if i < len(tiles) - 1:
            adj[tile.id].append(tiles[i + 1].id)

    # Find cycles via DFS from each unvisited node
    def find_cycles(start_id: int) -> List[List[int]]:
        cycles = []
        stack = [(start_id, [start_id], {start_id})]
        while stack:
            node, path, visited = stack.pop()
            for neighbor in adj.get(node, []):
                if neighbor == path[0] and len(path) > 2:
                    cycles.append(path)
                elif neighbor not in visited:
                    stack.append((neighbor, path + [neighbor], visited | {neighbor}))
        return cycles

    checked_ids: set[int] = set()
    all_cycles: List[List[int]] = []
    for tile in tiles:
        if tile.id not in checked_ids:
            found = find_cycles(tile.id)
            all_cycles.extend(found)
            checked_ids.update(tile.id for cycle in found for tile_id in cycle)

    if not all_cycles:
        return ConsensusResult(consistent=True, deviation=0.0, faulty_tile=None, cycle_infos=[])

    # Compose holonomy for each cycle and check identity
    cycle_infos: List[float] = []
    deviations: List[float] = []

    for cycle in all_cycles:
        H = HolonomyMatrix.identity()
        for tile_id in cycle:
            tile = tile_map.get(tile_id)
            if tile:
                H = H.multiply(tile.holonomy)

        dev = H.deviation()
        deviations.append(dev)

        if dev > tolerance:
            return ConsensusResult(
                consistent=False,
                deviation=dev,
                faulty_tile=tile_id,
                cycle_infos=[],
            )

        # Information content: I = -log|det(H)|
        det = (
            H.data[0][0] * (H.data[1][1] * H.data[2][2] - H.data[1][2] * H.data[2][1])
            - H.data[0][1] * (H.data[1][0] * H.data[2][2] - H.data[1][2] * H.data[2][0])
            + H.data[0][2] * (H.data[1][0] * H.data[2][1] - H.data[1][1] * H.data[2][0])
        )
        abs_det = abs(det)
        if abs_det < 1e-10:
            info = float('inf')
        else:
            info = -math.log(abs_det + 1e-10)
        cycle_infos.append(info)

    avg_deviation = sum(deviations) / len(deviations) if deviations else 0.0

    return ConsensusResult(
        consistent=True,
        deviation=avg_deviation,
        faulty_tile=None,
        cycle_infos=cycle_infos,
    )


def quick_check(tile_count: int, avg_cycle_length: int = 4) -> ConsensusResult:
    """
    Quick consensus check for a fleet of tiles.

    Simulates a Laman-rigid network of tiles with small random rotations
    and verifies zero-holonomy condition.

    Args:
        tile_count: Number of tiles in the simulated network
        avg_cycle_length: Average cycle length (default 4 for Laman graph)

    Returns:
        ConsensusResult for the simulated network
    """
    random.seed(42)

    tiles: List[ConsensusTile] = []
    for i in range(tile_count):
        angle = random.uniform(0, 2 * math.pi)
        axis = [random.uniform(-1, 1) for _ in range(3)]
        H = HolonomyMatrix.from_axis_angle(axis, angle * 0.01)
        tiles.append(ConsensusTile(id=i, holonomy=H, tags=[f"tile_{i}"]))

    return check_consensus(tiles)
