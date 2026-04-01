Daily Progress 2026-03-28
=========================

This note captures the repository analysis requested by the daily progress
workflow for 2026-03-28 and keeps the result in the docs tree for later
reference.

Current Direction
-----------------

Recent merged work points in a consistent direction:

- ``Merge pull request #141`` completed the missing protobuf schema and tests
  for the streaming subscription API.
- ``Merge pull request #123`` documented security trade-offs and added parser
  limits to reduce denial-of-service risk.
- ``Merge pull request #125`` added ``START_HERE.md`` to make onboarding and
  maintenance easier.

Taken together, the project is moving toward a more complete real-time API,
better operational safety, and clearer contributor guidance rather than a large
new subsystem.

Why These Are The Next Logical Steps
------------------------------------

The remaining work already called out by the repository is clustered around the
same themes:

- ``IMPLEMENTATION_SUMMARY.md`` now reflects that the streaming API foundation
  is in place.
- ``docs/AMAZON_Q_REVIEW_2026-01-05_SUMMARY.md`` and ``SECURITY_SUMMARY.md``
  both list follow-up work for configurable SSL verification and safer
  serialization.
- ``integration/test_subscription.py`` still carries a note that its database
  queries should be aligned with the newer shared query patterns.

That makes the best next work incremental: finish the rough edges around the
streaming path, then keep reducing known security and maintenance debt.

Prioritized Improvements
------------------------

Quick wins
~~~~~~~~~~

1. Make downloader SSL verification configurable per crawl policy.
   - Value: resolves the clearest documented security follow-up without
     removing the self-signed certificate escape hatch.
   - Likely files: ``starbelly/downloader.py``, policy configuration docs, and
     downloader tests.

2. Expand streaming subscription coverage around failure handling and initial
   state delivery.
   - Value: builds directly on the newly completed subscription protobuf work.
   - Likely files: ``tests/test_subscription_streaming.py`` and subscription
     helpers.

3. Normalize ``integration/test_subscription.py`` to use the shared database
   access patterns already used elsewhere.
   - Value: small cleanup that reduces drift between integration tests and the
     current implementation.

Incremental follow-up work
~~~~~~~~~~~~~~~~~~~~~~~~~~

4. Plan the ``pickle`` to JSON migration for URL-set serialization.
   - Value: removes a documented long-term security concern.
   - Likely files: ``starbelly/job.py``, compatibility helpers, migration
     tests, and release notes.

5. Add tighter request validation around WebSocket and subscription-facing
   inputs.
   - Value: continues the hardening work started in the recent security PRs.
   - Likely files: ``starbelly/server/``, protobuf request handling, and API
     tests.

Actionable Task List
--------------------

- [ ] Add a policy-level setting for TLS certificate verification and default
      it to the current disabled-verification behavior so existing crawler
      deployments keep working.
- [ ] Add focused tests for subscription startup snapshots, disconnect
      handling, and cancellation paths.
- [ ] Refactor ``integration/test_subscription.py`` to use shared query
      helpers instead of in-test query duplication.
- [ ] Design a backwards-compatible JSON serialization format for persisted URL
      sets.
- [ ] Audit request handlers for missing size, type, and bounds checks.

Recommended Next PR
-------------------

The smallest high-value next PR is the SSL verification follow-up:

- it is already documented as unfinished work,
- it improves security without changing the crawler architecture, and
- it fits the project's recent pattern of small, production-focused updates.
