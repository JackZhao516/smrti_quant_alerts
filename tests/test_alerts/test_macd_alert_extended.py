"""Extended tests for the MACD comprehensive alert."""

import csv
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from smrti_quant_alerts.alerts.comprehensive_alerts import macd_alert
from smrti_quant_alerts.alerts.comprehensive_alerts.macd_alert import MACDAlert
from smrti_quant_alerts.data_type import BinanceExchange, StockSymbol
from smrti_quant_alerts.settings import Config

ALERT_NAME = "macd_alert_test"


def _make_alert(
    monkeypatch: pytest.MonkeyPatch,
    *,
    timeframe_list: list[str] | None = None,
    symbols_file: str = "",
    add_on_timeframe_list: list[str] | None = None,
    email: bool = False,
    xlsx: bool = False,
    stock_screener_alert_db_name: str | None = None,
) -> MACDAlert:
    """Construct a MACDAlert with all external API clients replaced by mocks."""
    Config.SETTINGS = {ALERT_NAME: {"database_name": ALERT_NAME}}
    monkeypatch.setattr(macd_alert, "StockApi", MagicMock)
    monkeypatch.setattr(macd_alert, "BinanceApi", MagicMock)
    monkeypatch.setattr(macd_alert, "EmailApi", MagicMock)
    alert = MACDAlert(
        alert_name=ALERT_NAME,
        timeframe_list=timeframe_list if timeframe_list is not None else ["1D"],
        symbols_file=symbols_file,
        add_on_timeframe_list=add_on_timeframe_list,
        email=email,
        stock_screener_alert_db_name=stock_screener_alert_db_name,
        xlsx=xlsx,
    )
    # Never let a test reach the real Telegram endpoints.
    alert._tg_bot = MagicMock()
    return alert


