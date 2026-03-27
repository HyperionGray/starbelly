# Overview

Starbelly is a user-friendly web crawler that is easy to deploy and configure.
Learn more at
[starbelly.readthedocs.io](http://starbelly.readthedocs.io/en/latest/).

[![Read the Docs](https://img.shields.io/readthedocs/starbelly.svg)](https://starbelly.readthedocs.io)

## CI pipeline

This repository uses GitHub Actions for continuous integration in
`.github/workflows/ci.yml`.

- `quality` job (Python 3.9): validates Poetry metadata and bytecode-compiles
  project packages (`starbelly`, `tests`, `tools`, `integration`) to catch
  syntax/import regressions quickly.
- `unit-tests` job (Python 3.7, 3.8, 3.9): runs the unit test suite in `tests/`.

### Running the same checks locally

```bash
poetry install
poetry check
poetry run python -m compileall starbelly tests tools integration
poetry run pytest -q tests/
```

# LICENSE

Starbelly is under a proprietary license. Please contact Hyperion Gray at
acaceres@hyperiongray.com

