# Starbelly Examples

This directory contains small runnable examples for Starbelly features.

## Scheduler validation and queue behavior

The scheduler behavior covered by tests now includes:

- Early validation of invalid schedule `time_unit` and `timing` values.
- Heap-safe queue popping when dispatching due schedule events.

These are exercised in:

- `tests/test_schedule.py::test_invalid_schedule`
- `tests/test_schedule.py::test_schedule_task_preserves_heap_order_after_pop`

## Other examples

Additional examples can be added here as they are created.
