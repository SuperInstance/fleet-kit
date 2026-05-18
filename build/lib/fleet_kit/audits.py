"""
fleet_kit.audits — zero-shot repo audit tool.

Audits local or remote repos for README, license, tests, CI, and file stats.
Submits reports to PLATO as signed tiles.

Example:
    auditor = RepoAuditor()
    reports = auditor.audit_all()
    auditor.file_to_plato(reports[0])
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import PlatoClient directly from file to avoid triggering package __init__
import importlib.util
spec = importlib.util.spec_from_file_location(
    "plato", Path(__file__).parent / "plato.py"
)
plato_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plato_module)
PlatoClient = plato_module.PlatoClient

__all__ = ["RepoAuditor"]


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: List[str], cwd: Optional[str] = None) -> str:
    """Run a command, return stdout, swallow errors silently."""
    try:
        return subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.DEVNULL, text=True)
    except Exception:
        return ""


def _file_count(repo_path: Path) -> int:
    """Count tracked files in a repo."""
    out = _run(["git", "ls-files"], cwd=str(repo_path))
    return len([l for l in out.splitlines() if l.strip()])


def _test_count(repo_path: Path) -> int:
    """Count test files by extension heuristics."""
    patterns = ["test_", "_test.py", ".test.", "tests/", "__tests__/", "spec/"]
    count = 0
    for root, _, files in os.walk(repo_path):
        skip = {".git", "node_modules", "__pycache__", ".mypy_cache", "dist", "build", "venv", "target"}
        parts = Path(root).relative_to(repo_path).parts
        if any(s in parts for s in skip):
            continue
        for f in files:
            if any(p in f for p in patterns):
                count += 1
    return count


def _has_ci(repo_path: Path) -> bool:
    """Check for CI config files."""
    ci_names = [
        ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile", "Jenkinsfile.locked",
        ".circleci", ".travis.yml", ".taskgraph.yml", "tox.ini", "Makefile",
        ".github", ".workflows",
    ]
    for name in ci_names:
        if (repo_path / name).exists() or (repo_path / ".github" / "workflows").exists():
            return True
    return False


def _score(report: Dict[str, Any]) -> float:
    """Score a repo audit report 0.0–1.0."""
    score = 0.0
    if report.get("readme"):
        score += 0.25
    if report.get("license"):
        score += 0.10
    if report.get("tests", 0) > 0:
        score += 0.25
    if report.get("ci"):
        score += 0.20
    # files: 0→0, 50+ → +0.20
    files = report.get("files", 0)
    score += min(0.20, files / 250)
    return round(score, 3)


# ── RepoAuditor ───────────────────────────────────────────────────────────────

class RepoAuditor:
    """Zero-shot repo audit tool.

    Audits local or remote GitHub repos for presence of documentation,
    licensing, tests, CI, and file-level metrics. Submits reports to PLATO.

    Args:
        workspace_dir: Root directory containing repos to audit.
            Defaults to "/home/ubuntu/.openclaw/workspace/repos".
    """

    def __init__(self, workspace_dir: str = "/home/ubuntu/.openclaw/workspace/repos") -> None:
        self.workspace_dir = Path(workspace_dir)

    def audit(self, name: str) -> Dict[str, Any]:
        """Audit a single local repo by name.

        Args:
            name: Repo directory name (not path) under workspace_dir.

        Returns:
            Dict with keys: name, exists, readme, license, tests, ci, files,
            issues (list), score (float 0–1).
        """
        repo_path = self.workspace_dir / name
        report: Dict[str, Any] = {
            "name": name,
            "exists": repo_path.is_dir(),
            "readme": False,
            "license": False,
            "tests": 0,
            "ci": False,
            "files": 0,
            "issues": [],
            "score": 0.0,
        }
        if not report["exists"]:
            report["issues"].append(f"Directory '{name}' not found in {self.workspace_dir}")
            return report

        # README check
        if any((repo_path / n).exists() for n in ["README.md", "README.txt", "README"]):
            report["readme"] = True
        else:
            report["issues"].append("No README found")

        # License check
        if any((repo_path / n).exists() for n in ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]):
            report["license"] = True
        else:
            report["issues"].append("No LICENSE found")

        # Tests
        report["tests"] = _test_count(repo_path)
        if report["tests"] == 0:
            report["issues"].append("No test files found")

        # CI
        report["ci"] = _has_ci(repo_path)
        if not report["ci"]:
            report["issues"].append("No CI configuration found")

        # File count
        if (repo_path / ".git").exists():
            report["files"] = _file_count(repo_path)
        else:
            # Non-git: walk manually
            for _, _, files in os.walk(repo_path):
                report["files"] += len(files)

        report["score"] = _score(report)
        return report

    def audit_all(self) -> List[Dict[str, Any]]:
        """Audit all repos under workspace_dir.

        Returns:
            List of audit reports sorted by score descending.
        """
        if not self.workspace_dir.is_dir():
            return []

        reports = []
        for entry in sorted(self.workspace_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                reports.append(self.audit(entry.name))

        reports.sort(key=lambda r: -r["score"])
        return reports

    def audit_remote(self, repo_url: str) -> Dict[str, Any]:
        """Clone a remote GitHub repo to a temp dir, audit it, then clean up.

        Args:
            repo_url: HTTPS git URL, e.g. https://github.com/owner/repo.git

        Returns:
            Same structure as audit().
        """
        tmp = Path(tempfile.mkdtemp(prefix="auditor_"))
        try:
            _run(["git", "clone", "--depth=1", repo_url, str(tmp)], cwd=None)
            # Swap workspace_dir temporarily
            original = self.workspace_dir
            self.workspace_dir = tmp
            name = Path(repo_url).stem
            report = self.audit(name)
            report["name"] = repo_url  # use URL as identifier for remote
            self.workspace_dir = original
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return report

    def file_to_plato(self, report: Dict[str, Any], domain: str = "oracle1_infrastructure") -> Dict[str, Any]:
        """Submit an audit report as a tile to PLATO.

        Args:
            report: Audit report dict from audit() or audit_remote().
            domain: PLATO room/domain name. Defaults to "oracle1_infrastructure".

        Returns:
            PLATO server response dict.
        """
        client = PlatoClient()
        score = report.get("score", 0.0)
        grade = "🟢 excellent" if score >= 0.8 else "🟡 good" if score >= 0.5 else "🔴 poor"

        question = f"Repo audit: {report.get('name', 'unknown')}"
        answer = (
            f"**Score: {score} ({grade})**\n\n"
            f"- README: {'✅' if report.get('readme') else '❌'}\n"
            f"- LICENSE: {'✅' if report.get('license') else '❌'}\n"
            f"- Tests: {report.get('tests', 0)} found\n"
            f"- CI: {'✅' if report.get('ci') else '❌'}\n"
            f"- Files: {report.get('files', 0)}\n\n"
        )
        if report.get("issues"):
            answer += "**Issues:**\n" + "\n".join(f"- {i}" for i in report["issues"]) + "\n\n"
        answer += f"_Audited by fleet-kit RepoAuditor_"

        return client.submit_tile(
            domain=domain,
            question=question,
            answer=answer,
            tags=["audit", "repo", "fleet-kit"],
            confidence=float(score),
        )
