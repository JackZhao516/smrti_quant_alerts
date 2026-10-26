"""Unit tests for the stock screener alert.

All network, email, and database access is mocked. The ``runtime_database``
fixture provides an isolated SQLite runtime for the alert's BaseAlert setup.
"""

import os
from collections import defaultdict
from unittest.mock import MagicMock

import pandas as pd
import pytest

from smrti_quant_alerts.alerts.stock_alerts import stock_screener_alert
from smrti_quant_alerts.alerts.stock_alerts.stock_screener_alert import StockScreenerAlert
from smrti_quant_alerts.data_type import FinancialMetricType, FinancialMetricsData, StockSymbol
from smrti_quant_alerts.db import StockAlertDBUtils
from smrti_quant_alerts.settings import Config


def _stock(ticker: str, sector: str = "Technology") -> StockSymbol:
    return StockSymbol(ticker, gics_sector=sector)


def _metric(value: float) -> FinancialMetricsData:
    return FinancialMetricsData(value)


def _quarter_stats(value: float = 0.1) -> dict:
    return {
        FinancialMetricType.REVENUE_YOY_GROWTH: _metric(value),
        FinancialMetricType.GROSS_MARGIN: _metric(0.5),
        FinancialMetricType.OPERATING_MARGIN: _metric(0.2),
        FinancialMetricType.FREE_CASH_FLOW_MARGIN: _metric(0.3),
    }


@pytest.fixture
def alert(runtime_database, monkeypatch):
    monkeypatch.setattr(stock_screener_alert, "EmailApi", MagicMock())
    Config.SETTINGS = {"stock_screener": {"database_name": "stock_screener"}}

    screener_alert = StockScreenerAlert("stock_screener", start_threads=False)
    screener_alert._get_stock_info_thread = MagicMock()
    screener_alert._get_price_top_performer_thread = MagicMock()
    return screener_alert


def test_init_starts_background_threads(runtime_database, monkeypatch):
    monkeypatch.setattr(stock_screener_alert, "EmailApi", MagicMock())
    monkeypatch.setattr(StockScreenerAlert, "_get_all_stock_info", MagicMock())
    monkeypatch.setattr(
        StockScreenerAlert,
        "get_top_percent_stock_price_top_performer_by_gics_sector_timeframe",
        MagicMock(),
    )
    Config.SETTINGS = {"stock_screener": {"database_name": "stock_screener"}}

    screener_alert = StockScreenerAlert("stock_screener", start_threads=True)
    screener_alert._get_stock_info_thread.join(timeout=2)
    screener_alert._get_price_top_performer_thread.join(timeout=2)

    assert not screener_alert._get_stock_info_thread.is_alive()
    assert not screener_alert._get_price_top_performer_thread.is_alive()


def test_get_stocks_delegates_to_market_cap_filter(alert, monkeypatch):
    stocks = [_stock("AAA1")]
    get_stocks = MagicMock(return_value=stocks)
    monkeypatch.setattr(alert, "get_top_market_cap_stocks_by_market_cap_threshold", get_stocks)
    alert._market_cap_threshold = 123456

    assert alert._get_stocks() == stocks
    get_stocks.assert_called_once_with(123456)


def test_get_all_stock_info_combines_nyse_and_nasdaq(alert, monkeypatch):
    nyse_stock = _stock("NYE1")
    nasdaq_stock = _stock("NSD1")
    monkeypatch.setattr(alert, "get_nyse_list", MagicMock(return_value=[nyse_stock]))
    monkeypatch.setattr(alert, "get_nasdaq_list", MagicMock(return_value=[nasdaq_stock]))
    get_stock_info = MagicMock()
    monkeypatch.setattr(alert, "get_stock_info", get_stock_info)

    alert._get_all_stock_info()

    get_stock_info.assert_called_once_with([nyse_stock, nasdaq_stock])


def test_get_newly_added_stocks_str_returns_and_persists_new_stocks(monkeypatch):
    stock1 = _stock("NEW1")
    stock2 = _stock("OLD1")
    stock3 = _stock("OLD2")
    get_stocks = MagicMock(return_value={stock2, stock3})
    reset_stocks = MagicMock()
    add_stocks = MagicMock()
    monkeypatch.setattr(StockAlertDBUtils, "get_stocks", get_stocks)
    monkeypatch.setattr(StockAlertDBUtils, "reset_stocks", reset_stocks)
    monkeypatch.setattr(StockAlertDBUtils, "add_stocks", add_stocks)

    new_stocks = StockScreenerAlert._get_newly_added_stocks_str([stock1, stock2], "screener_x")

    assert new_stocks == {stock1}
    get_stocks.assert_called_once_with("screener_x")
    reset_stocks.assert_called_once_with("screener_x")
    add_stocks.assert_called_once_with([stock1, stock2], "screener_x")


