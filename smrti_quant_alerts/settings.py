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
    API_ENDPOINTS = {
        "BINANCE_SPOT_API_URL": "https://api.binance.com/api/v3/",
        "BINANCE_FUTURES_API_URL": "https://fapi.binance.com/fapi/v1/",
        "SP_500_SOURCE_URL": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies#S&P_500_component_stocks",
        "FMP_API_URL": "https://financialmodelingprep.com/api/v3/",
        "Polygon_API_URL": "https://api.polygon.io/v1/"
    }

    def __init__(self):
        self.validate_tokens()
        self.validate_settings()

    def validate_tokens(self):
        """
        validate token.json
        """
        necessary_keys = ["TelegramBot", "COINGECKO_API_KEY"]
        for key in necessary_keys:
            if key not in self.TOKENS:
                logging.error(f'token.json does not contain "{key}"')
                exit(1)
        if "TOKEN" not in self.TOKENS["TelegramBot"] or \
                "TELEGRAM_IDS" not in self.TOKENS["TelegramBot"]:
            logging.error("token.json does not contain "
                          "TelegramBot.TOKEN or TelegramBot.TELEGRAM_IDS")
            exit(1)
        if "FMP_API_KEY" not in self.TOKENS:
            logging.warning('token.json does not contain FMP_API_KEY, '
                            'cannot run "nasdaq 100" alert')

        if "POLYGON_API_KEY" not in self.TOKENS:
            logging.warning('token.json does not contain POLYGON_API_KEY, '
                            'cannot run "nasdaq 100", "sp_500" alert')

        logging.warning('"TELEGRAM_IDS" in token.json:\n'
                        '"CG_SUM": alert_100, alert_300, alert_500, sequential\n'
                        '"VOLUME_15M", "VOLUME_1H", "PRICE_15M", "PRICE_1H": price_volume\n'
                        '"CG_MAR_CAP": market_cap\n'
                        '"ALTS": alts\n'
                        '"FUNDING_RATE": funding_rate\n'
                        '"MEME": meme_alert\n'
                        'Remember to fill in the Telegram channel/group ID for each alert type')
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
