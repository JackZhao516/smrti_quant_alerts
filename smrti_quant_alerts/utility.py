import pytz
import logging
import datetime
import time
import threading
from collections.abc import Callable, Iterable

from smrti_quant_alerts.settings import Config


class CancellationEvent:
    """Cancellation synchronized with dispatch; set() waits for an in-flight callback."""

    def __init__(self):
        self.event = threading.Event()
        self.dispatch_lock = threading.RLock()

    def is_set(self):
        return self.event.is_set()

    def set(self):
        with self.dispatch_lock:
            self.event.set()

    def wait(self, timeout):
        return self.event.wait(timeout)

    def dispatch(self, task):
        with self.dispatch_lock:
            if self.event.is_set():
                return False
            task()
            return True


def next_run_time(now, daily_times, excluded_week_days=None):
    """Next future local slot; skip nonexistent DST times, prefer standard time when choosing a future fold."""
    tz = now.tzinfo
    times = sorted({datetime.datetime.strptime(value, "%H:%M").time() for value in daily_times})
    if not times:
        raise ValueError("daily_times must not be empty")
    for offset in range(8):
        day = now.date() + datetime.timedelta(days=offset)
        if ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[day.weekday()] in (excluded_week_days or []):
            continue
        for value in times:
            naive = datetime.datetime.combine(day, value)
            try:
                candidate = tz.localize(naive, is_dst=None) if hasattr(tz, "localize") else naive.replace(tzinfo=tz)
            except pytz.NonExistentTimeError:
                continue
            except pytz.AmbiguousTimeError:
                candidate = tz.localize(naive, is_dst=False)
            if candidate > now:
                return candidate
    raise ValueError("No runnable slot in the next eight days")


def run_task_at_daily_time(
    task: Callable,
    daily_times: Iterable[str] | str,
    excluded_week_days: list[str] | None = None,
    timezone: str | None = None,
    stop_event=None,
) -> None:
    """Run every configured local slot without assuming equal intervals."""
    if stop_event is not None and not isinstance(stop_event, CancellationEvent):
        raise TypeError("stop_event must be CancellationEvent")
    daily_times = [daily_times] if isinstance(daily_times, str) else list(daily_times)
    tz = pytz.timezone(timezone or "Asia/Shanghai")
    seen = set()
    while stop_event is None or not stop_event.is_set():
        now = datetime.datetime.now(tz)
        slot = (now.date(), now.strftime("%H:%M"))
        if (
            slot[1] in daily_times
            and slot not in seen
            and ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[now.weekday()] not in (excluded_week_days or [])
        ):
            seen.add(slot)
            if stop_event is None:
                task()
            elif not stop_event.dispatch(task):
                return
        seen = {value for value in seen if value[0] == now.date()}
        upcoming = next_run_time(now, daily_times, excluded_week_days)
        delay = min(60, max(0.01, (upcoming - now).total_seconds()))
        if stop_event is None:
            time.sleep(delay)
        else:
            stop_event.wait(delay)


def run_alert(alert_name: str, alert_class: Callable) -> None:
    """
    run alert by name and CONFIGS defined in configs.json

    :param alert_name: alert name
    :param alert_class: alert class
    """
    logging.info(f"{alert_name} start")
    config = Config()

    settings = config.SETTINGS[alert_name]

    def task():
        config.reload_settings()
        config.SETTINGS[alert_name]["alert_input_args"]["alert_name"] = alert_name
        alert = alert_class(**config.SETTINGS[alert_name]["alert_input_args"])
        alert.run()

    run_task_at_daily_time(task, **settings["run_time_input_args"])
    logging.info(f"{alert_name} finished")
