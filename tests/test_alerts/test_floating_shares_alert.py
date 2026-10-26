"""Unit tests for the floating shares alert."""

from unittest import mock

import pytest

from smrti_quant_alerts.alerts.stock_alerts.floating_shares_alert import FloatingSharesAlert
from smrti_quant_alerts.data_type import FinancialMetricsData, StockSymbol
from smrti_quant_alerts.settings import Config


@pytest.fixture
def alert(runtime_database):
    Config.SETTINGS = {"floating_shares_test": {"database_name": "floating_shares_test"}}
    with mock.patch("smrti_quant_alerts.alerts.stock_alerts.floating_shares_alert.EmailApi"):
        alert = FloatingSharesAlert("floating_shares_test", start_threads=False)
    alert._tg_bot = mock.Mock()
    alert._email_api = mock.Mock()
    return alert


def _stock(ticker: str, sector: str = "Technology") -> StockSymbol:
    return StockSymbol(ticker, f"{ticker} Inc.", sector, "Software", "Testville", "123", "2000")


def _shares(seven_day: float = 0.05, ninety_day: float = 0.1) -> dict:
    return {
        "7d": FinancialMetricsData(seven_day, has_percentage=True),
        "90d": FinancialMetricsData(ninety_day, has_percentage=True),
    }


def test_constructor_without_threads(alert: FloatingSharesAlert) -> None:
    assert alert._symbols == []
    assert not hasattr(alert, "_load_stocks_info_thread")


def test_constructor_starts_loading_thread(runtime_database) -> None:
    Config.SETTINGS = {"floating_shares_test": {"database_name": "floating_shares_test"}}
    with (
        mock.patch("smrti_quant_alerts.alerts.stock_alerts.floating_shares_alert.EmailApi"),
        mock.patch("smrti_quant_alerts.alerts.stock_alerts.floating_shares_alert.threading.Thread") as thread,
    ):
        FloatingSharesAlert("floating_shares_test", start_threads=True)

    thread.assert_called_once_with(
        target=mock.ANY,
        # bound method equality is not stable, so only assert the target is callable
    )
    thread.return_value.start.assert_called_once_with()


def test_load_symbols_from_file(alert: FloatingSharesAlert, tmp_path) -> None:
    symbols_file = tmp_path / "symbols.txt"
    symbols_file.write_text(" AAPL \nMSFT\n")

    alert._load_symbols(str(symbols_file))

    assert alert._symbols == ["AAPL", "MSFT"]


def test_load_symbols_without_file(alert: FloatingSharesAlert) -> None:
    alert._load_symbols(None)

    assert alert._symbols == []


def test_load_stocks_info(alert: FloatingSharesAlert) -> None:
    nasdaq, nyse = _stock("AAA"), _stock("BBB")
    with (
        mock.patch.object(alert, "get_nasdaq_list", return_value=[nasdaq]),
        mock.patch.object(alert, "get_nyse_list", return_value=[nyse]),
        mock.patch.object(alert, "get_stock_info") as get_stock_info,
    ):
        alert._load_stocks_info()

    get_stock_info.assert_called_once_with([nasdaq, nyse])


def test_generate_floating_shares(alert: FloatingSharesAlert) -> None:
    with_info, empty_info = _stock("AAA"), _stock("BBB")
    with mock.patch.object(
        alert,
        "get_floating_shares_change",
        return_value={with_info: _shares(), empty_info: {}},
    ):
        content, shares = alert._generate_floating_shares([with_info, empty_info])

    assert shares[with_info]["7d"] == FinancialMetricsData(0.05, has_percentage=True)
    assert "~ AAA:" in content
    assert "7d: 5.0%" in content
    assert "~ BBB:" not in content


def test_generate_file_8k_summary_csv(alert: FloatingSharesAlert, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    filer_a = {"title": "8-K", "symbol": "AAA", "cik": "1"}
    filer_b = {"title": "8-K", "symbol": "BBB", "cik": "2"}
    alert._symbols = ["AAA"]

    with mock.patch.object(alert, "get_all_8k_filings_for_today", return_value=[filer_a, filer_b]):
        alert._generate_file_8k_summary_csv()

    content = (tmp_path / alert._file_8k_summary_filename).read_text()
    assert content.splitlines()[0] == "title,symbol,cik,link,process,hasFinancials,date"
    assert "AAA" in content
    assert "BBB" not in content


def test_generate_file_8k_summary_csv_without_symbol_filter(alert: FloatingSharesAlert, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    with mock.patch.object(alert, "get_all_8k_filings_for_today", return_value=[]):
        alert._generate_file_8k_summary_csv()

    assert (tmp_path / alert._file_8k_summary_filename).exists()


def test_generate_floating_shares_summary_xlsx(alert: FloatingSharesAlert, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    alert._load_stocks_info_thread = mock.Mock()
    tech, other = _stock("XTECH", "Technology"), _stock("XOTH", "")

    alert._generate_floating_shares_summary_xlsx({tech: _shares(), other: _shares(-0.02, 0.03)})

    alert._load_stocks_info_thread.join.assert_called_once_with()
    assert (tmp_path / alert._floating_shares_summary_filename).exists()


def test_run_sends_email_telegram_and_cleans_up(alert: FloatingSharesAlert, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    alert._symbols = ["BBB", "AAA"]
    alert._alert_name = "floating_shares_test"
    alert._file_8k_summary_filename = "summary.csv"
    alert._floating_shares_summary_filename = "floating.xlsx"
    (tmp_path / "summary.csv").write_text("a")
    (tmp_path / "floating.xlsx").write_text("b")

    with (
        mock.patch.object(alert, "_generate_file_8k_summary_csv"),
        mock.patch.object(
            alert,
            "_generate_floating_shares",
            return_value=("shares content", {_stock("AAA"): _shares()}),
        ),
        mock.patch.object(alert, "_generate_floating_shares_summary_xlsx") as generate_xlsx,
    ):
        alert.run()

    generate_xlsx.assert_called_once()
    alert._email_api.send_email.assert_called_once_with(
        "floating_shares_test",
        "Filter by symbols: ['BBB', 'AAA']\n\nshares content",
        ["summary.csv"],
        ["floating.xlsx"],
    )
    alert._tg_bot.send_message.assert_called_once_with(
        "floating_shares_test\nFilter by symbols: ['BBB', 'AAA']\n\nshares content"
    )
    assert alert._tg_bot.send_file.call_count == 2
    assert not (tmp_path / "summary.csv").exists()
    assert not (tmp_path / "floating.xlsx").exists()


def test_run_without_symbols_skips_file_filter(alert: FloatingSharesAlert, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    alert._file_8k_summary_filename = "summary.csv"
    alert._floating_shares_summary_filename = "floating.xlsx"

    with (
        mock.patch.object(alert, "_generate_file_8k_summary_csv"),
        mock.patch.object(alert, "_generate_floating_shares", return_value=("", {})),
        mock.patch.object(alert, "_generate_floating_shares_summary_xlsx"),
    ):
        alert.run()

    alert._tg_bot.send_message.assert_called_once_with("floating_shares_test\n\n\n")
    alert._tg_bot.send_file.assert_not_called()
