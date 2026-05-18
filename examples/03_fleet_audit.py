#!/usr/bin/env python3
"""
Example 03: Fleet Audit
========================
Demonstrates RepoAuditor — audits local repos for README, LICENSE, tests,
CI configuration, and file counts, then scores them 0–1.

Run:
    python examples/03_fleet_audit.py

Note: Audits repos under /home/ubuntu/.openclaw/workspace/repos by default.
      Adjust workspace_dir in RepoAuditor() if your setup differs.
"""

import sys

try:
    from fleet_kit.audits import RepoAuditor
except ImportError:
    print("ERROR: fleet_kit not installed or not in PYTHONPATH.")
    print("  Run from the fleet-kit root directory, or install with:")
    print("    pip install -e .")
    sys.exit(1)


def main() -> None:
    auditor = RepoAuditor()

    # ── Single repo audit ────────────────────────────────────────────────────
    print("=== Single Repo Audit ===")
    report = auditor.audit("fleet-kit")
    print(f"  Repo:       {report['name']}")
    print(f"  Exists:     {report['exists']}")
    print(f"  README:     {'✅' if report['readme'] else '❌'}")
    print(f"  LICENSE:    {'✅' if report['license'] else '❌'}")
    print(f"  Tests:      {report['tests']} found")
    print(f"  CI:         {'✅' if report['ci'] else '❌'}")
    print(f"  Files:      {report['files']}")
    print(f"  Score:      {report['score']}")
    if report["issues"]:
        print(f"  Issues:")
        for issue in report["issues"]:
            print(f"    - {issue}")

    # ── Audit a non-existent repo ────────────────────────────────────────────
    print("\n=== Missing Repo ===")
    missing = auditor.audit("this-repo-does-not-exist")
    print(f"  Exists:    {missing['exists']}")
    print(f"  Issues:   {missing['issues']}")

    # ── Audit all repos in workspace ─────────────────────────────────────────
    print("\n=== All Repos ===")
    all_reports = auditor.audit_all()
    print(f"  Total repos audited: {len(all_reports)}")
    for r in all_reports[:5]:  # show top 5
        grade = "🟢" if r["score"] >= 0.8 else "🟡" if r["score"] >= 0.5 else "🔴"
        print(f"  {grade} {r['name']:30s} score={r['score']}")
    if len(all_reports) > 5:
        print(f"  ... and {len(all_reports) - 5} more")


if __name__ == "__main__":
    main()