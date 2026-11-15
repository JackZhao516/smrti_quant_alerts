"""Compatibility imports for the former telegram_api package."""

import sys

from smrti_quant_alerts.gateway import telegram_api

TelegramBot = telegram_api.TelegramBot
sys.modules[f"{__name__}.telegram_api"] = telegram_api
