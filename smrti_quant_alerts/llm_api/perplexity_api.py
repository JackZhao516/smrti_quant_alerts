from typing import Iterable, List
from time import time, sleep

from openai import OpenAI

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.data_type import StockSymbol


class PerplexityAPI:
    _rate_limit_per_minute = 20
    _last_request_time = 0
    _current_count = 0

    def __init__(self) -> None:
        config = Config()
        self._perplexity_client = OpenAI(api_key=config.TOKENS["PERPLEXITY_API_KEY"],
                                         base_url=config.API_ENDPOINTS["PERPLEXITY_API_URL"])
        self._model = "llama-3-sonar-large-32k-online"

    @staticmethod
    def build_chat_message(system_message: str, user_message: str) -> list:
        """
        build chat message for perplexity api

        :param system_message: system message
        :param user_message: user message
        :return: chat message
        """
        res = []
        if system_message:
            res.append({"role": "system", "content": system_message})
        if user_message:
            res.append({"role": "user", "content": user_message})
        return res

    @error_handling("perplexity", default_val="")
    def get_stock_increase_reason(self, company_stock_code: StockSymbol) -> str:
        """
        get stock increase reason

        :param company_stock_code: company stock code
        :return: stock increase reason
        """
        if self._current_count % self._rate_limit_per_minute == 0:
            sleep(max(60 - time() + self._last_request_time, 0))
            self._last_request_time = time()
            self._current_count = 0
        self._current_count += 1

        message = self.build_chat_message(
            "You are an artificial intelligence trading market analyst. "
            "With the latest market data, news, and company information, "
            f"please do analysis on the companies with stock code {company_stock_code}."
            "Then answer the following questions: ",
            f"what is the company with stock code {company_stock_code}? "
            f"Why did {company_stock_code} stock appreciate so much since (time period) ago?"
        )
        response = self._perplexity_client.chat.completions.create(
            model=self._model,
            messages=message,
        )
        return response.choices[0].message.content
