"""
fleet_kit.cli — Command-line interface for fleet-kit.

Usage:
    fleet-kit [--version]
    fleet-kit plato status
    fleet-kit plato submit <domain> <question> <answer> [--tags TAGS] [--confidence SCORE]
    fleet-kit keeper status
    fleet-kit keeper list
    fleet-kit audit <repo_name>
    fleet-kit audit all
    fleet-kit badges scan
    fleet-kit index <fleet_dir>

Examples:
    fleet-kit plato status
    fleet-kit plato submit general "What is a ship?" "A vessel for fishing." --tags fishing --confidence 0.9
    fleet-kit keeper status
    fleet-kit keeper list
    fleet-kit audit fleet-kit
    fleet-kit audit all
    fleet-kit badges scan
    fleet-kit index /home/ubuntu/.openclaw/workspace/fleet
"""
import argparse
import json
import sys
from typing import List, Optional

from fleet_kit.plato import PlatoClient
from fleet_kit.keeper import KeeperClient
from fleet_kit.audits import RepoAuditor
from fleet_kit.badges import scan_missing_badges
from fleet_kit.indexer import generate_index


# ── Plato commands ─────────────────────────────────────────────────────────────

def cmd_plato_status(_args: argparse.Namespace) -> int:
    client = PlatoClient()
    status = client.status()
    print(json.dumps(status, indent=2))
    return 0


def cmd_plato_submit(args: argparse.Namespace) -> int:
    client = PlatoClient()
    tags: List[str] = args.tags.split(",") if args.tags else []
    result = client.submit_tile(
        domain=args.domain,
        question=args.question,
        answer=args.answer,
        tags=tags,
        confidence=args.confidence,
    )
    print(json.dumps(result, indent=2))
    return 0


# ── Keeper commands ─────────────────────────────────────────────────────────────

def cmd_keeper_status(_args: argparse.Namespace) -> int:
    client = KeeperClient()
    status = client.status()
    print(json.dumps(status, indent=2))
    return 0


def cmd_keeper_list(_args: argparse.Namespace) -> int:
    client = KeeperClient()
    agents = client.list_agents()
    print(json.dumps(agents, indent=2))
    return 0


# ── Audit commands ─────────────────────────────────────────────────────────────

def cmd_audit(args: argparse.Namespace) -> int:
    auditor = RepoAuditor()
    if args.repo_name == "all":
        reports = auditor.audit_all()
        for r in reports:
            print(json.dumps(r, indent=2))
            print("---")
        print(f"\nTotal: {len(reports)} repos audited")
    else:
        report = auditor.audit(args.repo_name)
        print(json.dumps(report, indent=2))
    return 0


# ── Badges command ─────────────────────────────────────────────────────────────

def cmd_badges_scan(_args: argparse.Namespace) -> int:
    missing = scan_missing_badges()
    if not missing:
        print("All repos have CI badges.")
        return 0
    print(f"Repos missing CI badges ({len(missing)}):")
    for item in missing:
        print(f"  - {item['repo']}: {item['path']}")
    return 0


# ── Index command ───────────────────────────────────────────────────────────────

def cmd_index(args: argparse.Namespace) -> int:
    index = generate_index(args.fleet_dir)
    print(index)
    return 0


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="fleet-kit",
        description="fleet-kit CLI — modular toolkit for the SuperInstance fleet.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="fleet-kit 0.1.0",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # plato status
    p_status = sub.add_parser("plato", help="PLATO room server commands")
    p_status_sub = p_status.add_subparsers(dest="plato_command", required=True)

    ps = p_status_sub.add_parser("status", help="Get PLATO server status")
    ps.set_defaults(func=cmd_plato_status)

    psubmit = p_status_sub.add_parser("submit", help="Submit a tile to a PLATO room")
    psubmit.add_argument("domain", help="Room/domain name")
    psubmit.add_argument("question", help="Question text")
    psubmit.add_argument("answer", help="Answer text")
    psubmit.add_argument("--tags", help="Comma-separated tags", default=None)
    psubmit.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="Confidence score (0.0–1.0, default: 0.5)",
    )
    psubmit.set_defaults(func=cmd_plato_submit)

    # keeper status / keeper list
    k = sub.add_parser("keeper", help="Fleet Keeper service commands")
    k_sub = k.add_subparsers(dest="keeper_command", required=True)

    ks = k_sub.add_parser("status", help="Get Keeper service status")
    ks.set_defaults(func=cmd_keeper_status)

    kl = k_sub.add_parser("list", help="List all registered agents")
    kl.set_defaults(func=cmd_keeper_list)

    # audit <repo_name> / audit all
    audit = sub.add_parser("audit", help="Audit repos for README, license, tests, CI")
    audit.add_argument(
        "repo_name",
        help="Repo directory name or 'all' to audit every repo",
    )
    audit.set_defaults(func=cmd_audit)

    # badges scan
    badges = sub.add_parser("badges", help="CI badge injection tool")
    badges_sub = badges.add_subparsers(dest="badges_command", required=True)
    bs = badges_sub.add_parser("scan", help="Scan repos for missing CI badges")
    bs.set_defaults(func=cmd_badges_scan)

    # index <fleet_dir>
    idx = sub.add_parser("index", help="Generate a markdown service index from fleet/ subdirs")
    idx.add_argument(
        "fleet_dir",
        default="/home/ubuntu/.openclaw/workspace/fleet",
        nargs="?",
        help="Path to fleet root directory",
    )
    idx.set_defaults(func=cmd_index)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())