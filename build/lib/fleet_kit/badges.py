"""CI badge injection tool for fleet repos."""
import re
from pathlib import Path

# Match any SuperInstance Actions badge URL (any workflow)
BADGE_PATTERN = re.compile(
    r"!\[[^\]]*\]\(https://github\.com/SuperInstance/[^)]+\)"
)
WORKFLOW_PATTERNS = [
    r"\.github/workflows/([^/]+)\.ya?ml",
]


def inject_badge(repo_path: str, workflow_name: str = "ci.yml") -> dict:
    """
    Inject a GitHub Actions CI badge into a repo's README.md.

    Args:
        repo_path: Absolute path to the repo root.
        workflow_name: Workflow filename (default: ci.yml).

    Returns:
        {"badge_added": bool, "reason": str}
    """
    repo = Path(repo_path)
    readme = repo / "README.md"

    if not readme.exists():
        return {"badge_added": False, "reason": "No README.md found"}

    content = readme.read_text()

    # Already has a SuperInstance Actions badge
    if BADGE_PATTERN.search(content):
        return {"badge_added": False, "reason": "Badge already present"}

    repo_name = repo.name
    badge = (
        f"![CI](https://github.com/SuperInstance/{repo_name}"
        f"/actions/workflows/{workflow_name}/badge.svg)"
    )

    # Find first markdown heading and insert badge after it
    heading_match = re.search(r"^#{1,6}\s+.+$", content, re.MULTILINE)
    if heading_match:
        pos = heading_match.end()
        new_content = content[:pos] + "\n\n" + badge + content[pos:]
    else:
        new_content = badge + "\n\n" + content

    readme.write_text(new_content)
    return {"badge_added": True, "reason": f"Badge added after first heading"}


def scan_missing_badges(workspace_dir: str = "/home/ubuntu/.openclaw/workspace/repos") -> list[dict]:
    """
    Scan all repos in a workspace for missing CI badges.

    Args:
        workspace_dir: Parent directory containing repo subdirs.

    Returns:
        List of {"repo": str, "path": str} for repos missing badges.
    """
    workspace = Path(workspace_dir)
    missing = []

    for repo in sorted(workspace.iterdir()):
        if not repo.is_dir() or repo.name.startswith("."):
            continue

        workflows = repo / ".github" / "workflows"
        readme = repo / "README.md"

        if not workflows.is_dir() or not readme.exists():
            continue

        # Check if any workflow exists
        yaml_files = list(workflows.glob("*.y*ml"))
        if not yaml_files:
            continue

        content = readme.read_text()
        if not BADGE_PATTERN.search(content):
            missing.append({
                "repo": repo.name,
                "path": str(repo),
            })

    return missing
