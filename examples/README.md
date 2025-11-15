# Starbelly Examples

This directory contains example code demonstrating various Starbelly features.

## Streaming API Example

The `streaming_api_example.py` file demonstrates how to use the new streaming API to subscribe to real-time data updates.

**Status**: Requires protobuf definitions to be completed (see ../STREAMING_API.md)

The streaming API allows clients to:
- Subscribe to policy, schedule, and domain login changes
- Receive real-time updates via WebSocket
- Avoid polling and reduce database load
- Process only changed data

### Running the Example

```bash
python3 examples/streaming_api_example.py
```

Note: The full example code is commented out until protobuf definitions are added.

## Other Examples

Add additional examples here as they are created.
