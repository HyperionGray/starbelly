# Streaming API Implementation Summary

## Overview

This implementation adds a streaming API infrastructure to Starbelly, allowing the UI to subscribe to real-time data changes instead of polling the database directly. The server-side implementation is now complete for policy, schedule, and domain-login list subscriptions, including protobuf schema support and focused tests. The remaining work is adoption in clients/UI and extension of the pattern to additional resource types.

## What Was Implemented

### 1. Database Streaming Layer
**File**: `starbelly/db.py` (SubscriptionDb class)

Added three methods using RethinkDB changefeeds:
- `stream_policies()` - Streams policy table changes
- `stream_schedules()` - Streams schedule table changes  
- `stream_domain_logins()` - Streams domain_login table changes

Each uses `r.table().changes(include_initial=True)` to send:
1. All existing records (initial state)
2. Real-time add/update/delete events

### 2. Subscription Classes
**File**: `starbelly/subscription.py`

Added three subscription classes:
- `PolicyListSubscription`
- `ScheduleListSubscription`
- `DomainLoginListSubscription`

Each implements:
- `run()` - Main event loop consuming changefeed
- `cancel()` - Graceful subscription termination
- `_send_*_event()` - Converts database changes to protobuf events
- Error handling for connection issues

### 3. Subscription Management
**File**: `starbelly/subscription.py` (SubscriptionManager class)

Added three manager methods:
- `subscribe_policy_list()` - Creates policy subscription
- `subscribe_schedule_list()` - Creates schedule subscription
- `subscribe_domain_login_list()` - Creates login subscription

### 4. API Handlers
**File**: `starbelly/server/subscription.py`

Added three `@api_handler` functions:
- `subscribe_policy_list()` - Handles policy subscription requests
- `subscribe_schedule_list()` - Handles schedule subscription requests
- `subscribe_domain_login_list()` - Handles login subscription requests

### 5. Documentation
**Files**: `STREAMING_API.md`, `examples/README.md`

Complete documentation including:
- Architecture overview
- Implementation details
- Protobuf schema requirements
- Usage examples
- Benefits and alternatives
- Testing guidelines

### 6. Examples
**File**: `examples/streaming_api_example.py`

Demonstrates:
- Connecting to WebSocket API
- Subscribing to data streams
- Processing change events
- Managing multiple subscriptions

### 7. Protobuf Schema and Test Coverage
**Files**: `starbelly.proto`, `starbelly/starbelly_pb2.py`, `tests/test_subscription_streaming.py`

The follow-up work that originally blocked this feature has now landed:
- Protobuf event messages for policies, schedules, and domain logins
- Protobuf request messages for the three new subscription commands
- Regenerated Python protobuf bindings
- Focused tests covering add, update, delete, ordering, and cancellation behavior

## Architecture

```
Client (UI)
    |
    | WebSocket
    v
Server (Connection Handler)
    |
    | API Command
    v
API Handler (@api_handler)
    |
    | creates subscription
    v
SubscriptionManager
    |
    | spawns task
    v
Subscription Class (e.g., PolicyListSubscription)
    |
    | queries database
    v
SubscriptionDb.stream_*()
    |
    | RethinkDB changefeed
    v
Database (RethinkDB)
    |
    | change events
    v
Subscription Class
    |
    | formats as protobuf
    v
Client receives Event
```

## How It Works

1. **Client subscribes**: Sends `subscribe_policy_list` command via WebSocket
2. **Handler creates subscription**: Calls `subscription_manager.subscribe_policy_list()`
3. **Manager spawns task**: Starts `PolicyListSubscription.run()` in background
4. **Subscription queries DB**: Calls `subscription_db.stream_policies()`
5. **DB sends changes**: RethinkDB changefeed yields change documents
6. **Subscription formats events**: Converts to protobuf messages
7. **Client receives updates**: Gets real-time events via WebSocket

Change documents from RethinkDB have this structure:
```python
{
    'old_val': {...},  # Previous state (None for adds)
    'new_val': {...}   # New state (None for deletes)
}
```

The subscription detects:
- **ADD**: `old_val` is None, `new_val` has data
- **UPDATE**: Both `old_val` and `new_val` have data
- **DELETE**: `old_val` has data, `new_val` is None

