# price_volume

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

Binance Spot REST and WebSocket access; Telegram channels PRICE_15M, PRICE_1H, VOLUME_15M, VOLUME_1H.

## Command

```sh
python -m smrti_quant_alerts.main '<price_volume_alert_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 11:59, Asia/Shanghai; excluded weekdays: none.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
15m top 1 positive price (close/open) change in % over 5%: ['BTCUSDT: 6.0%, monthly count: 1']
```

This entry starts all four configured streaming detectors immediately. Telegram emits price/volume threshold events and daily count summaries; no matching closed candle means no event. Volume messages include candle volumes, USD amount and monthly count. The schedule below controls daily summaries, not stream startup.
