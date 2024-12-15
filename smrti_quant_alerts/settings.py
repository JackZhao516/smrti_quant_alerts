import json
import os
import logging
from typing import Dict, Any, List

import pytz
import datetime

from binance.lib.utils import config_logging
config_logging(logging, logging.WARNING)


class Config:
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TOKENS = None
    SETTINGS = None
    API_ENDPOINTS = {
        "SP_500_SOURCE_URL": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies#S&P_500_component_stocks",
        "FMP_API_URL": "https://financialmodelingprep.com/api",
        "EODHD_API_URL": "https://eodhd.com/api",
        "PERPLEXITY_API_URL": "https://api.perplexity.ai",
        "SEC_API_URL": "https://api.sec-api.io",
    }
    IS_SETUP = False

    def __init__(self, verbose: bool = False) -> None:
        if not self.IS_SETUP:
            self._read_configs_tokens()
            self._validate_tokens(verbose=verbose)
            self._validate_configs()

    @classmethod
    def _read_configs_tokens(cls) -> None:
        """
        read configs.json and token.json
        """
        for file in ["token.json", "configs.json"]:
            if not os.path.isfile(os.path.join(cls.PROJECT_DIR, file)):
                logging.error(f"{file} not found")
                exit(1)
        try:
            cls.TOKENS = json.load(open(os.path.join(cls.PROJECT_DIR, "token.json")))
            cls.SETTINGS = json.load(open(os.path.join(cls.PROJECT_DIR, "configs.json")))
        except json.decoder.JSONDecodeError:
            logging.error("token.json/configs.json is not a valid json file")
            exit(1)
        cls.IS_SETUP = True

    def _validate_tokens(self, verbose: bool = True) -> None:
        """
        validate token.json

        :param verbose: print warning or not
        """
        necessary_keys = ["TELEGRAMBOT", "COINGECKO_API_KEY"]
        for key in necessary_keys:
            if key not in self.TOKENS:
                logging.error(f'token.json does not contain "{key}"')
                exit(1)
        if "TOKEN" not in self.TOKENS["TELEGRAMBOT"] or \
                "TELEGRAM_IDS" not in self.TOKENS["TELEGRAMBOT"]:
            logging.error("token.json does not contain "
                          "TELEGRAMBOT.TOKEN or TELEGRAMBOT.TELEGRAM_IDS")
            exit(1)
        if "FMP_API_KEY" not in self.TOKENS or "EODHD_API_KEY" not in self.TOKENS:
            logging.warning('token.json does not contain FMP_API_KEY/EODHD_API_KEY '
                            'cannot run "stock_alert"')

        if "SEC_API_KEY" not in self.TOKENS:
            logging.warning('token.json does not contain SEC_API_KEY '
                            'cannot run "file_8k_alert"')

        if "PERPLEXITY_API_KEY" not in self.TOKENS:
            logging.warning('token.json does not contain PERPLEXITY_API_KEY '
                            'cannot run "ai_analysis" for stock_alert')

        if "GMAIL" not in self.TOKENS:
            logging.warning('token.json does not contain GMAIL cannot send email')

        if verbose:
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

    def _validate_configs(self) -> None:
        """
        validate configs.json
        """
        # every alert setting should contain these keys
        alert_setting_keys = ["alert_input_args", "alert_params",
                              "run_time_input_args", "database_name", "alert_type"]
        for alert_name, alert_setting in self.SETTINGS.items():
            for key in alert_setting_keys:
                if key not in alert_setting.keys():
                    logging.error(f'configs.json does not contain "{key}" for {alert_name}')
                    exit(1)
            alert_type = alert_setting["alert_type"]
            self._validate_run_time_input_args(alert_setting["run_time_input_args"], alert_name)
            if not alert_setting["database_name"]:
                self.SETTINGS[alert_name]["database_name"] = alert_name
            if alert_type == "price_volume":
                self._validate_individual_configs(["15m_volume_usd", "1h_volume_usd",
                                                   "15m_price_change_percentage", "1h_price_change_percentage"],
                                                  ["alert_name", "tg_types", "alert_types"],
                                                  alert_setting, alert_name)
            elif alert_type == "price_increase_alert":
                self._validate_individual_configs([], ["top_range", "top_n", "timeframe", "tg_type"],
                                                  alert_setting, alert_name)
            elif alert_type == "stock_alert":
                self._validate_individual_configs([], ["tg_type", "timeframe_list", "email"],
                                                  alert_setting, alert_name)
            elif alert_type == "alts_alert":
                self._validate_individual_configs([], ["tg_type"],
                                                  alert_setting, alert_name)
            elif alert_type in ["sequential", "alert_100", "alert_300", "alert_500", "meme_alert"]:
                self._validate_individual_configs([], ["tg_type", "timeframe", "window", "alert_type",
                                                       "alert_name", "alert_coins_info"],
                                                  alert_setting, alert_name)
            elif alert_type == "market_cap":
                self._validate_individual_configs([], ["top_n", "tg_type"], alert_setting, alert_name)
            elif alert_type == "funding_rate":
                self._validate_individual_configs([], ["tg_type", "rate_threshold"], alert_setting, alert_name)

    @staticmethod
    def _validate_run_time_input_args(run_time_input_args: Dict[str, Any], alert_name: str) -> None:
        """
        validate the configs inside run_time_input_args

        :param run_time_input_args: the configs inside run_time_input_args
        :param alert_name: the alert type
        """

        if not isinstance(run_time_input_args, dict):
            logging.error(f'configs.json contains "run_time_input_args" not a dict for {alert_name}')
            exit(1)

        for key, value in run_time_input_args.items():
            if key not in ["daily_times", "excluded_week_days", "timezone"]:
                logging.error(f'configs.json contains unknown key "{key}" for {alert_name}')
                exit(1)
            if key == "daily_times":
                if not isinstance(value, list) and not isinstance(value, str):
                    logging.error(f'configs.json contains "daily_times" not a list or str for {alert_name}'
                                  f', in the format of ["00:00", "12:00"] or "00:00"')
                    exit(1)
                try:
                    if isinstance(value, list):
                        for time in value:
                            datetime.datetime.strptime(time, '%H:%M')
                    else:
                        datetime.datetime.strptime(value, '%H:%M')
                except ValueError:
                    logging.error(f'configs.json contains "daily_times" not in the format of "HH:MM" for {alert_name}'
                                  f', in the format of ["00:00", "12:00"] or "00:00"')
                    exit(1)

            if key == "excluded_week_days":
                if not isinstance(value, list):
                    logging.error(f'"excluded_week_days" should be a list for {alert_name}, '
                                  f'in the format of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]')
                    exit(1)
                for day in value:
                    if day not in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                        logging.error(f'configs.json contains unknown week day "{day}" for {alert_name}, '
                                      f'in the format of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]')
                        exit(1)
            if key == "timezone" and value and value not in pytz.all_timezones:
                logging.error(f'configs.json contains unknown timezone "{value}" for {alert_name}')
                exit(1)

    @staticmethod
    def _validate_individual_configs(param_keys: List[str], input_args_keys: List[str],
                                     alert_settings: Dict[str, Any], alert_name: str) -> None:
        """
        validate price_volume alert configs

        :param param_keys: the keys inside alert_params
        :param input_args_keys: the keys inside alert_input_args
        :param alert_settings: the configs inside alert_settings
        :param alert_name: the alert type
        """
        alert_params = alert_settings["alert_params"]
        for param in param_keys:
            if param not in alert_params:
                logging.error(f'configs.json does not contain "{param}" under "alert_params", '
                              f'cannot run "{alert_name}" alerts')
                exit(1)
        for key in input_args_keys:
            if key not in alert_settings["alert_input_args"]:
                logging.error(f'configs.json does not contain "{key}" under "alert_input_args", '
                              f'cannot run "{alert_name}" alerts')
                exit(1)

    def reload_settings(self) -> None:
        self.SETTINGS = json.load(open(os.path.join(self.PROJECT_DIR, "configs.json")))
        self._validate_configs()
