class TradingSymbol:
    def __init__(self, symbol):
        self._symbol = symbol.upper()

    def __repr__(self):
        return self._symbol

    def __str__(self):
        return self._symbol

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._symbol == other._symbol
        elif isinstance(other, str):
            return self._symbol == other.upper()
        return False

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            return self._symbol < other._symbol
        elif isinstance(other, str):
            return self._symbol < other.upper()
        return False

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            return self._symbol > other._symbol
        elif isinstance(other, str):
            return self._symbol > other.upper()
        return False

    def __le__(self, other):
        if isinstance(other, self.__class__):
            return self._symbol <= other._symbol
        elif isinstance(other, str):
            return self._symbol <= other.upper()
        return False

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            return self._symbol >= other._symbol
        elif isinstance(other, str):
            return self._symbol >= other.upper()
        return False

    def __hash__(self):
        return hash(self._symbol)


class BinanceExchange(TradingSymbol):
    def __init__(self, base_symbol, quote_symbol):
        self.base_symbol = base_symbol.upper()
        self.quote_symbol = quote_symbol.upper()
        super().__init__(f"{self.base_symbol}{self.quote_symbol}")

    @property
    def exchange(self):
        return self._symbol

    @exchange.setter
    def exchange(self, value):
        self._symbol = value.upper()


class CoingeckoCoin(TradingSymbol):
    symbol_id_map = {}

    def __init__(self, coin_id, coin_symbol):
        coin_symbol = coin_symbol.upper()

        self.coin_id = coin_id
        super().__init__(coin_symbol)
        self.symbol_id_map[coin_symbol] = self.coin_id

    @property
    def coin_symbol(self):
        return self._symbol

    @coin_symbol.setter
    def coin_symbol(self, value):
        self._symbol = value.upper()

    @staticmethod
    def get_coingecko_coin(coin_symbol):
        if coin_symbol.upper() in CoingeckoCoin.symbol_id_map:
            coin_id = CoingeckoCoin.symbol_id_map[coin_symbol.upper()]
            return CoingeckoCoin(coin_id, coin_symbol)
        return None


class StockSymbol(TradingSymbol):
    def __init__(self, symbol, security_name=None, gics_sector=None,
                 gics_sub_industry=None, location=None, cik=None, founded_time=None):
        super().__init__(symbol.upper())

        self.security_name = security_name
        self.gics_sector = gics_sector
        self.gics_sub_industry = gics_sub_industry
        self.location = location
        self.cik = cik
        self.founded_time = founded_time

    @property
    def ticker(self):
        return self._symbol

    @ticker.setter
    def ticker(self, value):
        self._symbol = value.upper()


if __name__ == "__main__":
    be = BinanceExchange("BTC", "usdt")
    print(be)
    cc = CoingeckoCoin("bitcoin", "Btc")
    print(cc)
