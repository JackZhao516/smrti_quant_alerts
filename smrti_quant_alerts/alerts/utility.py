import os


######################################
# file_io
def update_coins_exchanges_txt(spot_over_h4, txt_type="coins", mode="300"):
    """
    :param spot_over_h4: list of coins or exchanges
    :param txt_type: "coins" or "exchanges"
    :param mode: "100" | "300" | "500"
    :return: spot_over_h4, newly_deleted, newly_added
    """
    if os.path.exists(f"{mode}_{txt_type}.txt"):
        with open(f"{mode}_{txt_type}.txt", "r") as f:
            past_coins = set(f.read().strip().split("\n"))
        newly_deleted = list(past_coins - spot_over_h4)
        newly_added = list(spot_over_h4 - past_coins)
        spot_over_h4 = list(spot_over_h4)
        with open(f"{mode}_{txt_type}.txt", "w") as f:
            f.write("\n".join(spot_over_h4))
        return list(sorted(spot_over_h4)), newly_deleted, newly_added
    else:
        spot_over_h4 = list(spot_over_h4)
        with open(f"{mode}_{txt_type}.txt", "w") as f:
            f.write("\n".join(spot_over_h4))
        return spot_over_h4, [], []

#####################################
