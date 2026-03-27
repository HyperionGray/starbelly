Repository Hygiene Checks
=========================

Starbelly includes a lightweight repository hygiene check to help keep the
repository clean and CI-friendly.

What is checked
---------------

The checker (``tools/repo_hygiene.py``) currently fails if any tracked file:

* Is an editor backup file ending in ``~``
* Is a legacy CI configuration file (for example ``.travis.yml``)
* Is a binary/archive file committed at the repository root (for example
  ``.jar``, ``.zip``, ``.tar``, ``.tgz``, ``.gz``)

Run locally
-----------

From the project root:

.. code:: bash

    poetry run make hygiene

CI integration
--------------

The GitHub Actions CI workflow runs this check before tests. This catches stale
or stray files early and keeps cleanup regressions from re-entering the main
branch.
