import logging
import uuid
import os

import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.data_type import StockSymbol, BinanceExchange, TradingSymbol, get_class
from smrti_quant_alerts.stock_crypto_api import StockApi, BinanceApi, get_stock_market_close_timestamp_from_date
from smrti_quant_alerts.stock_crypto_api.utility import calculate_macd
from smrti_quant_alerts.alerts.base_alert import BaseAlert

logging.basicConfig(level=logging.INFO)


class MACDAlert(BaseAlert):
    def __init__(self, alert_name: str, timeframe_list: List[str],
                 symbols: List[Dict[str, str]], email: bool = False, xlsx: bool = False, tg_type: str = "TEST") -> None:
        """
        :param alert_name: alert name
        :param timeframe_list: list of timeframes to check
        :param symbols: list of pairs of symbols
        :param email: send email or not
        :param tg_type: telegram type
        """
        super().__init__(tg_type)
        self._symbol_pairs = self._get_symbol_pairs(symbols)
        self._email = email
        self._xlsx = xlsx
        self._alert_name = alert_name
        self._timeframe_list = timeframe_list
        self._stock_api = StockApi()
        self._binance_api = BinanceApi()
        self._email_api = EmailApi()

        self._excel_file_paths = []

    @staticmethod
    def _get_symbol_pairs(symbols: List[Dict[str, str]]) -> List[Tuple[TradingSymbol, TradingSymbol]]:
        """
        Get the symbol pairs from the symbol list
        """
        res = []
        for symbol_pair in symbols:
            # stock does not care about the quote symbol
            if not symbol_pair["symbol_right"]:
                res.append((get_class(symbol_pair["type_left"])(symbol_pair["symbol_left"], "USDT"), None))
            else:
                res.append((get_class(symbol_pair["type_left"])(symbol_pair["symbol_left"], "USDT"),
                            get_class(symbol_pair["type_right"])(symbol_pair["symbol_right"], "USDT")))
        return res

    @staticmethod
    def _encode_symbol_pair(symbol_pair: Tuple[TradingSymbol, TradingSymbol]) -> str:
        """
        Encode the symbol pair
        """
        return f"{symbol_pair[0]}/{symbol_pair[1]}" if symbol_pair[1] else str(symbol_pair[0])

    def _get_past_number_of_macd(self, num_of_macd: int = 14) \
            -> Dict[str, Dict[str, List[Tuple[str, float]]]]:
        """
        Get the past number of MACD values

        :param num_of_macd: number of MACD values
        """
        macd_dict = defaultdict(dict)
        for symbol_pair in self._symbol_pairs:
            for timeframe in self._timeframe_list:
                left_close_prices, right_close_prices = self._get_left_right_close_prices(symbol_pair, timeframe)
                res = self._get_macd_for_stocks_or_cryptos(left_close_prices, right_close_prices, num_of_macd)
                macd_dict[self._encode_symbol_pair(symbol_pair)][timeframe] = res
        return macd_dict

    @staticmethod
    def _get_macd_for_stocks_or_cryptos(left_close_prices: List[Tuple[str, float]],
                                        right_close_prices: List[Tuple[str, float]], num_of_macd: int = 14) \
            -> List[Tuple[str, float]]:
        """
        Get the MACD values for the stocks

        :param left_close_prices: left close prices
        :param right_close_prices: right close prices
        :param num_of_macd: number of MACD values

        :return: list of MACD values
        """
        if not right_close_prices:
            macds = calculate_macd([close_price for _, close_price in left_close_prices[::-1]])[:num_of_macd]
            return [(date, macd) for date, macd in zip([date for date, _ in left_close_prices], macds)]
        close_prices = []
        dates = []
        index_left, index_right = 0, 0
        while index_left < len(left_close_prices) and index_right < len(right_close_prices):
            if left_close_prices[index_left][0] == right_close_prices[index_right][0]:
                if right_close_prices[index_right][1] != 0:
                    close_prices.append(left_close_prices[index_left][1] / right_close_prices[index_right][1])
                    dates.append(left_close_prices[index_left][0])
                index_left += 1
                index_right += 1
            elif left_close_prices[index_left][0] > right_close_prices[index_right][0]:
                index_left += 1
            else:
                index_right += 1
        macds = calculate_macd(close_prices[::-1])[:num_of_macd]
        return [(date, macd) for date, macd in zip(dates, macds)]

    def _get_left_right_close_prices(self, symbol_pair: Tuple[TradingSymbol, TradingSymbol], timeframe: str) \
            -> Tuple[List[Tuple[str, float]], List[Tuple[str, float]]]:
        """
        Get the close prices for the left and right symbols
        """
        right_close_prices = None
        if isinstance(symbol_pair[0], StockSymbol):
            left_close_prices = self._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks(
                symbol_pair[0], timeframe, 200)
            if isinstance(symbol_pair[1], StockSymbol):
                right_close_prices = self._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks(
                    symbol_pair[1], timeframe, 200)
            elif isinstance(symbol_pair[1], BinanceExchange):
                right_close_prices = []
                for date, _ in left_close_prices:
                    right_close_prices.append((date, self._binance_api.get_exchange_close_price_on_timestamp(
                        symbol_pair[1], get_stock_market_close_timestamp_from_date(date))))
                    if right_close_prices[-1][1] == 0:
                        right_close_prices.pop()
                        break
        else:
            left_close_prices = self._binance_api.get_exchange_close_prices_by_timeframe_num_of_ticks(
                symbol_pair[0], timeframe, 200)
            if isinstance(symbol_pair[1], BinanceExchange):
                right_close_prices = self._binance_api.get_exchange_close_prices_by_timeframe_num_of_ticks(
                    symbol_pair[1], timeframe, 200)
            elif isinstance(symbol_pair[1], StockSymbol):
                left_close_prices = []
                right_close_prices = self._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks(
                    symbol_pair[1], timeframe, 200)
                for date, _ in right_close_prices:
                    left_close_prices.append((date, self._binance_api.get_exchange_close_price_on_timestamp(
                        symbol_pair[0], get_stock_market_close_timestamp_from_date(date))))
                    if left_close_prices[-1][1] == 0:
                        left_close_prices.pop()
                        break

        return left_close_prices, right_close_prices

    @staticmethod
    def _generate_xlsx(symbol_pair_encoded: str, macd_dict: Dict[str, List[Tuple[str, float]]]) -> str:
        """
        Generate the csv file for the MACD values

        :param symbol_pair_encoded: symbol pair
        :param macd_dict: mapping from timeframe to list of MACD values

        :return: file path
        """
        filename = f"{symbol_pair_encoded.replace('/', '_')}_{uuid.uuid4()}.xlsx"
        with pd.ExcelWriter(filename) as writer:
            for timeframe, macd_values in macd_dict.items():
                dates = [date for date, _ in macd_values]
                macds = [macd for _, macd in macd_values]
                df = pd.DataFrame([dates, macds], index=["date", "macd"]).T
                df.to_excel(writer, sheet_name=timeframe, index=False)
        return filename

    @staticmethod
    def _generate_email_content(macd_dict: Dict[str, Dict[str, List[Tuple[str, float]]]]) -> str:
        """
        Generate the email content
        """
        content = ""

        rising_to_falling = ["·Rising to Falling"]
        falling_to_rising = ["·Falling to Rising"]
        for symbol_pair_encoded, macd_values in macd_dict.items():
            symbol_content = f"{symbol_pair_encoded}:"
            for timeframe, values in macd_values.items():
                r_to_f = []
                f_to_r = []
                current_macd, previous_macd = values[0][1], values[1][1]
                symbol_content += f"\n   ·{timeframe}: {round(previous_macd, 8)} to {round(current_macd, 8)}"

                if current_macd > 0 > previous_macd:
                    f_to_r.append(timeframe)
                elif current_macd < 0 < previous_macd:
                    r_to_f.append(timeframe)
                if r_to_f:
                    rising_to_falling.append(f"   ·{symbol_pair_encoded} {r_to_f}")
                if f_to_r:
                    falling_to_rising.append(f"   ·{symbol_pair_encoded} {f_to_r}")

                if current_macd * previous_macd < 0:
                    symbol_content += "  *"

            content += symbol_content + "\n\n"
        return "Summary\n\n" + "\n".join(rising_to_falling) + "\n" + \
               "\n".join(falling_to_rising) + "\n\n\n" + content

    def run(self) -> None:
        """
        Run the alert
        """
        macd_dict = self._get_past_number_of_macd()
        self._tg_bot.send_message(f"MACD values for {list(macd_dict.keys())}")
        if self._xlsx:
            for symbol_pair_encoded, macd_values in macd_dict.items():
                file_path = self._generate_xlsx(symbol_pair_encoded, macd_values)
                self._excel_file_paths.append(file_path)

        email_content = self._generate_email_content(macd_dict)

        # send email
        if self._email:
            self._email_api.send_email(self._alert_name, email_content, [], self._excel_file_paths)

        # send telegram message
        self._tg_bot.send_message(email_content)
        for file_path in self._excel_file_paths:
            self._tg_bot.send_file(file_path, file_path)
            os.remove(file_path)


if __name__ == "__main__":
    crypto_pair = [{"type_left": "BinanceExchange", "symbol_left": "SOL",
                    "type_right": "BinanceExchange", "symbol_right": "BTC"}]
    stock_pair = [{"type_left": "StockSymbol", "symbol_left": "TSLA",
                   "type_right": "StockSymbol", "symbol_right": "NVDA"}]
    stock_crypto_pair = [{"type_right": "StockSymbol", "symbol_right": "NVDA",
                          "type_left": "BinanceExchange", "symbol_left": "BTC"}]
    crypto_none_pair = [{"type_left": "BinanceExchange", "symbol_left": "BTC",
                         "type_right": "", "symbol_right": ""}]
    stock_none_pair = [{"type_left": "StockSymbol", "symbol_left": "TSLA",
                        "type_right": "", "symbol_right": ""}]

    alert = MACDAlert("macd_alert_daily", ["1M"],
                      crypto_none_pair, email=False, xlsx=True, tg_type="TEST")
    alert.run()
