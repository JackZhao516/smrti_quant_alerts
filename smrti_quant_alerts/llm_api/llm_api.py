import os
import re
import logging
from time import time, sleep
from datetime import datetime
from urllib.parse import urlsplit

from smrti_quant_alerts.http_client import redact

from openai import OpenAI

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.data_type import StockSymbol


class LLMAPI:
    _rate_limit_per_minute = 20
    _last_request_time = 0
    _current_count = 0
    _default_source = "OPENAI"

    def __init__(self) -> None:
        config = Config()
        if config.TOKENS and f"{self._default_source}_API_KEY" in config.TOKENS:
            self._api_key = config.TOKENS[f"{self._default_source}_API_KEY"]
        else:
            # Fallback to environment variable
            self._api_key = os.getenv("OPENAI_API_KEY")

        if not self._api_key:
            logging.warning("No OpenAI API key found in tokens.json or environment variables")

        options = config.TOKENS.get("OPENAI", {}) if config.TOKENS else {}
        if not isinstance(options, dict):
            raise ValueError("OPENAI must be a JSON object")
        if not isinstance(options.get("WEB_SEARCH", True), bool):
            raise ValueError("OPENAI.WEB_SEARCH must be a JSON boolean")
        self._model = options.get("MODEL", "gpt-4.1")
        self._web_search = options.get("WEB_SEARCH", True)
        self._client = OpenAI(api_key=self._api_key) if self._api_key else None

    @staticmethod
    def build_chat_message(system_message: str, user_message: str) -> list:
        """
        build chat message for OpenAI API

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
    def _parse_timeframe_number(tf: str) -> int:
        digits = re.findall(r"\d+", tf)
        return int(digits[0]) if digits else 0

    @staticmethod
    def _get_max_timeframe(timeframe: list[str]) -> str:
        """
        get max timeframe

        :param timeframe: list of timeframe
        :return: max timeframe
        """
        if not timeframe:
            return ""
        years = [tf for tf in timeframe if "Y" in tf.upper()]
        if years:
            return max(years, key=LLMAPI._parse_timeframe_number)
        months = [tf for tf in timeframe if "M" in tf.upper()]
        if months:
            return max(months, key=LLMAPI._parse_timeframe_number)
        days = [tf for tf in timeframe if "D" in tf.upper()]
        if days:
            return max(days, key=LLMAPI._parse_timeframe_number)
        hours = [tf for tf in timeframe if "H" in tf.upper()]
        if hours:
            return max(hours, key=LLMAPI._parse_timeframe_number)
        return timeframe[0]

    def get_ai_response(self, prompt: str) -> tuple[str, str]:
        """
        Get a response, optionally using web search according to OPENAI.WEB_SEARCH.

        Args:
            prompt: The prompt to send to the AI

        Returns:
            Tuple[str, str]: (response_content, citations)
        """
        if self._client is None:
            return "", ""
        try:
            search = getattr(self, "_web_search", True)
            response = self._client.responses.create(
                model=self._model,
                tools=[{"type": "web_search"}] if search else [],
                instructions=(
                    "Use web search to verify current facts and cite sources."
                    if search
                    else "Use only supplied information. Do not claim to have searched the web."
                ),
                input=prompt,
                max_output_tokens=2000,
            )

            def read(item, key, default=None):
                return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)

            citations = set()
            for item in response.output or []:
                for content in read(item, "content", []) or []:
                    for annotation in read(content, "annotations", []) or []:
                        if read(annotation, "type") != "url_citation":
                            continue
                        url = read(annotation, "url", "")
                        parsed = urlsplit(url)
                        if parsed.scheme in {"http", "https"} and parsed.netloc:
                            citations.add(f"- [{parsed.netloc}]({url})")
            sources = "\n\n## Sources:\n" + "\n".join(sorted(citations)) if citations else ""
            return response.output_text or "", sources
        except Exception as error:
            logging.error("Error getting AI response: %s", redact(error))
            return "", ""

    @error_handling("openai", default_val="")
    def get_stock_increase_reason(self, company_stock_code: StockSymbol, timeframe: list[str] | str) -> str:
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

        prompt = f"""You are an artificial intelligence trading market analyst.
        With the latest market data, news, and company information,
        please do analysis on the companies with stock code {company_stock_code}.
        Then answer the following questions:
        IMPORTANT: The date of the stock price increase is {date_str}.
        What is the company with stock code {company_stock_code}?
        Why did {company_stock_code} stock appreciate so much since
        {self._get_max_timeframe(timeframe)} timeframe ago since {date_str}?

        Please provide a comprehensive analysis including (but not limited to):
        1. Company overview and business model
        2. Recent news and events that may have impacted the stock
        3. Financial performance and market sentiment
        4. Technical analysis factors
        5. Any regulatory or industry-specific developments
        6. Any other relevant information"""

        response_content, citations = self.get_ai_response(prompt)

        # Combine response with citations
        if citations:
            return response_content + citations
        return response_content
