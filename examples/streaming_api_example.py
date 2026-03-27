#!/usr/bin/env python3
"""Example client skeleton for Starbelly subscriptions."""


def main():
    """Run the example."""
    print("Starbelly subscription example")
    print("=" * 32)
    print()
    print("This repository uses websocket subscriptions for streaming updates.")
    print("See docs/websocket_api.rst for protocol details.")
    print()
    print("Available built-in subscriptions include:")
    print("  - subscribe_job_sync")
    print("  - subscribe_job_status")
    print("  - subscribe_resource_monitor")
    print("  - subscribe_task_monitor")
    print()

if __name__ == '__main__':
    main()