def test_get_enterprise_value_over_gross_profit_skips_cached_and_empty_stats(alert, monkeypatch):
    cached = _stock("EVC1")
    with_stats = _stock("EVS1")
    without_stats = _stock("EVN1")
    fresh = _stock("EVF1")
    alert._stocks_ev_over_gross_profit[cached] = 99.0

    enterprise_values = {
        with_stats: _metric(200.0),
        without_stats: _metric(100.0),
        fresh: _metric(300.0),
    }
    stocks_stats = defaultdict(
        list,
        {
            with_stats: [{FinancialMetricType.GROSS_PROFIT: _metric(50.0)}],
            without_stats: [],
            fresh: [{FinancialMetricType.GROSS_PROFIT: _metric(100.0)}],
        },
    )
    get_enterprise_value = MagicMock(return_value=enterprise_values)
    get_stocks_stats = MagicMock(return_value=stocks_stats)
    monkeypatch.setattr(alert, "get_stocks_enterprise_value", get_enterprise_value)
    monkeypatch.setattr(alert, "get_stocks_stats_by_num_of_timeframe", get_stocks_stats)

    stocks = [cached, with_stats, without_stats, fresh]
    alert._get_enterprise_value_over_gross_profit(stocks)

    remaining = [with_stats, without_stats, fresh]
    get_enterprise_value.assert_called_once_with(remaining)
    get_stocks_stats.assert_called_once_with(remaining, "annual", 1)
    assert alert._stocks_ev_over_gross_profit[with_stats] == 4.0
    assert alert._stocks_ev_over_gross_profit[fresh] == 3.0
    assert without_stats not in alert._stocks_ev_over_gross_profit
    assert alert._stocks_ev_over_gross_profit[cached] == 99.0


def test_parallel_get_stocks_valuation_score_updates_uncached_stocks(alert, monkeypatch):
    cached = _stock("VLC1")
    stocks = [_stock(f"VAL{i}") for i in range(10)]
    alert._stocks_valuation_score[cached] = "cached-score"

    def score(chunk):
        return {stock: _metric(1.5) for stock in chunk}

    get_valuation_score = MagicMock(side_effect=score)
    monkeypatch.setattr(alert, "get_stocks_valuation_score", get_valuation_score)

    alert._parallel_get_stocks_valuation_score([cached, *stocks])

    assert all(alert._stocks_valuation_score[stock] == 1.5 for stock in stocks)
    assert alert._stocks_valuation_score[cached] == "cached-score"
    requested_stocks = [stock for call in get_valuation_score.call_args_list for stock in call.args[0]]
    assert set(requested_stocks) == set(stocks)


def test_get_stocks_eight_quarters_stats_builds_metric_rows(alert, monkeypatch):
    cached = _stock("QTC1")
    stocks = [_stock("QT1"), _stock("QT2")]
    alert._stocks_eight_quarters_stats[cached] = ["cached-stats"]
    quarterly_growth = {stock: [_metric(0.1 + index / 100) for index in range(8)] for stock in stocks}
    stock_stats = {stock: [_quarter_stats(0.2) for _ in range(8)] for stock in stocks}
    get_growth = MagicMock(return_value=quarterly_growth)
    get_stats = MagicMock(return_value=stock_stats)
    monkeypatch.setattr(alert, "get_stocks_quarterly_revenue_yoy_growth", get_growth)
    monkeypatch.setattr(alert, "get_stocks_stats_by_num_of_timeframe", get_stats)

    alert._get_stocks_eight_quarters_stats([cached, *stocks])

    get_growth.assert_called_once_with(stocks, 8)
    get_stats.assert_called_once_with(stocks, "quarter", 8)
    for stock in stocks:
        assert len(alert._stocks_eight_quarters_stats[stock]) == 8
        assert set(alert._stocks_eight_quarters_stats[stock][0]) == {
            FinancialMetricType.REVENUE_YOY_GROWTH,
            FinancialMetricType.GROSS_MARGIN,
            FinancialMetricType.OPERATING_MARGIN,
            FinancialMetricType.FREE_CASH_FLOW_MARGIN,
        }
    assert alert._stocks_eight_quarters_stats[stocks[0]][0][FinancialMetricType.REVENUE_YOY_GROWTH] == 0.1
    assert alert._stocks_eight_quarters_stats[cached] == ["cached-stats"]


