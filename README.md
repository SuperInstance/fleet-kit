# Fleet Kit

Modular Python toolkit extracted from the SuperInstance fleet workspace.
Import what you need — one tool, one function, no heavy framework.

```python
from fleet_kit.plato import PlatoClient
from fleet_kit.consensus import check_consensus
from fleet_kit.models import ask
```

## Install

```bash
pip install fleet-kit
```

Or clone and install locally:

```bash
git clone https://github.com/SuperInstance/fleet-kit.git
cd fleet-kit
pip install -e .
```

## Tools

| Module | Export | What it does |
|--------|--------|-------------|
| `plato` | `PlatoClient` | HMAC-signed read/write to PLATO room server (:8847) |
| `services` | `TileGate`, `RoomManager`, `run_server` | PLATO room server, tile decomposition, quality gates |
| `consensus` | `HolonomyMatrix`, `check_consensus` | Zero-holonomy consensus, tile cardinality tracking |
| `models` | `FleetModelClient`, `ModelRouter` | Route LLM calls to z.ai / DeepSeek / Seed |
| `matrix` | `MatrixClient` | Fleet Matrix bridge — rooms, whispers, sync |
| `crab` | `Crab`, `Crabs` | Agent shell — register, heartbeat, skill injection |
| `construct` | `build_agent`, `deploy_pipeline` | Agent lifecycle — build, tag, deploy, teardown |
| `plugins` | `scan_manifests`, `PluginRuntime` | Plugin system — discover, load, run plugins |
| `keeper` | `KeeperClient` | Agent registry — register, discover, status |
| `audits` | `RepoAuditor` | Zero-shot repo audit — clone, analyze, score, file to PLATO |
| `badges` | `inject_badge`, `scan_missing_badges` | CI badge manager — add badges to repo READMEs |
| `indexer` | `generate_index` | Fleet INDEX.md generator — catalog services, dependencies |
| `utils` | `load_key`, `sign_data` | Shared helpers — credential vault, HMAC, JSON ops |

## Examples

Real working examples in `examples/`:

| File | Demonstrates |
|------|-------------|
| `examples/01_plato_basics.py` | PlatoClient — status, tile submission, room queries |
| `examples/02_consensus_check.py` | HolonomyMatrix and zero-holonomy consensus check |
| `examples/03_fleet_audit.py` | RepoAuditor — audit repos, score them, report issues |

Run any example directly:
```bash
python examples/01_plato_basics.py
```

## Architecture

```
fleet_kit/
├── __init__.py      # Unified export of all symbols
├── plato.py         # PLATO client — read, write, submit tiles
├── services.py      # PLATO server — run, manage rooms
├── consensus.py     # Zero-holonomy + Pythagorean48
├── models.py        # LLM routing — 3 tiers
├── matrix.py        # Matrix bridge — fleet comms
├── crab.py          # Agent shell — agent lifecycle
├── construct.py     # Agent construction pipeline
├── plugins.py       # Plugin runtime
├── keeper.py        # Keeper client — fleet registry
├── audits.py        # Repo audit tools
├── badges.py        # CI badge injection
├── indexer.py       # Infrastructure INDEX.md generator
└── utils.py         # Shared utilities
```

## Adding a New Tool

1. Create `fleet_kit/your_tool.py` with a single class or function
2. Add the export to `fleet_kit/__init__.py`
3. Write tests in `tests/test_your_tool.py`
4. Open a PR

Tools should be:
- **Zero external deps** — stdlib only where possible
- **Self-documenting** — each public symbol has a docstring
- **Tested** — at minimum a smoke test and a unit test

## License

MIT — SuperInstance Contributors
