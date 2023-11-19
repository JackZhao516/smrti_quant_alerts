import json
import os
import logging


class Config:
    current_dir = os.getcwd().split("smrti_quant_alerts")[0] + "smrti_quant_alerts/"
    if not os.path.isfile(f"{current_dir}token.json"):
        logging.error("token.json not found")
        exit(1)
    if not os.path.isfile(f"{current_dir}configs.json"):
        logging.error("configs.json not found")
        exit(1)
    TOKENS = json.load(open(f"{current_dir}token.json"))
    SETTINGS = json.load(open(f"{current_dir}configs.json"))
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
        if "FMP_API_KEY" not in self.TOKENS or "FINNHUB_API_KEY" not in self.TOKENS:
            logging.warning('token.json does not contain FMP_API_KEY, '
                            'cannot run "stock_alert"')

        logging.warning('"TELEGRAM_IDS" in token.json:\n'
                        '"CG_SUM": alert_100, alert_300, alert_500, sequential\n'
                        '"VOLUME_15M", "VOLUME_1H", "PRICE_15M", "PRICE_1H": price_volume\n'
                        '"CG_MAR_CAP": market_cap\n'
                        '"ALTS": alts\n'
                        '"FUNDING_RATE": funding_rate\n'
                        '"MEME": meme_alert\n'
                        '"STOCK": stock_alert\n'
                        '"CG_PRICE_INCREASE": price_increase\n'
                        'Remember to fill in the Telegram channel/group ID for each alert type')
        logging.info("token.json validated")

    def validate_settings(self):
        """
        validate configs.json
        """
        # every alert setting should contain these keys
        alert_setting_keys = ["alert_input_args", "alert_params", "run_time_input_args", "database_name"]
        for alert_name, alert_setting in self.SETTINGS.items():
            for key in alert_setting_keys:
                if key not in alert_setting:
                    logging.error(f'configs.json does not contain "{key}" for {alert_name}')
                    exit(1)

            if alert_name == "price_volume":
                # validate the alert_params for price_volume
                param_keys = ["15m_volume_usd", "1h_volume_usd",
                              "15m_price_change_percentage", "1h_price_change_percentage"]
                alert_params = alert_setting["alert_params"]
                for param in param_keys:
                    if param not in alert_params:
                        logging.warning(f'configs.json does not contain "{param}" under "alert_params", '
                                        f'cannot run "price_volume" alerts')
                        break
                    if not isinstance(alert_params[param], int) and \
                            not isinstance(alert_params[param], float):
                        logging.warning(f'configs.json contains param "{param}" not numerical number, '
                                        f'cannot run "price_volume" alerts')
                        break

                if not alert_setting["database_name"]:
                    self.SETTINGS["price_volume"]["database_name"] = "price_volume"


if __name__ == "__main__":
    Config()
