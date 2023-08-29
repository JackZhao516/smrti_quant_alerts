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
        return False

    def __hash__(self):
        return hash(self.exchange)


class CoingeckoCoin:
    def __init__(self, coin_id, coin_symbol):
        self.coin_id = coin_id
        self.coin_symbol = coin_symbol.upper()

    def __repr__(self):
        return self.coin_symbol

    def __str__(self):
        return self.coin_symbol

    def __eq__(self, other):
        if isinstance(other, CoingeckoCoin):
            return self.coin_symbol == other.coin_symbol
        return False

    def __hash__(self):
        return hash(self.coin_symbol)


if __name__ == "__main__":
    be = BinanceExchange("BTC", "usdt")
    print(be)
    cc = CoingeckoCoin("bitcoin", "Btc")
    print(cc)
