import pytz
from datetime import datetime
from time import sleep, time

tz = pytz.timezone('Asia/Shanghai')


def run_task_at_daily_time(task, run_time, kwargs=None, duration=60 * 60 * 24):
    """
    :param task: function to run
    :param kwargs: key word args of the function
    :param run_time: time to run the task, format: "HH:MM"
    :param duration: duration of between time, default: 60 * 60 * 24
    """
    if isinstance(run_time, str):
        run_time = [run_time]
    if not kwargs:
        kwargs = {}
    while True:
        if datetime.now(tz).strftime('%H:%M') in run_time:
            start = time()
            task(**kwargs)
            # print(f"Task finished, time used: {time() - start} seconds")
            sleep(duration - max(2 * (time() - start), 120))
        sleep(60)
