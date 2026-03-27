"""Repository hygiene checks used by CI.

This script enforces a small set of baseline repository cleanliness rules:
- No editor backup artifacts (e.g. files ending with "~")
- No unresolved TODO/FIXME/HACK/XXX/STUB/TBD markers in tracked Python code
  outside docs/tests/workflow metadata.
"""

from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_MARKER_PATTERN = re.compile(r"\b(TODO|FIXME|HACK|XXX|STUB|TBD)\b")

BACKUP_SUFFIXES = ("~", ".bak", ".orig", ".rej")
BACKUP_PATTERNS = ("*~", "*.bak", "*.orig", "*.rej")


def tracked_files() -> List[Path]:
    """Return all tracked files from git."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def _is_excluded_from_marker_check(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if rel.suffix != ".py":
        return True
    if rel == Path("tools/repo_hygiene_check.py"):
        # Avoid self-referential marker matches in this checker's own source.
        return True

    excluded_roots = {
        ".github",
        "docs",
        "notebooks",
        "integration",
        "tests",
    }
    return rel.parts[0] in excluded_roots


def _line_matches(path: Path) -> List[Tuple[int, str]]:
    matches: List[Tuple[int, str]] = []
    if not path.exists():
        return matches
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return matches

    for line_no, line in enumerate(content.splitlines(), start=1):
        if FORBIDDEN_MARKER_PATTERN.search(line):
            matches.append((line_no, line.strip()))
    return matches


def find_marker_violations(files: Sequence[Path]) -> List[Tuple[Path, int, str]]:
    violations: List[Tuple[Path, int, str]] = []
    for path in files:
        if _is_excluded_from_marker_check(path):
            continue
        for line_no, line in _line_matches(path):
            violations.append((path, line_no, line))
    return violations


def _looks_like_backup(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    name = rel.name
    if any(name.endswith(suffix) for suffix in BACKUP_SUFFIXES):
        return True
    return any(rel.match(pattern) for pattern in BACKUP_PATTERNS)


def find_backup_artifacts(files: Iterable[Path]) -> List[Path]:
    return [path for path in files if path.exists() and _looks_like_backup(path)]


def main() -> int:
    files = tracked_files()
    marker_violations = find_marker_violations(files)
    backup_artifacts = find_backup_artifacts(files)

    has_error = False
    if marker_violations:
        has_error = True
        print("ERROR: unresolved marker comments found:")
        for path, line_no, line in marker_violations:
            rel = path.relative_to(ROOT)
            print(f"  - {rel}:{line_no}: {line}")

    if backup_artifacts:
        has_error = True
        print("ERROR: backup/stale artifacts are tracked:")
        for path in backup_artifacts:
            print(f"  - {path.relative_to(ROOT)}")

    if has_error:
        print("\nRepository hygiene check failed.")
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
