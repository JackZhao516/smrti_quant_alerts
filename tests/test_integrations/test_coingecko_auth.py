from smrti_quant_alerts.stock_crypto_api import CoingeckoApi


def test_pro_key_is_header_only_with_pro_host():
    client = CoingeckoApi(api_key="secret")._cg
    assert "pro-api.coingecko.com" in client.api_base_url
    assert client.api_key == ""
    assert client.session.headers["x-cg-pro-api-key"] == "secret"


def test_demo_host_and_header_are_consistent():
    client = CoingeckoApi(api_key="secret", api_tier="demo")._cg
    assert "pro-api" not in client.api_base_url
    assert client.session.headers["x-cg-demo-api-key"] == "secret"


def test_public_tier_needs_no_key_and_sends_no_auth_headers(monkeypatch):
    from unittest.mock import patch
    from smrti_quant_alerts.settings import Config
    from smrti_quant_alerts.diagnostics import diagnose

    monkeypatch.setattr(Config, "TOKENS", None)
    client = CoingeckoApi(api_tier="public")._cg
    assert not any(key.startswith("x-cg-") for key in client.session.headers)
    with patch("smrti_quant_alerts.diagnostics.get_json", return_value={}) as get:
        result = diagnose({"COINGECKO_API_TIER": "public"}, True, ["coingecko"])
    assert result[0]["status"] == "reachable"
    assert get.call_args.kwargs["headers"] == {}


def test_explicit_key_respects_loaded_tier_and_rejects_invalid_tier(monkeypatch):
    import pytest
    from smrti_quant_alerts.settings import Config
    from smrti_quant_alerts.diagnostics import diagnose

    monkeypatch.setattr(Config, "TOKENS", {"COINGECKO_API_TIER": "demo"})
    client = CoingeckoApi(api_key="demo-secret")._cg
    assert client.session.headers["x-cg-demo-api-key"] == "demo-secret"
    with pytest.raises(ValueError, match="COINGECKO_API_TIER"):
        CoingeckoApi(api_key="secret", api_tier="invalid")
    assert diagnose({"COINGECKO_API_TIER": "invalid"}, True, ["coingecko"])[0]["status"] == "invalid_configuration"
