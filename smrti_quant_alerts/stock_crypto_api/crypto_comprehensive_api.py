import time
import math
from typing import Tuple, List, Optional, Union, Set
from multiprocessing.pool import ThreadPool

import numpy as np

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin, TradingSymbol
from .crypto_binance_api import BinanceApi
from .crypto_coingecko_api import CoingeckoApi


class CryptoComprehensiveApi(BinanceApi, CoingeckoApi):
    def __init__(self) -> None:
        BinanceApi.__init__(self)
        CoingeckoApi.__init__(self)

    def get_exclude_coins(
            self, input_exclude_coins: Union[List[TradingSymbol], Set[TradingSymbol], None] = None) \
            -> Set[TradingSymbol]:
        """
        expand exclude coins to include all quotes for each base

        :param input_exclude_coins: [BinanceExchange, CoingeckoCoin, ...]

        :return: [BinanceExchange, CoingeckoCoin, ...]
        """
        exclude_coins = set()
        exclude_coins.update(BinanceApi.get_exclude_coins(self, input_exclude_coins))
        exclude_coins.update(CoingeckoApi.get_exclude_coins(self, input_exclude_coins))
        return exclude_coins

    @error_handling("coingecko", default_val=([], []))
    def get_2023_coins_with_daily_volume_threshold(
            self, threshold: int = 3000000) -> Tuple[List[BinanceExchange], List[CoingeckoCoin]]:
        """
        Get all coins with 24h volume larger than threshold (in USD)
        coin/usdt coin/eth coin/busd coin/btc exchanges on binance:
            [BinanceExchange, ...]
        if not on binance, get coin_id, and coin_name from coingeco:
            [CoingeckoCoin, ...]
        :param threshold: threshold of 24h volume in USD

        :return: [BinanceExchange, ...], [CoingeckoCoin, ...]
        """
        self._update_active_binance_spot_exchanges()
        coins = self.get_all_coingecko_coins()

        # pagination by 250
        pages = math.ceil(len(coins) / 250)
        coingecko_coins = []
        binance_exchanges = []

        quotes = ['USDT', 'BUSD', 'BTC', 'ETH']

        for page in range(pages):
            cur_coins_info = self._cg.get_coins_markets(
                vs_currency='usd', ids=[coin.coin_id for coin in coins[page * 250:(page + 1) * 250]],
                per_page=250, page=1)

            for info in cur_coins_info:
                symbol = info['symbol']
                coin = CoingeckoCoin(info['id'], info['symbol'])
                if 'atl_date' not in info or not info['atl_date'] \
                        or 'ath_date' not in info or not info['ath_date']:
                    continue
                atl_year = int(info['atl_date'][:4])
                ath_year = int(info['ath_date'][:4])
                if atl_year < 2023 or ath_year < 2023:
                    continue

                if info['total_volume'] and int(info['total_volume']) > threshold:
                    genesis_date = self.get_coin_info(coin)['genesis_date']
                    if not genesis_date or genesis_date and int(genesis_date[:4]) >= 2023:
                        binance_coin = False
                        for quote in quotes:
                            exchange = BinanceExchange(symbol, quote)
                            if exchange in self.active_binance_spot_exchanges_set:
                                binance_exchanges.append(BinanceExchange(symbol, quote))
                                binance_coin = True
                        if not binance_coin:
                            coingecko_coins.append(coin)

        return binance_exchanges, coingecko_coins

    def get_top_market_cap_coins_with_volume_threshold(
            self, num: int = 300, daily_volume_threshold: Optional[int] = None,
            weekly_volume_threshold: Optional[int] = None) \
            -> Tuple[List[BinanceExchange], List[CoingeckoCoin]]:
        """
        get the top <num> market cap
        coin/usdt coin/eth coin/busd coin/btc exchanges on binance:
            [BinanceExchange, ...]
        if not on binance, get coin_id, and coin_name from coingeco:
            [CoingeckoCoin, ...]
        if volume_threshold is not None, all the coins should have weekly
           volume larger than threshold

        :param num: number of exchanges to get
        :param daily_volume_threshold: threshold of daily volume in USD
        :param weekly_volume_threshold: threshold of weekly volume in USD

        :return: [BinanceExchange, ...], [CoingeckoCoin, ...]
        """
        self._update_active_binance_spot_exchanges()

        binance_exchanges = []
        coingeco_coins = []

        market_list = self.get_top_n_market_cap_coins(n=num)

        def filter_coin(coin):
            time.sleep(0.5)
            if weekly_volume_threshold or daily_volume_threshold:
                # get weekly volume
                data = self.get_coin_market_info(coin, ["total_volumes"], days=7, interval='daily')
                weekly_volume = np.sum(np.array(data.get('total_volumes', [])))
                daily_volume = data.get('total_volumes', [[0, 0]])[-1][1]
                if weekly_volume_threshold and weekly_volume < weekly_volume_threshold or \
                        daily_volume_threshold and daily_volume < daily_volume_threshold:
                    return

            symbol = coin.coin_symbol
            if f"{symbol}USDT" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}BTC" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}ETH" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}BUSD" not in self.active_binance_spot_exchanges_set:
                coingeco_coins.append(CoingeckoCoin(coin.coin_id, symbol))
            else:
                if f"{symbol}USDT" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "USDT"))
                elif f"{symbol}BUSD" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "BUSD"))
                if f"{symbol}BTC" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "BTC"))
                if f"{symbol}ETH" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "ETH"))

        pool = ThreadPool(4)
        pool.map(filter_coin, market_list)
        pool.close()

        return binance_exchanges, coingeco_coins

    @error_handling("coingecko", default_val=([], []))
    def get_coins_with_weekly_volume_increase(
            self, volume_threshold: float = 1.3,
            num: int = 500) -> Tuple[List[BinanceExchange], List[CoingeckoCoin]]:
        """
        Get top <num> market cap coins with weekly volume increase larger than volume_threshold
        for alt/btc, alt/eth, ignore the volume increase threshold

        After the filtering,
        if a coin exchange is on binance, put its exchange name into [BinanceExchange, ...]
        if a coin exchange is not on binance, put its coin_id and coin_name from coingeco
        into [CoingeckoCoin, ...]

        :param volume_threshold: weekly volume increase threshold
        :param num: top <num> market cap coins

        :return: [BinanceExchange, ...], [CoingeckoCoin, ...]
        """
        self._update_active_binance_spot_exchanges()
        market_list = self.get_top_n_market_cap_coins(num)
        coin_volume_increase_detail = []
        coingeco_coins, binance_exchanges = [], []

        for i, coin in enumerate(market_list):
            symbol = coin.coin_symbol
            coin_id = coin.coin_id
            # add alt/btc, alt/eth exchanges
            for quote in ["BTC", "ETH"]:
                if BinanceExchange(symbol, quote) in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, quote))

            # get volume increase ratio
            data = self.get_coin_market_info(coin, ["total_volumes"], days=13, interval='daily')

            data = np.array(data['total_volumes'])
            if np.sum(data[:7, 1]) == 0:
                continue
            volume_increase = np.sum(data[7:, 1]) / np.sum(data[:7, 1])

            if volume_increase >= volume_threshold:
                coin_volume_increase_detail.append([volume_increase, symbol, coin_id])

        coin_volume_increase_detail = sorted(coin_volume_increase_detail, key=lambda x: x[0], reverse=True)
        for volume_increase, symbol, coin_id in coin_volume_increase_detail:
            binance_exchange = False
            for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                if BinanceExchange(symbol, quote) in self.active_binance_spot_exchanges_set:
                    binance_exchange = True
                    if quote == "USDT" or quote == "BUSD":
                        binance_exchanges.append(BinanceExchange(symbol, quote))
                    break
            if not binance_exchange:
                coingeco_coins.append(CoingeckoCoin(coin_id, symbol))

        return binance_exchanges, coingeco_coins
