"""Repository hygiene checks for tracked files.

This script is intentionally lightweight so it can run in CI and during local
development without extra dependencies.
"""

from pathlib import PurePosixPath
import subprocess
import sys
from typing import Iterable, List, Sequence


LEGACY_CI_FILES = {".travis.yml"}
ROOT_BINARY_EXTENSIONS = {".jar", ".zip", ".tar", ".tgz", ".gz"}


def collect_violations(tracked_paths: Sequence[str]) -> List[str]:
    """Return a list of human-readable hygiene violations."""
    violations: List[str] = []
    for raw_path in tracked_paths:
        path = PurePosixPath(raw_path)
        path_text = path.as_posix()

        if path.name.endswith("~"):
            violations.append(f"Tracked editor backup file: {path_text}")

        if path_text in LEGACY_CI_FILES:
            violations.append(
                f"Tracked legacy CI configuration: {path_text} (use GitHub Actions)"
            )

        if len(path.parts) == 1 and path.suffix.lower() in ROOT_BINARY_EXTENSIONS:
            violations.append(
                f"Tracked binary/archive file in repository root: {path_text}"
            )

    return violations


def get_tracked_files() -> Iterable[str]:
    """Read tracked files from git."""
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    violations = collect_violations(list(get_tracked_files()))
    if not violations:
        print("Repository hygiene check passed.")
        return 0

    print("Repository hygiene violations found:")
    for violation in violations:
        print(f"- {violation}")
    print(f"Total violations: {len(violations)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
