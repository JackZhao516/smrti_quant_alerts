import json
import os
import logging


class Config:
    current_dir = os.getcwd().split("smrti_quant_alerts")[0] + "smrti_quant_alerts/"
    if not os.path.isfile(f"{current_dir}token.json"):
        logging.error("token.json not found")
        exit(1)
    TOKENS = json.load(open(f"{current_dir}token.json"))
    SETTINGS = json.load(open(f"{current_dir}settings.json"))

    def __init__(self):
        self.validate_tokens()
        self.validate_settings()

    def validate_tokens(self):
        """
        validate token.json
        """
        necessary_keys = ["TelegramBot", "BINANCE", "COINGECKO_API_KEY"]
        for key in necessary_keys:
            if key not in self.TOKENS:
                logging.error(f'token.json does not contain "{key}"')
                exit(1)
        if "TOKEN" not in self.TOKENS["TelegramBot"] or \
                "TELEGRAM_IDS" not in self.TOKENS["TelegramBot"]:
            logging.error("token.json does not contain "
                          "TelegramBot.TOKEN or TelegramBot.TELEGRAM_IDS")
            exit(1)

        logging.warning('"TELEGRAM_IDS" in token.json:'
                        '"CG_SUM": alert_100, alert_300, alert_500, sequential'
                        '"VOLUME_15M", "VOLUME_1H", "PRICE_15M", "PRICE_1H": price_volume'
                        '"CG_MAR_CAP": market_cap'
                        '"ALTS": alts'
                        'Fill in the Telegram channel/group ID for each alert type')
        logging.info("token.json validated")

    def validate_settings(self):
        """
        validate settings.json
        """
        keys = ["15m_volume_usd", "1h_volume_usd",
                "15m_price_change_percentage", "1h_price_change_percentage"]
        for key in keys:
            if key not in self.SETTINGS:
                logging.warning(f'settings.json does not contain "{key}", '
                                f'cannot run "price_volume" alerts')
                break


if __name__ == "__main__":
    Config()
