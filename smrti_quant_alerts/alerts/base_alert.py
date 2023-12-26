from typing import Any

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.telegram_api import TelegramBot


class BaseAlert:
    """
    Base class for all alerts.

    All alerts should inherit from this class. It provides a telegram bot for sending message,
    a global config dictionary, a project directory, and a run method for running the alert.

    All alerts should implement the run method, which is the main method for running the alert.
    """
    ALERT_SETTINGS = Config.SETTINGS

    PWD = Config.PROJECT_DIR

    def __init__(self, tg_type: str) -> None:
        self._tg_bot = TelegramBot(tg_type=tg_type)

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return self.__class__.__name__

    def run(self, *args: Any, **kwargs: Any) -> None:
        """
        run the alert
        """
        raise NotImplementedError
