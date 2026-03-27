#!/usr/bin/env python3
"""
Repository hygiene checks used by CI and local development.

This script blocks known stray artifacts from being committed, such as editor
backup files and legacy .bish-* index files.
"""

import argparse
import fnmatch
import os
import subprocess
import sys
from typing import Iterable, List, Sequence, Tuple


BLOCKED_PATTERNS = (
    ".bish-index",
    ".bish.sqlite",
    "**/.bish-index",
    "**/.bish.sqlite",
    "*~",
    "**/*~",
    ".DS_Store",
    "**/.DS_Store",
)


def _git_lines(args: Sequence[str]) -> List[str]:
    result = subprocess.run(
        ["git"] + list(args),
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _unquote_porcelain_path(path: str) -> str:
    # git status --porcelain may quote paths with spaces/special chars.
    if path.startswith('"') and path.endswith('"'):
        return bytes(path[1:-1], "utf-8").decode("unicode_escape")
    return path


def _matches_any(path: str, patterns: Iterable[str]) -> Tuple[bool, str]:
    normalized = path.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1]
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(filename, pattern):
            return True, pattern
    return False, ""


def find_blocked_paths(paths: Iterable[str]) -> List[Tuple[str, str]]:
    blocked = []
    for path in paths:
        matches, pattern = _matches_any(path, BLOCKED_PATTERNS)
        if matches:
            blocked.append((path, pattern))
    return blocked


def tracked_paths() -> List[str]:
    return [path for path in _git_lines(["ls-files"]) if os.path.exists(path)]


def untracked_paths() -> List[str]:
    lines = _git_lines(["status", "--porcelain", "--untracked-files=all"])
    untracked = []
    for line in lines:
        if line.startswith("?? "):
            untracked.append(_unquote_porcelain_path(line[3:]))
    return untracked


def _print_failures(label: str, failures: List[Tuple[str, str]]) -> None:
    if not failures:
        return
    print(f"{label} blocked artifacts:")
    for path, pattern in failures:
        print(f"  - {path} (matched: {pattern})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check repository for blocked stray artifacts."
    )
    parser.add_argument(
        "--tracked-only",
        action="store_true",
        help="Only check tracked files (used in CI).",
    )
    args = parser.parse_args()

    try:
        tracked_failures = find_blocked_paths(tracked_paths())
        untracked_failures = [] if args.tracked_only else find_blocked_paths(untracked_paths())
    except RuntimeError as exc:
        print(f"Error running repository hygiene checks: {exc}", file=sys.stderr)
        return 2

    if tracked_failures or untracked_failures:
        print("Repository hygiene check failed.")
        _print_failures("Tracked", tracked_failures)
        _print_failures("Untracked", untracked_failures)
        print("Remove these files or add safer ignore rules before committing.")
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
