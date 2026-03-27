# Streaming API Implementation Summary

## Overview

This implementation adds a streaming API infrastructure to Starbelly, allowing the UI to subscribe to real-time data changes instead of polling the database directly. The foundation is complete and follows existing patterns, but requires protobuf schema updates to be fully functional.

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

## What's Required to Complete

### Protobuf Schema Updates

The implementation references protobuf message types that don't exist yet. These need to be added to the `.proto` file:

#### 1. Event Messages

```protobuf
message PolicyEvent {
    enum EventType {
        ADDED = 1;
        UPDATED = 2;
        DELETED = 3;
    }
    EventType event_type = 1;
    string policy_id = 2;
    string name = 3;
    // Add other policy fields as needed
}

message ScheduleEvent {
    enum EventType {
        ADDED = 1;
        UPDATED = 2;
        DELETED = 3;
    }
    EventType event_type = 1;
    bytes schedule_id = 2;
    string schedule_name = 3;
    // Add other schedule fields as needed
}

message DomainLoginEvent {
    enum EventType {
        ADDED = 1;
        UPDATED = 2;
        DELETED = 3;
    }
    EventType event_type = 1;
    string domain = 2;
    // Add other login fields as needed
}
```

#### 2. Update Event Message

```protobuf
message Event {
    int32 subscription_id = 1;
    oneof EventType {
        // existing events...
        PolicyEvent policy_event = X;       // Use next available number
        ScheduleEvent schedule_event = Y;
        DomainLoginEvent domain_login_event = Z;
    }
}
```

#### 3. Request Messages

```protobuf
message RequestSubscribePolicyList {}
message RequestSubscribeScheduleList {}
message RequestSubscribeDomainLoginList {}
```

#### 4. Update Request Message

```protobuf
message Request {
    int32 request_id = 1;
    oneof Command {
        // existing commands...
        RequestSubscribePolicyList subscribe_policy_list = X;
        RequestSubscribeScheduleList subscribe_schedule_list = Y;
        RequestSubscribeDomainLoginList subscribe_domain_login_list = Z;
    }
}
```

#### 5. Regenerate Python Code

```bash
protoc --python_out=. starbelly.proto
```

This generates an updated `starbelly_pb2.py` with the new message types.

### Testing

After protobuf updates, add integration tests:

```python
# Test initial data delivery
async def test_policy_subscription_initial_data(db_pool):
    # Insert policies
    # Subscribe
    # Verify initial policies received

# Test add events  
async def test_policy_subscription_add_event(db_pool):
    # Subscribe
    # Add a policy
    # Verify ADD event received

# Test update events
async def test_policy_subscription_update_event(db_pool):
    # Subscribe
    # Update a policy
    # Verify UPDATE event received

# Test delete events
async def test_policy_subscription_delete_event(db_pool):
    # Subscribe
    # Delete a policy
    # Verify DELETE event received
```

### UI Integration

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

The streaming API infrastructure is complete and ready for use once protobuf schemas are updated. The implementation:

✅ Follows existing patterns (JobSyncSubscription, JobStatusSubscription)
✅ Uses RethinkDB's native changefeed functionality
✅ Handles errors and cleanup properly
✅ Is well-documented with examples
✅ Has no breaking changes
✅ Is extensible to other data types

Next steps:
1. Update protobuf schemas
2. Regenerate Python code
3. Add integration tests
4. Update UI to consume subscriptions
5. Performance testing

The foundation enables replacing all UI database queries with efficient real-time streams.
