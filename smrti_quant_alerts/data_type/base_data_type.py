from __future__ import annotations
from typing import Union, Optional
from dataclasses import dataclass


@dataclass
class Tick:
    symbol: TradingSymbol
    volume: float = 0.0
    open: float = 0.0
    close: float = 0.0
    high: Optional[float] = None
    low: Optional[float] = None
    timestamp: Optional[int] = None

    @property
    def amount(self) -> float:
        return self.close * self.volume


class TradingSymbol:
    def __init__(self, symbol: str) -> None:
        self._symbol = symbol.upper()

    def __repr__(self) -> str:
        return self._symbol

    def __str__(self) -> str:
        return self._symbol

    def __eq__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol == other._symbol
        elif isinstance(other, str):
            return self._symbol == other.upper()
        return False

    def __lt__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol < other._symbol
        elif isinstance(other, str):
            return self._symbol < other.upper()
        return False

    def __gt__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol > other._symbol
        elif isinstance(other, str):
            return self._symbol > other.upper()
        return False

    def __le__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol <= other._symbol
        elif isinstance(other, str):
            return self._symbol <= other.upper()
        return False

    def __ge__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol >= other._symbol
        elif isinstance(other, str):
            return self._symbol >= other.upper()
        return False

    def __hash__(self) -> int:
        return hash(self._symbol)

    def lower(self) -> str:
        return self._symbol.lower()

    def upper(self) -> str:
        return self._symbol

    def str(self) -> str:
        return self._symbol

    @staticmethod
    def get_symbol_object(symbol: str) -> Optional[TradingSymbol]:
        raise NotImplementedError

    @classmethod
    def type(cls) -> str:
        return cls.__name__
