from typing import List, Union
from time import time, sleep
from datetime import datetime

import openai

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.data_type import StockSymbol


class LLMAPI:
    _rate_limit_per_minute = 20
    _last_request_time = 0
    _current_count = 0
    _default_source = "PERPLEXITY"

    def __init__(self) -> None:
        config = Config()
        self._llm_client = openai.OpenAI(api_key=config.TOKENS[f"{self._default_source}_API_KEY"],
                                         base_url=config.API_ENDPOINTS[f"{self._default_source}_API_URL"])
        self._model = "grok-2-latest" if self._default_source == "XAI" else "llama-3.1-sonar-large-128k-online"

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

    @staticmethod
    def _get_max_timeframe(timeframe: List[str]) -> str:
        """
        get max timeframe

        :param timeframe: list of timeframe
        :return: max timeframe
        """
        if not timeframe:
            return ""
        years = [timeframe[i] for i in range(len(timeframe)) if "Y" in timeframe[i].upper()]
        if years:
            return max(years)
        months = [timeframe[i] for i in range(len(timeframe)) if "M" in timeframe[i].upper()]
        if months:
            return max(months)
        days = [timeframe[i] for i in range(len(timeframe)) if "D" in timeframe[i].upper()]
        if days:
            return max(days)
        hours = [timeframe[i] for i in range(len(timeframe)) if "H" in timeframe[i].upper()]
        if hours:
            return max(hours)
        return timeframe[0]

    @error_handling("perplexity", default_val="")
    def get_stock_increase_reason(self, company_stock_code: StockSymbol, timeframe: Union[List[str], str]) -> str:
        """
        get stock increase reason

        :param company_stock_code: company stock code
        :param timeframe: timeframe list
        :return: stock increase reason
        """
        if self._current_count % self._rate_limit_per_minute == 0:
            sleep(max(60 - time() + self._last_request_time, 0))
            self._last_request_time = time()
            self._current_count = 0
        self._current_count += 1
        timeframe = [timeframe] if isinstance(timeframe, str) else timeframe
        date_str = datetime.now().strftime("%Y-%m-%d")

        message = self.build_chat_message(
            "You are an artificial intelligence trading market analyst. "
            "With the latest market data, news, and company information, "
            f"please do analysis on the companies with stock code {company_stock_code}."
            f"The date of the stock price increase is {date_str}."
            "Then answer the following questions: ",
            f"what is the company with stock code {company_stock_code}? "
            f"Why did {company_stock_code} stock appreciate so much since "
            f"{self._get_max_timeframe(timeframe)} timeframe ago since {date_str}?"
        )
        response = self._llm_client.chat.completions.create(
            model=self._model,
            messages=message,
        )
        return response.choices[0].message.content
