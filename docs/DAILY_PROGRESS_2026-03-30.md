# Daily Progress: 2026-03-30

## Repository direction

Recent repository activity points in a clear direction:

- The latest merged code change in this clone is PR #141, which introduced streaming subscription infrastructure for policies, schedules, and domain logins.
- `README.md` and `START_HERE.md` continue to position Starbelly as a usability-focused crawler with a GUI and real-time WebSocket API.
- `IMPLEMENTATION_SUMMARY.md` and `STREAMING_API.md` both describe the streaming API work as only partially complete because the protobuf schema, regenerated client/server bindings, and integration coverage still need to be finished.
- Recent issues and PRs are dominated by automated daily-progress tracking, so the most concrete product momentum still comes from the streaming API work already in progress.

Natural project direction: finish the streaming API path so the existing subscription infrastructure becomes fully usable by clients, then harden and validate the implementation.

## Key evidence reviewed

- Recent commits: `cf7bd86` (merge of PR #141), `6bc0634` (initial plan on this branch)
- Product and architecture docs: `README.md`, `START_HERE.md`
- Streaming implementation docs: `IMPLEMENTATION_SUMMARY.md`, `STREAMING_API.md`
- Known follow-ups and TODOs: `integration/test_subscription.py`, `SECURITY_SUMMARY.md`, `docs/AMAZON_Q_REVIEW_2026-01-05_SUMMARY.md`
- Recent GitHub activity: daily progress issues and draft PRs, including issue #148 for 2026-03-30

## Prioritized next improvements

### 1. Complete the protobuf layer for streaming subscriptions

Why this is next:

- It is the main blocker called out by both streaming implementation documents.
- The repository already contains the database streaming methods, subscription classes, API handlers, and example documentation.
- Finishing the schema is the smallest code change that unlocks real use of the new subscriptions.

Primary files:

- `starbelly.proto`
- `starbelly/starbelly_pb2.py`
- `starbelly/subscription.py`
- `starbelly/server/subscription.py`

Expected outcome:

- Clients can subscribe to policy, schedule, and domain-login updates using supported protobuf messages instead of incomplete placeholders.

### 2. Add focused integration coverage for the new subscription flows

Why this is next:

- `STREAMING_API.md` explicitly lists initial-state delivery, add, update, delete, cancellation, and concurrent subscription cases as missing test coverage.
- `integration/test_subscription.py` already contains a TODO indicating this area should be improved or reorganized.
- Finishing the schema without tests would leave the most important new behavior unverified.

Primary files:

- `integration/test_subscription.py`
- `tests/test_subscription.py`
- `tests/test_server.py`

Expected outcome:

- The new subscription behavior is exercised with realistic database events and server message assertions.

### 3. Convert the client-facing path from polling to subscriptions

Why this is next:

- The project goal is a usable real-time crawler UI and API.
- The docs repeatedly frame subscriptions as the intended replacement for direct polling.
- This delivers visible product value once the schema and tests are in place.

Primary files:

- `examples/streaming_api_example.py`
- `STREAMING_API.md`
- Any client/UI integration layer that still polls list endpoints

Expected outcome:

- The documented examples and client behavior align with the streaming architecture already added to the server.

### 4. Address the documented security follow-ups

Why this should follow the streaming completion work:

- The repository already documents two known security improvements, but both are larger changes than the streaming quick wins.
- They require either policy/schema changes or data migration work, so they are better treated as the next incremental hardening pass.

Primary files:

- `starbelly/downloader.py`
- `starbelly/job.py`
- `docs/SECURITY.md`
- `SECURITY_SUMMARY.md`

Expected outcome:

- SSL verification becomes configurable per policy or deployment context.
- Pickle-backed job state moves toward safer serialization.

## Actionable task list

- [ ] Clean up the streaming implementation path by comparing `starbelly.proto` against `IMPLEMENTATION_SUMMARY.md` and removing any remaining schema gaps for policy, schedule, and domain-login subscriptions.
- [ ] Add the missing request and event protobuf messages, then regenerate `starbelly/starbelly_pb2.py`.
- [ ] Add targeted integration tests for initial data delivery and add/update/delete events for the new subscriptions.
- [ ] Extend server-level tests so subscription requests and responses are verified end to end.
- [ ] Update `examples/streaming_api_example.py` and `STREAMING_API.md` so the example usage matches the completed protobuf schema.
- [ ] Open a follow-up hardening task for configurable SSL verification and a separate migration task for replacing pickle serialization.

## Quick wins

1. Finish the protobuf definitions and regenerate bindings.
2. Add one integration test that proves `include_initial=True` delivers existing records on subscription start.
3. Add one add/update/delete event test for a single subscription type, then extend the same pattern to the remaining subscription types.
4. Refresh the example client code to use the supported messages.

## Notes on validation

The repository documents validation through Poetry-based commands such as `poetry run make test` and `poetry run pytest tests/`, but this sandbox does not currently have `poetry` or `pytest` installed. As a result, this progress update is based on repository inspection and existing documentation rather than successful execution of the documented test commands in this environment.
