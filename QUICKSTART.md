# Quickstart

## Clean up this directory

- Environment bootstrapping now lives in `bin/setup-env.sh`.
- Poetry is configured to create the virtual environment in `.venv/`.
- Python runtime selection is pinned in `.python-version`.

## Prerequisites

- `python3`
- network access for Python package downloads

## Set up the development environment

Run:

```bash
./bin/setup-env.sh
```

The script will:

1. install `uv` and `poetry` into `~/.local/bin` if needed
2. install Python 3.9
3. create a project-local Poetry environment in `.venv`
4. install the project dependencies

## Use the environment

Activate the environment:

```bash
source .venv/bin/activate
```

Run tests:

```bash
.venv/bin/pytest tests/
```

Build docs:

```bash
poetry run make docs
```

## Notes

- The original dependency URLs for `formasaurus` and `rethinkdb` are no longer usable, so the project now installs from public package sources.
- The project currently installs and runs against Python 3.9 for reproducible setup on current machines.

## Environment configuration overrides

Runtime configuration still defaults to `conf/system.ini` + `conf/local.ini`, but
you can now override config sources and key settings with environment variables.

### Config file discovery

- `STARBELLY_CONFIG_DIR`  
  Use `system.ini` and `local.ini` from this directory instead of `./conf`.
- `STARBELLY_CONFIG_FILES`  
  Use an explicit file list (path separator-delimited) instead of the default
  two-file lookup.

### Supported setting overrides

- `STARBELLY_DB_HOST`
- `STARBELLY_DB_PORT`
- `STARBELLY_DB_NAME`
- `STARBELLY_DB_USER`
- `STARBELLY_DB_PASSWORD`
- `STARBELLY_DB_SUPER_USER`
- `STARBELLY_DB_SUPER_PASSWORD`
- `STARBELLY_RATE_LIMITER_CAPACITY`

Example:

```bash
export STARBELLY_CONFIG_DIR="$PWD/conf"
export STARBELLY_DB_HOST="127.0.0.1"
export STARBELLY_DB_PORT="28015"
export STARBELLY_DB_NAME="starbelly"
python -m starbelly --log-level info
```
