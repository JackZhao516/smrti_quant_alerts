"""Additional unit tests for the stock data API.

All HTTP and database boundaries are mocked; no network access is required.
"""

import datetime
from unittest import mock

import pytest

from smrti_quant_alerts.data_type import (
    FinancialMetricType,
    FinancialMetricsData,
    StockSymbol,
)
from smrti_quant_alerts.db import StockAlertDBUtils
from smrti_quant_alerts.stock_crypto_api import StockApi


def _response(payload, status_code=200):
    response = mock.Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


@pytest.fixture(autouse=True)
def clean_symbol_state():
    StockSymbol.symbol_info_map = {}
    StockSymbol.sp500_set = set()
    StockSymbol.nasdaq_set = set()
    StockSymbol.nyse_set = set()
    yield


@pytest.fixture
def api() -> StockApi:
    return StockApi()


def test_parse_eodhd_symbol() -> None:
    assert StockApi._parse_eodhd_symbol(StockSymbol("AAPL")) == "AAPL.US"
    assert StockApi._parse_eodhd_symbol(StockSymbol("AAPL@NASDAQ")) == "AAPL.NASDAQ"


def test_get_all_non_etf_stocks_by_gics_sector(api: StockApi) -> None:
    included = StockSymbol("AAA", "Apple", "Tech")
    etf = StockSymbol("BBBB", "Bond ETF", "Tech")
    long_ticker = StockSymbol("CCCCC", "Some Company", "Tech")

    with (
        mock.patch.object(api, "get_nasdaq_list", return_value=[included]),
        mock.patch.object(api, "get_nyse_list", return_value=[etf, long_ticker]),
        mock.patch.object(api, "get_stock_info", side_effect=lambda stocks: stocks),
    ):
        result = api.get_all_non_etf_stocks_by_gics_sector()

    assert result == {"Tech": [included]}


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_all_stock_price_volume_by_day_delta(mock_get, api: StockApi) -> None:
    today = datetime.datetime(2024, 5, 20)
    target = "2024-05-20"
    mock_get.return_value = _response(
        [
            {
                "code": "aapl",
                "adjusted_close": 100,
                "volume": 1000,
                "date": target,
                "exchange_short_name": "US",
            },
            {"code": "msft", "adjusted_close": 0, "volume": 1000, "date": target, "exchange_short_name": "US"},
            {"code": "nvda", "adjusted_close": 10, "volume": 0, "date": target, "exchange_short_name": "US"},
            {"code": "amzn", "adjusted_close": 10, "volume": 10, "date": "2024-05-16", "exchange_short_name": "US"},
            {"code": "meta", "adjusted_close": 10, "volume": 10, "date": target, "exchange_short_name": "DE"},
            {"adjusted_close": 10, "volume": 10, "date": target, "exchange_short_name": "US"},
        ]
    )

    with mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now", return_value=today):
        prices, volumes = api.get_all_stock_price_volume_by_day_delta(0)

    assert prices == {StockSymbol("AAPL"): 100}
    assert volumes == {StockSymbol("AAPL"): 1000}
    mock_get.assert_called_once()


def test_get_all_stock_price_change_percentage(api: StockApi) -> None:
    stock = StockSymbol("AAA")

    def price_by_day(day_delta):
        return ({stock: 110} if day_delta == 1 else {stock: 100}), {}

    with mock.patch.object(api, "get_all_stock_price_volume_by_day_delta", side_effect=price_by_day):
        result = api.get_all_stock_price_change_percentage(["1D"])

    assert result[stock]["1D"] == pytest.approx(10)


def test_get_all_stock_price_change_percentage_missing_history(api: StockApi) -> None:
    stock = StockSymbol("AAA")

    def price_by_day(day_delta):
        return ({stock: 110} if day_delta == 1 else {StockSymbol("BBB"): 100}), {}

    with mock.patch.object(api, "get_all_stock_price_volume_by_day_delta", side_effect=price_by_day):
        result = api.get_all_stock_price_change_percentage(["1D"])

    assert result[stock]["1D"] == 0


