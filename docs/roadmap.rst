Roadmap
=======

This roadmap captures the next logical work after the recent streaming API and
documentation push. It is based on the root-level ``README.md``, the
architecture notes in the root-level ``START_HERE.md``, the implementation
summaries in the repository root, and the most recent merged work on streaming
subscriptions.

Current Direction
-----------------

The repository's recent changes point in a consistent direction:

* complete and stabilize the streaming WebSocket API,
* make that functionality easier to adopt through clearer documentation and
  examples, and
* harden areas that are already documented as security or maintenance risks.

The most recent merged pull request completed missing protobuf support for
streaming list subscriptions and added focused tests around those subscription
events. That makes end-to-end streaming support, follow-up integration
coverage, and operator-facing documentation the most natural next steps.

Quick Wins
----------

1. Add end-to-end tests for subscription handlers
   Validate that the WebSocket subscription handlers, subscription manager, and
   generated protobuf messages work together for policy, schedule, and domain
   login subscriptions.

2. Document the protobuf regeneration workflow
   The codebase now depends on ``starbelly.proto`` being the source of truth.
   Contributor docs should show how to regenerate ``starbelly/starbelly_pb2.py``
   and when schema changes require coordinated client updates.

3. Expand streaming API examples
   The repository has the foundation for streaming subscriptions, but the docs
   still emphasize the lower-level API. Short examples for the new list
   subscriptions would make the feature easier to adopt.

Next Incremental Milestones
---------------------------

1. Make TLS verification configurable per policy
   The root-level ``SECURITY_SUMMARY.md`` documents disabled certificate
   verification as a deliberate trade-off. Making this policy-driven is the
   clearest security improvement that aligns with the crawler's existing policy
   architecture.

2. Replace pickle-based job state with a safer serialized format
   The root-level ``SECURITY_SUMMARY.md`` also documents pickle
   deserialization as trusted environment debt. A small migration plan for JSON
   or another safe format is a good follow-on maintenance task.

3. Improve the Python client story
   ``docs/websocket_api.rst`` describes the Python client library as basic and
   incomplete. Better client-side examples or helper utilities would reduce the
   friction of adopting the streaming API that was just completed.

Prioritized Task List
---------------------

The following tasks are intentionally small and incremental.

.. list-table::
   :header-rows: 1

   * - Priority
     - Task
     - Why now
     - Suggested validation
   * - P0
     - Add integration coverage for streaming subscription handlers
     - Recent work completed the protobuf schema and event formatting, so the
       main remaining risk is the server wiring between handlers and events.
     - Run focused pytest coverage for subscription and server modules.
   * - P0
     - Add contributor documentation for protobuf regeneration and compatibility
     - The proto file is now a first-class artifact, and schema drift is an
       easy way to break clients.
     - Build the docs and manually review the updated contributor guidance.
   * - P1
     - Add user-facing examples for the new streaming list subscriptions
     - This turns recent backend work into something easier to consume from the
       UI or Python client.
     - Exercise the example against a local server or mocked event stream.
   * - P1
     - Add policy-level TLS verification controls
     - This directly addresses the highest-priority documented security debt
       without changing the overall crawler architecture.
     - Add focused downloader and policy tests for secure and insecure modes.
   * - P2
     - Plan and implement migration away from pickle job state
     - This is a worthwhile security and maintenance improvement, but it is
       broader than the streaming API follow-up work.
     - Add migration tests that prove existing job state can be read or
       converted safely.

Suggested Execution Order
-------------------------

For the next few incremental pull requests, the lowest-risk sequence is:

1. cover the new streaming subscription paths with end-to-end tests,
2. document protobuf regeneration and streaming subscription usage,
3. improve client-facing examples, then
4. tackle the TLS and serialization hardening work.

That sequence keeps the project moving in the same direction as the recent
changes while reducing the risk of regressions in the parts of the system that
were just completed.
