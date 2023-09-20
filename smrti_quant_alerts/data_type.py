class BinanceExchange:
    def __init__(self, base_symbol, quote_symbol):
        self.base_symbol = base_symbol.upper()
        self.quote_symbol = quote_symbol.upper()
        self.exchange = f"{self.base_symbol}{self.quote_symbol}"

    def __repr__(self):
        return self.exchange

    def __str__(self):
        return self.exchange

    def __eq__(self, other):
        if isinstance(other, BinanceExchange):
            return self.exchange == other.exchange
        elif isinstance(other, str):
            return self.exchange == other.upper()
        return False

    def __lt__(self, other):
        if isinstance(other, BinanceExchange):
            return self.exchange < other.exchange
        elif isinstance(other, str):
            return self.exchange < other.upper()
        return False

    def __gt__(self, other):
        if isinstance(other, BinanceExchange):
            return self.exchange > other.exchange
        elif isinstance(other, str):
            return self.exchange > other.upper()
        return False

    def __le__(self, other):
        if isinstance(other, BinanceExchange):
            return self.exchange <= other.exchange
        elif isinstance(other, str):
            return self.exchange <= other.upper()
        return False

    def __ge__(self, other):
        if isinstance(other, BinanceExchange):
            return self.exchange >= other.exchange
        elif isinstance(other, str):
            return self.exchange >= other.upper()
        return False

    def __hash__(self):
        return hash(self.exchange)


class CoingeckoCoin:
    symbol_id_map = {}

    def __init__(self, coin_id, coin_symbol):
        self.coin_id = coin_id
        self.coin_symbol = coin_symbol.upper()
        self.symbol_id_map[self.coin_symbol] = self.coin_id

    def __repr__(self):
        return self.coin_symbol

    def __str__(self):
        return self.coin_symbol

    def __eq__(self, other):
        if isinstance(other, CoingeckoCoin):
            return self.coin_symbol == other.coin_symbol
        elif isinstance(other, str):
            return self.coin_symbol == other.upper()
        return False

    def __lt__(self, other):
        if isinstance(other, CoingeckoCoin):
            return self.coin_symbol < other.coin_symbol
        elif isinstance(other, str):
            return self.coin_symbol < other.upper()
        return False

    def __gt__(self, other):
        if isinstance(other, CoingeckoCoin):
            return self.coin_symbol > other.coin_symbol
        elif isinstance(other, str):
            return self.coin_symbol > other.upper()
        return False

    def __le__(self, other):
        if isinstance(other, CoingeckoCoin):
            return self.coin_symbol <= other.coin_symbol
        elif isinstance(other, str):
            return self.coin_symbol <= other.upper()
        return False

    def __ge__(self, other):
        if isinstance(other, CoingeckoCoin):
            return self.coin_symbol >= other.coin_symbol
        elif isinstance(other, str):
            return self.coin_symbol >= other.upper()
        return False

    def __hash__(self):
        return hash(self.coin_symbol)

    @staticmethod
    def get_coingecko_coin(coin_symbol):
        if coin_symbol.upper() in CoingeckoCoin.symbol_id_map:
            coin_id = CoingeckoCoin.symbol_id_map[coin_symbol.upper()]
            return CoingeckoCoin(coin_id, coin_symbol)
        return None


if __name__ == "__main__":
    be = BinanceExchange("BTC", "usdt")
    print(be)
    cc = CoingeckoCoin("bitcoin", "Btc")
    print(cc)
