Repository Hygiene
==================

Starbelly includes a lightweight repository hygiene check to keep the codebase
clean and prevent accidental commits of editor artifacts or unfinished work
markers in Python modules.

What is checked
---------------

The checker currently enforces:

* No stray artifact files such as backup/temp/editor outputs (for example:
  ``*~``, ``.DS_Store``, ``.swp``, ``.tmp``, ``.orig``, ``.pyc``,
  ``.bish-index``, and ``.bish.sqlite``).
* No unfinished work markers in Python modules under ``starbelly/``,
  ``tests/``, ``integration/``, and ``tools/``. Markers include:
  ``TODO``, ``FIXME``, ``STUB``, ``XXX``, ``TBD``, ``WIP``, and ``HACK``.

How to run
----------

Run directly:

.. code::

   poetry run python tools/repo_hygiene.py

Or run the convenience Make target:

.. code::

   poetry run make repo-hygiene

CI Integration
--------------

The GitHub Actions CI workflow runs this check before tests so hygiene
regressions fail fast.
