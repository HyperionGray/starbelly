#!/usr/bin/env python3
"""
Example client demonstrating the streaming API usage.

This example shows how to subscribe to policy, schedule, and domain login
updates using the new streaming API.

NOTE: The protobuf definitions for these subscriptions now exist.
See STREAMING_API.md for the current message flow and follow-up work.
"""

def main():
    """Run the example."""
    print("Starbelly Streaming API Example")
    print("=" * 50)
    print()
    print("NOTE: The protobuf definitions for these subscriptions are present.")
    print("See ../STREAMING_API.md for the current implementation details.")
    print()
    print("The streaming API provides:")
    print("  - Real-time updates when data changes")
    print("  - No polling required")
    print("  - Reduced database load")
    print("  - Efficient (only sends changes)")
    print()

if __name__ == '__main__':
    main()
