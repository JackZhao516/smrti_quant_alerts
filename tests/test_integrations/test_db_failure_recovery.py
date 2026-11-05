from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from smrti_quant_alerts.data_type import BinanceExchange
from smrti_quant_alerts.db import PriceVolumeDBUtils


def test_failed_query_releases_counter_lock_for_other_threads(runtime_database):
    with patch.object(PriceVolumeDBUtils, "get_count", side_effect=RuntimeError("query failed")):
        with pytest.raises(RuntimeError):
            PriceVolumeDBUtils.update_count(BinanceExchange("BTC", "USDT"), "test", 0)

    def can_acquire():
        acquired = PriceVolumeDBUtils.db_lock.acquire(timeout=0.2)
        if acquired:
            PriceVolumeDBUtils.db_lock.release()
        return acquired

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(can_acquire).result(timeout=2)
    if not result and PriceVolumeDBUtils.db_lock._is_owned():
        PriceVolumeDBUtils.db_lock.release()
    assert result
    assert PriceVolumeDBUtils.update_count(BinanceExchange("BTC", "USDT"), "test", 0) == 1
