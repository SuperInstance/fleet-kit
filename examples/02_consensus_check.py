#!/usr/bin/env python3
"""
Example 02: Consensus Check
============================
Demonstrates zero-holonomy consensus across a fleet of tiles using
HolonomyMatrix and check_consensus.

The idea: each tile contributes a rotation (SO(3) holonomy) to the fleet graph.
All cycles through the tile network should compose to identity (zero net rotation).
This example builds a small fleet, checks consensus, and shows the result.

Run:
    python examples/02_consensus_check.py
"""

import sys

try:
    from fleet_kit.consensus import HolonomyMatrix, ConsensusTile, check_consensus
except ImportError:
    print("ERROR: fleet_kit not installed or not in PYTHONPATH.")
    print("  Run from the fleet-kit root directory, or install with:")
    print("    pip install -e .")
    sys.exit(1)


def main() -> None:
    # ── Identity matrix ───────────────────────────────────────────────────────
    print("=== HolonomyMatrix Identity ===")
    h_id = HolonomyMatrix.identity()
    print(f"  Is identity: {h_id.is_identity()}")
    print(f"  Deviation from identity: {h_id.deviation():.6f}")

    # ── Rotation from axis-angle ──────────────────────────────────────────────
    print("\n=== Rotation Matrix ===")
    h_rot = HolonomyMatrix.from_axis_angle([0.0, 0.0, 1.0], 0.1)
    print(f"  Is identity (should be False): {h_rot.is_identity()}")
    print(f"  Deviation: {h_rot.deviation():.6f}")

    # ── Build a fleet of 5 tiles (ring topology) ─────────────────────────────
    print("\n=== Building Fleet of 5 Tiles ===")
    tiles = []
    for i in range(5):
        # Each tile gets a small random-ish rotation
        angle = 0.001  # very small angle — near-identity
        axis = [0.0, 0.0, 1.0]  # rotate around z-axis
        h = HolonomyMatrix.from_axis_angle(axis, angle)
        tile = ConsensusTile(id=i, holonomy=h, tags=[f"tile_{i}", "example"])
        tiles.append(tile)
        print(f"  Tile {i}: holonomy deviation={h.deviation():.6f}")

    # ── Check consensus ───────────────────────────────────────────────────────
    print("\n=== Consensus Check ===")
    result = check_consensus(tiles)
    print(f"  Consistent:     {result.consistent}")
    print(f"  Average deviation: {result.deviation:.6f}")
    print(f"  Faulty tile:   {result.faulty_tile}")
    print(f"  Cycle infos:   {len(result.cycle_infos)} cycles checked")

    # ── Quick-check (simulated fleet) ────────────────────────────────────────
    print("\n=== quick_check (simulated fleet of 8 tiles) ===")
    quick_result = check_consensus.__module__  # just show it exists
    from fleet_kit.consensus import quick_check
    qresult = quick_check(tile_count=8, avg_cycle_length=4)
    print(f"  Consistent:     {qresult.consistent}")
    print(f"  Average deviation: {qresult.deviation:.6f}")


if __name__ == "__main__":
    main()