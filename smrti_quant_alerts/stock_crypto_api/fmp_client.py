"""FMP Stable adapter. No silent fallback to account-restricted legacy routes."""

from smrti_quant_alerts.http_client import PermanentAPIError, get_json


class FMPClient:
    def __init__(self, base_url, api_key, timeout=30):
        self.root = base_url.rstrip("/").removesuffix("/api").removesuffix("/stable") + "/stable"
        self.api_key = api_key
        self.timeout = timeout

    def get(self, endpoint, **params):
        rows = get_json(f"{self.root}/{endpoint}", params={**params, "apikey": self.api_key}, timeout=self.timeout)
        if not isinstance(rows, list):
            raise PermanentAPIError(200, "Expected FMP result array")
        return rows

    def profiles(self, symbols):
        rows = []
        for symbol in symbols:
            rows.extend(self.get("profile", symbol=symbol))
        return rows

    def universe(self):
        rows = self.get("actively-trading-list")
        for row in rows:
            row.setdefault("exchangeShortName", row.get("exchange", ""))
            row.setdefault("name", row.get("companyName", ""))
            row.setdefault("type", "etf" if row.get("isEtf") else "stock")
        return rows
