import logging
import uuid
import os
import csv

import pandas as pd
import numpy as np
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
                 symbols_file: str, email: bool = False, xlsx: bool = False, tg_type: str = "TEST") -> None:
        """
        :param alert_name: alert name
        :param timeframe_list: list of timeframes to check
        :param symbols_file: csv file containing the symbols
        :param email: send email or not
        :param tg_type: telegram type
        """
        super().__init__(tg_type)
        self._sectors = defaultdict(dict)
        self._symbol_pairs = self._parse_symbols_file(symbols_file)
        self._email = email
        self._xlsx = xlsx
        self._alert_name = alert_name
        self._timeframe_list = timeframe_list
        self._stock_api = StockApi()
        self._binance_api = BinanceApi()
        self._email_api = EmailApi()

        self._excel_file_paths = []

    def _parse_symbols_file(self, file_name: str) -> List[Tuple[TradingSymbol, TradingSymbol]]:
        """
        parse the symbols file

        :param file_name: file name
        :return: list of symbol pairs
        """
        symbols = []
        with open(file_name, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row["sub_sector"]:
                    row["sub_sector"] = None
                # stock does not care about the quote currency
                left_symbol = get_class(row["type_left"])(row["symbol_left"], "USDT")
                right_symbol = get_class(row["type_right"])(row["symbol_right"], "USDT") \
                    if row["symbol_right"] else None
                symbol = (left_symbol, right_symbol)
                symbols.append(symbol)
                if self._sectors[row["sector"]].get(row["sub_sector"]):
                    self._sectors[row["sector"]][row["sub_sector"]].append(symbol)
                else:
                    self._sectors[row["sector"]][row["sub_sector"]] = [symbol]
        return symbols

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
    def _process_timeframe_for_changed_macd(
            changed_timeframes: List[str], positive_timeframes: List[str], negative_timeframes: List[str]) -> str:
        pos_set_exclude_changed = set(positive_timeframes) - set(changed_timeframes)
        neg_set_exclude_changed = set(negative_timeframes) - set(changed_timeframes)
        pos_str = "+, ".join(pos_set_exclude_changed)
        neg_str = "-, ".join(neg_set_exclude_changed)
        pos_str = f"[{pos_str}+]" if pos_set_exclude_changed else ""
        neg_str = f"[{neg_str}-]" if neg_set_exclude_changed else ""

        return f"{pos_str} {neg_str}"

    def _generate_email_content(self, macd_dict: Dict[str, Dict[str, List[Tuple[str, float]]]]) -> str:
        """
        Generate the email content

        :param macd_dict: mapping from symbol pair to mapping from timeframe to list of MACD values

        :return: email content
        """
        content = ""
        space = " " * 4
        level = 0

        rising_to_falling = ["·Rising to Falling"]
        falling_to_rising = ["·Falling to Rising"]

        for sector, sub_sectors in self._sectors.items():
            content += f"- {sector}:\n"
            level += 1
            for sub_sector, symbol_pairs in sub_sectors.items():
                content += space * level + f"- {sub_sector}:\n" if sub_sector else ""
                level += 1 if sub_sector else 0
                for symbol_pair in symbol_pairs:
                    symbol_pair_encoded = self._encode_symbol_pair(symbol_pair)
                    # print individual symbol content
                    symbol_content = space * level + f"- {symbol_pair_encoded}:"
                    r_to_f, f_to_r, pos, neg = [], [], [], []
                    for timeframe, values in macd_dict[symbol_pair_encoded].items():
                        current_macd, previous_macd = values[0][1], values[1][1]
                        symbol_content += '\n' + space * (level + 1)
                        if np.isnan(current_macd) or np.isnan(previous_macd):
                            symbol_content += f"·{timeframe}: No enough data to calculate MACD"
                        else:
                            symbol_content += f"·{timeframe}: {round(previous_macd, 8)} to {round(current_macd, 8)}"

                        if current_macd > 0:
                            pos.append(timeframe)
                            if previous_macd < 0:
                                f_to_r.append(timeframe)
                        else:
                            neg.append(timeframe)
                            if previous_macd > 0:
                                r_to_f.append(timeframe)
                        if current_macd * previous_macd < 0:
                            symbol_content += "  *"
                    if r_to_f:
                        rising_to_falling.append(
                            f"{space}·{symbol_pair_encoded} {r_to_f}\n"
                            f"{space * 2}-{self._process_timeframe_for_changed_macd(r_to_f, pos, neg)}")
                    if f_to_r:
                        falling_to_rising.append(
                            f"{space}·{symbol_pair_encoded} {f_to_r}\n"
                            f"{space * 2}-{self._process_timeframe_for_changed_macd(f_to_r, pos, neg)}")

                    content += symbol_content + "\n\n"
                level -= 1 if sub_sector else 0
            level = 0

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
    # macd_symbols_file = "macd_symbols_example.csv"
    # macd_symbols_file = "macd_symbols.csv"
    macd_symbols_file = "test.csv"
    alert = MACDAlert("macd_alert_daily", ["1D", "2D", "3D"],
                      macd_symbols_file, email=False, xlsx=False, tg_type="TEST")
    alert.run()
