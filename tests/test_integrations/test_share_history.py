from smrti_quant_alerts.stock_crypto_api.share_history import ShareHistory


def test_snapshots_survive_instances_and_upsert_daily_value(tmp_path):
    first = ShareHistory(tmp_path)
    assert first.update("AAPL", [{"date": "2026-11-01", "floatShares": 100}]) == [
        {"date": "2026-11-01", "floatShares": 100}
    ]
    rows = ShareHistory(tmp_path).update("AAPL", [{"date": "2026-11-08", "floatShares": 110}])
    assert [r["floatShares"] for r in rows] == [110, 100]
    rows = first.update("AAPL", [{"date": "2026-11-08", "floatShares": 120}])
    assert len(rows) == 2 and rows[0]["floatShares"] == 120


def test_invalid_or_zero_snapshots_do_not_create_false_history(tmp_path):
    assert ShareHistory(tmp_path).update("AAPL", [{"date": "bad", "floatShares": 0}]) == []
