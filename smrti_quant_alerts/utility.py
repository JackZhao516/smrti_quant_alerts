import pytz
import logging
from datetime import datetime
from time import sleep, time
from typing import Callable, Union, Iterable, Dict, Optional, List, Any

from smrti_quant_alerts.settings import Config


def run_task_at_daily_time(task: Callable, daily_times: Union[Iterable[str], str],
                           kwargs: Optional[Dict[str, Any]] = None,
                           excluded_week_days: Optional[List[str]] = None,
                           timezone: Optional[str] = None) -> None:
    """
    :param task: function to run
    :param kwargs: key word args of the function
    :param daily_times: time to run the task, format: "HH:MM"
    :param excluded_week_days: exclude week day, format: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    :param timezone: timezone to run the task
    """
    if isinstance(daily_times, str):
        daily_times = [daily_times]
    if not kwargs:
        kwargs = {}

    if len(daily_times) == 1:
        between_time = 60 * 60 * 24
    else:
        between_time = (datetime.strptime(daily_times[1], '%H:%M') -
                        datetime.strptime(daily_times[0], '%H:%M')).seconds

    tz = pytz.timezone('Asia/Shanghai') if not timezone else pytz.timezone(timezone)

    while True:
        if datetime.now(tz).strftime('%H:%M') in daily_times:
            start = time()
            if not excluded_week_days or datetime.now(tz).strftime('%a') not in excluded_week_days:
                task(**kwargs)
            # print(f"Task finished, time used: {time() - start} seconds")
            sleep(between_time - max(2 * (time() - start), 180))
        sleep(60)


def run_alert(alert_name: str, alert_class: Callable) -> None:
    """
    run alert by name and CONFIGS defined in configs.json

    :param alert_name: alert name
    :param alert_class: alert class
    """
    logging.info(f"{alert_name} start")
    settings = Config.SETTINGS[alert_name]
    alert = alert_class(**settings["alert_input_args"])
    run_task_at_daily_time(alert.run, **settings["run_time_input_args"])
    logging.info(f"{alert_name} finished")
