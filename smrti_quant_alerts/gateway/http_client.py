"""Bounded JSON requests with explicit failures and secret-safe error messages."""

import re
import time

import requests


class APIError(requests.RequestException):
    def __init__(self, status, message="API request failed"):
        self.status = status
        super().__init__(f"{message} (HTTP {status})")


class PermanentAPIError(APIError):
    """Invalid credentials, permissions, request parameters, or restricted region."""


def redact(value):
    text = str(value)
    text = re.sub(r"(bot)[\w:-]+(/)", r"\1[REDACTED]\2", text)
    return re.sub(
        r"((?:api_?key|api_token|token|authorization|x_cg_pro_api_key)=)[^&\s]+",
        r"\1[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )


def get_json(url, *, params=None, headers=None, attempts=3, timeout=30):
    """Retry only transient failures; never include URLs, credentials or bodies in errors."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout, allow_redirects=False)
        except requests.RequestException:
            if attempt + 1 == attempts:
                raise APIError(0, "Network request failed") from None
            time.sleep(min(2**attempt, 5))
            continue
        status = response.status_code
        if isinstance(status, int) and 300 <= status < 400:
            raise PermanentAPIError(status, "Redirects are not allowed")
        if isinstance(status, int) and status >= 400:
            error = APIError if status == 429 or status >= 500 else PermanentAPIError
            if error is PermanentAPIError or attempt + 1 == attempts:
                raise error(status)
            try:
                delay = float(response.headers.get("Retry-After", 2**attempt))
            except (TypeError, ValueError):
                delay = 2**attempt
            time.sleep(max(0, min(delay, 30)))
            continue
        try:
            data = response.json()
        except ValueError:
            raise APIError(status, "Invalid JSON response") from None
        if isinstance(data, dict) and any(key in data for key in ("Error Message", "error")):
            raise PermanentAPIError(status, "Provider rejected request")
        return data
    raise APIError(0)  # Defensive; every loop path returns or raises.