def test_get_all_stock_price_change_percentage_skips_empty_today(api: StockApi) -> None:
    stock = StockSymbol("AAA")
    responses = [({}, {}), ({stock: 110}, {}), ({stock: 100}, {})]

    with mock.patch.object(api, "get_all_stock_price_volume_by_day_delta", side_effect=responses) as get_prices:
        result = api.get_all_stock_price_change_percentage(["1D"])

    assert get_prices.call_count == 3
    assert result[stock]["1D"] == pytest.approx(10)


def test_get_all_non_etf_stocks_price_change_percentage_by_gics_sector(api: StockApi) -> None:
    stock_a, stock_b, missing = StockSymbol("AAA"), StockSymbol("BBB"), StockSymbol("CCC")
    sectors = {"Tech": [stock_a, stock_b], "Health": [missing]}

    with (
        mock.patch.object(api, "get_all_non_etf_stocks_by_gics_sector", return_value=sectors),
        mock.patch.object(
            api,
            "get_all_stock_price_change_percentage",
            return_value={stock_a: {"1D": 5}, stock_b: {"1D": 10}},
        ),
    ):
        result = api.get_all_non_etf_stocks_price_change_percentage_by_gics_sector_timeframes(["1D"])

    assert result["1D"]["Tech"] == [(stock_b, 10), (stock_a, 5)]
    assert "Health" not in result["1D"]


