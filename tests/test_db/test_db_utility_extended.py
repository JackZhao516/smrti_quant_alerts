"""Additional unit tests for the database utility helpers.

Every test runs against a temporary SQLite database created by the
``runtime_database`` fixture; no files in the repository are touched.
"""

from decimal import Decimal

from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.db import StockAlertDBUtils
from smrti_quant_alerts.db.utility import MACDAlertDBUtils


def _full_stock(ticker: str, name: str = "Test Corp") -> StockSymbol:
    return StockSymbol(ticker, name, "Technology", "Software", "Testville", "123", "2000")


def test_get_all_stocks_returns_symbols_from_every_alert_type(runtime_database) -> None:
    StockAlertDBUtils.add_stocks([StockSymbol("ZZFA")], "first_alert")
    StockAlertDBUtils.add_stocks([StockSymbol("ZZFB")], "second_alert")

    assert StockAlertDBUtils.get_all_stocks() == {StockSymbol("ZZFA"), StockSymbol("ZZFB")}


def test_add_stocks_ignores_empty_input(runtime_database) -> None:
    StockAlertDBUtils.add_stocks([])

    assert StockAlertDBUtils.get_all_stocks() == set()


def test_get_stocks_info_returns_empty_lists_for_no_input(runtime_database) -> None:
    assert StockAlertDBUtils.get_stocks_info([]) == ([], [])


def test_get_stocks_info_accepts_a_set(runtime_database) -> None:
    full = _full_stock("ZZFC")
    StockAlertDBUtils.add_stocks_info([full])

    with_info, without_info = StockAlertDBUtils.get_stocks_info({StockSymbol("ZZFC")})

    assert [stock.ticker for stock in with_info] == ["ZZFC"]
    assert without_info == []


def test_get_stocks_info_accepts_strings(runtime_database) -> None:
    full = _full_stock("ZZFD")
    StockAlertDBUtils.add_stocks_info([full])

    with_info, without_info = StockAlertDBUtils.get_stocks_info(["ZZFD", "ZZFE"])

    assert [stock.ticker for stock in with_info] == ["ZZFD"]
    assert [stock.ticker for stock in without_info] == ["ZZFE"]


def test_add_stocks_info_ignores_empty_input(runtime_database) -> None:
    StockAlertDBUtils.add_stocks_info([])

    with_info, without_info = StockAlertDBUtils.get_stocks_info([StockSymbol("ZZFF")])
    assert with_info == []
    assert [stock.ticker for stock in without_info] == ["ZZFF"]


def test_macd_last_week_value_round_trip(runtime_database) -> None:
    assert MACDAlertDBUtils.get_last_week_value("ZZLEFT", "ZZRIGHT") is None

    MACDAlertDBUtils.update_last_week_value("ZZLEFT", "ZZRIGHT", Decimal("1.25"))
    assert MACDAlertDBUtils.get_last_week_value("ZZLEFT", "ZZRIGHT") == Decimal("1.25")

    MACDAlertDBUtils.update_last_week_value("ZZLEFT", "ZZRIGHT", Decimal("2.5"))
    assert MACDAlertDBUtils.get_last_week_value("ZZLEFT", "ZZRIGHT") == Decimal("2.5")

    assert MACDAlertDBUtils.get_last_week_value("ZZOTHER", "ZZRIGHT") is None
