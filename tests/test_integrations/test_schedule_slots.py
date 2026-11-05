import datetime
from unittest.mock import patch

import pytest
import pytz

from smrti_quant_alerts.utility import CancellationEvent, next_run_time, run_task_at_daily_time


def test_uneven_slots_choose_immediate_next_not_first_interval():
    now = pytz.UTC.localize(datetime.datetime(2026, 11, 5, 16, 0))
    assert next_run_time(now, ["09:00", "16:00", "16:30"]).strftime("%H:%M") == "16:30"


def test_spring_gap_skips_nonexistent_local_time():
    tz = pytz.timezone("America/New_York")
    now = tz.localize(datetime.datetime(2026, 3, 8, 1, 59))
    result = next_run_time(now, ["02:30"])
    assert result.day == 9 and result.hour == 2


def test_all_days_excluded_is_rejected():
    with pytest.raises(ValueError):
        next_run_time(
            pytz.UTC.localize(datetime.datetime(2026, 1, 1)),
            ["09:00"],
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        )


def test_stopped_scheduler_never_calls_task():
    event = CancellationEvent()
    event.set()
    with patch("smrti_quant_alerts.utility.next_run_time") as next_time:
        run_task_at_daily_time(lambda: pytest.fail("should not run"), "09:00", stop_event=event)
    next_time.assert_not_called()


def test_empty_slots_and_fall_back_fold():
    now = pytz.UTC.localize(datetime.datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="empty"):
        next_run_time(now, [])
    tz = pytz.timezone("America/New_York")
    now = tz.localize(datetime.datetime(2026, 11, 1, 0, 59))
    result = next_run_time(now, ["01:30"])
    assert result.utcoffset() == datetime.timedelta(hours=-5)


def test_scheduler_waits_through_cancellable_event():
    event = CancellationEvent()

    def wait(_delay):
        event.set()

    with patch.object(event, "wait", side_effect=wait) as waiting:
        run_task_at_daily_time(lambda: None, ["09:00"], timezone="UTC", stop_event=event)
    assert waiting.call_count == 1


def test_cancellation_observed_before_dispatch():
    from unittest.mock import Mock

    now = pytz.UTC.localize(datetime.datetime(2026, 11, 5, 9))
    clock = Mock()
    clock.datetime.now.return_value = now
    stop = CancellationEvent()

    def read_clock(_tz):
        stop.set()
        return now

    clock.datetime.now.side_effect = read_clock
    task = Mock()
    with patch("smrti_quant_alerts.utility.datetime", clock):
        run_task_at_daily_time(task, "09:00", timezone="UTC", stop_event=stop)
    task.assert_not_called()


def test_cancelled_dispatch_and_inflight_cancellation_are_synchronized():
    import threading
    from unittest.mock import Mock

    stop = CancellationEvent()
    started, finish, cancelled = (threading.Event() for _ in range(3))

    def task():
        started.set()
        assert finish.wait(2)

    worker = threading.Thread(target=lambda: stop.dispatch(task))
    worker.start()
    assert started.wait(2)

    def cancel():
        stop.set()
        cancelled.set()

    canceller = threading.Thread(target=cancel)
    canceller.start()
    assert not cancelled.wait(0.05)
    finish.set()
    worker.join(2)
    canceller.join(2)
    assert cancelled.is_set()
    callback = Mock()
    assert stop.dispatch(callback) is False
    callback.assert_not_called()
    with pytest.raises(TypeError, match="CancellationEvent"):
        run_task_at_daily_time(callback, "09:00", stop_event=threading.Event())
