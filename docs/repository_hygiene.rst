Repository Hygiene Checks
=========================

Starbelly includes a lightweight repository hygiene check that runs in CI and can
also be executed locally.

What it validates
-----------------

The checker currently enforces two baseline rules:

1. No tracked backup/stale editor artifacts, such as:
   - ``*~``
   - ``*.bak``
   - ``*.orig``
   - ``*.rej``
2. No unresolved marker comments in tracked production Python code:
   - ``TODO``
   - ``FIXME``
   - ``HACK``
   - ``XXX``
   - ``STUB``
   - ``TBD``

The marker scan intentionally excludes docs/tests/workflow metadata directories
to avoid failing on explanatory text that is not production runtime code.

Run locally
-----------

From the repository root:

.. code:: bash

    python tools/repo_hygiene_check.py

If violations are found, the script prints exact file paths and line numbers.

CI workflow
-----------

The workflow definition is stored at:

``.github/workflows/repo-hygiene.yml``

It runs on pull requests and pushes to ``master``.
