import responses
import unittest
from decimal import Decimal

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


class TestCoinList(unittest.TestCase):
    COINGECKO_API_KEY = Config.TOKENS["COINGECKO_API_KEY"]
    BINANCE_SPOT_API_URL = Config.API_ENDPOINTS["BINANCE_SPOT_API_URL"]
    BINANCE_FUTURES_API_URL = Config.API_ENDPOINTS["BINANCE_FUTURES_API_URL"]
    gel = GetExchangeList("TEST")

    @responses.activate
    def test_get_all_binance_exchanges(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "USDT", "status": "TRADING"}]},
                      status=200)
        exchanges = self.gel.get_all_binance_exchanges()
        self.assertEqual([BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")], exchanges)

    @responses.activate
    def test_get_popular_quote_binance_spot_exchanges(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "BUSD", "status": "TRADING"},
                                        {"baseAsset": "SOL", "quoteAsset": "ETH", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "SOL", "status": "TRADING"}]},
                      status=200)
        active_exchanges = self.gel.get_popular_quote_binance_spot_exchanges()
        self.assertEqual([BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "BUSD"),
                          BinanceExchange("SOL", "ETH")], active_exchanges)

    @responses.activate
    def test_get_future_exchange_funding_rate(self):
        api_url = f'{self.BINANCE_FUTURES_API_URL}premiumIndex?symbol=BTCUSDT'
        responses.add(responses.GET, api_url,
                      json={"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING",
                            "lastFundingRate": "0.0001"},
                      status=200)
        api_url = f'{self.BINANCE_FUTURES_API_URL}premiumIndex?symbol=ETHUSDT'
        responses.add(responses.GET, api_url,
                      json={"baseAsset": "ETH", "quoteAsset": "USDT", "status": "TRADING",
                            "lastFundingRate": "-0.0002"},
                      status=200)
        rate = self.gel.get_future_exchange_funding_rate(BinanceExchange("BTC", "USDT"))
        self.assertEqual(Decimal('0.0001'), rate)
        rate = self.gel.get_future_exchange_funding_rate(BinanceExchange("ETH", "USDT"))
        self.assertEqual(Decimal('-0.0002'), rate)

    @responses.activate
    def test_get_top_n_market_cap_coins(self):
        api_url = "https://pro-api.coingecko.com/api/v3/coins/markets?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}&vs_currency=usd&" \
                  "order=market_cap_desc&per_page=250&page=1&sparkline=false"
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc"}, {"id": "ethereum", "symbol": "eth"}],
                      status=200, match_querystring=True)
        coins = self.gel.get_top_n_market_cap_coins(2)
        self.assertEqual([CoingeckoCoin('bitcoin', 'BTC'), CoingeckoCoin('ethereum', 'ETH')], coins)

    @responses.activate
    def test_get_coins_market_info(self):
        api_url = "https://pro-api.coingecko.com/api/v3/coins/markets?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}&vs_currency=usd&" \
                  "per_page=250&page=1&sparkline=false&" \
                  "ids=bitcoin,ethereum&price_change_percentage=24h&locale=en"
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc", "market_cap": 200},
                            {"id": "ethereum", "symbol": "eth", "market_cap": 100}],
                      status=200, match_querystring=True)
        coins = self.gel.get_coins_market_info([CoingeckoCoin("bitcoin", "BTC"),
                                                CoingeckoCoin("ethereum", "ETH")], ["market_cap"])
        self.assertEqual([{"coingecko_coin": CoingeckoCoin("bitcoin", "BTC"), "market_cap": 200},
                          {"coingecko_coin": CoingeckoCoin("ethereum", "ETH"), "market_cap": 100}], coins)

    @responses.activate
    def test_get_coin_market_info(self):
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/market_chart?" \
                  f"vs_currency=usd&days=1&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc", "market_cap": 200},
                      status=200, match_querystring=True)
        coins = self.gel.get_coin_market_info(CoingeckoCoin("bitcoin", "BTC"), ["market_cap"], 1, "daily")
        self.assertEqual({"market_cap": 200}, coins)

    @responses.activate
    def test_get_coins_with_24h_volume_larger_than_threshold(self):
        pass

    @responses.activate
    def test_get_top_market_cap_exchanges(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHBUSD"},
                                        {"symbol": "SOLETH"}, {"symbol": "ETHSOL"}]
                            },
                      status=200)
        api_url = "https://pro-api.coingecko.com/api/v3/coins/markets?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}&vs_currency=usd&" \
                  "order=market_cap_desc&per_page=250&page=1&sparkline=false"
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc"}, {"id": "ethereum", "symbol": "eth"},
                            {"id": "testcoin", "symbol": "ts"}],
                      status=200, match_querystring=True)
        exchanges, cg_ids, cg_names = self.gel.get_top_market_cap_exchanges(3)

        self.assertEqual(["BTCUSDT", "ETHBUSD"], exchanges)
        self.assertEqual(["testcoin"], cg_ids)
        self.assertEqual(["TS"], cg_names)

    @responses.activate
    def test_get_spot_all_exchanges_in_usdt_busd_btc(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHBUSD"},
                                        {"symbol": "SOLETH"}, {"symbol": "ETHSOL"}]
                            },
                      status=200)
        exchanges = self.gel.get_all_spot_exchanges_in_usdt_busd_btc()
        self.assertEqual({"BTCUSDT", "ETHBUSD"}, set(exchanges))

    @responses.activate
    def test_get_coins_with_weekly_volume_increase(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHBUSD"},
                                        {"symbol": "SOLETH"}, {"symbol": "ETHSOL"}]
                            },
                      status=200)
        api_url = "https://pro-api.coingecko.com/api/v3/coins/markets?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}&vs_currency=usd&" \
                  "order=market_cap_desc&per_page=250&page=1&sparkline=false"
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc"}, {"id": "ethereum", "symbol": "eth"},
                            {"id": "sol", "symbol": "sol"}],
                      status=200, match_querystring=True)

        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/market_chart?" \
                  f"vs_currency=usd&days=13&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc",
                            "total_volumes": [[1, 100], [2, 100], [3, 100], [1, 100], [2, 100],
                                              [3, 100], [1, 100], [1, 100], [2, 100], [3, 100],
                                              [1, 100], [2, 100], [3, 100], [1, 100]]},
                      status=200, match_querystring=True)
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/ethereum/market_chart?" \
                  f"vs_currency=usd&days=13&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "ethereum", "symbol": "eth",
                            "total_volumes": [[1, 100], [2, 100], [3, 100], [1, 100], [2, 100],
                                              [3, 100], [1, 100], [1, 1000], [2, 1000], [3, 1000],
                                              [1, 1000], [2, 1000], [3, 100], [1, 1000]]},
                      status=200, match_querystring=True)
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/sol/market_chart?" \
                  f"vs_currency=usd&days=13&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "sol", "symbol": "sol",
                            "total_volumes": [[1, 100], [2, 100], [3, 100], [1, 100], [2, 100],
                                              [3, 100], [1, 100], [1, 100], [2, 100], [3, 100],
                                              [1, 100], [2, 100], [3, 100], [1, 100]]},
                      status=200, match_querystring=True)
        res, _, _ = self.gel.get_coins_with_weekly_volume_increase(1.3, 3, False)
        self.assertEqual(["SOLETH", "ETHBUSD"], res)
