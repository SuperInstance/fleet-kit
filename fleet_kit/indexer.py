"""Fleet INDEX generator — builds a markdown service index from fleet/ subdirs."""
import re
from pathlib import Path

SERVICE_EXTENSIONS = {".py", ".sh", ".rs", ".go", ".js", ".ts"}


def _extract_docstring(file_path: Path) -> str:
    """Read a service file and extract its module/package docstring."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""

    # Python docstring
    if file_path.suffix == ".py":
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            text = match.group(1).strip().split("\n")[0]
            return text.strip().strip('"').strip("'")[:80]

    # Shell comment
    if file_path.suffix == ".sh":
        lines = content.split("\n")
        for line in lines[:10]:
            m = re.match(r"^\s*#\s*(.+)", line)
            if m:
                return m.group(1).strip()[:80]

    return ""


def _scan_subdir(subdir: Path) -> list[dict]:
    """Scan a fleet subdir for service files and return list of service dicts."""
    services = []
    if not subdir.is_dir():
        return services

    for file in sorted(subdir.iterdir()):
        if file.is_file() and file.suffix in SERVICE_EXTENSIONS:
            doc = _extract_docstring(file)
            services.append({
                "file": file.name,
                "purpose": doc or "—",
            })
    return services


def generate_index(fleet_dir: str = "/home/ubuntu/.openclaw/workspace/fleet") -> str:
    """
    Scan fleet/ subdirectories and build a markdown INDEX.

    Args:
        fleet_dir: Path to the fleet root directory.

    Returns:
        Markdown string (does not write to disk).
    """
    fleet = Path(fleet_dir)
    lines = ["# Fleet Index\n"]

    if not fleet.exists():
        return "# Fleet Index\n\n_Fleet directory not found._\n"

    subdirs = sorted(d for d in fleet.iterdir() if d.is_dir() and not d.name.startswith("."))

    if not subdirs:
        return "# Fleet Index\n\n_No services found._\n"

    for subdir in subdirs:
        services = _scan_subdir(subdir)
        if not services:
            continue

        lines.append(f"## {subdir.name}\n")
        lines.append("| Name | Purpose |")
        lines.append("|------|---------|")
        for svc in services:
            name = svc["file"]
            purpose = svc["purpose"]
            lines.append(f"| `{name}` | {purpose} |")
        lines.append("")

    return "\n".join(lines) + "\n"