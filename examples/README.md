# Starbelly Examples

This directory contains example code demonstrating various Starbelly features.

## Streaming API Example

The `streaming_api_example.py` file demonstrates how to use the new streaming API to subscribe to real-time data updates.

**Status**: The protobuf definitions and server-side subscription support are in place. The example remains a lightweight walkthrough of the flow rather than a fully wired live client.

The streaming API allows clients to:
- Subscribe to policy, schedule, and domain login changes
- Receive real-time updates via WebSocket
- Avoid polling and reduce database load
- Process only changed data

### Running the Example

```bash
python3 examples/streaming_api_example.py
```

Note: See `../STREAMING_API.md` for the current subscription message flow and follow-up work.

## Other Examples

Add additional examples here as they are created.