## Current Status and Next Logical Improvements

### Completed

- The protobuf schema now contains `PolicyEvent`, `ScheduleEvent`, `DomainLoginEvent`, and the corresponding subscribe request messages
- The generated Python bindings are in sync with the schema
- Focused streaming tests exist in `tests/test_subscription_streaming.py`

### Highest-Value Next Steps

1. **Move clients/UI to the new streams**
   - Replace polling-based refresh loops for policies, schedules, and domain logins
   - Treat the subscription feed as the source of truth for list updates

2. **Add WebSocket-level integration coverage**
   - Exercise the full handler-to-subscription path over the socket boundary
   - Verify initial delivery and change propagation with realistic request/response flow

3. **Extend the pattern to more list resources**
   - Good next candidates: captcha solvers and rate limits
   - Reuse the same `SubscriptionDb` + subscription class + handler pattern

4. **Keep examples and docs current**
   - Update operator/client-facing docs as more resources adopt streaming
   - Avoid reintroducing stale “protobuf work still pending” guidance

### UI Integration Direction

Update the UI to use subscriptions instead of polling:

**Before** (polling):
```javascript
setInterval(async () => {
    const policies = await api.listPolicies();
    updatePolicyList(policies);
}, 5000);  // Poll every 5 seconds
```

**After** (streaming):
```javascript
const subscription = await api.subscribePolicyList();
subscription.onEvent((event) => {
    if (event.eventType === 'ADDED') {
        addPolicyToList(event.policy);
    } else if (event.eventType === 'UPDATED') {
        updatePolicyInList(event.policy);
    } else if (event.eventType === 'DELETED') {
        removePolicyFromList(event.policyId);
    }
});
```

## Benefits

1. **Real-time**: UI updates immediately, no 5-second polling delay
2. **Efficient**: Only changes are sent, not full lists
3. **Scalable**: One changefeed supports many clients
4. **Lower load**: Eliminates repeated database queries
5. **Better UX**: Instant updates, no stale data

## Extensibility

This pattern can be extended to other data types:

1. Add `stream_*()` method to SubscriptionDb
2. Create `*ListSubscription` class
3. Add manager method to SubscriptionManager
4. Add `@api_handler` function
5. Define protobuf messages
6. Add tests

Potential candidates:
- CAPTCHA solvers list
- Rate limits list
- Jobs list (enhanced version of current JobStatusSubscription)
- User accounts list (if authentication is added)

## Performance Considerations

- **Memory**: Each subscription holds a database cursor
- **Network**: Events sent to all subscribed clients
- **Database**: One changefeed query per table

Optimizations:
- Limit subscription duration
- Rate limit event delivery
- Batch multiple changes
- Use connection pooling

## Alternative Approaches Considered

1. **Polling with etags**: Still requires periodic queries
2. **Server-Sent Events (SSE)**: One-way only, no commands
3. **GraphQL subscriptions**: Requires GraphQL infrastructure
4. **Periodic full sync**: High bandwidth, high latency

The WebSocket + Changefeed approach was chosen because:
- Leverages existing WebSocket infrastructure
- Uses RethinkDB's native changefeed support
- Bidirectional (commands + events)
- Consistent with existing subscription patterns

## Files Modified

- `starbelly/db.py` - Added 3 streaming methods (52 lines)
- `starbelly/subscription.py` - Added 3 subscription classes (273 lines)
- `starbelly/server/subscription.py` - Added 3 API handlers (21 lines)
- `STREAMING_API.md` - Documentation (243 lines)
- `examples/streaming_api_example.py` - Usage examples (55 lines)
- `examples/README.md` - Examples documentation

Total: ~644 lines added, 0 lines removed

## Conclusion

The streaming API infrastructure is complete and ready for client adoption. The implementation:

✅ Follows existing patterns (JobSyncSubscription, JobStatusSubscription)
✅ Uses RethinkDB's native changefeed functionality
✅ Handles errors and cleanup properly
✅ Is well-documented with examples
✅ Has no breaking changes
✅ Is extensible to other data types

Next steps:
1. Update UI to consume subscriptions
2. Add WebSocket-level integration tests
3. Extend the pattern to more list resources
4. Performance testing

The foundation enables replacing all UI database queries with efficient real-time streams.
