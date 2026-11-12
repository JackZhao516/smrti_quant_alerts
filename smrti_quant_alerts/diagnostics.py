"""Read-only API diagnostics. Live probes never send alerts, email, or trades."""

import argparse
import json
import os
from pathlib import Path

from smrti_quant_alerts.gateway.http_client import APIError, get_json

KEYS = {
    "coingecko": "COINGECKO_API_KEY",
    "fmp": "FMP_API_KEY",
    "eodhd": "EODHD_API_KEY",
    "openai": "OPENAI_API_KEY",
    "telegram": "TELEGRAMBOT",
    "gmail": "GMAIL",
}


def configured(value):
    if not isinstance(value, str):
        return False
    return bool(value.strip()) and not value.startswith(("<", "YOUR", "test", "offline"))


def diagnose(tokens, live=False, providers=None):
    results = []
    for provider in ["binance", *KEYS] if providers is None else providers:
        key = tokens.get(KEYS.get(provider, ""), "")
        if provider == "telegram":
            key = key.get("TOKEN", "") if isinstance(key, dict) else ""
        if provider == "gmail":
            results.append({"provider": provider, "status": "not_probed", "detail": "SMTP not contacted"})
            continue
        tier = tokens.get("COINGECKO_API_TIER", "pro")
        public = provider == "coingecko" and tier == "public"
        if provider == "coingecko" and tier not in {"pro", "demo", "public"}:
            results.append({"provider": provider, "status": "invalid_configuration"})
            continue
        if provider != "binance" and not public and not configured(key):
            results.append({"provider": provider, "status": "missing_credentials"})
            continue
        if not live:
            results.append({"provider": provider, "status": "configured" if key else "public_not_probed"})
            continue
        probes = {
            "binance": ("https://api.binance.com/api/v3/ping", {}, {}),
            "coingecko": (
                (
                    "https://pro-api.coingecko.com/api/v3/ping"
                    if tokens.get("COINGECKO_API_TIER", "pro") == "pro"
                    else "https://api.coingecko.com/api/v3/ping"
                ),
                {},
                {
                    (
                        "x-cg-pro-api-key" if tokens.get("COINGECKO_API_TIER", "pro") == "pro" else "x-cg-demo-api-key"
                    ): key
                },
            ),
            "fmp": ("https://financialmodelingprep.com/stable/profile", {"symbol": "AAPL", "apikey": key}, {}),
            "eodhd": ("https://eodhd.com/api/real-time/AAPL.US", {"api_token": key, "fmt": "json"}, {}),
            "openai": ("https://api.openai.com/v1/models", {}, {"Authorization": f"Bearer {key}"}),
            "telegram": (f"https://api.telegram.org/bot{key}/getMe", {}, {}),
        }
        url, params, headers = probes[provider]
        if public:
            headers = {}
        try:
            data = get_json(url, params=params, headers=headers, attempts=1, timeout=10)
            status = "reachable" if data is not None else "empty_response"
            if provider == "telegram" and not data.get("ok"):
                status = "rejected"
            results.append({"provider": provider, "status": status})
        except APIError as error:
            status = "region_restricted" if error.status == 451 else "request_failed"
            results.append({"provider": provider, "status": status, "http_status": error.status})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-root", type=Path, default=Path(os.environ.get("SMRTI_CONFIG_DIR", Path.cwd())))
    parser.add_argument("--live", action="store_true", help="Make one read-only probe per provider (may consume quota)")
    parser.add_argument("--provider", action="append", choices=["binance", *KEYS])
    args = parser.parse_args()
    path = args.config_root / "token.json"
    try:
        tokens = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(tokens, dict):
            raise ValueError("token.json must contain an object")
    except (OSError, ValueError):
        parser.error("Unable to read valid token.json; no credential contents printed")
    print(json.dumps(diagnose(tokens, args.live, args.provider), indent=2))


if __name__ == "__main__":
    main()
