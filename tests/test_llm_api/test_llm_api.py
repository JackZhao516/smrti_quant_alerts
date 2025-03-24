import unittest
import os
from typing import List
from dataclasses import dataclass
from unittest.mock import patch, create_autospec

import openai

from smrti_quant_alerts.llm_api import LLMAPI
from smrti_quant_alerts.settings import Config


@dataclass
class OpenAIMessage:
    content: str


@dataclass
class OpenAIMessageWrapper:
    message: OpenAIMessage


@dataclass
class OpenAIResponse:
    choices: List[OpenAIMessageWrapper]


class TestLLMApi(unittest.TestCase):
    PWD = os.path.dirname(os.path.abspath(__file__))
    Config.PROJECT_DIR = os.path.join(os.path.dirname(PWD), "test_settings")

    def setUp(self) -> None:
        self.openai_mock = create_autospec(openai.OpenAI)
        with patch("openai.OpenAI", side_effect=lambda **kwargs: self.openai_mock):
            self.perplexity_api = LLMAPI()

    def test_build_chat_message(self) -> None:
        system_message = "test_system_message"
        user_message = "test_user_message"
        self.assertEqual(self.perplexity_api.build_chat_message(system_message, user_message),
                         [{"role": "system", "content": "test_system_message"},
                         {"role": "user", "content": "test_user_message"}])

    def test_get_max_timeframe(self) -> None:
        self.assertEqual(self.perplexity_api._get_max_timeframe([]), "")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["1y", "5Y"]), "5Y")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["1m", "5M"]), "5M")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["1d", "5D"]), "5D")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["1h", "5H"]), "5H")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["5m", "1h"]), "5m")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["1d", "5y"]), "5y")
        self.assertEqual(self.perplexity_api._get_max_timeframe(["1s"]), "1s")
