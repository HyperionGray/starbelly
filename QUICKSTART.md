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

## Configuration file selection

Starbelly now supports explicit configuration path selection without editing
`starbelly/config.py`.

Resolution order is:

1. `get_config(config_files=[...])`
2. `STARBELLY_CONFIG_FILES` (multiple files separated by `:` on Linux/macOS)
3. `get_config(config_dir=...)`
4. `STARBELLY_CONFIG_DIR`
5. default project `conf/system.ini` + `conf/local.ini`

Examples:

```bash
# Use one alternate config directory containing system.ini + local.ini
export STARBELLY_CONFIG_DIR=/etc/starbelly

# Or provide explicit files in precedence order
export STARBELLY_CONFIG_FILES=/etc/starbelly/system.ini:/etc/starbelly/local.ini
```
