import responses
import unittest
import time
from unittest import mock
from decimal import Decimal

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


class TestCoinList(unittest.TestCase):
    COINGECKO_API_KEY = Config.TOKENS["COINGECKO_API_KEY"]
    BINANCE_SPOT_API_URL = Config.API_ENDPOINTS["BINANCE_SPOT_API_URL"]
    BINANCE_FUTURES_API_URL = Config.API_ENDPOINTS["BINANCE_FUTURES_API_URL"]
    gel = GetExchangeList("TEST")

    def test_get_exclude_coins(self):
        self.gel.PWD = __file__.split("test_get_exchange_list.py")[0]
        self.gel._get_exclude_coins()
        self.assertEqual({BinanceExchange("USDT", "USDT"), BinanceExchange("BYTE", "USDT"),
                          BinanceExchange("USDT", "ETH"), BinanceExchange("USDT", "BTC"),
                          BinanceExchange("USDT", "BUSD"), BinanceExchange("BYTE", "BUSD"),
                          BinanceExchange("BYTE", "ETH"), BinanceExchange("BYTE", "BTC"),
                          CoingeckoCoin("tether", "USDT"), CoingeckoCoin("binarydao", "BYTE")},
                         self.gel._exclude_coins)

    @responses.activate
    def test_get_all_binance_exchanges(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "USDT", "status": "TRADING"},
                                        {"baseAsset": "SOL", "quoteAsset": "ETH", "status": "NOT_TRADING"}]},
                      status=200)
        self.gel._reset_timestamp()
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
        self.gel._reset_timestamp()
        active_exchanges = self.gel.get_popular_quote_binance_spot_exchanges()
        self.assertEqual([BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "BUSD"),
                          BinanceExchange("SOL", "ETH")], active_exchanges)

    @responses.activate
    def test_get_all_coingecko_coins(self):
        api_url = f'https://pro-api.coingecko.com/api/v3/coins/list?' \
                  f'x_cg_pro_api_key={self.COINGECKO_API_KEY}'
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                            {"id": "ethereum", "symbol": "eth", "name": "Ethereum"}],
                      status=200)
        self.gel._reset_timestamp()
        coins = self.gel.get_all_coingecko_coins()
        self.assertEqual([CoingeckoCoin("bitcoin", "btc"), CoingeckoCoin("ethereum", "eth")], coins)

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
        self.gel._reset_timestamp()
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
        self.gel._reset_timestamp()
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
        self.gel._reset_timestamp()
        coins = self.gel.get_coins_market_info([CoingeckoCoin("bitcoin", "BTC"),
                                                CoingeckoCoin("ethereum", "ETH")], ["market_cap"])
        self.assertEqual([{"coingecko_coin": CoingeckoCoin("bitcoin", "BTC"), "market_cap": 200},
                          {"coingecko_coin": CoingeckoCoin("ethereum", "ETH"), "market_cap": 100}], coins)

    @responses.activate
    def test_get_coin_info(self):
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}" \
                  f"&localization=false&tickers=false&market_data=false&" \
                  f"community_data=false&developer_data=false&sparkline=false"

        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
                            "description": {"en": "test"}, "genesis_date": "2009-01-03T00:00:00.000Z",
                            "links": {"homepage": ["https://www.bitcoin.org", ""]}},
                      status=200, match_querystring=True)
        self.gel._reset_timestamp()
        info = self.gel.get_coin_info(CoingeckoCoin("bitcoin", "BTC"))
        self.assertEqual({"symbol": "BTC", "name": "Bitcoin", "genesis_date": "2009-01-03T00:00:00.000Z",
                          "description": "test", "website": "https://www.bitcoin.org"}, info)

    @responses.activate
    def test_get_coin_market_info(self):
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/market_chart?" \
                  f"vs_currency=usd&days=1&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc", "market_cap": 200},
                      status=200, match_querystring=True)
        self.gel._reset_timestamp()
        coins = self.gel.get_coin_market_info(CoingeckoCoin("bitcoin", "BTC"), ["market_cap"], 1, "daily")
        self.assertEqual({"market_cap": 200}, coins)

    @responses.activate
    def test_get_coin_history_hourly_close_price(self):
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/market_chart?" \
                  f"vs_currency=usd&days=3&precision=full&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"prices": [[1, 100], [2, 200], [3, 300], [4, 400]]},
                      status=200, match_querystring=True)
        self.gel._reset_timestamp()
        coins = self.gel.get_coin_history_hourly_close_price(CoingeckoCoin("bitcoin", "BTC"), 3)
        self.assertEqual([400, 300, 200, 100], coins)

    @responses.activate
    def test_get_coin_current_price(self):
        api_url = f"https://pro-api.coingecko.com/api/v3/simple/price?" \
                  f"ids=bitcoin&vs_currencies=usd&precision=full&" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"bitcoin": {"usd": 100}},
                      status=200, match_querystring=True)
        self.gel._reset_timestamp()
        price = self.gel.get_coin_current_price(CoingeckoCoin("bitcoin", "BTC"))
        self.assertEqual(100, price)

    @responses.activate
    def test_get_exchange_history_hourly_close_price(self):
        with mock.patch.object(time, "time", return_value=86400):
            api_url = f"{self.BINANCE_SPOT_API_URL}klines?symbol=BTCUSDT&interval=1h&limit=1000&startTime=0"
            responses.add(responses.GET, api_url,
                          json=[[1, 100, 100, 100, 100], [2, 200, 200, 200, 200],
                                [3, 300, 200, 300, 300], [4, 400, 400, 400, 400]],
                          status=200, match_querystring=True)
            self.gel._reset_timestamp()
            prices = self.gel.get_exchange_history_hourly_close_price(BinanceExchange("BTC", "USDT"), 1)
            self.assertEqual([400, 300, 200, 100], prices)

    @responses.activate
    def test_get_exchange_current_price(self):
        api_url = f"{self.BINANCE_SPOT_API_URL}ticker/price?symbol=BTCUSDT"
        responses.add(responses.GET, api_url,
                      json={"symbol": "BTCUSDT", "price": "100"},
                      status=200, match_querystring=True)
        self.gel._reset_timestamp()
        price = self.gel.get_exchange_current_price(BinanceExchange("BTC", "USDT"))
        self.assertEqual(100, price)

    @responses.activate
    def test_get_2023_coins_with_daily_volume_threshold(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"}]},
                      status=200)

        api_url = f'https://pro-api.coingecko.com/api/v3/coins/list?' \
                  f'x_cg_pro_api_key={self.COINGECKO_API_KEY}'
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                            {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
                            {"id": "okcoin", "symbol": "okc", "name": "OKCoin"}],
                      status=200)

        api_url = "https://pro-api.coingecko.com/api/v3/coins/markets?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}&vs_currency=usd&" \
                  "per_page=250&page=1&" \
                  "ids=bitcoin,ethereum,okcoin"
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc", "total_volume": 20000000,
                             "atl_date": "2023-03-02T00:00:00.000Z", "ath_date": "2023-03-02T00:00:00.000Z"},
                            {"id": "ethereum", "symbol": "eth", "total_volume": 10000000,
                             "atl_date": "2023-03-02T00:00:00.000Z", "ath_date": "2021-03-02T00:00:00.000Z"},
                            {"id": "okcoin", "symbol": "okc", "total_volume": 1000,
                             "atl_date": "2023-03-02T00:00:00.000Z", "ath_date": "2023-03-02T00:00:00.000Z"}],
                      status=200, match_querystring=True)
        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}" \
                  f"&localization=false&tickers=false&market_data=false&" \
                  f"community_data=false&developer_data=false&sparkline=false"

        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
                            "description": {"en": "test"}, "genesis_date": "2023-01-03",
                            "links": {"homepage": ["https://www.bitcoin.org", ""]}},
                      status=200, match_querystring=True)
        self.gel._reset_timestamp()
        exchanges, coins = self.gel.get_2023_coins_with_daily_volume_threshold(1000000)
        self.assertEqual([BinanceExchange("BTC", "USDT")], exchanges)

    @responses.activate
    def test_get_top_market_cap_coins_with_volume_threshold(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "BUSD", "status": "TRADING"},
                                        {"baseAsset": "SOL", "quoteAsset": "ETH", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "SOL", "status": "TRADING"}]
                            },
                      status=200)
        api_url = "https://pro-api.coingecko.com/api/v3/coins/markets?" \
                  f"x_cg_pro_api_key={self.COINGECKO_API_KEY}&vs_currency=usd&" \
                  "order=market_cap_desc&per_page=250&page=1&sparkline=false"
        responses.add(responses.GET, api_url,
                      json=[{"id": "bitcoin", "symbol": "btc"}, {"id": "ethereum", "symbol": "eth"},
                            {"id": "testcoin", "symbol": "ts"}],
                      status=200, match_querystring=True)

        api_url = f"https://pro-api.coingecko.com/api/v3/coins/ethereum/market_chart?" \
                  f"vs_currency=usd&days=7&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "ethereum", "symbol": "eth",
                            "total_volumes": [[1, 100], [2, 1000000], [3, 1000000], [4, 1000000], [5, 1000000],
                                              [6, 1000000], [7, 1000000], [8, 1000000]]},
                      status=200, match_querystring=True)

        api_url = f"https://pro-api.coingecko.com/api/v3/coins/bitcoin/market_chart?" \
                  f"vs_currency=usd&days=7&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "bitcoin", "symbol": "btc",
                            "total_volumes": [[1, 100], [2, 1000000], [3, 10000], [4, 1000000], [5, 1000000],
                                              [6, 1000000], [7, 1000000], [8, 1000000]]},
                      status=200, match_querystring=True)

        api_url = f"https://pro-api.coingecko.com/api/v3/coins/testcoin/market_chart?" \
                  f"vs_currency=usd&days=7&interval=daily&x_cg_pro_api_key={self.COINGECKO_API_KEY}"
        responses.add(responses.GET, api_url,
                      json={"id": "testcoin", "symbol": "ts",
                            "total_volumes": [[1, 100], [2, 1000000], [3, 70000000], [4, 1000000], [5, 1000000],
                                              [6, 1000000], [7, 1000000], [8, 1000000]]},
                      status=200, match_querystring=True)

        self.gel._reset_timestamp()
        exchanges, cg_coins = self.gel.get_top_market_cap_coins_with_volume_threshold(3, weekly_volume_threshold=7000000)

        self.assertEqual([BinanceExchange("ETH", "BUSD")], exchanges)
        self.assertEqual([CoingeckoCoin("testcoin", "ts")], cg_coins)

    @responses.activate
    def test_get_spot_all_exchanges_in_usdt_busd_btc(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "USDT", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "BUSD", "status": "TRADING"},
                                        {"baseAsset": "SOL", "quoteAsset": "ETH", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "SOL", "status": "TRADING"}]
                            },
                      status=200)
        self.gel._reset_timestamp()
        exchanges = self.gel.get_all_spot_exchanges_in_usdt_busd_btc()
        self.assertEqual({BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "BUSD")}, set(exchanges))

    @responses.activate
    def test_get_coins_with_weekly_volume_increase(self):
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'
        responses.add(responses.GET, api_url,
                      json={"symbols": [{"baseAsset": "BTC", "quoteAsset": "TTT", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "BUSD", "status": "TRADING"},
                                        {"baseAsset": "SOL", "quoteAsset": "ETH", "status": "TRADING"},
                                        {"baseAsset": "ETH", "quoteAsset": "SOL", "status": "TRADING"}]
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
                                              [3, 100], [1, 100], [1, 1000], [2, 1000], [3, 1000],
                                              [1, 1000], [2, 1000], [3, 1000], [1, 1000]]},
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
        self.gel._reset_timestamp()
        binance_exchanges, coingecko_coins = self.gel.get_coins_with_weekly_volume_increase(1.3, 3, False)
        self.assertEqual([BinanceExchange("SOL", "ETH"), BinanceExchange("ETH", "BUSD")], binance_exchanges)
        self.assertEqual([CoingeckoCoin("bitcoin", "btc")], coingecko_coins)
