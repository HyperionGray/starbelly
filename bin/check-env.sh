#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRED_PYTHON="${PYTHON_VERSION:-$(cat "$ROOT_DIR/.python-version")}"
DEFAULT_UV_BIN="$HOME/.local/bin/uv"
DEFAULT_POETRY_BIN="$HOME/.local/bin/poetry"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

ERROR_COUNT=0

ok() {
    printf '[ok] %s\n' "$1"
}

warn() {
    printf '[warn] %s\n' "$1"
}

err() {
    printf '[error] %s\n' "$1"
    ERROR_COUNT=$((ERROR_COUNT + 1))
}

resolve_tool() {
    local requested="$1"
    local fallback="$2"

    if [[ -x "$requested" ]]; then
        printf '%s\n' "$requested"
        return 0
    fi

    if command -v "$fallback" >/dev/null 2>&1; then
        command -v "$fallback"
        return 0
    fi

    return 1
}

version_matches() {
    local expected="$1"
    local actual="$2"

    [[ "$actual" == "$expected" || "$actual" == "$expected".* ]]
}

main() {
    local uv_bin poetry_bin poetry_env_path venv_version

    if uv_bin="$(resolve_tool "${UV_BIN:-$DEFAULT_UV_BIN}" uv)"; then
        ok "uv available at $uv_bin"
    else
        err "uv is not installed. Run ./bin/setup-env.sh first."
    fi

    if poetry_bin="$(resolve_tool "${POETRY_BIN:-$DEFAULT_POETRY_BIN}" poetry)"; then
        ok "poetry available at $poetry_bin"
    else
        err "poetry is not installed. Run ./bin/setup-env.sh first."
    fi

    if [[ -n "${uv_bin:-}" ]]; then
        if "$uv_bin" python find "$REQUIRED_PYTHON" >/dev/null 2>&1; then
            ok "python $REQUIRED_PYTHON is installed in uv"
        else
            err "python $REQUIRED_PYTHON is not installed in uv"
        fi
    fi

    if [[ -x "$VENV_PYTHON" ]]; then
        venv_version="$("$VENV_PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
        if version_matches "$REQUIRED_PYTHON" "$venv_version"; then
            ok ".venv Python version is $venv_version"
        else
            err ".venv Python version $venv_version does not match required $REQUIRED_PYTHON"
        fi
    else
        err "virtualenv is missing at .venv/. Run ./bin/setup-env.sh first."
    fi

    if [[ -n "${poetry_bin:-}" ]]; then
        if poetry_env_path="$("$poetry_bin" env info --path 2>/dev/null)"; then
            if [[ "$poetry_env_path" == "$ROOT_DIR/.venv" ]]; then
                ok "poetry env path is project-local (.venv)"
            else
                err "poetry env path points to '$poetry_env_path', expected '$ROOT_DIR/.venv'"
            fi
        else
            warn "poetry env has not been created yet"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi

        if (cd "$ROOT_DIR" && "$poetry_bin" check --lock >/dev/null); then
            ok "poetry metadata and lock file are consistent"
        else
            err "poetry check --lock failed"
        fi
    fi

    if [[ "$ERROR_COUNT" -eq 0 ]]; then
        printf '\nEnvironment verification passed.\n'
        exit 0
    fi

    printf '\nEnvironment verification failed with %s issue(s).\n' "$ERROR_COUNT"
    exit 1
}

main "$@"
