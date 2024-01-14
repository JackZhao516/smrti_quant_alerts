import os
from smrti_quant_alerts.settings import Config
from .mock_class import MockTelegramBot

Config.PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_settings")
