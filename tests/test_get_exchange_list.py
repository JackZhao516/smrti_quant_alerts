import responses
import unittest
from decimal import Decimal

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.settings import Config


class TestCoinList(unittest.TestCase):
    COINGECKO_API_KEY = Config.TOKENS["COINGECKO_API_KEY"]
    BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/"
    BINANCE_FUTURE_API_URL = "https://fapi.binance.com/fapi/v1/"
    gel = GetExchangeList("TEST")

    @responses.activate
    def test_get_all_binance_spot_exchanges(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]},
                      status=200)
        exchanges = self.gel.get_all_binance_spot_exchanges()
        self.assertEqual(["BTCUSDT", "ETHUSDT"], exchanges)

    @responses.activate
    def test_get_all_binance_active_spot_exchanges(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHBUSD"},
                                        {"symbol": "SOLETH"}, {"symbol": "ETHSOL"}]
                            },
                      status=200)
        active_exchanges = set(self.gel.get_all_binance_active_spot_exchanges())
        self.assertEqual({"BTCUSDT", "ETHBUSD", "SOLETH"}, active_exchanges)

    @responses.activate
    def test_get_all_binance_future_exchanges(self):
        api_url = f'{self.BINANCE_FUTURE_API_URL}exchangeInfo'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT", "contractType": "Test"},
                                        {"symbol": "ETHUSDT", "contractType": "Test"}]},
                      status=200)
        exchanges = self.gel.get_all_binance_future_exchanges()
        self.assertEqual([['BTCUSDT', 'Test'], ['ETHUSDT', 'Test']], exchanges)

    @responses.activate
    def test_get_future_exchange_funding_rate(self):
        api_url = f'{self.BINANCE_FUTURE_API_URL}premiumIndex?symbol=BTCUSDT'
        responses.add(responses.GET, api_url,
                      json={"symbol": "BTCUSDT", "lastFundingRate": "0.0001"},
                      status=200)
        api_url = f'{self.BINANCE_FUTURE_API_URL}premiumIndex?symbol=ETHUSDT'
        responses.add(responses.GET, api_url,
                      json={"symbol": "ETHUSDT", "lastFundingRate": "-0.0002"},
                      status=200)
        rate = self.gel.get_future_exchange_funding_rate("BTCUSDT")
        self.assertEqual(Decimal('0.0001'), rate)
        rate = self.gel.get_future_exchange_funding_rate("ETHUSDT")
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
        self.assertEqual([('bitcoin', 'BTC'), ('ethereum', 'ETH')], coins)

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
        coins = self.gel.get_coins_market_info(["bitcoin", "ethereum"], ["market_cap"])
        self.assertEqual([{"id": "bitcoin", "symbol": "BTC", "market_cap": 200},
                          {"id": "ethereum", "symbol": "ETH", "market_cap": 100}], coins)

    @responses.activate
    def test_get_coin_market_info(self):
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/market_chart?" \
                  f"vs_currency=usd&days=1&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc", "market_cap": 200},
                      status=200, match_querystring=True)
        coins = self.gel.get_coin_market_info("bitcoin", ["market_cap"], 1, "daily")
        self.assertEqual({"market_cap": 200}, coins)

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
