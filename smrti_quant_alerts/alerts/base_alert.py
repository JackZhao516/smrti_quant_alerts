from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.db import init_database_runtime


class BaseAlert:
    """
    Base class for all alerts.

    All alerts should inherit from this class. It provides a telegram bot for sending message,
    a global config dictionary, a project directory, and a run method for running the alert.

    All alerts should implement the run method, which is the main method for running the alert.
    """
    CONFIG = Config(verbose=False)
    PWD = CONFIG.PROJECT_DIR

    def __init__(self, alert_name: str, tg_type: str = "TEST") -> None:
        self._alert_name = alert_name
        self._tg_bot = TelegramBot(tg_type=tg_type)
        database_name = f"{self.CONFIG.SETTINGS[self._alert_name].get('database_name', self._alert_name)}.db"
        init_database_runtime(database_name)

    def __str__(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return self.__class__.__name__

    def run(self) -> None:
        """
        run the alert
        """
        raise NotImplementedError
