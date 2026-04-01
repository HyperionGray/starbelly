# Daily Progress: 2026-03-27

## Current project direction

Recent repository activity points in a consistent direction:

1. **Finish the streaming API migration path**  
   The latest merged work completed the protobuf schema, generated bindings, and focused tests for policy, schedule, and domain-login subscriptions (`#141`).
2. **Improve contributor onboarding and operator clarity**  
   `START_HERE.md` was added to make the server architecture and extension points easier to understand (`#125`).
3. **Harden the crawler while keeping the async architecture intact**  
   Recent security work documented parser trade-offs and added denial-of-service protections in the parsing layer (`#123`).

Taken together, the natural direction of the project is:

- keep moving UI and client workflows onto the WebSocket streaming API,
- document the intended architecture clearly enough for contributors to extend it,
- and make crawler safety/reliability improvements without changing the core Trio/RethinkDB design.

## Issues, PRs, and incomplete areas that matter most

- The historical **Streaming API** issue (`#80`) is effectively resolved for the first three list-style resources.
- The newest merged PR shows the server-side subscription pattern is now real code, not just scaffolding.
- The main remaining gap is no longer protobuf plumbing; it is **adoption and expansion**:
  - update clients/UI to consume the new streams instead of polling,
  - extend the same pattern to more resource types,
  - and keep the examples/docs aligned with the current implementation.

## Prioritized next steps

### Quick wins

- [ ] Switch the UI/client flows for policies, schedules, and domain logins from polling to the existing subscriptions
- [ ] Replace any stale “streaming API is incomplete” wording in docs/examples as code continues to evolve
- [ ] Add a short operator note describing which resources already support live subscriptions

### Incremental follow-up work

- [ ] Add end-to-end integration coverage for subscription handlers across the WebSocket boundary, not just subscription-class unit tests
- [ ] Add streaming subscriptions for the next obvious list resources: captcha solvers and rate limits
- [ ] Document a recommended local development/test bootstrap path so contributors can run the existing pytest suite reliably

### Larger follow-on work

- [ ] Update the UI to treat the WebSocket API as the primary source of truth for list updates
- [ ] Expand real-time monitoring with more subscription-backed operational views
- [ ] Continue targeted security hardening in the downloader/parser pipeline while preserving current behavior

## Suggested implementation order

1. **Client/UI adoption for the three completed list subscriptions**
2. **WebSocket-level integration tests for those subscriptions**
3. **Streaming support for the next two resource types**
4. **Additional crawler hardening and monitoring improvements**
