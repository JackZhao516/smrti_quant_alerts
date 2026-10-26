import csv
import logging
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from smrti_quant_alerts.alerts import base_alert as base_alert_module
from smrti_quant_alerts.alerts.stock_alerts import stock_price_top_performer_alert as alert_module
from smrti_quant_alerts.alerts.stock_alerts.stock_price_top_performer_alert import StockPriceTopPerformerAlert
from smrti_quant_alerts.data_type import FinancialMetricType, FinancialMetricsData, StockSymbol
from smrti_quant_alerts.db import StockAlertDBUtils
from smrti_quant_alerts.settings import Config

ALERT_NAME = "stock_alert"

HEADER = [
    "Symbol",
    "Name",
    "GICS Sector",
    "Sub Sector",
    "Headquarter Location",
    "Founded Year/IPO Date",
    "Is SP500",
    "Is Nasdaq",
    "Is NYSE",
    "Is Newly Added",
    "Timeframe Alerted",
    "Free Cash Flow",
    "Net Income",
    "Free Cash Flow Margin",
    "Revenue 1Y CAGR",
    "Revenue 3Y CAGR",
    "Revenue 5Y CAGR",
    "One Day Volume",
    "Market Cap",
    "Close > 4H SMA200",
    "Close > 1D SMA200",
]


def _stock(ticker: str, name: str = "Test Corp", *, sp500: bool = False, nasdaq: bool = False, nyse: bool = False):
    """Build a StockSymbol with complete stock info."""
    return StockSymbol(
        ticker,
        name,
        "Technology",
        "Software",
        "New York",
        f"CIK-{ticker}",
        "2000",
        sp500=sp500,
        nasdaq=nasdaq,
        nyse=nyse,
    )


def _stats(fcf: float = 1.0, net_income: float = 2.0, fcf_margin: float = 0.1, revenue: float = 3.0):
    """Build the dict returned inside get_stocks_stats_by_num_of_timeframe."""
    return {
        FinancialMetricType.FREE_CASH_FLOW: FinancialMetricsData(fcf),
        FinancialMetricType.NET_INCOME: FinancialMetricsData(net_income),
        FinancialMetricType.FREE_CASH_FLOW_MARGIN: FinancialMetricsData(fcf_margin, has_percentage=True),
        FinancialMetricType.REVENUE: FinancialMetricsData(revenue),
    }


def _cagr(one_year: float = 0.1, three_year: float = 0.2, five_year: float = 0.3):
    return {
        FinancialMetricType.REVENUE_1Y_CAGR: FinancialMetricsData(one_year, has_percentage=True),
        FinancialMetricType.REVENUE_3Y_CAGR: FinancialMetricsData(three_year, has_percentage=True),
        FinancialMetricType.REVENUE_5Y_CAGR: FinancialMetricsData(five_year, has_percentage=True),
    }


def _growth(score: float):
    return {FinancialMetricType.GROWTH_SCORE: FinancialMetricsData(score, has_percentage=True)}


def _prepare_send_data(alert: StockPriceTopPerformerAlert):
    """Configure all stock lookups used by send_stocks_info_as_csv."""
    first = _stock("SND1", "Sender One")
    second = _stock("SND2", "Sender Two")
    stock_stats_list = {first: [_stats()], second: []}
    revenue_cagr = {first: _cagr(), second: _cagr(0.0, 0.0, 0.0)}
    growth_score = {first: _growth(0.9), second: _growth(0.1)}
    sma_data = {first: {"4hour": True, "1day": True}, second: {"1day": True}}
    market_caps = {first: FinancialMetricsData(1000), second: FinancialMetricsData(2000)}

    alert.get_stocks_stats_by_num_of_timeframe = MagicMock(return_value=stock_stats_list)
    alert.get_stocks_revenue_cagr = MagicMock(return_value=revenue_cagr)
    alert.get_stocks_growth_score = MagicMock(return_value=growth_score)
    alert.get_close_price_sma_status = MagicMock(return_value=sma_data)
    alert.get_stocks_market_cap = MagicMock(return_value=market_caps)
    alert._daily_volume = {first: Decimal("1234")}
    return first, second, stock_stats_list


