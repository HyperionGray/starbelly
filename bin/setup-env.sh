#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="${PYTHON_VERSION:-$(cat "$ROOT_DIR/.python-version")}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"
POETRY_BIN="${POETRY_BIN:-$HOME/.local/bin/poetry}"

install_bootstrap_tools() {
    if [[ ! -x "$UV_BIN" || ! -x "$POETRY_BIN" ]]; then
        python3 -m pip install --user uv poetry
    fi
}

main() {
    install_bootstrap_tools

    export PATH="$HOME/.local/bin:$PATH"

    "$UV_BIN" python install "$PYTHON_VERSION"

    local python_bin
    python_bin="$("$UV_BIN" python find "$PYTHON_VERSION")"

    cd "$ROOT_DIR"
    "$POETRY_BIN" env use "$python_bin"
    "$POETRY_BIN" install

    echo
    echo "Environment ready."
    echo "Activate with: source \"$ROOT_DIR/.venv/bin/activate\""
    echo "Run tests with: \"$ROOT_DIR/.venv/bin/pytest\" tests/"
}

main "$@"
