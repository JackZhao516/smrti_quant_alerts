import time
import math
from decimal import Decimal
from typing import List, Dict, Set, Any, Union, Optional

from pycoingecko import CoinGeckoAPI

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import CoingeckoCoin, TradingSymbol, BinanceExchange
from .utility import read_exclude_coins_from_file


class CoingeckoApi:
    COINGECKO_API_KEY = Config().TOKENS["COINGECKO_API_KEY"]
    PWD = Config.PROJECT_DIR

    def __init__(self) -> None:
        self._cg = CoinGeckoAPI(api_key=self.COINGECKO_API_KEY)

    def get_exclude_coins(
            self, input_exclude_coins: Union[List[TradingSymbol], Set[TradingSymbol], None] = None) \
            -> Set[CoingeckoCoin]:
        """
        expand exclude coins to include all quotes for each base

        :param input_exclude_coins: [BinanceExchange, CoingeckoCoin, ...]

        :return: [CoingeckoCoin, ...]
        """
        exclude_coins = set()
        self.get_all_coingecko_coins()
        # process exclude coins from class input
        if input_exclude_coins:
            for coin in input_exclude_coins:
                if isinstance(coin, BinanceExchange):
                    coin = CoingeckoCoin.get_symbol_object(coin.base_symbol)
                    if coin:
                        exclude_coins.add(coin)
                elif isinstance(coin, CoingeckoCoin):
                    exclude_coins.add(coin)

        # process exclude coins from stable coins and json file
        exclude_coin_symbols = read_exclude_coins_from_file()

        for coin in exclude_coin_symbols:
            coingecok_coin = CoingeckoCoin.get_symbol_object(coin)
            if coingecok_coin:
                exclude_coins.add(coingecok_coin)
            else:
                binance_exchange = BinanceExchange.get_symbol_object(coin)
                if binance_exchange:
                    coingecok_coin = CoingeckoCoin.get_symbol_object(binance_exchange.base_symbol)
                    if coingecok_coin:
                        exclude_coins.add(coingecok_coin)
        return exclude_coins

    @error_handling("coingecko", default_val=[])
    def get_all_coingecko_coins(self) -> List[CoingeckoCoin]:
        """
        Get all coins on coingecko

        :return: [CoingeckoCoin, ...]
        """
        coingecko_coins = self._cg.get_coins_list()
        return [CoingeckoCoin(coin["id"], coin["symbol"]) for coin in coingecko_coins]

    @error_handling("coingecko", default_val=[])
    def get_top_n_market_cap_coins(self, n: int = 100) -> List[CoingeckoCoin]:
        """
        get the top n market cap coins on coingecko

        :param n: number of coins to get

        :return: [CoingeckoCoin, ...]
        """
        # coingecko only allows 250 coins per page
        pages = math.ceil(n / 250)

        market_list = []
        for page in range(1, pages + 1):
            market_list += self._cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=250,
                page=page, sparkline=False)
            time.sleep(0.2)
        market_list = market_list

        seen = set()
        coingecko_coins = []
        for market in market_list:
            if market['id'] not in seen:
                coingecko_coins.append(CoingeckoCoin(market['id'], market['symbol']))
                seen.add(market['id'])

        return coingecko_coins[:n]

    @error_handling("coingecko", default_val=[])
    def get_coins_market_info(self, coingecko_coins: Union[List[CoingeckoCoin], Set[CoingeckoCoin]],
                              market_attribute_name_list: List[str],
                              price_change_percentage: str = "24h") -> List[Dict[str, Any]]:
        """
        get coin market info from coingecko

        :param coingecko_coins: [CoingeckoCoin, ...]
        :param market_attribute_name_list: [market_attribute_name, ...]
        :param price_change_percentage: comma separated list of price change percentage, e.g. "24h,7d,30d,1y"

        :return: [{"coingecko_coin": CoingeckoCoin, <market_attribute_name>: value, ...}]
        """
        pages = math.ceil(len(coingecko_coins) / 250)
        market_info = []
        for page in range(pages):
            cur_full_info = self._cg.get_coins_markets(
                vs_currency='usd', ids=[coin.coin_id for coin in coingecko_coins[page * 250:(page + 1) * 250]],
                per_page=250, page=1, sparkline=False,
                price_change_percentage=price_change_percentage, locale='en')

            for info in cur_full_info:
                cur_info = {"coingecko_coin": CoingeckoCoin(info['id'], info['symbol'])}
                for market_attribute_name in market_attribute_name_list:
                    cur_info[market_attribute_name] = info.get(market_attribute_name, None)

                market_info.append(cur_info)

        return market_info

    @error_handling("coingecko",
                    default_val={"symbol": "", "name": "", "description": "",
                                 "website": "", "genesis_date": "", "market_cap_rank": ""})
    def get_coin_info(self, coingecko_coin: Optional[CoingeckoCoin] = None) -> Dict[str, Any]:
        """
        get coin info from coingecko

        :param coingecko_coin: CoingeckoCoin

        :return: {"symbol": .., "name": .., "description": .. , "website:": ..,
                  "genesis_date": .., "market_cap_rank": ..}
        """
        if not coingecko_coin:
            return {"symbol": "", "name": "", "description": "", "website": "",
                    "genesis_date": "", "market_cap_rank": ""}
        coin_info = self._cg.get_coin_by_id(id=coingecko_coin.coin_id, localization='false',
                                            tickers='false', market_data='false',
                                            community_data='false', developer_data='false',
                                            sparkline='false')

        links = coin_info.get("links", {}).get("homepage", [])
        links = [link for link in links if link.startswith("http")]
        links = "; ".join(links) if links else ""
        return {"symbol": coingecko_coin.coin_symbol, "name": coin_info.get("name", ""),
                "description": coin_info.get("description", "").get("en", ""),
                "website": links, "genesis_date": coin_info.get("genesis_date", ""),
                "market_cap_rank": coin_info.get("market_cap_rank", "")}

    @error_handling("coingecko", default_val={})
    def get_coin_market_info(self, coingecko_coin: Optional[CoingeckoCoin] = None,
                             market_attribute_name_list: Optional[List[str]] = None,
                             days: int = 1, interval: str = "daily") -> Dict[str, Any]:
        """
        get coin market info from coingecko

        :param coingecko_coin: CoingeckoCoin
        :param market_attribute_name_list: [market_attribute_name, ...]
        :param days: number of days to get
        :param interval: interval of the data

        :return: {<market_attribute_name>: value, ...}
        """
        if not coingecko_coin:
            return {}
        coin_info = self._cg.get_coin_market_chart_by_id(
            id=coingecko_coin.coin_id, vs_currency='usd', days=days, interval=interval)

        return {market_attribute_name: coin_info[market_attribute_name]
                for market_attribute_name in market_attribute_name_list}

    @error_handling("coingecko", default_val=[])
    def get_coin_history_hourly_close_price(self, coingecko_coin: Optional[CoingeckoCoin] = None, days: int = 10) \
            -> List[Decimal]:
        """
        Get coin past close price for the history <days> days

        :param coingecko_coin: CoingeckoCoin
        :param days: number of days to get

        :return: [close_price, ...] in the order from newest to oldest
        """
        if not coingecko_coin:
            return []
        respond = self._cg.get_coin_market_chart_by_id(id=coingecko_coin.coin_id,
                                                       vs_currency='usd', days=days,
                                                       precision="full")
        prices = respond.get("prices", [])
        prices = [Decimal(i[1]) for i in prices][::-1]

        return prices

    @error_handling("coingecko", default_val=Decimal(0))
    def get_coin_current_price(self, coingecko_coin: Optional[CoingeckoCoin] = None) -> Decimal:
        """
        Get coin current close price

        :param coingecko_coin: CoingeckoCoin

        :return: close_price
        """
        if not coingecko_coin:
            return Decimal(0)
        respond = self._cg.get_price(ids=coingecko_coin.coin_id, vs_currencies='usd', precision='full')
        price = respond.get(coingecko_coin.coin_id, {}).get('usd', 0)
        return Decimal(price)
