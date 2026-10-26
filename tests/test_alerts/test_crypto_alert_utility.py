"""Unit tests for the crypto alert helpers."""

from unittest.mock import patch

from smrti_quant_alerts.alerts.crypto_alerts import utility
from smrti_quant_alerts.alerts.crypto_alerts.utility import send_coins_info_to_telegram
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


def test_send_coins_info_skips_empty_input() -> None:
    tg_bot = utility.TelegramBot.__new__(utility.TelegramBot)

    with patch.object(utility, "CoingeckoApi") as coingecko_api:
        send_coins_info_to_telegram([], tg_bot)

    coingecko_api.assert_not_called()


def test_send_coins_info_converts_binance_exchanges() -> None:
    BinanceExchange.add_base_coin_id_pair_to_dict("ETH", "ethereum")
    btc = CoingeckoCoin("bitcoin", "BTC")
    eth_exchange = BinanceExchange("ETH", "USDT")
    eth = CoingeckoCoin("ethereum", "ETH")
    tg_bot = utility.TelegramBot.__new__(utility.TelegramBot)
    tg_bot.send_data_as_csv_file = lambda *args, **kwargs: None

    def coin_info(coin):
        return {
            "symbol": coin.coin_symbol,
            "name": coin.coin_id,
            "website": f"https://{coin.coin_id}.org",
            "description": f"{coin.coin_id} description",
            "market_cap_rank": 1,
        }

    with patch.object(utility, "CoingeckoApi") as coingecko_api_cls:
        coingecko_api = coingecko_api_cls.return_value
        coingecko_api.get_coins_chain_info.return_value = {btc: ["bitcoin"], eth: ["ethereum"]}
        coingecko_api.get_coin_info.side_effect = coin_info

        with patch.object(tg_bot, "send_data_as_csv_file") as send_csv:
            send_coins_info_to_telegram([btc, eth_exchange], tg_bot, "price_increase_14d")

    file_name, headers, data = send_csv.call_args.args
    assert file_name.startswith("price_increase_14d_coins_info_")
    assert file_name.endswith(".csv")
    assert headers == ["symbol", "name", "website", "description", "market cap rank", "chains"]
    assert data == [
        ["BTC", "bitcoin", "https://bitcoin.org", "bitcoin description", 1, ["bitcoin"]],
        ["ETH", "ethereum", "https://ethereum.org", "ethereum description", 1, ["ethereum"]],
    ]


def test_send_coins_info_returns_when_every_binance_exchange_is_unmapped() -> None:
    tg_bot = utility.TelegramBot.__new__(utility.TelegramBot)

    with (
        patch.object(utility, "CoingeckoApi") as coingecko_api,
        patch.object(tg_bot, "send_data_as_csv_file") as send_csv,
    ):
        send_coins_info_to_telegram([BinanceExchange("NOMAP", "USDT")], tg_bot)

    coingecko_api.assert_not_called()
    send_csv.assert_not_called()