def test_get_top_percent_stock_price_top_performer_by_gics_sector_timeframe(alert, monkeypatch):
    sector_stocks = {
        "Technology": [_stock(f"TEC{i}") for i in range(5)],
        "": [_stock(f"OTH{i}") for i in range(10)],
        "Energy": [_stock(f"ENG{i}") for i in range(3)],
        "Health": [_stock(f"HLT{i}") for i in range(2)],
    }
    price_performers = {
        timeframe: {sector: [(stock, 1.0) for stock in stocks] for sector, stocks in sector_stocks.items()}
        for timeframe in ["5D", "1M"]
    }
    monkeypatch.setattr(
        alert,
        "get_all_non_etf_stocks_by_gics_sector",
        MagicMock(return_value=sector_stocks),
    )
    get_price_performers = MagicMock(return_value=price_performers)
    monkeypatch.setattr(
        alert,
        "get_all_non_etf_stocks_price_change_percentage_by_gics_sector_timeframes",
        get_price_performers,
    )
    alert._top_performer_exclude_sectors = ["Energy"]
    alert._price_top_percent = 20

    alert.get_top_percent_stock_price_top_performer_by_gics_sector_timeframe()

    get_price_performers.assert_called_once_with(["5D", "1M"])
    for timeframe in ["5D", "1M"]:
        result = alert._stock_price_top_performer_by_gics_sector_timeframe[timeframe]
        assert set(result) == {"Technology", "", "Health"}
        assert len(result["Technology"]) == 1
        assert len(result[""]) == 2
        assert len(result["Health"]) == 0


def test_get_top_percent_stocks_without_excluded_sectors(alert, monkeypatch):
    sector_stocks = {"Energy": [_stock(f"ENG{i}") for i in range(5)]}
    price_performers = {
        timeframe: {sector: [(stock, 1.0) for stock in stocks] for sector, stocks in sector_stocks.items()}
        for timeframe in ["5D", "1M"]
    }
    monkeypatch.setattr(alert, "get_all_non_etf_stocks_by_gics_sector", MagicMock(return_value=sector_stocks))
    monkeypatch.setattr(
        alert,
        "get_all_non_etf_stocks_price_change_percentage_by_gics_sector_timeframes",
        MagicMock(return_value=price_performers),
    )
    alert._top_performer_exclude_sectors = None

    alert.get_top_percent_stock_price_top_performer_by_gics_sector_timeframe()

    for timeframe in ["5D", "1M"]:
        assert len(alert._stock_price_top_performer_by_gics_sector_timeframe[timeframe]["Energy"]) == 1


def test_growth_score_filter_filters_and_sorts(alert, monkeypatch):
    high = _stock("GRH1")
    medium = _stock("GRM1")
    low = _stock("GRL1")
    stocks = [high, medium, low]
    growth_scores = {
        high: {FinancialMetricType.GROWTH_SCORE: _metric(1.2)},
        medium: {FinancialMetricType.GROWTH_SCORE: _metric(0.9)},
        low: {FinancialMetricType.GROWTH_SCORE: _metric(0.5)},
    }
    get_growth_score = MagicMock(return_value=growth_scores)
    monkeypatch.setattr(alert, "get_stocks_growth_score", get_growth_score)

    filtered, returned_scores = alert._growth_score_filter(stocks)

    get_growth_score.assert_called_once_with(stocks, True)
    assert filtered == [high, medium]
    assert returned_scores is growth_scores


def test_quarterly_revenue_yoy_growth_operating_margin_filter(alert, monkeypatch):
    passing = _stock("OMP1")
    boundary = _stock("OMB1")
    failing = _stock("OMF1")
    stocks = [passing, boundary, failing]
    revenue_growth = {
        passing: [_metric(0.3)],
        boundary: [_metric(0.2)],
        failing: [_metric(0.1)],
    }
    stock_stats = {
        passing: [{FinancialMetricType.OPERATING_MARGIN: _metric(0.2)}],
        boundary: [{FinancialMetricType.OPERATING_MARGIN: _metric(0.2)}],
        failing: [{FinancialMetricType.OPERATING_MARGIN: _metric(0.2)}],
    }
    get_growth = MagicMock(return_value=revenue_growth)
    get_stats = MagicMock(return_value=stock_stats)
    monkeypatch.setattr(alert, "get_stocks_quarterly_revenue_yoy_growth", get_growth)
    monkeypatch.setattr(alert, "get_stocks_stats_by_num_of_timeframe", get_stats)

    assert alert._quarterly_revenue_yoy_growth_operating_margin_filter(stocks) == [passing]
    get_growth.assert_called_once_with(stocks, 1)
    get_stats.assert_called_once_with(stocks, "quarter", 1)


