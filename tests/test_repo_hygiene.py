from pathlib import Path

from tools import repo_hygiene


MARKER_TO_DO = "TO" "DO"
MARKER_FIX_ME = "FIX" "ME"


def _write(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_find_unfinished_markers_detects_source_markers(tmp_path):
    _write(
        tmp_path / "starbelly" / "module.py",
        "def foo():\n    pass  # TO" "DO\n",
    )
    _write(tmp_path / "docs" / "note.md", f"{MARKER_TO_DO} in docs should be ignored\n")

    violations = repo_hygiene.find_unfinished_markers(tmp_path)

    assert len(violations) == 1
    violation = violations[0]
    assert violation.kind == "unfinished-marker"
    assert violation.path == "starbelly/module.py"
    assert violation.line == 2
    assert violation.detail == MARKER_TO_DO


def test_find_unfinished_markers_ignores_non_python_files(tmp_path):
    _write(tmp_path / "tests" / "sample.txt", f"{MARKER_FIX_ME}\n")

    violations = repo_hygiene.find_unfinished_markers(tmp_path)

    assert violations == []


def test_find_stray_files_detects_known_artifacts(tmp_path):
    _write(tmp_path / "notes.txt~", "backup")
    _write(tmp_path / ".DS_Store", "x")
    _write(tmp_path / "starbelly" / "cache.pyc", "x")
    _write(tmp_path / "starbelly" / "keep.py", "print('ok')\n")

    violations = repo_hygiene.find_stray_files(tmp_path)
    found = {item.path for item in violations}

    assert ".DS_Store" in found
    assert "notes.txt~" in found
    assert "starbelly/cache.pyc" in found
    assert "starbelly/keep.py" not in found


def test_run_checks_returns_sorted_violations(tmp_path):
    _write(tmp_path / "z.tmp")
    _write(tmp_path / "tests" / "a.py", "# HA" "CK\n")  # repo-hygiene: allow-marker

    violations = repo_hygiene.run_checks(tmp_path)

    rendered = [f"{v.kind}:{v.path}:{v.line}" for v in violations]
    assert rendered == sorted(rendered)


def test_main_returns_nonzero_when_violations_exist(tmp_path, capsys):
    _write(tmp_path / "integration" / "task.py", f"# {MARKER_TO_DO}: complete\n")

    exit_code = repo_hygiene.main([str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Repository hygiene check failed." in captured.out
    assert f"integration/task.py:1 ({MARKER_TO_DO})" in captured.out


def test_main_returns_zero_when_clean(tmp_path, capsys):
    _write(tmp_path / "tools" / "script.py", "print('clean')\n")

    exit_code = repo_hygiene.main([str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Repository hygiene check passed." in captured.out
