import uuid
from typing import Union, List, Set, Optional

from smrti_quant_alerts.data_type import TradingSymbol, BinanceExchange, CoingeckoCoin
from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.stock_crypto_api import CoingeckoApi


def send_coins_info_to_telegram(coins: Union[List[TradingSymbol], Set[TradingSymbol]],
                                tg_bot: TelegramBot, file_name: Optional[str] = "") -> None:
    """
    alert coins info

    :param coins: coins
    :param tg_bot: telegram bot
    :param file_name: file name
    """
    if coins:
        coins = sorted(coins)

        file_name = f"{file_name}_coins_info_{uuid.uuid4()}.csv"
        headers = ["symbol", "name", "website", "description"]
        data = []
        for i, coin in enumerate(coins):
            if isinstance(coin, BinanceExchange):
                coins[i] = CoingeckoCoin.get_symbol_object(coin.base_symbol)
        coins = sorted(set(coins))
        cg = CoingeckoApi()
        for coin in coins:
            info = cg.get_coin_info(coin)
            data.append([info["symbol"], info["name"],
                         info["website"], info["description"]])
        tg_bot.send_data_as_csv_file(file_name, headers, data)
