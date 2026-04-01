Daily Progress 2026-03-18
=========================

This note captures the repository analysis requested by the daily progress
workflow for 2026-03-18 and keeps the result in the docs tree for later
reference.

Current Direction
-----------------

Recent repository activity points in a consistent direction:

- ``Merge pull request #141`` completed the protobuf schema, generated code,
  and focused tests needed to make the streaming subscription API functional.
- ``README.md``, ``QUICKSTART.md``, and ``START_HERE.md`` all emphasize a
  crawler that is easier to deploy, operate, and extend without rebuilding the
  core architecture.
- ``docs/SECURITY.md`` and ``SECURITY_SUMMARY.md`` keep the near-term focus on
  hardening the existing crawler rather than adding a brand new subsystem.

Taken together, Starbelly is currently moving toward a better documented,
real-time crawler backend with fewer rough edges around operations, security,
and testability.

Recent Issue And PR Signals
---------------------------

The recent GitHub signals support the same direction:

- The most important recent engineering PR is still ``#141``, which finished
  the streaming subscription path for policies, schedules, and domain logins.
- Open review issues such as ``#116`` and ``#101`` keep surfacing build,
  documentation, and maintainability gaps rather than requesting a major new
  product area.
- The issue queue is otherwise dominated by automated daily-progress prompts,
  which means the strongest signal for next work comes from merged PRs,
  documented follow-ups, and obvious inconsistencies in the repo.

Why These Are The Next Logical Steps
------------------------------------

The remaining work is tightly clustered around the streaming and hardening work
that is already in progress:

- ``STREAMING_API.md`` still says the protobuf event and request definitions
  are missing even though PR ``#141`` completed that work.
- ``IMPLEMENTATION_SUMMARY.md`` also still describes the streaming API as only
  partially complete, so the repository's own status docs no longer match the
  implementation.
- ``integration/test_subscription.py`` still starts with an old note about
  duplicated database query setup that should be moved into cleaner helpers.
- ``docs/SECURITY.md`` and ``SECURITY_SUMMARY.md`` keep documenting follow-up
  work around configurable TLS verification and safer persisted state handling.

That makes the best next steps incremental: first make the repository's
documentation accurately describe the finished streaming work, then keep paying
down the nearby security and test-maintenance debt.

Prioritized Improvements
------------------------

Quick wins
~~~~~~~~~~

1. Update stale streaming status documents.

   Value: removes the clearest source of confusion for contributors by making
   ``STREAMING_API.md`` and ``IMPLEMENTATION_SUMMARY.md`` match the code that
   shipped in PR ``#141``.

2. Refactor ``integration/test_subscription.py`` to use shared query helpers.

   Value: small, localized cleanup directly called out in the file itself and
   closely related to the project's newest subscription work.

3. Add focused validation around policy-level TLS verification settings.

   Value: addresses the most clearly documented security follow-up without
   changing the crawler's overall behavior or deployment model.

Incremental follow-up work
~~~~~~~~~~~~~~~~~~~~~~~~~~

4. Expand subscription coverage around startup snapshots, disconnect handling,
   and cancellation paths.

5. Plan a backwards-compatible migration from ``pickle``-based persisted URL
   set storage to a safer serialized format.

6. Audit request handlers for missing size, type, and bounds validation on
   API-facing inputs.

Actionable Task List
--------------------

- [ ] Clean up the streaming documentation so all status notes agree that the
      protobuf-backed subscription API is complete.
- [ ] Refactor ``integration/test_subscription.py`` to use shared helpers for
      table setup and query access.
- [ ] Add a policy-level TLS verification setting and cover both trusted and
      self-signed target scenarios with focused tests.
- [ ] Expand subscription tests around initial snapshots, disconnect handling,
      and graceful cancellation.
- [ ] Design a migration path away from persisted ``pickle`` state before
      changing on-disk formats.
- [ ] Review WebSocket request handlers for missing validation checks.

Recommended Next PR
-------------------

The smallest high-value next PR is the streaming documentation refresh because
it is tightly scoped, immediately useful to contributors, and directly aligned
with the work that just landed in PR ``#141``. After that, the subscription
test cleanup is the next most natural incremental improvement.
