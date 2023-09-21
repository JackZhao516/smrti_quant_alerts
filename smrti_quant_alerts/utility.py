import pytz
from datetime import datetime
from time import sleep, time

tz = pytz.timezone('Asia/Shanghai')


def run_task_at_daily_time(task, run_time, kwargs=None, exclude_week_day=None, duration=60 * 60 * 24):
    """
    :param task: function to run
    :param kwargs: key word args of the function
    :param run_time: time to run the task, format: "HH:MM"
    :param exclude_week_day: exclude week day, format: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    :param duration: duration of between time, default: 60 * 60 * 24
    """
    if isinstance(run_time, str):
        run_time = [run_time]
    if not kwargs:
        kwargs = {}
    while True:
        if datetime.now(tz).strftime('%H:%M') in run_time and \
                (not exclude_week_day or datetime.now(tz).strftime('%a') not in exclude_week_day):
            start = time()
            task(**kwargs)
            # print(f"Task finished, time used: {time() - start} seconds")
            sleep(duration - max(2 * (time() - start), 120))
        sleep(60)
