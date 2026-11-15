"""Time and date conversion for market data."""

import datetime

import pytz


def get_datetime_now(timezone: str = "US/Eastern") -> datetime.datetime:
    """
    get datetime now with timezone

    :param timezone: str
    :return: datetime.datetime
    """
    return datetime.datetime.now(pytz.timezone(timezone))


def get_stock_market_close_timestamp_from_date(date: str) -> int:
    """
    get stock market close time stamp from date at 4pm EST

    :param date: str
    :return: timestamp in ms
    """
    timezone_utc = pytz.timezone("UTC")
    return (
        int(
            timezone_utc.localize(datetime.datetime.strptime(date, "%Y-%m-%d"))
            .replace(hour=23, minute=59, second=59)
            .timestamp()
        )
        * 1000
    )


def get_date_from_timestamp(timestamp: int) -> str:
    """
    get date from timestamp

    :param timestamp: int
    :return: str
    """
    timezone = pytz.timezone("US/Eastern")
    return datetime.datetime.fromtimestamp(timestamp / 1000, timezone).strftime("%Y-%m-%d")