def test_quarterly_revenue_yoy_growth_revenue_cagr_filter(alert, monkeypatch):
    cagr_pass = _stock("CGP1")
    average_pass = _stock("CGA1")
    latest_fail = _stock("CGL1")
    avg_and_cagr_fail = _stock("CGF1")
    stocks = [cagr_pass, average_pass, latest_fail, avg_and_cagr_fail]
    revenue_growth = {
        cagr_pass: [_metric(0.4), _metric(0.1), _metric(0.1), _metric(0.1), _metric(0.1), _metric(0.1)],
        average_pass: [_metric(0.4), _metric(0.4), _metric(0.4), _metric(0.4), _metric(0.2), _metric(0.2)],
        latest_fail: [_metric(0.2), _metric(0.5), _metric(0.5), _metric(0.5), _metric(0.5), _metric(0.5)],
        avg_and_cagr_fail: [_metric(0.4), _metric(0.0), _metric(0.0), _metric(0.0), _metric(0.0), _metric(0.0)],
    }
    revenue_cagr = {
        cagr_pass: {FinancialMetricType.REVENUE_3Y_CAGR: _metric(0.35)},
        average_pass: {FinancialMetricType.REVENUE_3Y_CAGR: _metric(0.1)},
        latest_fail: {FinancialMetricType.REVENUE_3Y_CAGR: _metric(0.5)},
        avg_and_cagr_fail: {FinancialMetricType.REVENUE_3Y_CAGR: _metric(0.1)},
    }
    get_growth = MagicMock(return_value=revenue_growth)
    get_cagr = MagicMock(return_value=revenue_cagr)
    monkeypatch.setattr(alert, "get_stocks_quarterly_revenue_yoy_growth", get_growth)
    monkeypatch.setattr(alert, "get_stocks_revenue_cagr", get_cagr)

    assert alert._quarterly_revenue_yoy_growth_revenue_cagr_filter(stocks) == [cagr_pass, average_pass]
    get_growth.assert_called_once_with(stocks, 6)
    get_cagr.assert_called_once_with(stocks)


def test_quarterly_revenue_yoy_growth_filter(alert, monkeypatch):
    average_pass = _stock("YOY1")
    latest_fail = _stock("YOY2")
    average_fail = _stock("YOY3")
    stocks = [average_pass, latest_fail, average_fail]
    revenue_growth = {
        average_pass: [_metric(0.4), _metric(0.4), _metric(0.4)],
        latest_fail: [_metric(0.2), _metric(0.5), _metric(0.5)],
        average_fail: [_metric(0.4), _metric(0.1), _metric(0.1)],
    }
    get_growth = MagicMock(return_value=revenue_growth)
    monkeypatch.setattr(alert, "get_stocks_quarterly_revenue_yoy_growth", get_growth)

    assert alert._quarterly_revenue_yoy_growth_filter(stocks) == [average_pass]
    get_growth.assert_called_once_with(stocks, 3)


def test_get_screener_stocks_in_top_performer_marks_new_and_others(alert):
    new_stock = _stock("NEWP")
    old_stock = _stock("OLDP")
    other_new_stock = _stock("OTHN")
    alert._price_top_percent = 20
    alert._stock_price_top_performer_by_gics_sector_timeframe = {
        "5D": {
            "Technology": [(new_stock, 1.0), (old_stock, 2.0)],
            "": [(other_new_stock, 3.0)],
        },
        "1M": {"Technology": [(old_stock, 1.0)]},
    }
    alert._screener_name_to_stocks = defaultdict(list, {"screener_x": [new_stock, old_stock, other_new_stock]})
    alert._newly_added_stocks = {new_stock, other_new_stock}

    content = alert._get_screener_stocks_in_top_performer()

    alert._get_price_top_performer_thread.join.assert_called_once_with()
    assert "~Top 20% price performer in 5D:" in content
    assert "~Top 20% price performer in 1M:" in content
    assert "   ~screener_x top performer: \n" in content
    assert "       ·Technology: ['NEWP (new)', OLDP]\n" in content
    assert "       ·Others: ['OTHN (new)']\n" in content
    assert "       ·Technology: [OLDP]\n" in content


