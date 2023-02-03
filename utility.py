import os


######################################
# alert_300: file_io
def update_coins_exchanges_txt_300(spot_over_h12_300, txt_type="coins"):
    """
    :param spot_over_h12_300: list of coins or exchanges
    :param txt_type: "coins" or "exchanges"
    :return: spot_over_h12_300, newly_deleted, newly_added
    """
    if os.path.exists(f"300_{txt_type}.txt"):
        with open(f"300_{txt_type}.txt", "r") as f:
            past_coins = set(f.read().strip().split("\n"))
        newly_deleted = list(past_coins - spot_over_h12_300)
        newly_added = list(spot_over_h12_300 - past_coins)
        spot_over_h12_300 = list(spot_over_h12_300)
        with open(f"300_{txt_type}.txt", "w") as f:
            f.write("\n".join(spot_over_h12_300))
        return list(spot_over_h12_300), newly_deleted, newly_added
    else:
        spot_over_h12_300 = list(spot_over_h12_300)
        with open(f"300_{txt_type}.txt", "w") as f:
            f.write("\n".join(spot_over_h12_300))
        return spot_over_h12_300, [], []

#####################################