@pytest.fixture
def alert(runtime_database, monkeypatch):
    """Build an alert with all external services and database seams mocked."""
    monkeypatch.setattr(alert_module, "EmailApi", MagicMock)
    monkeypatch.setattr(alert_module, "LLMAPI", MagicMock)
    monkeypatch.setattr(alert_module, "PDFApi", MagicMock)
    monkeypatch.setattr(base_alert_module, "TelegramBot", MagicMock)
    monkeypatch.setattr(alert_module, "close_database", MagicMock())
    monkeypatch.setattr(alert_module, "init_database_runtime", MagicMock())
    monkeypatch.setattr(StockAlertDBUtils, "get_all_stocks", MagicMock(return_value=set()))

    Config.TOKENS = {
        "TELEGRAMBOT": {"TOKEN": "token", "TELEGRAM_IDS": {"TEST": "chat"}},
        "FMP_API_KEY": "fmp-key",
        "EODHD_API_KEY": "eodhd-key",
    }
    Config.SETTINGS = {ALERT_NAME: {"database_name": ALERT_NAME}}
    Config.IS_SETUP = True

    return StockPriceTopPerformerAlert(
        ALERT_NAME,
        tg_type="TEST",
        timeframe_list=["1D"],
        email=False,
        stock_screener_alert_db_name="",
    )


# ----------------- constructor -----------------
def test_constructor_uses_default_timeframes(alert):
    default_alert = StockPriceTopPerformerAlert(
        ALERT_NAME,
        tg_type="TEST",
        timeframe_list=None,
        email=False,
        stock_screener_alert_db_name="",
    )

    assert default_alert._timeframe_list == ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]


# ----------------- stock screener results -----------------
def test_get_stock_screener_alert_results_empty_name(alert, monkeypatch):
    close_database = MagicMock()
    init_database_runtime = MagicMock()
    get_all_stocks = MagicMock()
    monkeypatch.setattr(alert_module, "close_database", close_database)
    monkeypatch.setattr(alert_module, "init_database_runtime", init_database_runtime)
    monkeypatch.setattr(StockAlertDBUtils, "get_all_stocks", get_all_stocks)

    assert alert._get_stock_screener_alert_results("") == set()
    assert alert._get_stock_screener_alert_results(None) == set()
    close_database.assert_not_called()
    init_database_runtime.assert_not_called()
    get_all_stocks.assert_not_called()


def test_get_stock_screener_alert_results_success(alert, monkeypatch):
    stock = _stock("SCR1")
    close_database = MagicMock()
    init_database_runtime = MagicMock()
    get_all_stocks = MagicMock(return_value=[stock])
    monkeypatch.setattr(alert_module, "close_database", close_database)
    monkeypatch.setattr(alert_module, "init_database_runtime", init_database_runtime)
    monkeypatch.setattr(StockAlertDBUtils, "get_all_stocks", get_all_stocks)

    result = alert._get_stock_screener_alert_results("stock_screener.db")

    assert result == {stock}
    assert init_database_runtime.call_args_list == [call("stock_screener.db"), call("stock_alert.db")]
    assert close_database.call_count == 2
    get_all_stocks.assert_called_once_with()


def test_get_stock_screener_alert_results_exception(alert, monkeypatch, caplog):
    init_database_runtime = MagicMock(side_effect=RuntimeError("db unavailable"))
    monkeypatch.setattr(alert_module, "init_database_runtime", init_database_runtime)

    with caplog.at_level(logging.ERROR):
        assert alert._get_stock_screener_alert_results("stock_screener.db") == set()

    assert "Failed to get stock screener alert results: db unavailable" in caplog.text