def test_build_growth_filter_docs_creates_files_and_others_sheet(alert, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    below_tech = _stock("GRB1", "Technology")
    below_other = _stock("GRB2", "")
    above_tech = _stock("GRA1", "Technology")
    above_other = _stock("GRA2", "")
    stocks = [below_tech, below_other, above_tech, above_other]
    scores = {
        stock: {
            FinancialMetricType.GROWTH_SCORE: _metric(score),
            FinancialMetricType.REVENUE_YOY_GROWTH_LATEST: _metric(0.4),
            FinancialMetricType.REVENUE_YOY_GROWTH_SECOND_LATEST: _metric(0.3),
            FinancialMetricType.REVENUE_YOY_GROWTH_SUM: _metric(0.7),
            FinancialMetricType.FREE_CASH_FLOW_MARGIN_LATEST: _metric(0.2),
            FinancialMetricType.FREE_CASH_FLOW_MARGIN_SECOND_LATEST: _metric(0.1),
            FinancialMetricType.FREE_CASH_FLOW_MARGIN_AVG: _metric(0.15),
        }
        for stock, score in zip(stocks, [0.5, 0.6, 1.5, 1.6], strict=True)
    }

    filenames = alert._build_growth_filter_docs(stocks, scores)

    assert len(filenames) == 2
    assert filenames[0].startswith("screener_1_growth_score_filter_lt_1_stock_screener_")
    assert filenames[1].startswith("screener_1_growth_score_filter_gt_1_stock_screener_")
    for filename in filenames:
        assert filename.endswith(".xlsx")
        assert os.path.exists(filename)
        assert set(pd.ExcelFile(filename).sheet_names) == {"Technology", "Others"}
    below_tech_rows = pd.read_excel(filenames[0], sheet_name="Technology", header=None)
    assert "GRB1" in below_tech_rows.values
    above_other_rows = pd.read_excel(filenames[1], sheet_name="Others", header=None)
    assert "GRA2" in above_other_rows.values


def test_build_standard_filter_xlsx_creates_file_and_tracks_stocks(alert, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    new_stock = _stock("STN1", "Technology")
    old_stock = _stock("STO1", "")
    stocks = [new_stock, old_stock]
    alert._stocks_eight_quarters_stats[new_stock] = [_quarter_stats(0.1) for _ in range(8)]
    alert._stocks_eight_quarters_stats[old_stock] = [_quarter_stats(0.2) for _ in range(8)]
    get_new_stocks = MagicMock(return_value={new_stock})
    get_ev = MagicMock()
    get_eight_quarters = MagicMock()
    get_valuation = MagicMock()
    monkeypatch.setattr(alert, "_get_newly_added_stocks_str", get_new_stocks)
    monkeypatch.setattr(alert, "_get_enterprise_value_over_gross_profit", get_ev)
    monkeypatch.setattr(alert, "_get_stocks_eight_quarters_stats", get_eight_quarters)
    monkeypatch.setattr(alert, "_parallel_get_stocks_valuation_score", get_valuation)

    filename = alert._build_standard_filter_xlsx(stocks, "screener_test")

    get_new_stocks.assert_called_once_with(stocks, "screener_test")
    get_ev.assert_called_once_with(stocks)
    get_eight_quarters.assert_called_once_with(stocks)
    get_valuation.assert_called_once_with(stocks)
    assert alert._screener_name_to_stocks["screener_test"] == stocks
    assert alert._newly_added_stocks == {new_stock}
    assert filename.startswith("screener_test_stock_screener_")
    assert filename.endswith(".xlsx")
    assert os.path.exists(filename)
    assert set(pd.ExcelFile(filename).sheet_names) == {"Technology", "Others"}
    technology_rows = pd.read_excel(filename, sheet_name="Technology", header=None)
    assert any("STN1 *" in str(value) for value in technology_rows.values.flatten())


def test_send_email_contains_screener_descriptions(alert):
    alert._email_api = MagicMock()

    alert._send_email(
        csv_files=["stocks.csv"],
        pdf_xlsx_files=["stocks.xlsx"],
        email_content_add_on="top performer add on",
    )

    args = alert._email_api.send_email.call_args.args
    assert args[0] == "stock_screener"
    content = args[1]
    for description in [
        "Stock Screener 1: Growth Score Filter",
        "Stock Screener 2: Quarterly Revenue YoY Growth + Operating Margin Filter",
        "Stock Screener 3: Quarterly Revenue YoY Growth + Revenue CAGR Filter",
        "Stock Screener 4: Quarterly Revenue YoY Growth Filter",
    ]:
        assert description in content
    assert content.endswith("top performer add on")
    assert args[2] == ["stocks.csv"]
    assert args[3] == ["stocks.xlsx"]


@pytest.mark.parametrize("email_enabled", [True, False])
def test_run_builds_screeners_deduplicates_and_removes_files(alert, monkeypatch, tmp_path, email_enabled):
    monkeypatch.chdir(tmp_path)
    stock_a = _stock("RUN1")
    stock_b = _stock("RUN2")
    stock_c = _stock("RUN3")
    stock_d = _stock("RUN4")
    stock_e = _stock("RUN5")
    all_stocks = [stock_a, stock_b, stock_c, stock_d, stock_e]
    alert._email = email_enabled
    alert._get_stocks = MagicMock(return_value=all_stocks)
    alert._growth_score_filter = MagicMock(return_value=([stock_a, stock_b], {"growth_scores": True}))
    alert._quarterly_revenue_yoy_growth_operating_margin_filter = MagicMock(return_value=[stock_b, stock_c])
    alert._quarterly_revenue_yoy_growth_revenue_cagr_filter = MagicMock(return_value=[stock_a, stock_c, stock_d])
    alert._quarterly_revenue_yoy_growth_filter = MagicMock(return_value=[stock_d, stock_e])
    growth_files = ["growth_1.xlsx", "growth_2.xlsx"]
    alert._build_growth_filter_docs = MagicMock(return_value=list(growth_files))
    for filename in growth_files:
        with open(filename, "w", encoding="utf-8") as file:
            file.write("growth")

    def build_standard(stocks, screener_name):
        filename = f"{screener_name}.xlsx"
        with open(filename, "w", encoding="utf-8") as file:
            file.write("standard")
        return filename

    build_standard_mock = MagicMock(side_effect=build_standard)
    alert._build_standard_filter_xlsx = build_standard_mock
    alert._get_screener_stocks_in_top_performer = MagicMock(return_value="top performer content")
    alert._send_email = MagicMock()
    close_database = MagicMock()
    monkeypatch.setattr(stock_screener_alert, "close_database", close_database)

    alert.run()

    alert._get_stock_info_thread.join.assert_called_once_with()
    alert._get_stocks.assert_called_once_with()
    alert._growth_score_filter.assert_called_once_with(all_stocks)
    alert._quarterly_revenue_yoy_growth_operating_margin_filter.assert_called_once_with(all_stocks)
    alert._quarterly_revenue_yoy_growth_revenue_cagr_filter.assert_called_once_with(all_stocks)
    alert._quarterly_revenue_yoy_growth_filter.assert_called_once_with(all_stocks)
    alert._build_growth_filter_docs.assert_called_once_with([stock_a, stock_b], {"growth_scores": True})
    assert build_standard_mock.call_args_list[0].args == (
        [stock_a, stock_b],
        "screener_1_8-quarters_stats",
    )
    assert build_standard_mock.call_args_list[1].args == (
        [stock_b, stock_c],
        "screener_2_quarter_rev_yoy_growth_operating_margin",
    )
    assert build_standard_mock.call_args_list[2].args == (
        [stock_d],
        "screener_3_quarter_rev_yoy_growth_revenue_cagr",
    )
    assert build_standard_mock.call_args_list[3].args == (
        [stock_e],
        "screener_4_quarter_rev_yoy_growth",
    )
    alert._get_screener_stocks_in_top_performer.assert_called_once_with()

    expected_files = [
        "growth_1.xlsx",
        "growth_2.xlsx",
        "screener_1_8-quarters_stats.xlsx",
        "screener_2_quarter_rev_yoy_growth_operating_margin.xlsx",
        "screener_3_quarter_rev_yoy_growth_revenue_cagr.xlsx",
        "screener_4_quarter_rev_yoy_growth.xlsx",
    ]
    if email_enabled:
        alert._send_email.assert_called_once_with(
            pdf_xlsx_files=expected_files,
            email_content_add_on="top performer content",
        )
    else:
        alert._send_email.assert_not_called()
    assert all(not os.path.exists(filename) for filename in expected_files)
    close_database.assert_called_once_with()
