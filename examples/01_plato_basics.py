#!/usr/bin/env python3
"""
Example 01: PLATO Basics
========================
Demonstrates basic PlatoClient usage — status checks, room queries,
and tile submission with HMAC signatures.

Run:
    python examples/01_plato_basics.py
"""

import sys

try:
    from fleet_kit import PlatoClient
except ImportError:
    print("ERROR: fleet_kit not installed or not in PYTHONPATH.")
    print("  Run from the fleet-kit root directory, or install with:")
    print("    pip install -e .")
    sys.exit(1)


def main() -> None:
    # Create an HMAC-signed client (uses PLATO_SECRET env var or default)
    plato = PlatoClient()

    # ── Status ───────────────────────────────────────────────────────────────
    print("=== PLATO Status ===")
    status = plato.status()
    print(f"  Status:     {status.get('status', 'unknown')}")
    print(f"  Version:    {status.get('version', 'unknown')}")
    print(f"  Total tiles: {status.get('total_tiles', 'unknown')}")

    # Quick tile count helper
    print(f"\n=== Tile Count ===")
    count = plato.tile_count()
    print(f"  Total tiles across all rooms: {count}")

    # ── Room query ────────────────────────────────────────────────────────────
    print("\n=== Room Query ===")
    room = plato.get_room("general")
    print(f"  Room 'general' tile count: {room.get('tile_count', 0)}")

    # ── Tile submission ───────────────────────────────────────────────────────
    print("\n=== Tile Submission ===")
    result = plato.submit_tile(
        domain="oracle1_examples",
        question="What is fleet-kit?",
        answer=(
            "fleet-kit is a modular Python toolkit for the Oracle1 fleet workspace. "
            "It provides PlatoClient, consensus tools, repo audits, and more."
        ),
        tags=["example", "fleet-kit", "demo"],
        confidence=0.95,
    )
    print(f"  Submitted:  {result.get('status', result)}")

    # ── Fetch our submitted tile ─────────────────────────────────────────────
    print("\n=== Fetch Submitted Tiles ===")
    tiles = plato.get_tiles("oracle1_examples", limit=5)
    print(f"  Tiles in 'oracle1_examples': {len(tiles)}")
    for tile in tiles:
        print(f"    - {tile.get('question', '?')}")


if __name__ == "__main__":
    main()