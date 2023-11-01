import pytz
from datetime import datetime
from time import sleep, time


def run_task_at_daily_time(task, run_time, kwargs=None, excluded_week_day=None, timezone=None):
    """
    :param task: function to run
    :param kwargs: key word args of the function
    :param run_time: time to run the task, format: "HH:MM"
    :param excluded_week_day: exclude week day, format: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    :param timezone: timezone to run the task
    """
    if isinstance(run_time, str):
        run_time = [run_time]
    if not kwargs:
        kwargs = {}

    if len(run_time) == 1:
        between_time = 60 * 60 * 24
    else:
        between_time = (datetime.strptime(run_time[1], '%H:%M') -
                        datetime.strptime(run_time[0], '%H:%M')).seconds

    tz = pytz.timezone('Asia/Shanghai') if not timezone else pytz.timezone(timezone)

    while True:
        if datetime.now(tz).strftime('%H:%M') in run_time:
            start = time()
            if not excluded_week_day or datetime.now(tz).strftime('%a') not in excluded_week_day:
                task(**kwargs)
            # print(f"Task finished, time used: {time() - start} seconds")
            sleep(between_time - max(2 * (time() - start), 180))
        sleep(60)