def test_parse_symbols_file_and_sectors(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    symbols_file = tmp_path / "symbols.csv"
    fieldnames = ["type_left", "symbol_left", "type_right", "symbol_right", "sector", "sub_sector", "name"]
    rows = [
        {
            "type_left": "StockSymbol",
            "symbol_left": "AAPL",
            "type_right": "StockSymbol",
            "symbol_right": "MSFT",
            "sector": "Tech",
            "sub_sector": "Software",
            "name": "Apple/Microsoft",
        },
        {
            "type_left": "BinanceExchange",
            "symbol_left": "BTC",
            "type_right": "BinanceExchange",
            "symbol_right": "ETH",
            "sector": "Crypto",
            "sub_sector": "",
            "name": "BTC/ETH",
        },
        {
            "type_left": "StockSymbol",
            "symbol_left": "GOOG",
            "type_right": "",
            "symbol_right": "",
            "sector": "Tech",
            "sub_sector": "Software",
            "name": "Alphabet",
        },
        {
            "type_left": "BinanceExchange",
            "symbol_left": "BNB",
            "type_right": "BinanceExchange",
            "symbol_right": "SOL",
            "sector": "Crypto",
            "sub_sector": "Layer1",
            "name": "BNB/SOL",
        },
    ]
    with symbols_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    alert = _make_alert(monkeypatch, symbols_file=str(symbols_file), timeframe_list=["1D", "2D"])

    aapl_pair = (StockSymbol("AAPL"), StockSymbol("MSFT"))
    btc_pair = (BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT"))
    goog_pair = (StockSymbol("GOOG"), None)
    bnb_pair = (BinanceExchange("BNB", "USDT"), BinanceExchange("SOL", "USDT"))

    assert alert._symbol_pairs == [aapl_pair, btc_pair, goog_pair, bnb_pair]
    assert alert._sectors["Tech"]["Software"] == [aapl_pair, goog_pair]
    assert alert._sectors["Crypto"][None] == [btc_pair]
    assert alert._sectors["Crypto"]["Layer1"] == [bnb_pair]
    assert alert._stock_pair_name[aapl_pair] == "Apple/Microsoft"
    assert alert._stock_pair_name[goog_pair] == "Alphabet"


def test_encode_symbol_pair() -> None:
    stock = StockSymbol("AAPL")
    crypto = BinanceExchange("BTC", "USDT")

    assert MACDAlert._encode_symbol_pair((stock, None)) == "AAPL"
    assert MACDAlert._encode_symbol_pair((stock, crypto)) == "AAPL/BTCUSDT"


def test_get_macd_for_stocks_or_cryptos_without_right_prices() -> None:
    left_prices = [(f"2024-01-{day:02d}", float(day)) for day in range(8, 0, -1)]

    result = MACDAlert._get_macd_for_stocks_or_cryptos(left_prices, [], timeframe="2D", num_of_macd=2)

    assert [date for date, _ in result] == ["2024-01-08", "2024-01-06"]
    assert len(result) == 2


def test_get_macd_for_stocks_or_cryptos_with_right_prices_and_zero() -> None:
    left_prices = [
        ("2024-01-05", 10.0),
        ("2024-01-04", 20.0),
        ("2024-01-03", 30.0),
        ("2024-01-02", 40.0),
    ]
    right_prices = [
        ("2024-01-05", 2.0),
        ("2024-01-04", 0.0),
        ("2024-01-03", 5.0),
        ("2024-01-02", 1.0),
    ]

    daily = MACDAlert._get_macd_for_stocks_or_cryptos(left_prices, right_prices, timeframe="1D", num_of_macd=10)
    every_other_day = MACDAlert._get_macd_for_stocks_or_cryptos(
        left_prices, right_prices, timeframe="2D", num_of_macd=10
    )

    # The zero right price on 2024-01-04 is skipped in both cases.
    assert [date for date, _ in daily] == ["2024-01-05", "2024-01-03", "2024-01-02"]
    assert [date for date, _ in every_other_day] == ["2024-01-05", "2024-01-03"]


def test_enrich_close_prices_with_previous_day_price() -> None:
    assert MACDAlert._enrich_close_prices_with_previous_day_price([]) == []

    contiguous = [
        ("2024-01-03", 3.0),
        ("2024-01-02", 2.0),
        ("2024-01-01", 1.0),
    ]
    assert MACDAlert._enrich_close_prices_with_previous_day_price(contiguous) == contiguous

    weekend_gap = [("2024-01-08", 80.0), ("2024-01-05", 50.0)]
    assert MACDAlert._enrich_close_prices_with_previous_day_price(weekend_gap) == [
        ("2024-01-08", 80.0),
        ("2024-01-07", 50.0),
        ("2024-01-06", 50.0),
        ("2024-01-05", 50.0),
    ]


def test_enrich_close_prices_with_second_ticker() -> None:
    left_prices = [
        ("2024-01-03", 3.0),
        ("2024-01-02", 2.0),
        ("2024-01-01", 1.0),
    ]

    # Equal dates are consumed together; a trailing left date is appended as-is.
    assert (
        MACDAlert._enrich_close_prices_with_previous_day_price_and_second_ticker(left_prices, [("2024-01-02", 20.0)])
        == left_prices
    )

    # A right date earlier than the current left date is inserted using the left price.
    assert MACDAlert._enrich_close_prices_with_previous_day_price_and_second_ticker(
        [("2024-01-02", 2.0)],
        [("2024-01-03", 30.0), ("2024-01-02", 20.0)],
    ) == [("2024-01-03", 2.0), ("2024-01-02", 2.0)]


def test_generate_xlsx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    file_path = MACDAlert._generate_xlsx(
        "AAPL/MSFT",
        {
            "1D": [("2024-01-02", 1.5)],
            "2D": [("2024-01-02", -0.5)],
        },
    )

    assert Path(file_path).exists()
    assert file_path.startswith("AAPL_MSFT_")
    with pd.ExcelFile(file_path) as excel_file:
        assert set(excel_file.sheet_names) == {"1D", "2D"}
        daily = pd.read_excel(excel_file, sheet_name="1D")
    assert list(daily.columns) == ["date", "macd"]
    assert daily.iloc[0].tolist() == ["2024-01-02", 1.5]


def test_process_timeframe_for_changed_macd_without_add_on(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alert = _make_alert(monkeypatch)
    symbol_pair = (StockSymbol("AAPL"), None)

    result = alert._process_timeframe_for_changed_macd(symbol_pair, ["2D"], ["1D", "2D"], ["3D"])
    empty_result = alert._process_timeframe_for_changed_macd(symbol_pair, ["1D", "2D"], ["1D", "2D"], [])

    assert result == "[1D+] [3D-]"
    assert empty_result == " "


def test_process_timeframe_for_changed_macd_with_add_on(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alert = _make_alert(monkeypatch, add_on_timeframe_list=["1W", "1M", "3D", "2W", "5D"])
    symbol_pair = (StockSymbol("AAPL"), None)
    add_on_macd = {
        "AAPL": {
            "1W": [("2024-01-01", 0.5)],
            "1M": [("2024-01-01", -0.5)],
            "3D": [("2024-01-01", float("nan"))],
            "2W": [],
            "5D": [("2024-01-01", 0.1)],
        }
    }
    monkeypatch.setattr(alert, "_get_past_number_of_macd", MagicMock(return_value=add_on_macd))

    result = alert._process_timeframe_for_changed_macd(symbol_pair, ["1W"], ["2D"], [])

    assert "2D" in result
    assert "5D" in result
    assert "1M" in result
    # 1W is excluded because it changed, and empty/NaN series are skipped.
    assert "1W" not in result
    assert "3D" not in result
    assert "2W" not in result


def test_generate_individual_symbol_xlsx_content(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch, timeframe_list=["1D", "2D", "3D", "1W"])
    symbol_pair = (StockSymbol("AAPL"), None)
    alert._stock_pair_name[symbol_pair] = "Apple Inc"
    macd_dict = {
        "AAPL": {
            "1D": [("2024-01-04", -1.0), ("2024-01-03", 2.0)],
            "2D": [("2024-01-04", 2.0), ("2024-01-03", -1.0)],
            "3D": [("2024-01-04", 1.0)],
            "1W": [],
        }
    }
    rising_to_falling: list[str] = []
    falling_to_rising: list[str] = []

    result = alert._generate_individual_symbol_xlsx_content(
        symbol_pair, rising_to_falling, falling_to_rising, macd_dict
    )

    assert result[0] == "AAPL * *"
    assert result[1] == "2.0 to -1.0"
    assert result[2] == "-1.0 to 2.0"
    assert result[3] == "No enough data to calculate MACD"
    assert result[4] == "No enough data to calculate MACD"
    assert len(rising_to_falling) == 1
    assert "AAPL" in rising_to_falling[0]
    assert "Apple Inc" in rising_to_falling[0]
    assert "2D" in rising_to_falling[0]
    assert "3D" in rising_to_falling[0]
    # The changed timeframe only appears in the bullet list, not the positive set.
    assert "1D+" not in rising_to_falling[0]
    assert len(falling_to_rising) == 1
    assert "1D" in falling_to_rising[0]
    assert "3D" in falling_to_rising[0]
    assert "1W" in falling_to_rising[0]


def test_generate_individual_symbol_xlsx_content_with_add_on(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alert = _make_alert(monkeypatch, timeframe_list=["1D"], add_on_timeframe_list=["1W"])
    symbol_pair = (StockSymbol("AAPL"), None)
    macd_dict = {"AAPL": {"1D": [("2024-01-04", -1.0), ("2024-01-03", 1.0)]}}
    monkeypatch.setattr(
        alert,
        "_get_past_number_of_macd",
        MagicMock(return_value={"AAPL": {"1W": [("2024-01-01", -2.0)]}}),
    )
    rising_to_falling: list[str] = []
    falling_to_rising: list[str] = []

    alert._generate_individual_symbol_xlsx_content(symbol_pair, rising_to_falling, falling_to_rising, macd_dict)

    assert len(rising_to_falling) == 1
    assert "1W" in rising_to_falling[0]
    assert falling_to_rising == []


def test_generate_email_content(runtime_database: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    alert = _make_alert(monkeypatch, timeframe_list=["1D"])
    aapl_pair = (StockSymbol("AAPL"), None)
    msft_pair = (StockSymbol("MSFT"), None)
    btc_pair = (BinanceExchange("BTC", "USDT"), None)
    alert._stock_pair_name[aapl_pair] = "Apple"
    alert._stock_pair_name[msft_pair] = "Microsoft"
    alert._stock_pair_name[btc_pair] = "Bitcoin"
    alert._sectors = {"Tech": {"Software": [aapl_pair, msft_pair], None: [btc_pair]}}
    macd_dict = {
        "AAPL": {"1D": [("2024-01-04", -1.0), ("2024-01-03", 2.0)]},
        "MSFT": {"1D": [("2024-01-04", 1.0), ("2024-01-03", 2.0)]},
        "BTCUSDT": {"1D": [("2024-01-04", 2.0), ("2024-01-03", -1.0)]},
    }

    content, file_path = alert._generate_email_content(macd_dict)

    assert Path(file_path).exists()
    assert "<b>Summary</b>" in content
    assert "Rising to Falling" in content
    assert "Falling to Rising" in content
    assert "AAPL" in content
    assert "BTCUSDT" in content
    with pd.ExcelFile(file_path) as excel_file:
        assert set(excel_file.sheet_names) == {"Software", "others"}
        software = pd.read_excel(excel_file, sheet_name="Software", header=None)
        others = pd.read_excel(excel_file, sheet_name="others", header=None)
    assert "Apple" in software.astype(str).values.flatten().tolist()
    assert "Bitcoin" in others.astype(str).values.flatten().tolist()


def test_generate_email_content_with_empty_sub_sector(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    alert = _make_alert(monkeypatch, timeframe_list=["1D"])
    symbol_pair = (StockSymbol("AAPL"), None)
    alert._sectors = {"Tech": {"": [symbol_pair]}}
    macd_dict = {"AAPL": {"1D": [("2024-01-04", 1.0), ("2024-01-03", 2.0)]}}

    content, file_path = alert._generate_email_content(macd_dict)

    assert Path(file_path).exists()
    assert "<b>Summary</b>" in content
    with pd.ExcelFile(file_path) as excel_file:
        assert excel_file.sheet_names == ["others"]


def test_get_past_number_of_macd(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)
    stock_pair = (StockSymbol("AAPL"), None)
    crypto_pair = (BinanceExchange("BTC", "USDT"), None)
    left_right_mock = MagicMock(return_value=([], []))
    macd_mock = MagicMock(return_value=[("2024-01-01", 0.5)])
    monkeypatch.setattr(alert, "_get_left_right_close_prices", left_right_mock)
    monkeypatch.setattr(alert, "_get_macd_for_stocks_or_cryptos", macd_mock)

    result = alert._get_past_number_of_macd([stock_pair, crypto_pair], ["1D", "1W"], num_of_macd=3)

    assert set(result) == {"AAPL", "BTCUSDT"}
    assert set(result["AAPL"]) == {"1D", "1W"}
    assert result["BTCUSDT"]["1D"] == [("2024-01-01", 0.5)]
    assert left_right_mock.call_count == 4
    assert macd_mock.call_count == 4
    assert macd_mock.call_args_list[0] == call([], [], "1D", 3)


def test_get_left_right_close_prices_stock_to_stock(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)
    left_prices = [("2024-01-03", 30.0), ("2024-01-02", 20.0), ("2024-01-01", 10.0)]
    right_prices = [("2024-01-03", 3.0), ("2024-01-02", 2.0), ("2024-01-01", 1.0)]
    prices = {"AAPL": left_prices, "MSFT": right_prices}
    alert._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks.side_effect = (
        lambda symbol, timeframe, num_of_ticks: prices[str(symbol)]
    )

    left_result, right_result = alert._get_left_right_close_prices((StockSymbol("AAPL"), StockSymbol("MSFT")), "1D")

    assert (left_result, right_result) == (left_prices, right_prices)
    assert alert._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks.call_count == 2
    for stock_call in alert._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks.call_args_list:
        assert stock_call.args[1:] == ("1D", 200)


def test_get_left_right_close_prices_stock_without_right_symbol(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alert = _make_alert(monkeypatch)
    left_prices = [("2024-01-02", 20.0), ("2024-01-01", 10.0)]
    alert._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks.return_value = left_prices

    left_result, right_result = alert._get_left_right_close_prices((StockSymbol("AAPL"), None), "1W")

    assert left_result == left_prices
    assert right_result == []
    alert._binance_api.get_exchange_close_price_on_timestamp.assert_not_called()


def test_get_left_right_close_prices_stock_to_binance(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)
    left_prices = [("2024-01-03", 30.0), ("2024-01-02", 20.0), ("2024-01-01", 10.0)]
    alert._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks.return_value = left_prices
    alert._binance_api.get_exchange_close_price_on_timestamp.side_effect = [2.0, 0.0]
    monkeypatch.setattr(macd_alert, "get_stock_market_close_timestamp_from_date", lambda date: 1_000_000)

    left_result, right_result = alert._get_left_right_close_prices(
        (StockSymbol("AAPL"), BinanceExchange("BTC", "USDT")), "1D"
    )

    assert left_result == left_prices
    # The second Binance price is zero, so it is dropped and iteration stops.
    assert right_result == [("2024-01-03", 2.0)]
    assert alert._binance_api.get_exchange_close_price_on_timestamp.call_args_list[0] == call(
        BinanceExchange("BTC", "USDT"), 940_000
    )


def test_get_left_right_close_prices_binance_to_stock(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)
    right_prices = [("2024-01-03", 30.0), ("2024-01-02", 20.0), ("2024-01-01", 10.0)]
    alert._stock_api.get_stock_close_prices_by_timeframe_num_of_ticks.return_value = right_prices
    alert._binance_api.get_exchange_close_price_on_timestamp.side_effect = [5.0, 0.0]
    monkeypatch.setattr(macd_alert, "get_stock_market_close_timestamp_from_date", lambda date: 2_000_000)

    left_result, right_result = alert._get_left_right_close_prices(
        (BinanceExchange("BTC", "USDT"), StockSymbol("AAPL")), "1D"
    )

    assert right_result == right_prices
    # The second Binance price is zero, so it is dropped and iteration stops.
    assert left_result == [("2024-01-03", 5.0)]
    assert alert._binance_api.get_exchange_close_price_on_timestamp.call_args_list[0] == call(
        BinanceExchange("BTC", "USDT"), 1_940_000
    )


def test_get_left_right_close_prices_binance_to_binance(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alert = _make_alert(monkeypatch)
    left_prices = [("2024-01-03", 30.0), ("2024-01-02", 20.0)]
    right_prices = [("2024-01-03", 3.0), ("2024-01-02", 2.0)]
    prices = {"BTCUSDT": left_prices, "ETHUSDT": right_prices}
    alert._binance_api.get_exchange_close_prices_by_timeframe_num_of_ticks.side_effect = (
        lambda exchange, timeframe, num_of_ticks: prices[str(exchange)]
    )

    left_result, right_result = alert._get_left_right_close_prices(
        (BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")), "2W"
    )

    assert (left_result, right_result) == (left_prices, right_prices)
    assert alert._binance_api.get_exchange_close_prices_by_timeframe_num_of_ticks.call_count == 2
    for exchange_call in alert._binance_api.get_exchange_close_prices_by_timeframe_num_of_ticks.call_args_list:
        assert exchange_call.args[1:] == ("2W", 400)


def test_get_stock_screener_alert_results_empty(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)

    assert alert._get_stock_screener_alert_results("") == []


def test_get_stock_screener_alert_results_success(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)
    stock1 = StockSymbol("AAPL", gics_sector="Tech")
    stock2 = StockSymbol("MSFT", gics_sector="Tech")
    stock3 = StockSymbol("NVDA", gics_sector="Chips")
    alert._stock_api.get_stock_info.return_value = [stock1, stock2, stock3]
    with (
        patch.object(macd_alert, "StockAlertDBUtils") as db_utils,
        patch.object(macd_alert, "close_database") as close_database,
        patch.object(macd_alert, "init_database_runtime") as init_database,
    ):
        db_utils.get_all_stocks.return_value = {stock1, stock2, stock3}

        result = alert._get_stock_screener_alert_results("screener.db")

    assert result == [(stock1, None), (stock2, None), (stock3, None)]
    assert alert._sectors["share"]["Tech"] == [(stock1, None), (stock2, None)]
    assert alert._sectors["share"]["Chips"] == [(stock3, None)]
    assert close_database.call_count == 2
    assert init_database.call_args_list == [call("screener.db"), call(f"{ALERT_NAME}.db")]


def test_get_stock_screener_alert_results_exception(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    alert = _make_alert(monkeypatch)
    with (
        patch.object(macd_alert, "StockAlertDBUtils") as db_utils,
        patch.object(macd_alert, "close_database"),
        patch.object(macd_alert, "init_database_runtime"),
    ):
        db_utils.get_all_stocks.side_effect = RuntimeError("database unavailable")

        result = alert._get_stock_screener_alert_results("screener.db")

    assert result == []


def test_constructor_uses_stock_screener_symbols(runtime_database: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    symbol_pair = (StockSymbol("AAPL"), None)
    with patch.object(MACDAlert, "_get_stock_screener_alert_results", return_value=[symbol_pair]) as screener_mock:
        alert = _make_alert(monkeypatch, stock_screener_alert_db_name="screener")

    screener_mock.assert_called_once_with("screener.db")
    assert alert._symbol_pairs == [symbol_pair]
    assert alert._use_stock_screener_symbols is True


def _prepare_run(alert: MACDAlert, monkeypatch: pytest.MonkeyPatch, email_file: Path) -> tuple[MagicMock, MagicMock]:
    """Patch the expensive parts of ``run`` and return the send/remove mocks."""
    email_file.write_text("xlsx")
    monkeypatch.setattr(
        alert,
        "_get_past_number_of_macd",
        MagicMock(return_value={"AAPL": {"1D": [("2024-01-01", 1.0)]}}),
    )
    monkeypatch.setattr(
        alert,
        "_generate_email_content",
        MagicMock(return_value=("<b>Summary</b>", str(email_file))),
    )
    remove_mock = MagicMock()
    monkeypatch.setattr(macd_alert.os, "remove", remove_mock)
    return alert._tg_bot, remove_mock


def test_run_with_email_and_xlsx(runtime_database: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    alert = _make_alert(monkeypatch, email=True, xlsx=True)
    alert._symbol_pairs = [(StockSymbol("AAPL"), None)]
    email_file = tmp_path / "email.xlsx"
    telegram_mock, remove_mock = _prepare_run(alert, monkeypatch, email_file)
    monkeypatch.setattr(alert, "_generate_xlsx", MagicMock(return_value="AAPL.xlsx"))

    alert.run()

    telegram_mock.send_message.assert_has_calls([call("MACD values for ['AAPL']"), call("<b>Summary</b>")])
    telegram_mock.send_file.assert_has_calls([call("AAPL.xlsx", "AAPL.xlsx"), call(str(email_file), str(email_file))])
    assert alert._excel_file_paths == ["AAPL.xlsx", str(email_file)]
    alert._email_api.send_email.assert_called_once_with(
        f"Pair {ALERT_NAME}",
        "<b>Summary</b>",
        [],
        ["AAPL.xlsx", str(email_file)],
        user_html=True,
    )
    assert remove_mock.call_args_list == [call("AAPL.xlsx"), call(str(email_file))]


def test_run_without_email_or_xlsx(runtime_database: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    alert = _make_alert(monkeypatch)
    email_file = tmp_path / "email.xlsx"
    telegram_mock, remove_mock = _prepare_run(alert, monkeypatch, email_file)
    generate_xlsx_mock = MagicMock()
    monkeypatch.setattr(alert, "_generate_xlsx", generate_xlsx_mock)

    alert.run()

    generate_xlsx_mock.assert_not_called()
    alert._email_api.send_email.assert_not_called()
    assert alert._excel_file_paths == [str(email_file)]
    telegram_mock.send_file.assert_called_once_with(str(email_file), str(email_file))
    remove_mock.assert_called_once_with(str(email_file))


def test_run_with_stock_screener_symbols_omits_pair_prefix(
    runtime_database: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with patch.object(MACDAlert, "_get_stock_screener_alert_results", return_value=[]):
        alert = _make_alert(monkeypatch, email=True, stock_screener_alert_db_name="screener")
    email_file = tmp_path / "email.xlsx"
    _prepare_run(alert, monkeypatch, email_file)

    alert.run()

    alert._email_api.send_email.assert_called_once_with(
        ALERT_NAME,
        "<b>Summary</b>",
        [],
        [str(email_file)],
        user_html=True,
    )
