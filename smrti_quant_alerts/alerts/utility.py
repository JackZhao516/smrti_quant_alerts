import os
import pytz
from datetime import datetime
from time import sleep, time


######################################
# file_io
# def update_coins_exchanges_txt(spot_over_h4, txt_type="coins", mode="300"):
#     """
#     :param spot_over_h4: list of coins or exchanges
#     :param txt_type: "coins" or "exchanges"
#     :param mode: "100" | "300" | "500"
#     :return: spot_over_ma, newly_deleted, newly_added
#     """
#     if os.path.exists(f"{mode}_{txt_type}.txt"):
#         with open(f"{mode}_{txt_type}.txt", "r") as f:
#             past_coins = set(f.read().strip().split("\n"))
#         newly_deleted = list(past_coins - spot_over_h4)
#         newly_added = list(spot_over_h4 - past_coins)
#         spot_over_h4 = list(spot_over_h4)
#         with open(f"{mode}_{txt_type}.txt", "w") as f:
#             f.write("\n".join(spot_over_h4))
#         return list(sorted(spot_over_h4)), newly_deleted, newly_added
#     else:
#         spot_over_h4 = list(spot_over_h4)
#         with open(f"{mode}_{txt_type}.txt", "w") as f:
#             f.write("\n".join(spot_over_h4))
#         return spot_over_h4, [], []

#####################################


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
        tz = pytz.timezone('Asia/Shanghai')
        if datetime.now(tz).strftime('%H:%M') in run_time:
            start = time()
            task(**kwargs)
            # print(f"Task finished, time used: {time() - start} seconds")
            sleep(duration - 3 * (time() - start))
        sleep(60)
