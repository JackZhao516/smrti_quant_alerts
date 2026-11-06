# funding_rate

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

Binance USD-M futures market-data access; Telegram channel FUNDING_RATE.

## Command

```sh
python -m smrti_quant_alerts.main '<funding_rate_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00, Asia/Shanghai; excluded weekdays: none.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
Bi-hourly Funding Rate Alert:
[[BTCUSDT, '0.3%']]
```

The example threshold 0.002 means 0.2%, not 0.002%. Telegram is silent if no absolute funding rate exceeds it. HTTP 451 means the deployment region is restricted.