# ----------------- send stocks info as csv -----------------
def test_send_stocks_info_as_csv_without_email(alert, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    first, second, _ = _prepare_send_data(alert)
    alert._stock_screener_alert_stocks = {first}
    alert.get_stocks_ai_analysis_for_stock_screener_alert_intersection = MagicMock(return_value="screener.pdf")

    alert.send_stocks_info_as_csv(
        {first: True, second: False},
        {"1Y": [first], "6M": [first], "1D": [second]},
        "email body",
    )

    alert.get_stocks_stats_by_num_of_timeframe.assert_called_once_with([first, second], "semi", 1)
    alert.get_close_price_sma_status.assert_called_once_with([first, second], [200, 200], ["4hour", "1day"])
    alert.get_stocks_revenue_cagr.assert_called_once_with([first, second])
    alert.get_stocks_growth_score.assert_called_once_with([first, second])
    alert.get_stocks_market_cap.assert_called_once_with([first, second])

    alert._tg_bot.send_data_as_csv_file.assert_called_once()
    csv_file_name = alert._tg_bot.send_data_as_csv_file.call_args.args[0]
    data = alert._tg_bot.send_data_as_csv_file.call_args.kwargs["data"]

    assert csv_file_name.endswith(".csv")
    assert alert._tg_bot.send_data_as_csv_file.call_args.kwargs["headers"] == HEADER
    assert data[0][0] == "SND1 *"
    assert data[0][1] == "Sender One"
    assert data[0][9] is True
    assert data[0][10] == ["1Y", "6M"]
    assert data[0][11] == FinancialMetricsData(1.0)
    assert data[0][12] == FinancialMetricsData(2.0)
    assert data[0][17] == FinancialMetricsData(0.9, has_percentage=True)
    assert data[0][18] == Decimal("1234")
    assert data[0][19] == FinancialMetricsData(1000)
    assert data[0][20] is True
    assert data[0][21] is True

    assert data[1][0] == "SND2"
    assert data[1][9] is False
    assert data[1][10] == ["1D"]
    # Empty stats -> default FinancialMetricsData values.
    assert data[1][11] == FinancialMetricsData(0)
    assert data[1][12] == FinancialMetricsData(0)
    assert data[1][13] == FinancialMetricsData(0)
    assert data[1][18] == 0
    assert data[1][19] == FinancialMetricsData(2000)
    # Missing 4hour SMA -> fallback message.
    assert data[1][20] == "SMA Data Unavailable"
    assert data[1][21] is True

    alert._email_api.send_email.assert_not_called()
    assert not Path(csv_file_name).exists()


def test_send_stocks_info_as_csv_with_ai_analysis_and_email(alert, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    first, second, _ = _prepare_send_data(alert)
    alert._stock_screener_alert_stocks = {second}
    alert._time_frame_sma_filter_ai_analysis = True
    alert._newly_added_stock_ai_analysis = True
    alert._growth_score_filter_ai_analysis = True
    alert._send_email = True

    pdf_names = ["timeframe_sma.pdf", "newly_added.pdf", "growth_score.pdf", "screener.pdf"]
    alert.get_stocks_ai_analysis_for_timeframe_sma = MagicMock(return_value=pdf_names[0])
    alert.get_stocks_ai_analysis_for_newly_added = MagicMock(return_value=pdf_names[1])
    alert.get_stocks_ai_analysis_for_growth_score = MagicMock(return_value=pdf_names[2])
    alert.get_stocks_ai_analysis_for_stock_screener_alert_intersection = MagicMock(return_value=pdf_names[3])
    for pdf_name in pdf_names:
        Path(pdf_name).write_text("pdf", encoding="utf-8")

    captured = {}

    def _capture_email(subject, body, csv_file_names, pdf_files):
        captured["subject"] = subject
        captured["body"] = body
        captured["csv"] = Path(csv_file_names[0]).read_text(encoding="utf-8")
        captured["csv_file_name"] = csv_file_names[0]
        captured["pdfs"] = list(pdf_files)

    alert._email_api.send_email.side_effect = _capture_email

    alert.send_stocks_info_as_csv(
        {first: True, second: False},
        {"1Y": [first], "6M": [first], "1D": [second]},
        "email body",
    )

    timeframe_args = alert.get_stocks_ai_analysis_for_timeframe_sma.call_args.args
    assert timeframe_args[0] == {first: ["1Y", "6M"]}
    alert.get_stocks_ai_analysis_for_newly_added.assert_called_once()
    alert.get_stocks_ai_analysis_for_growth_score.assert_called_once()
    alert.get_stocks_ai_analysis_for_stock_screener_alert_intersection.assert_called_once()

    assert alert._tg_bot.send_file.call_args_list == [
        call("timeframe_sma.pdf", "Stock AI Analysis With Timeframe SMA Filter.pdf"),
        call("newly_added.pdf", "Newly Added Stock AI Analysis.pdf"),
        call("growth_score.pdf", "Stock AI Analysis With Growth Score Filter.pdf"),
        call("screener.pdf", "Stock AI Analysis With Stock Screener Alert Filter.pdf"),
    ]

    alert._email_api.send_email.assert_called_once()
    assert captured["subject"] == "Weekly Stock Alert with Daily Volume Threshold: 0"
    assert captured["body"] == "email body"
    assert captured["pdfs"] == pdf_names

    csv_rows = list(csv.reader(captured["csv"].splitlines()))
    assert csv_rows[0] == HEADER
    assert csv_rows[1][0] == "SND1"
    assert csv_rows[2][0] == "SND2 *"
    assert csv_rows[1][9] == "True"
    assert "SMA Data Unavailable" in captured["csv"]

    assert not Path(captured["csv_file_name"]).exists()
    for pdf_name in pdf_names:
        assert not Path(pdf_name).exists()


# ----------------- ai analysis helpers -----------------
def test_get_stock_increase_reason(alert):
    stock = _stock("AIR1")
    alert._ai_api.get_stock_increase_reason.return_value = "  reason one\nreason two  "
    stock_stats = {
        stock: {
            FinancialMetricType.FREE_CASH_FLOW: FinancialMetricsData(1.0),
            FinancialMetricType.REVENUE: FinancialMetricsData(2.0),
        }
    }

    alert._get_stock_increase_reason(stock, ["1D", "1M"], stock_stats)

    alert._ai_api.get_stock_increase_reason.assert_called_once_with(stock, ["1D", "1M"])
    alert._pdf_api.append_stock_info.assert_called_once_with(
        stock,
        [
            "Stock Stats: free_cash_flow: 1.0, revenue: 2.0",
            "Timeframes: 1D, 1M",
            "reason one",
            "reason two",
        ],
    )


def test_get_stocks_ai_analysis_for_newly_added(alert):
    new_stock = _stock("AIR2")
    old_stock = _stock("AIR3")
    alert._pdf_api.file_name = "newly_added.pdf"
    alert._ai_api.get_stock_increase_reason.return_value = "reason"
    stock_stats = {new_stock: _stats(), old_stock: _stats()}

    result = alert.get_stocks_ai_analysis_for_newly_added(
        {"1D": [new_stock, old_stock], "1M": [old_stock]},
        {new_stock: True, old_stock: False},
        stock_stats,
    )

    assert result == "newly_added.pdf"
    alert._pdf_api.start_new_pdf.assert_called_once()
    started_pdf = alert._pdf_api.start_new_pdf.call_args.args[0]
    assert started_pdf.startswith("Newly Added Stock AI Analysis_")
    assert started_pdf.endswith(".pdf")
    assert alert._pdf_api.append_text.call_args_list == [call("Timeframe 1D:"), call("Timeframe 1M:")]
    alert._ai_api.get_stock_increase_reason.assert_called_once_with(new_stock, "1D")
    alert._pdf_api.append_stock_info.assert_called_once()
    assert alert._pdf_api.append_stock_info.call_args.args[0] is new_stock
    assert alert._pdf_api.append_stock_info.call_args.args[1][0].startswith("Stock Stats: ")
    alert._pdf_api.save_pdf.assert_called_once_with()


def test_get_stocks_ai_analysis_for_timeframe_sma(alert):
    first = _stock("AIR4")
    second = _stock("AIR5")
    stock_stats = {first: _stats(), second: _stats()}
    alert._pdf_api.file_name = "timeframe_sma.pdf"
    alert._get_stock_increase_reason = MagicMock()

    result = alert.get_stocks_ai_analysis_for_timeframe_sma(
        {first: ["1D", "1M"], second: ["3M"]},
        stock_stats,
    )

    assert result == "timeframe_sma.pdf"
    alert._pdf_api.start_new_pdf.assert_called_once()
    assert alert._get_stock_increase_reason.call_args_list == [
        call(first, ["1D", "1M"], stock_stats),
        call(second, ["3M"], stock_stats),
    ]
    alert._pdf_api.save_pdf.assert_called_once_with()


def test_get_stocks_ai_analysis_for_growth_score(alert):
    high = _stock("AIR6")
    medium = _stock("AIR7")
    below = _stock("AIR8")
    low = _stock("AIR9")
    stock_stats = {
        below: {FinancialMetricType.GROWTH_SCORE: FinancialMetricsData(0.7)},
        high: {FinancialMetricType.GROWTH_SCORE: FinancialMetricsData(0.95)},
        low: {FinancialMetricType.GROWTH_SCORE: FinancialMetricsData(0.5)},
        medium: {FinancialMetricType.GROWTH_SCORE: FinancialMetricsData(0.85)},
    }
    stock_timeframe_dict = {stock: ["1D"] for stock in stock_stats}
    alert._pdf_api.file_name = "growth_score.pdf"
    alert._get_stock_increase_reason = MagicMock()

    result = alert.get_stocks_ai_analysis_for_growth_score(stock_timeframe_dict, stock_stats, 0.8)

    assert result == "growth_score.pdf"
    assert [c.args[0] for c in alert._get_stock_increase_reason.call_args_list] == [high, medium]
    alert._pdf_api.save_pdf.assert_called_once_with()


def test_get_stocks_ai_analysis_for_stock_screener_alert_intersection(alert):
    first = _stock("AIR10")
    second = _stock("AIR11")
    stock_stats = {first: _stats(), second: _stats()}
    alert._stock_screener_alert_stocks = {second}
    alert._pdf_api.file_name = "screener.pdf"
    alert._get_stock_increase_reason = MagicMock()

    result = alert.get_stocks_ai_analysis_for_stock_screener_alert_intersection(
        {first: ["1D"], second: ["1M"]},
        stock_stats,
    )

    assert result == "screener.pdf"
    alert._get_stock_increase_reason.assert_called_once_with(second, ["1M"], stock_stats)
    alert._pdf_api.save_pdf.assert_called_once_with()


# ----------------- filtering -----------------
def test_filter_stock_with_timeframe_sma():
    matched_first_combo = _stock("FLT1")
    failing_sma = _stock("FLT2")
    no_combo = _stock("FLT3")
    matched_second_combo = _stock("FLT4")
    stock_timeframe_dict = {
        matched_first_combo: ["1Y", "6M"],
        failing_sma: ["1Y", "6M"],
        no_combo: ["1M"],
        matched_second_combo: ["1Y", "3M", "6M"],
    }
    sma_dict = {
        matched_first_combo: {"4hour": True, "1day": True},
        failing_sma: {"4hour": True, "1day": False},
        no_combo: {"4hour": True, "1day": True},
        matched_second_combo: {"4hour": True, "1day": True},
    }

    result = StockPriceTopPerformerAlert.filter_stock_with_timeframe_sma(
        stock_timeframe_dict,
        [["1Y", "6M"], ["1Y", "3M"]],
        sma_dict,
    )

    assert result == {
        matched_first_combo: ["1Y", "6M"],
        matched_second_combo: ["1Y", "3M", "6M"],
    }


# ----------------- sorted price increase -----------------
def test_get_sorted_price_increased_stocks(alert):
    first = _stock("SRT1")
    second = _stock("SRT2")
    alert.get_all_stock_price_change_percentage = MagicMock(
        return_value={first: {"1D": Decimal("2")}, second: {"1D": Decimal("5")}}
    )

    result = alert.get_sorted_price_increased_stocks()

    assert result == {"1D": [(second, Decimal("5")), (first, Decimal("2"))]}
    alert.get_all_stock_price_change_percentage.assert_called_once_with(["1D"])


def test_get_sorted_price_increased_stocks_retries_on_zero(alert):
    first = _stock("SRT3")
    second = _stock("SRT4")
    alert.get_all_stock_price_change_percentage = MagicMock(
        side_effect=[
            {first: {"1D": Decimal("0")}, second: {"1D": Decimal("-1")}},
            {first: {"1D": Decimal("1")}, second: {"1D": Decimal("5")}},
        ]
    )

    result = alert.get_sorted_price_increased_stocks()

    assert result == {"1D": [(second, Decimal("5")), (first, Decimal("1"))]}
    assert alert.get_all_stock_price_change_percentage.call_count == 2


# ----------------- top n non-etf stocks -----------------
def test_get_top_n_non_etf_stocks_filters(alert, caplog):
    passing = _stock("TPA", "Alpha Corp", sp500=True)
    etf = _stock("ETF1", "Beta ETF", sp500=True)
    long_ticker = _stock("TPNGS", "Long Ticker", sp500=True)
    low_volume = _stock("TPLW", "Low Volume", sp500=True)
    no_name = _stock("TPE", "", sp500=True)
    unlisted = _stock("TPU", "Unlisted")
    another_passing = _stock("TPG", "Gamma Corp", sp500=True)

    alert._daily_volume_threshold = 500
    alert._daily_volume = {
        passing: Decimal("1000"),
        etf: Decimal("1000"),
        long_ticker: Decimal("1000"),
        low_volume: Decimal("100"),
        no_name: Decimal("1000"),
        unlisted: Decimal("1000"),
        another_passing: Decimal("1000"),
    }
    top_stocks = {
        "1D": [
            (passing, Decimal("10")),
            (etf, Decimal("9")),
            (long_ticker, Decimal("8")),
            (low_volume, Decimal("7")),
            (no_name, Decimal("6")),
            (unlisted, Decimal("5")),
            (another_passing, Decimal("4")),
        ]
    }
    stock_map = {
        stock.ticker: stock for stock in [passing, etf, long_ticker, low_volume, no_name, unlisted, another_passing]
    }
    alert.get_nasdaq_list = MagicMock(return_value=[])
    alert.get_sp_500_list = MagicMock(return_value=[])
    alert.get_nyse_list = MagicMock(return_value=[])
    alert.get_stock_info = MagicMock(side_effect=lambda stocks: [stock_map[s.ticker] for s in stocks])

    with caplog.at_level(logging.WARNING):
        result = alert.get_top_n_non_etf_stocks(2, top_stocks)

    assert result == {"1D": [(passing, Decimal("10")), (no_name, Decimal("6"))]}
    assert "Stock TPE does not have security name" in caplog.text
    alert.get_stock_info.assert_called_once()
    alert.get_nasdaq_list.assert_called_once_with()
    alert.get_sp_500_list.assert_called_once_with()
    alert.get_nyse_list.assert_called_once_with()


def test_get_top_n_non_etf_stocks_reads_multiple_batches(alert):
    fillers = [_stock(f"FL{i:02d}", "Filler ETF", sp500=True) for i in range(40)]
    passing = _stock("TPZ", "Zeta Corp", sp500=True)
    all_stocks = [*fillers, passing]
    stock_map = {stock.ticker: stock for stock in all_stocks}
    alert.get_nasdaq_list = MagicMock(return_value=[])
    alert.get_sp_500_list = MagicMock(return_value=[])
    alert.get_nyse_list = MagicMock(return_value=[])
    alert.get_stock_info = MagicMock(side_effect=lambda stocks: [stock_map[s.ticker] for s in stocks])
    top_stocks = {"1D": [(stock, Decimal("1")) for stock in all_stocks]}

    result = alert.get_top_n_non_etf_stocks(1, top_stocks)

    assert result == {"1D": [(passing, Decimal("1"))]}
    assert alert.get_stock_info.call_count == 2


def test_get_top_n_non_etf_stocks_with_empty_list(alert):
    alert.get_nasdaq_list = MagicMock(return_value=[])
    alert.get_sp_500_list = MagicMock(return_value=[])
    alert.get_nyse_list = MagicMock(return_value=[])
    alert.get_stock_info = MagicMock()

    result = alert.get_top_n_non_etf_stocks(50, {"1D": []})

    assert result == {"1D": []}
    alert.get_stock_info.assert_not_called()


# ----------------- run -----------------
def test_run(alert, monkeypatch):
    newly_added = _stock("RUN1", "Runner One")
    existing = _stock("RUN2", "Runner Two")
    alert._stock_screener_alert_stocks = {existing}
    top_stocks = {
        "1D": [
            (newly_added, Decimal("12.34")),
            (existing, Decimal("-3.21")),
        ]
    }
    alert.get_sorted_price_increased_stocks = MagicMock(return_value=top_stocks)
    alert.get_all_stock_price_volume_by_day_delta = MagicMock(
        return_value=({}, {newly_added: Decimal("1000"), existing: Decimal("2000")})
    )
    alert.get_top_n_non_etf_stocks = MagicMock(return_value=top_stocks)

    get_stocks = MagicMock(return_value={"RUN2"})
    reset_stocks = MagicMock()
    add_stocks = MagicMock()
    monkeypatch.setattr(StockAlertDBUtils, "get_stocks", get_stocks)
    monkeypatch.setattr(StockAlertDBUtils, "reset_stocks", reset_stocks)
    monkeypatch.setattr(StockAlertDBUtils, "add_stocks", add_stocks)

    close_database = MagicMock()
    sleep = MagicMock()
    monkeypatch.setattr(alert_module, "close_database", close_database)
    monkeypatch.setattr(alert_module.time, "sleep", sleep)
    alert.send_stocks_info_as_csv = MagicMock()

    alert.run()

    expected_msg = (
        "Top 50 stocks from SP500 and Nasdaq with the highest price increase with timeframe 1D: \n"
        "Stock: Price Change Percentage\n"
        "['RUN1: 12.34% (New)', 'RUN2: -3.21% *']"
    )
    alert._tg_bot.send_message.assert_called_once_with(expected_msg)
    alert.get_sorted_price_increased_stocks.assert_called_once_with()
    alert.get_all_stock_price_volume_by_day_delta.assert_called_once_with(1)
    alert.get_top_n_non_etf_stocks.assert_called_once_with(50, top_stocks)
    assert alert._daily_volume == {newly_added: Decimal("1000"), existing: Decimal("2000")}

    alert.send_stocks_info_as_csv.assert_called_once()
    is_newly_added, timeframe_stocks, email_message = alert.send_stocks_info_as_csv.call_args.args
    assert is_newly_added == {newly_added: True, existing: False}
    assert timeframe_stocks == {"1D": [newly_added, existing]}
    assert email_message == "* means the stock is in the stock screener alert result\n\n" + expected_msg + "\n\n"

    reset_stocks.assert_called_once_with()
    add_stocks.assert_called_once()
    assert list(add_stocks.call_args.args[0]) == [newly_added, existing]
    get_stocks.assert_called_once_with()
    sleep.assert_called_once_with(10)
    close_database.assert_called_once_with()