def test_get_stock_info_uses_fully_populated_cache(api: StockApi) -> None:
    full = StockSymbol("AAA", "A", "Tech", "Software", "NY", "1", "2000")
    cached = [full]

    with (
        mock.patch.object(StockAlertDBUtils, "get_stocks_info", return_value=(cached, [])),
        mock.patch.object(StockAlertDBUtils, "add_stocks_info") as add_stocks_info,
    ):
        result = api.get_stock_info([StockSymbol("AAA")])

    assert result == cached
    add_stocks_info.assert_not_called()


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stock_info_fetches_missing_symbols(mock_get, api: StockApi) -> None:
    cached = StockSymbol("AAA", "A", "Tech", "Software", "NY", "1", "2000")
    msft = StockSymbol("MSFT")
    mock_get.return_value = _response(
        [
            {
                "symbol": "MSFT",
                "companyName": "Microsoft",
                "sector": "Tech",
                "industry": "Software",
                "city": "Redmond",
                "state": "WA",
                "country": "US",
                "cik": "2",
                "ipoDate": "1986-03-13",
            }
        ]
    )

    with (
        mock.patch.object(StockAlertDBUtils, "get_stocks_info", return_value=([cached], [msft])),
        mock.patch.object(StockAlertDBUtils, "add_stocks_info") as add_stocks_info,
    ):
        result = api.get_stock_info([StockSymbol("MSFT"), StockSymbol("AAA")])

    assert len(result) == 2
    assert result[0].security_name == "Microsoft"
    assert result[1] == cached
    add_stocks_info.assert_called_once()


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_top_market_cap_stocks(mock_get, api: StockApi) -> None:
    mock_get.return_value = _response(
        {
            "data": [
                {"code": "aaa", "market_capitalization": 1000},
                {"code": "bbb", "market_capitalization": 900},
            ]
        }
    )

    result = api.get_top_market_cap_stocks(2)

    assert [item[0] for item in result] == [StockSymbol("AAA"), StockSymbol("BBB")]
    assert [item[1] for item in result] == [1000, 900]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stock_info_with_info_in_missing_list(mock_get, api: StockApi) -> None:
    full = StockSymbol("MSFT", "Microsoft", "Tech", "Software", "WA", "2", "1986")
    mock_get.return_value = _response([])

    with (
        mock.patch.object(StockAlertDBUtils, "get_stocks_info", return_value=([], [full])),
        mock.patch.object(StockAlertDBUtils, "add_stocks_info"),
    ):
        result = api.get_stock_info([StockSymbol("MSFT")])

    assert result == [full]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stock_info_alias_symbol_raises(mock_get, api: StockApi) -> None:
    mock_get.return_value = _response([])

    with (
        mock.patch.object(StockAlertDBUtils, "get_stocks_info", return_value=([], [StockSymbol("BRK.B")])),
        mock.patch.object(StockAlertDBUtils, "add_stocks_info"),
        pytest.raises(ValueError),
    ):
        StockApi.get_stock_info.__wrapped__(api, [StockSymbol("BRK.B")])


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_top_market_cap_stocks_by_market_cap_threshold(mock_get, api: StockApi) -> None:
    mock_get.return_value = _response(
        [
            {"symbol": "AAA", "name": "A", "marketCap": 1000},
            {"symbol": "BBB", "name": "B", "marketCap": 10},
        ]
    )

    with (
        mock.patch.object(api, "get_nasdaq_list", return_value=[StockSymbol("AAA")]),
        mock.patch.object(api, "get_nyse_list", return_value=[StockSymbol("BBB")]),
    ):
        result = api.get_top_market_cap_stocks_by_market_cap_threshold(100)

    assert result == [StockSymbol("AAA", "A")]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_close_price_sma_status(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    empty_close_stock = StockSymbol("BBB")
    empty_sma_stock = StockSymbol("CCC")
    mock_get.side_effect = [
        _response([{"price": 10}]),
        _response([{"sma": 5}]),
        _response([{"sma": 20}]),
        _response([]),
        _response([{"price": 10}]),
        _response([]),
        _response([]),
    ]

    with mock.patch(
        "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now", return_value=datetime.datetime(2024, 5, 20)
    ):
        result = api.get_close_price_sma_status(
            [stock, empty_close_stock, empty_sma_stock], [50, 200], ["1day", "1week"]
        )

    assert result[stock] == {"1day": True, "1week": False}
    assert empty_close_stock not in result
    assert empty_sma_stock not in result


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_market_cap(mock_get, api: StockApi) -> None:
    with_cap, without_cap = StockSymbol("AAA"), StockSymbol("BBB")
    mock_get.side_effect = [_response([{"marketCap": 100}]), _response([])]

    result = api.get_stocks_market_cap([with_cap, without_cap])

    assert result[with_cap] == 100
    assert without_cap not in result


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_stats_by_num_of_timeframe(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    income = [
        {"revenue": 100, "netIncome": 10, "grossProfit": 40, "operatingIncome": 20},
        {"revenue": 200, "netIncome": 20, "grossProfit": 80, "operatingIncome": 40},
    ]
    cash_flow = [{"freeCashFlow": 25}, {"freeCashFlow": 50}]
    mock_get.side_effect = [_response(income), _response(cash_flow)]

    result = api.get_stocks_stats_by_num_of_timeframe([stock], "quarter", 2)

    assert len(result[stock]) == 2
    assert result[stock][0][FinancialMetricType.REVENUE] == 100
    assert result[stock][0][FinancialMetricType.GROSS_PROFIT] == 40
    assert result[stock][0][FinancialMetricType.FREE_CASH_FLOW] == 25


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_stats_by_num_of_timeframe_empty_responses(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.side_effect = [_response([])]

    result = api.get_stocks_stats_by_num_of_timeframe([stock], "quarter", 2)

    assert len(result[stock]) == 2
    assert result[stock][0][FinancialMetricType.REVENUE] == 0

    mock_get.side_effect = [_response([{"revenue": 100}]), _response([])]
    result = api.get_stocks_stats_by_num_of_timeframe([stock], "quarter", 1)
    assert result[stock][0][FinancialMetricType.REVENUE] == 0


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_revenue_cagr(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([{"revenue": 100} for _ in range(24)])

    result = api.get_stocks_revenue_cagr([stock])

    assert result[stock]["revenue_1y_cagr"] == 0
    assert result[stock]["revenue_3y_cagr"] == 0
    assert result[stock]["revenue_5y_cagr"] == 0


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_revenue_cagr_empty_and_zero_revenue(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([])

    result = api.get_stocks_revenue_cagr([stock])
    assert result[stock]["revenue_1y_cagr"] == 0

    mock_get.return_value = _response([{"revenue": 0} for _ in range(24)])
    result = api.get_stocks_revenue_cagr([stock])
    assert result[stock]["revenue_1y_cagr"] == 0


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_revenue_cagr_stops_on_negative_revenue(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    revenues = [100, 100, 100, 100, -100, -100, -100, -100] + [100] * 16
    mock_get.return_value = _response([{"revenue": revenue} for revenue in revenues])

    result = api.get_stocks_revenue_cagr([stock])

    assert result[stock]["revenue_1y_cagr"] == 0


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stock_close_prices_by_timeframe_num_of_ticks(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response(
        [
            {"date": "2024-05-01", "adjusted_close": "9"},
            {"date": "2024-05-02", "adjusted_close": "10"},
        ]
    )

    with (
        mock.patch(
            "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now",
            return_value=datetime.datetime(2024, 5, 20),
        ),
        mock.patch.object(api, "get_stock_current_close_price", return_value=("2024-06-01", 11.0)),
    ):
        result = api.get_stock_close_prices_by_timeframe_num_of_ticks(stock, "1d", 2)

    assert result == [("2024-06-01", 11.0), ("2024-05-02", 10.0), ("2024-05-01", 9.0)]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stock_close_prices_skips_same_month_latest_price(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([{"date": "2024-05-02", "adjusted_close": "10"}])

    with (
        mock.patch(
            "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now",
            return_value=datetime.datetime(2024, 5, 20),
        ),
        mock.patch.object(api, "get_stock_current_close_price", return_value=("2024-05-20", 11.0)),
    ):
        result = api.get_stock_close_prices_by_timeframe_num_of_ticks(stock, "1d", 2)

    assert result == [("2024-05-02", 10.0)]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stock_current_close_price(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response({"timestamp": 1717200000, "close": "10.5"})

    with mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.get_date_from_timestamp", return_value="2024-06-01"):
        assert api.get_stock_current_close_price(stock) == ("2024-06-01", 10.5)

    mock_get.return_value = _response({"timestamp": "bad", "close": "10.5"})
    assert api.get_stock_current_close_price(stock) == ("", 0)


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_all_8k_filings_for_today(mock_get, api: StockApi) -> None:
    today = "2024-05-20"
    mock_get.side_effect = [
        _response(
            [
                {"date": f"{today}T10:00:00", "symbol": "AAA"},
                {"date": f"{today}T11:00:00"},
                {"date": "2024-05-19T10:00:00", "symbol": "BBB"},
            ]
        ),
        _response([]),
    ]

    with mock.patch(
        "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now", return_value=datetime.datetime(2024, 5, 20)
    ):
        result = api.get_all_8k_filings_for_today()

    assert result == [{"date": f"{today}T10:00:00", "symbol": "AAA"}]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_all_8k_filings_for_today_empty(mock_get, api: StockApi) -> None:
    mock_get.return_value = _response([])

    with mock.patch(
        "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now", return_value=datetime.datetime(2024, 5, 20)
    ):
        assert api.get_all_8k_filings_for_today() == []


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_all_8k_filings_for_today_paginates(mock_get, api: StockApi) -> None:
    today = "2024-05-20"
    mock_get.side_effect = [
        _response([{"date": f"{today}T10:00:00", "symbol": "AAA"}]),
        _response([]),
    ]

    with mock.patch(
        "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now",
        return_value=datetime.datetime(2024, 5, 20),
    ):
        result = api.get_all_8k_filings_for_today()

    assert result == [{"date": f"{today}T10:00:00", "symbol": "AAA"}]


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_floating_shares_change(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response(
        [
            {"date": "2024-05-20", "floatShares": "1100"},
            {"date": "2024-05-10", "floatShares": "1000"},
            {"date": "2024-02-20", "floatShares": "900"},
        ]
    )

    result = api.get_floating_shares_change([stock])

    assert result[stock]["7d"].percentage_data == pytest.approx(10)
    assert result[stock]["90d"].percentage_data == pytest.approx(22.2222, abs=0.001)


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_floating_shares_change_invalid_and_empty(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([{"date": "bad", "floatShares": "not-a-number"}])
    assert api.get_floating_shares_change([stock])[stock] == {}

    mock_get.return_value = _response([])
    assert stock not in api.get_floating_shares_change([stock])


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_enterprise_value(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([{"totalLiabilities": 1000, "cashAndCashEquivalents": 200}])

    with mock.patch.object(api, "get_stocks_market_cap", return_value={stock: FinancialMetricsData(500)}):
        result = api.get_stocks_enterprise_value([stock])

    assert result[stock] == 1300


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_valuation_score(mock_get, api: StockApi) -> None:
    stock, no_gross_profit, no_estimates = StockSymbol("AAA"), StockSymbol("BBB"), StockSymbol("CCC")
    mock_get.side_effect = [
        _response(
            [
                {"date": "2025-01-01", "estimatedRevenueAvg": 120},
                {"date": "2024-01-01", "estimatedRevenueAvg": 100},
            ]
        ),
        _response([]),
    ]

    stats = {
        stock: [{FinancialMetricType.GROSS_PROFIT: FinancialMetricsData(100)}],
        no_gross_profit: [{FinancialMetricType.GROSS_PROFIT: FinancialMetricsData(0)}],
        no_estimates: [{FinancialMetricType.GROSS_PROFIT: FinancialMetricsData(100)}],
    }
    with (
        mock.patch.object(
            api,
            "get_stocks_enterprise_value",
            return_value={
                stock: FinancialMetricsData(1000),
                no_gross_profit: FinancialMetricsData(1000),
                no_estimates: FinancialMetricsData(1000),
            },
        ),
        mock.patch.object(api, "get_stocks_stats_by_num_of_timeframe", return_value=stats),
        mock.patch(
            "smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now",
            return_value=datetime.datetime(2024, 5, 20),
        ),
    ):
        result = api.get_stocks_valuation_score([stock, no_gross_profit, no_estimates])

    assert result[stock] == pytest.approx(0.5)
    assert no_gross_profit not in result
    assert no_estimates not in result


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_revenue(mock_get, api: StockApi) -> None:
    with_revenue, without_revenue = StockSymbol("AAA"), StockSymbol("BBB")
    mock_get.side_effect = [_response([{"revenue": 100}]), _response([])]

    result = api.get_stocks_revenue([with_revenue, without_revenue])

    assert result[with_revenue] == 100
    assert without_revenue not in result


def test_get_stocks_growth_score(api: StockApi) -> None:
    stock = StockSymbol("AAA")
    stats = [
        {
            FinancialMetricType.REVENUE: FinancialMetricsData(1000),
            FinancialMetricType.FREE_CASH_FLOW_MARGIN: FinancialMetricsData(0.2),
        },
        {
            FinancialMetricType.REVENUE: FinancialMetricsData(1100),
            FinancialMetricType.FREE_CASH_FLOW_MARGIN: FinancialMetricsData(0.4),
        },
        {},
        {},
        {FinancialMetricType.REVENUE: FinancialMetricsData(800)},
        {FinancialMetricType.REVENUE: FinancialMetricsData(1000)},
    ]

    with mock.patch.object(api, "get_stocks_stats_by_num_of_timeframe", return_value={stock: stats}):
        result = api.get_stocks_growth_score([stock], full=True)

    assert result[stock][FinancialMetricType.GROWTH_SCORE] == pytest.approx(0.65)
    assert result[stock][FinancialMetricType.REVENUE_YOY_GROWTH_LATEST] == pytest.approx(0.25)
    assert result[stock][FinancialMetricType.REVENUE_YOY_GROWTH_SECOND_LATEST] == pytest.approx(0.1)
    assert result[stock][FinancialMetricType.FREE_CASH_FLOW_MARGIN_AVG] == pytest.approx(0.3)


def test_get_stocks_growth_score_requires_six_quarters(api: StockApi) -> None:
    stock = StockSymbol("AAA")

    with mock.patch.object(api, "get_stocks_stats_by_num_of_timeframe", return_value={stock: [{}]}):
        result = api.get_stocks_growth_score([stock])

    assert result[stock][FinancialMetricType.GROWTH_SCORE] == 0


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_quarterly_revenue_yoy_growth(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([{"revenue": revenue} for revenue in [110, 120, 130, 140, 100, 100]])

    result = api.get_stocks_quarterly_revenue_yoy_growth([stock], 2)

    assert result[stock][0].float_data == pytest.approx(0.1)
    assert result[stock][1].float_data == pytest.approx(0.2)


@mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.requests.get")
def test_get_stocks_quarterly_revenue_yoy_growth_empty_and_zero_base(mock_get, api: StockApi) -> None:
    stock = StockSymbol("AAA")
    mock_get.return_value = _response([])
    assert api.get_stocks_quarterly_revenue_yoy_growth([stock], 2)[stock][0].float_data == 0

    mock_get.return_value = _response([{"revenue": revenue} for revenue in [110, 120, 130, 140, 0, 100]])
    result = api.get_stocks_quarterly_revenue_yoy_growth([stock], 2)
    assert result[stock][0].float_data == 0
    assert result[stock][1].float_data == pytest.approx(0.2)
