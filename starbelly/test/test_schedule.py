from datetime import datetime, timedelta
import unittest
import unittest.mock

from ..schedule import *


def make_schedule(num, timing=None, num_units=None, time_unit=None,
    enabled=None):
    return {
        'id': 'test-{}-id'.format(num),
        'name': 'My Schedule {}'.format(num),
        'timing': timing or 'REGULAR_INTERVALS',
        'num_units': num_units or 3,
        'time_unit': time_unit or 'HOURS',
        'enabled': True if enabled is None else enabled,
        'latest_job': None,
    }


class TestScheduleEvent(unittest.TestCase):
    def test_event_is_due(self):
        schedule = make_schedule(1)
        due = datetime.now() - timedelta(minutes=1)
        event = ScheduleEvent(schedule, due)
        self.assertTrue(event.is_due())

    def test_event_is_not_due(self):
        schedule = make_schedule(1)
        due = datetime.now() + timedelta(minutes=1)
        event = ScheduleEvent(schedule, due)
        self.assertFalse(event.is_due())

    def test_event_is_disabled(self):
        schedule = make_schedule(1)
        due = datetime.now() + timedelta(minutes=1)
        event = ScheduleEvent(schedule, due)
        self.assertTrue(event.is_enabled())
        event.disable()
        self.assertFalse(event.is_enabled())

    def test_event_order(self):
        schedule = make_schedule(1)
        due_future = datetime.now() + timedelta(minutes=1)
        due_past = datetime.now() - timedelta(minutes=1)
        due_now = datetime.now()
        dues = [due_future, due_past, due_now]
        dues.sort()
        self.assertEqual(dues[0], due_past)
        self.assertEqual(dues[1], due_now)
        self.assertEqual(dues[2], due_future)


class TestSchedule(unittest.TestCase):
    def test_format_name(self):
        dt = datetime(2017, 10, 14, 12, 41, 33)

        format_name = Scheduler.format_job_name(
            'My Job #{COUNT} @ {TIME}',
            now=dt,
            job_count=3
        )
        self.assertEqual(format_name, 'My Job #3 @ 1507984893')

        format_name = Scheduler.format_job_name(
            'My Job @ {DATE}',
            now=dt,
            job_count=3
        )
        self.assertEqual(format_name, 'My Job @ 2017-10-14 12:41:33')

    def test_compute_next_event(self):
        db_mock = unittest.mock.Mock()
        scheduler = Scheduler(db_mock)
        base = datetime(2017, 10, 31, 12, 41, 33)

        next0 = scheduler._compute_next_event(base, 35, 'MINUTES')
        self.assertEqual(next0, datetime(2017, 10, 31, 13, 16, 33))

        next1 = scheduler._compute_next_event(base, 2, 'HOURS')
        self.assertEqual(next1, datetime(2017, 10, 31, 14, 41, 33))

        next2 = scheduler._compute_next_event(base, 3, 'DAYS')
        self.assertEqual(next2, datetime(2017, 11, 3, 12, 41, 33))

        next3 = scheduler._compute_next_event(base, 1, 'WEEKS')
        self.assertEqual(next3, datetime(2017, 11, 7, 12, 41, 33))

        # This is the trickiest case in the implementation: it handles rolling
        # over years and also adjusting the number of days in the month.
        next4 = scheduler._compute_next_event(base, 16, 'MONTHS')
        self.assertEqual(next4, datetime(2019, 2, 28, 12, 41, 33))

        next5 = scheduler._compute_next_event(base, 5, 'YEARS')
        self.assertEqual(next5, datetime(2022, 10, 31, 12, 41, 33))

    def test_no_events(self):
        db_mock = unittest.mock.Mock()
        scheduler = Scheduler(db_mock)
        self.assertIsNone(scheduler._get_next_event())

    def test_no_enabled_events(self):
        db_mock = unittest.mock.Mock()
        scheduler = Scheduler(db_mock)
        scheduler._add_next_event(make_schedule(1))
        scheduler._add_next_event(make_schedule(2))
        scheduler._add_next_event(make_schedule(3, enabled=False))

        #  The disabled schedule should never be added.
        self.assertEqual(len(scheduler._events), 2)

        # Disabled events are not removed, but they are ignored when
        # getting the next event.
        scheduler._events[0].disable()
        scheduler._events[1].disable()
        self.assertEqual(len(scheduler._events), 2)
        self.assertIsNone(scheduler._get_next_event())
        self.assertEqual(len(scheduler._events), 0)

    def test_no_events_due(self):
        db_mock = unittest.mock.Mock()
        scheduler = Scheduler(db_mock)
        scheduler._add_next_event(make_schedule(1))
        scheduler._add_next_event(make_schedule(2))
        self.assertIsNone(scheduler._get_next_event())

    def test_1_event_due(self):
        # This test is really hacky -- it manipulates internal state of an
        # event.
        db_mock = unittest.mock.Mock()
        scheduler = Scheduler(db_mock)
        scheduler._add_next_event(make_schedule(1))
        scheduler._events[0]._due -= timedelta(minutes=10)
        self.assertEqual(scheduler._get_next_event().schedule_id, 'test-1-id')
