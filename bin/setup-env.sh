#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_UV_BIN="$HOME/.local/bin/uv"
DEFAULT_POETRY_BIN="$HOME/.local/bin/poetry"
UV_BIN="${UV_BIN:-$DEFAULT_UV_BIN}"
POETRY_BIN="${POETRY_BIN:-$DEFAULT_POETRY_BIN}"
ACTION="setup"

usage() {
    cat <<'EOF'
Usage: ./bin/setup-env.sh [--check] [--help]

Options:
  --check   Validate environment readiness without installing anything.
  --help    Show this help message.

Environment overrides:
  PYTHON_VERSION  Python version to install/use (defaults to .python-version).
  UV_BIN          Preferred uv binary path.
  POETRY_BIN      Preferred poetry binary path.
EOF
}

get_python_version() {
    if [[ -n "${PYTHON_VERSION:-}" ]]; then
        echo "$PYTHON_VERSION"
    elif [[ -f "$ROOT_DIR/.python-version" ]]; then
        tr -d '[:space:]' < "$ROOT_DIR/.python-version"
    else
        echo "3.9"
    fi
}

resolve_tool_bin() {
    local tool_name="$1"
    local preferred_bin="$2"
    if [[ -x "$preferred_bin" ]]; then
        echo "$preferred_bin"
        return 0
    fi
    if command -v "$tool_name" >/dev/null 2>&1; then
        command -v "$tool_name"
        return 0
    fi
    return 1
}

check_environment() {
    local python_version="$1"
    local missing=0
    local uv_path="missing"
    local poetry_path="missing"

    echo "Environment diagnostics"
    echo "======================="
    echo "Project root: $ROOT_DIR"
    echo "Python version target: $python_version"

    if command -v python3 >/dev/null 2>&1; then
        echo "python3: OK ($(python3 --version 2>/dev/null || echo "unknown version"))"
    else
        echo "python3: MISSING"
        missing=1
    fi

    if python3 -m pip --version >/dev/null 2>&1; then
        echo "pip: OK ($(python3 -m pip --version | awk '{print $1 " " $2}'))"
    else
        echo "pip: MISSING (python3 -m pip unavailable)"
        missing=1
    fi

    if uv_path="$(resolve_tool_bin uv "$UV_BIN")"; then
        echo "uv: OK ($uv_path)"
        echo "  version: $("$uv_path" --version 2>/dev/null || echo "unknown")"
    else
        echo "uv: MISSING (checked $UV_BIN and PATH)"
        missing=1
    fi

    if poetry_path="$(resolve_tool_bin poetry "$POETRY_BIN")"; then
        echo "poetry: OK ($poetry_path)"
        echo "  version: $("$poetry_path" --version 2>/dev/null || echo "unknown")"
    else
        echo "poetry: MISSING (checked $POETRY_BIN and PATH)"
        missing=1
    fi

    if [[ -d "$ROOT_DIR/.venv" ]]; then
        echo ".venv: present ($ROOT_DIR/.venv)"
    else
        echo ".venv: not present"
    fi

    if [[ "$uv_path" != "missing" ]]; then
        if "$uv_path" python find "$python_version" >/dev/null 2>&1; then
            echo "python runtime $python_version: installed in uv"
        else
            echo "python runtime $python_version: not installed in uv"
        fi
    fi

    if [[ "$missing" -eq 0 ]]; then
        echo "Result: READY"
    else
        echo "Result: NOT READY"
    fi
    return "$missing"
}

install_bootstrap_tools() {
    if ! resolve_tool_bin uv "$UV_BIN" >/dev/null 2>&1 || \
       ! resolve_tool_bin poetry "$POETRY_BIN" >/dev/null 2>&1; then
        python3 -m pip install --user --upgrade uv poetry
    fi
}

main() {
    local python_version
    python_version="$(get_python_version)"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check)
                ACTION="check"
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                echo "Unknown argument: $1" >&2
                usage >&2
                exit 2
                ;;
        esac
        shift
    done

    export PATH="$HOME/.local/bin:$PATH"

    if [[ "$ACTION" == "check" ]]; then
        check_environment "$python_version"
        return
    fi

    install_bootstrap_tools

    local uv_bin
    local poetry_bin
    uv_bin="$(resolve_tool_bin uv "$UV_BIN")"
    poetry_bin="$(resolve_tool_bin poetry "$POETRY_BIN")"

    "$uv_bin" python install "$python_version"

    local python_bin
    python_bin="$("$uv_bin" python find "$python_version")"

    cd "$ROOT_DIR"
    "$poetry_bin" env use "$python_bin"
    "$poetry_bin" install

    echo
    echo "Environment ready."
    echo "Activate with: source \"$ROOT_DIR/.venv/bin/activate\""
    echo "Run tests with: \"$ROOT_DIR/.venv/bin/pytest\" tests/"
    echo "Run diagnostics with: \"$ROOT_DIR/bin/setup-env.sh\" --check"
}

main "$@"
