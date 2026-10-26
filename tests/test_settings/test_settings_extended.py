"""Additional validation tests for the remaining alert configuration branches."""

from smrti_quant_alerts.settings import Config


def _setting(alert_type: str, alert_input_args: dict, alert_params: dict | None = None) -> dict:
    return {
        "alert_type": alert_type,
        "alert_input_args": alert_input_args,
        "alert_params": alert_params or {},
        "run_time_input_args": {"daily_times": "00:00", "excluded_week_days": [], "timezone": ""},
        "database_name": "",
    }


def test_validate_configs_accepts_stock_price_outperformer() -> None:
    config = object.__new__(Config)
    config.SETTINGS = {
        "outperformer": _setting(
            "stock_price_outperformer",
            {
                "tg_type": "STOCK",
                "timeframe_list": ["1d"],
                "email": False,
                "time_frame_sma_filter_ai_analysis": False,
                "newly_added_stock_ai_analysis": False,
                "growth_score_filter_ai_analysis": False,
            },
        )
    }

    config._validate_configs()

    assert config.SETTINGS["outperformer"]["database_name"] == "outperformer"


def test_validate_configs_accepts_floating_shares() -> None:
    config = object.__new__(Config)
    config.SETTINGS = {
        "floating": _setting("floating_shares", {"tg_type": "STOCK", "symbols_file": "symbols.csv"}),
    }

    config._validate_configs()

    assert config.SETTINGS["floating"]["database_name"] == "floating"


def test_validate_configs_accepts_stock_screener() -> None:
    config = object.__new__(Config)
    config.SETTINGS = {
        "screener": _setting("stock_screener", {"market_cap_threshold": 100, "email": False}),
    }

    config._validate_configs()

    assert config.SETTINGS["screener"]["database_name"] == "screener"
