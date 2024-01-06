import unittest
import logging
import json
import os
from unittest.mock import patch, mock_open


from smrti_quant_alerts.settings import Config

logging.disable(logging.CRITICAL)
PWD = os.path.dirname(os.path.abspath(__file__))
dummy_config_str = open(os.path.join(PWD, "dummy_configs.json")).read()
dummy_config_json = json.load(open(os.path.join(PWD, "dummy_configs.json")))
dummy_token_str = open(os.path.join(PWD, "dummy_token.json")).read()
dummy_token_json = json.load(open(os.path.join(PWD, "dummy_token.json")))


class TestConfig(unittest.TestCase):
    def test_config_basics(self) -> None:
        config = Config()
        self.assertTrue(config.PROJECT_DIR)
        self.assertIsInstance(config.SETTINGS, dict)
        self.assertIsInstance(config.TOKENS, dict)
        self.assertIsInstance(config.API_ENDPOINTS, dict)

    def test_read_configs_tokens(self) -> None:
        config = Config()
        config.PROJECT_DIR = PWD
        with patch('builtins.open',
                   side_effect=lambda file, mode='r': mock_open(read_data=dummy_token_str).return_value
                   if file == os.path.join(config.PROJECT_DIR, "token.json")
                   else mock_open(read_data=dummy_config_str).return_value):
            config._read_configs_tokens()
            self.assertEqual(config.SETTINGS, dummy_config_json)
            self.assertEqual(config.TOKENS, dummy_token_json)

        with patch('builtins.open',
                   side_effect=lambda file, mode='r': mock_open(read_data=dummy_token_str).return_value
                   if file == os.path.join(config.PROJECT_DIR, "token.json")
                   else mock_open(read_data="test").return_value):
            with self.assertRaises(SystemExit) as cm:
                config._read_configs_tokens()
                self.assertEqual(cm.exception.code, 1)

        config.PROJECT_DIR = "test"
        with self.assertRaises(SystemExit) as cm:
            config._read_configs_tokens()
            self.assertEqual(cm.exception.code, 1)

    def test_validate_tokens(self) -> None:
        config = Config()
        config.TOKENS = dummy_token_json

        test_tokens = [
            {"TelegramBot": {}},
            {"TelegramBot": {"TOKEN": {}}, "COINGECKO_API_KEY": "test"}
        ]
        for test_token in test_tokens:
            config.TOKENS = test_token
            with self.assertRaises(SystemExit) as cm:
                config._validate_tokens(verbose=True)
                self.assertEqual(cm.exception.code, 1)
        config.TOKENS = {"TelegramBot": {"TOKEN": "test", "TELEGRAM_IDS": ["test"]},
                         "COINGECKO_API_KEY": "test"}

        with patch("logging.warning") as mock_warning:
            config._validate_tokens(verbose=False)
            mock_warning.assert_called()

    def test_validate_configs(self) -> None:
        config = Config()
        config.SETTINGS = json.load(open(os.path.join(PWD, "configs.json")))
        second_key = list(config.SETTINGS.keys())[1]
        del config.SETTINGS[second_key]["alert_params"]
        with self.assertRaises(SystemExit) as cm:
            config._validate_configs()
            self.assertEqual(cm.exception.code, 1)

    def test_validate_run_time_input_args(self) -> None:
        config = Config()
        test_configs = [
            {"run_time_input_args": {"test"}, "alert_name": "test"},
            {"run_time_input_args": {"test": "00:00"},
             "alert_name": "test"},
            {"run_time_input_args": {"daily_times": "00:00", "excluded_week_days": "", "timezone": ""},
             "alert_name": "test"},
            {"run_time_input_args": {"daily_times": ["00:00"], "excluded_week_days": ["test"], "timezone": ""},
             "alert_name": "test"},
            {"run_time_input_args": {"daily_times": ["test"], "excluded_week_days": [], "timezone": ""},
             "alert_name": "test"},
            {"run_time_input_args": {"daily_times": ["00:00"], "excluded_week_days": [], "timezone": "test"},
             "alert_name": "test"},
            {"run_time_input_args": {"daily_times": 1, "excluded_week_days": [], "timezone": "test"},
             "alert_name": "test"}
        ]
        for test_config in test_configs:
            with self.assertRaises(SystemExit) as cm:
                config._validate_run_time_input_args(**test_config)
                self.assertEqual(cm.exception.code, 1)

    def test_validate_individual_configs(self) -> None:
        config = Config()
        config.SETTINGS = dummy_config_json
        test_configs = [
            {"param_keys": ["test"], "input_args_keys": ["test"],
             "alert_settings": {"alert_params": {"test": 1}, "alert_input_args": {1: 1}}, "alert_name": "test"},
            {"param_keys": ["test"], "input_args_keys": ["test"],
             "alert_settings": {"alert_params": {1: 1}, "alert_input_args": {"test": 1}}, "alert_name": "test"}
        ]
        for test_config in test_configs:
            with self.assertRaises(SystemExit) as cm:
                config._validate_individual_configs(**test_config)
                self.assertEqual(cm.exception.code, 1)

    def test_reload_settings(self) -> None:
        config = Config()
        with patch("builtins.open", new_callable=mock_open, read_data=dummy_config_str):
            config.reload_settings()
            self.assertEqual(config.SETTINGS, dummy_config_json)
