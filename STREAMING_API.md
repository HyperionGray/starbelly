# Streaming API Implementation

## Overview

This document describes the streaming API architecture added to Starbelly to replace direct database access patterns with real-time data streams.

## Architecture

Starbelly already has a robust WebSocket-based API with subscription support. The existing subscription infrastructure includes:

1. **SubscriptionManager** - Manages active subscriptions for a WebSocket connection
2. **Subscription Classes** - Handle specific data streams (e.g., JobSyncSubscription, JobStatusSubscription)
3. **Database Streaming** - RethinkDB changefeed support for real-time updates
4. **API Handlers** - Decorated functions that process client commands

## What Was Added

### 1. Database Streaming Methods (db.py - SubscriptionDb class)

Added three new methods to support streaming data changes:

```python
async def stream_policies(self):
    '''Stream policy changes using RethinkDB changefeed.'''
    query = r.table('policy').changes(include_initial=True)
    # Yields change documents with old_val/new_val

async def stream_schedules(self):
    '''Stream schedule changes using RethinkDB changefeed.'''
    query = r.table('schedule').changes(include_initial=True)
    
async def stream_domain_logins(self):
    '''Stream domain login changes using RethinkDB changefeed.'''
    query = r.table('domain_login').changes(include_initial=True)
```

These methods use RethinkDB's `changes()` query with `include_initial=True` to:
- Send all existing records first (initial state)
- Then stream real-time changes (add/update/delete)

### 2. Subscription Classes (subscription.py)

Added three new subscription classes following the existing pattern:

- **PolicyListSubscription** - Streams policy changes
- **ScheduleListSubscription** - Streams schedule changes  
- **DomainLoginListSubscription** - Streams domain login changes

Each subscription:
- Manages its own cancellation scope
- Detects change types (ADDED, UPDATED, DELETED) from RethinkDB changefeeds
- Sends events via WebSocket using protobuf messages
- Handles connection errors gracefully

### 3. SubscriptionManager Methods (subscription.py)

Added methods to create new subscriptions:

```python
def subscribe_policy_list(self):
    '''Subscribe to policy list changes.'''
    
def subscribe_schedule_list(self):
    '''Subscribe to schedule list changes.'''
    
def subscribe_domain_login_list(self):
    '''Subscribe to domain login list changes.'''
```

### 4. API Handlers (server/subscription.py)

Added `@api_handler` decorated functions:

```python
@api_handler
async def subscribe_policy_list(response, subscription_manager):
    '''Handle the subscribe policy list command.'''

@api_handler
async def subscribe_schedule_list(response, subscription_manager):
    '''Handle the subscribe schedule list command.'''

@api_handler
async def subscribe_domain_login_list(response, subscription_manager):
    '''Handle the subscribe domain login list command.'''
```

## What's Needed for Complete Implementation

### Protobuf Message Definitions

The current implementation references protobuf event types that don't yet exist. To complete this, you need to:

1. **Add event message definitions** to the `.proto` file (source file for starbelly_pb2.py):

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

2. **Update the Event message** to include these new event types:

```protobuf
message Event {
    int32 subscription_id = 1;
    oneof EventType {
        // existing events...
        PolicyEvent policy_event = X;
        ScheduleEvent schedule_event = Y;
        DomainLoginEvent domain_login_event = Z;
    }
}
```

3. **Regenerate the Python protobuf** file:

```bash
protoc --python_out=. starbelly.proto
```

### Request Message Definitions

Add request messages for the new subscription commands:

```protobuf
message RequestSubscribePolicyList {}
message RequestSubscribeScheduleList {}
message RequestSubscribeDomainLoginList {}
```

And add them to the Request message oneof:

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

## Usage Example

Once protobuf definitions are complete, clients can subscribe like this:

```python
# Client code example
import trio
from trio_websocket import open_websocket
from starbelly_pb2 import Request, ServerMessage

async def subscribe_to_policies():
    async with open_websocket('ws://localhost:8080', '/') as ws:
        # Send subscription request
        request = Request()
        request.request_id = 1
        request.subscribe_policy_list.CopyFrom(RequestSubscribePolicyList())
        await ws.send_message(request.SerializeToString())
        
        # Get subscription ID from response
        response_data = await ws.get_message()
        response = ServerMessage.FromString(response_data).response
        sub_id = response.new_subscription.subscription_id
        
        # Receive policy events
        while True:
            event_data = await ws.get_message()
            event = ServerMessage.FromString(event_data).event
            if event.subscription_id == sub_id:
                policy_event = event.policy_event
                if policy_event.event_type == PolicyEvent.ADDED:
                    print(f"Policy added: {policy_event.name}")
                elif policy_event.event_type == PolicyEvent.UPDATED:
                    print(f"Policy updated: {policy_event.name}")
                elif policy_event.event_type == PolicyEvent.DELETED:
                    print(f"Policy deleted: {policy_event.policy_id}")
```

## Benefits of Streaming API

1. **Real-time Updates** - UI updates immediately when data changes, no polling required
2. **Reduced Database Load** - Single changefeed query instead of repeated list queries
3. **Efficient** - Only changed data is sent, not full lists on every update
4. **Scalable** - RethinkDB changefeeds are designed for this use case
5. **Consistent** - Same pattern as existing subscriptions (JobSync, JobStatus, etc.)

## Alternative Approaches

If protobuf changes are not desired, alternative approaches include:

1. **Use existing response types** - Send complete lists periodically (like JobStatusSubscription)
2. **JSON over WebSocket** - Use a separate JSON-based streaming endpoint
3. **Server-Sent Events** - Add SSE endpoint alongside WebSocket API
4. **GraphQL Subscriptions** - Add GraphQL layer with subscription support

## Testing

Tests should cover:

1. Initial data delivery (include_initial=True)
2. Add events
3. Update events
4. Delete events
5. Subscription cancellation
6. Connection errors and recovery
7. Multiple concurrent subscriptions

Example test structure is provided in tests/test_subscription.py.
