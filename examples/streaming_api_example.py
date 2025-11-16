#!/usr/bin/env python3
"""
Example client demonstrating the streaming API usage.

This example shows how to subscribe to policy, schedule, and domain login
updates using the new streaming API.

NOTE: This requires the protobuf definitions to be completed first.
See STREAMING_API.md for details on what protobuf changes are needed.
"""

def main():
    """Run the example."""
    print("Starbelly Streaming API Example")
    print("=" * 50)
    print()
    print("NOTE: This example requires protobuf definitions to be completed.")
    print("See ../STREAMING_API.md for implementation details.")
    print()
    print("The streaming API provides:")
    print("  - Real-time updates when data changes")
    print("  - No polling required")
    print("  - Reduced database load")
    print("  - Efficient (only sends changes)")
    print()

if __name__ == '__main__':
    main()
