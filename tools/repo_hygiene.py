"""Repository hygiene checks for source and test code.

This script validates two things:
1. No stray editor/backup artifacts are present.
2. No unfinished work markers remain in Python source/test/tooling modules.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Sequence


_UNFINISHED_MARKER_PARTS = (
    ("TO", "DO"),
    ("FIX", "ME"),
    ("ST", "UB"),
    ("X", "XX"),
    ("TB", "D"),
    ("W", "IP"),
    ("HA", "CK"),
)
UNFINISHED_MARKERS = tuple("".join(parts) for parts in _UNFINISHED_MARKER_PARTS)
UNFINISHED_MARKER_RE = re.compile(r"\b({})\b".format("|".join(UNFINISHED_MARKERS)))

SCANNED_SOURCE_DIRS = ("starbelly", "tests", "integration", "tools")
SCANNED_SOURCE_EXTENSIONS = (".py",)
SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

STRAY_SUFFIXES = (".bak", ".tmp", ".old", ".orig", ".rej", ".swp", ".swo", ".pyc")
STRAY_FILENAMES = {".DS_Store", ".bish-index", ".bish.sqlite"}


@dataclass(frozen=True)
class Violation:
    kind: str
    path: str
    line: int
    detail: str


def _iter_files(root: Path, start_dirs: Sequence[str]) -> Iterator[Path]:
    for start_dir in start_dirs:
        candidate = root / start_dir
        if not candidate.exists() or not candidate.is_dir():
            continue
        for current_root, dir_names, file_names in os.walk(candidate):
            dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]
            current_path = Path(current_root)
            for filename in file_names:
                yield current_path / filename


def _iter_all_repo_files(root: Path) -> Iterator[Path]:
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = [d for d in dir_names if d not in SKIP_DIRS]
        current_path = Path(current_root)
        for filename in file_names:
            yield current_path / filename


def find_unfinished_markers(root: Path) -> List[Violation]:
    violations = []
    for path in _iter_files(root, SCANNED_SOURCE_DIRS):
        if path.suffix not in SCANNED_SOURCE_EXTENSIONS:
            continue
        relative_path = str(path.relative_to(root))
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                match = UNFINISHED_MARKER_RE.search(line)
                if match:
                    marker = match.group(1)
                    violations.append(
                        Violation(
                            kind="unfinished-marker",
                            path=relative_path,
                            line=line_number,
                            detail=marker,
                        )
                    )
    return violations


def _is_stray_file(path: Path) -> bool:
    name = path.name
    if name in STRAY_FILENAMES:
        return True
    if name.endswith("~"):
        return True
    return path.suffix in STRAY_SUFFIXES


def find_stray_files(root: Path) -> List[Violation]:
    violations = []
    for path in _iter_all_repo_files(root):
        if not _is_stray_file(path):
            continue
        relative_path = str(path.relative_to(root))
        violations.append(
            Violation(kind="stray-file", path=relative_path, line=0, detail="artifact")
        )
    return violations


def run_checks(root: Path) -> List[Violation]:
    violations = []
    violations.extend(find_stray_files(root))
    violations.extend(find_unfinished_markers(root))
    return sorted(violations, key=lambda item: (item.kind, item.path, item.line))


def _render_violations(violations: Sequence[Violation]) -> str:
    lines = []
    for violation in violations:
        if violation.line:
            lines.append(
                "{kind}: {path}:{line} ({detail})".format(
                    kind=violation.kind,
                    path=violation.path,
                    line=violation.line,
                    detail=violation.detail,
                )
            )
        else:
            lines.append(
                "{kind}: {path} ({detail})".format(
                    kind=violation.kind,
                    path=violation.path,
                    detail=violation.detail,
                )
            )
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repository hygiene checks.")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Repository root directory to scan (default: current directory).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    root = Path(args.root).resolve()
    violations = run_checks(root)

    if violations:
        print("Repository hygiene check failed.")
        print(_render_violations(violations))
        return 1

    print("Repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
