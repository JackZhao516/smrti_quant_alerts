import responses
import unittest

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.settings import Config


class TestCoinList(unittest.TestCase):
    COINGECKO_API_KEY = Config.TOKENS["COINGECKO_API_KEY"]
    BINANCE_API_URL = "https://api.binance.com/api/v3/"
    gel = GetExchangeList("TEST")
    @responses.activate
    def test_get_all_binance_exchanges(self):
        api_url = f'{self.BINANCE_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]},
                      status=200)
        exchanges = self.gel.get_all_binance_exchanges()
        self.assertEqual(["BTCUSDT", "ETHUSDT"], exchanges)

    @responses.activate
    def test_get_all_binance_active_exchanges(self):
        api_url = f'{self.BINANCE_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHBUSD"},
                                        {"symbol": "SOLETH"}, {"symbol": "ETHSOL"}]
                            },
                      status=200)
        active_exchanges = set(self.gel.get_all_binance_active_exchanges())
        self.assertEqual({"BTCUSDT", "ETHBUSD", "SOLETH"}, active_exchanges)

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
        api_url = f'{self.BINANCE_API_URL}exchangeInfo?permissions=SPOT'
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
    def test_get_all_exchanges_in_usdt_busd_btc(self):
        api_url = f'{self.BINANCE_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHBUSD"},
                                        {"symbol": "SOLETH"}, {"symbol": "ETHSOL"}]
                            },
                      status=200)
        exchanges = self.gel.get_all_exchanges_in_usdt_busd_btc()
        self.assertEqual(["BTCUSDT", "ETHBUSD"], exchanges)

    @responses.activate
    def test_get_coins_with_weekly_volume_increase(self):
        pass
