Daily Progress 2026-03-31
=========================

This note captures the repository analysis requested by the daily progress
workflow for 2026-03-31 and keeps the result in the docs tree for later
reference.

Current Direction
-----------------

Recent merged work points in a consistent direction:

- ``Merge pull request #141`` completed the protobuf schema and test coverage
  needed to finish the new streaming subscription API.
- ``Merge pull request #125`` added ``START_HERE.md`` to make onboarding and
  maintenance easier for contributors.
- ``Merge pull request #123`` documented security trade-offs and added parsing
  safeguards around HTML processing.

Taken together with ``README.md``, ``QUICKSTART.md``, and ``START_HERE.md``,
the project is moving toward a better documented, real-time crawler backend
that is easier to operate safely rather than toward a brand new subsystem.

Why These Are The Next Logical Steps
------------------------------------

The remaining work already called out by the repository is clustered around the
same themes:

- ``IMPLEMENTATION_SUMMARY.md`` says the streaming API foundation is complete
  and names the next follow-ups as integration tests, UI consumption, and
  performance testing.
- ``STREAMING_API.md`` still describes the need to finish client-facing
  adoption of the subscription flow and to keep validating the event model.
- ``SECURITY_SUMMARY.md`` and ``docs/SECURITY.md`` both keep the focus on
  configurable TLS verification and safer persisted state handling.
- ``integration/test_subscription.py`` still contains an old note about moving
  duplicated database query setup into shared test helpers.

That makes the best next work incremental: finish the rough edges around the
streaming path, then keep reducing documented security and maintenance debt.

Recent Issue And PR Signals
---------------------------

The recent GitHub activity supports the same direction:

- Recent open issues are mostly automated daily progress prompts, so the best
  signal for active engineering work is in merged pull requests rather than the
  issue queue.
- The newest merged PRs focus on streaming subscriptions, security hardening,
  and contributor onboarding instead of a large feature pivot.
- The repository layout also reflects that emphasis: the top level now contains
  quick-start documentation, onboarding notes, security summaries, and the
  streaming design write-up alongside the core ``starbelly/`` package.

Prioritized Improvements
------------------------

Quick wins
~~~~~~~~~~

1. Clean up the follow-up path around streaming documentation and tests.

   Value: keeps the newly completed subscription work easy to finish and
   reduces confusion about what still blocks adoption.

   Likely files: ``STREAMING_API.md``, ``IMPLEMENTATION_SUMMARY.md``, and
   subscription-focused tests.

2. Make TLS certificate verification configurable per crawl policy.

   Value: resolves the clearest documented security follow-up without removing
   the crawler's ability to handle self-signed targets.

   Likely files: ``starbelly/downloader.py``, policy configuration code, and
   downloader tests.

3. Refactor ``integration/test_subscription.py`` to use shared database query
   helpers instead of in-test setup duplication.

   Value: small cleanup directly tied to the streaming area and called out by
   the existing test file itself.

Incremental follow-up work
~~~~~~~~~~~~~~~~~~~~~~~~~~

4. Plan the ``pickle`` to JSON migration for persisted URL-set serialization.

   Value: removes a documented long-term security concern.

   Likely files: ``starbelly/job.py``, migration helpers, and job tests.

5. Add tighter request validation around WebSocket and subscription-facing
   inputs.

   Value: continues the hardening work started in the recent security PRs.

   Likely files: ``starbelly/server/`` and API-facing tests.

Actionable Task List
--------------------

- [ ] Clean up the streaming follow-up docs so the remaining blockers are kept
      in one maintained location.
- [ ] Add a policy-level TLS verification setting and cover both secure and
      self-signed crawling scenarios with focused tests.
- [ ] Expand subscription tests around startup snapshots, disconnect handling,
      and cancellation paths.
- [ ] Refactor ``integration/test_subscription.py`` to use shared query
      helpers instead of duplicating database setup.
- [ ] Design a backwards-compatible JSON serialization format for persisted URL
      sets before changing storage code.
- [ ] Audit request handlers for missing size, type, and bounds checks.

Validation Notes
----------------

The repository's current validation flow still has pre-existing blockers that
are worth addressing soon:

- ``pytest tests/`` currently fails during collection because
  ``starbelly/starbelly_pb2.py`` imports ``google.protobuf.internal.builder``,
  which is not available in the installed protobuf package.
- ``poetry run make docs`` currently reaches Sphinx rendering and then fails on
  the ``administration`` page with ``UndefinedError("'style' is undefined")``.

Recommended Next PR
-------------------

The smallest high-value next PR is the TLS verification follow-up because it:

- is already documented as unfinished work,
- improves security without changing the crawler architecture, and
- fits the repository's recent pattern of small, production-focused updates.
