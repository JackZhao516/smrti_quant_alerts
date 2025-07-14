import os
import re
import logging
from typing import Tuple, List, Union
from time import time, sleep
from datetime import datetime

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
            self._api_key = os.getenv('OPENAI_API_KEY')
        
        if not self._api_key:
            logging.warning("No OpenAI API key found in tokens.json or environment variables")
        
        self._model = "gpt-4.1"
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

    def get_ai_response(self, prompt: str) -> Tuple[str, str]:
        """
        Get response from OpenAI API with web search
        
        Args:
            prompt: The prompt to send to the AI
            
        Returns:
            Tuple[str, str]: (response_content, citations)
        """
        try:                        
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a helpful assistant with access to current information through web search.
                        IMPORTANT: You MUST search the web for accurate information and cite your sources.
                        For each fact or piece of information you provide:
                        1. Include the specific URL where you found it
                        2. Format citations as markdown links: [domain.com](full_url)
                        3. Use multiple sources when possible for comprehensive information"""
                    },
                    {
                        "role": "user",
                        "content": f"""Please search the web to answer this question accurately. Include URLs for your sources:
                        {prompt}"""
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract main response and citations
            response_content = response.choices[0].message.content or ""
            citations = []
            
            # Extract citations from the response using markdown link format
            urls = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', response_content)
            if urls:
                for domain, url in urls:
                    citations.append(f"- [{domain}]({url})")
                    
            # remove duplicate citations
            citations = "\n\n## Sources:\n" + "\n".join(sorted(list(set(citations)))) if citations else ""

            return response_content, citations
            
        except Exception as e:
            error_msg = f"Error getting AI response: {e}"
            logging.error(error_msg)
            return "", ""

    @error_handling("openai", default_val="")
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

        prompt = f"""You are an artificial intelligence trading market analyst. 
        With the latest market data, news, and company information, 
        please do analysis on the companies with stock code {company_stock_code}.
        Then answer the following questions: 

        What is the company with stock code {company_stock_code}? 
        Why did {company_stock_code} stock appreciate so much since 
        {self._get_max_timeframe(timeframe)} timeframe ago? 
        
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
