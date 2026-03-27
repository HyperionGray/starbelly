#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"
POETRY_BIN="${POETRY_BIN:-$HOME/.local/bin/poetry}"
DEFAULT_VERSION_FILE="$ROOT_DIR/.python-version"
PYTHON_VERSION="${PYTHON_VERSION:-}"
CHECK_ONLY=0
INIT_LOCAL_CONFIG=0

print_usage() {
    cat <<'EOF'
Usage:
  ./bin/setup-env.sh [options]

Options:
  --check                 Validate local environment without installing anything
  --init-local-config     Create conf/local.ini from template if it is missing
  --python-version <ver>  Override python version (defaults to .python-version)
  -h, --help              Show this help text
EOF
}

parse_args() {
    while (($# > 0)); do
        case "$1" in
            --check)
                CHECK_ONLY=1
                shift
                ;;
            --init-local-config)
                INIT_LOCAL_CONFIG=1
                shift
                ;;
            --python-version)
                if (($# < 2)); then
                    echo "Error: --python-version requires a value." >&2
                    exit 2
                fi
                PYTHON_VERSION="$2"
                shift 2
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                echo "Error: unknown argument: $1" >&2
                print_usage >&2
                exit 2
                ;;
        esac
    done
}

resolve_python_version() {
    if [[ -n "$PYTHON_VERSION" ]]; then
        return
    fi

    if [[ -f "$DEFAULT_VERSION_FILE" ]]; then
        PYTHON_VERSION="$(<"$DEFAULT_VERSION_FILE")"
        return
    fi

    echo "Error: no Python version configured." >&2
    echo "Set PYTHON_VERSION, pass --python-version, or create .python-version." >&2
    exit 2
}

ensure_local_config() {
    local template="$ROOT_DIR/conf/local.ini.template"
    local target="$ROOT_DIR/conf/local.ini"

    if [[ -f "$target" ]]; then
        return
    fi

    if [[ -f "$template" ]]; then
        cp "$template" "$target"
        chmod 600 "$target"
        echo "Created $target from local.ini.template."
        return
    fi

    cat >"$target" <<'EOF'
[database]

host =
db =
user =
password =
super_user =
super_password =
EOF
    chmod 600 "$target"
    echo "Created minimal $target."
}

check_environment() {
    local missing=0
    echo "Running environment checks..."

    if command -v python3 >/dev/null 2>&1; then
        echo "ok: python3 found ($(python3 --version 2>&1))"
    else
        echo "missing: python3"
        missing=1
    fi

    if [[ -x "$UV_BIN" ]]; then
        echo "ok: uv found at $UV_BIN"
    else
        echo "missing: uv executable at $UV_BIN"
        missing=1
    fi

    if [[ -x "$POETRY_BIN" ]]; then
        echo "ok: poetry found at $POETRY_BIN"
    else
        echo "missing: poetry executable at $POETRY_BIN"
        missing=1
    fi

    if [[ -f "$DEFAULT_VERSION_FILE" ]]; then
        echo "ok: python version file exists ($DEFAULT_VERSION_FILE)"
    else
        echo "missing: $DEFAULT_VERSION_FILE"
        missing=1
    fi

    if [[ -f "$ROOT_DIR/conf/system.ini" ]]; then
        echo "ok: conf/system.ini present"
    else
        echo "missing: conf/system.ini"
        missing=1
    fi

    if [[ -f "$ROOT_DIR/conf/local.ini" ]]; then
        echo "ok: conf/local.ini present"
    elif [[ -f "$ROOT_DIR/conf/local.ini.template" ]]; then
        echo "warn: conf/local.ini missing; template exists"
    else
        echo "warn: conf/local.ini and template missing"
    fi

    if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
        echo "ok: project virtualenv detected"
    else
        echo "warn: project virtualenv not found at .venv"
    fi

    if ((missing > 0)); then
        echo
        echo "Environment check failed."
        echo "Run setup command after installing missing tools:"
        echo "  ./bin/setup-env.sh --init-local-config"
        return 1
    fi

    echo
    echo "Environment check passed."
}

install_bootstrap_tools() {
    if [[ ! -x "$UV_BIN" || ! -x "$POETRY_BIN" ]]; then
        python3 -m pip install --user uv poetry
    fi
}

main() {
    parse_args "$@"

    if ((CHECK_ONLY)); then
        check_environment
        return
    fi

    resolve_python_version

    install_bootstrap_tools

    export PATH="$HOME/.local/bin:$PATH"

    "$UV_BIN" python install "$PYTHON_VERSION"

    local python_bin
    python_bin="$("$UV_BIN" python find "$PYTHON_VERSION")"

    cd "$ROOT_DIR"
    "$POETRY_BIN" env use "$python_bin"
    "$POETRY_BIN" install

    if ((INIT_LOCAL_CONFIG)); then
        ensure_local_config
    fi

    echo
    echo "Environment ready."
    echo "Python version: $PYTHON_VERSION"
    echo "Activate with: source \"$ROOT_DIR/.venv/bin/activate\""
    echo "Run tests with: \"$ROOT_DIR/.venv/bin/pytest\" tests/"
}

main "$@"
