# sequential

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

CoinGecko and Binance Spot market-data access; Telegram channel CG_SUM.

## Command

```sh
python -m smrti_quant_alerts.main '<sequential_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 09:00, Asia/Shanghai; excluded weekdays: Mon, Wed, Fri, Sat.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
alert_100: market cap top 100
Top 100 coins/coin exchanges spot over H4 MA200:
[(BTCUSDT, 1)]
...
alert_300: market cap top 300
...
alert_500: market cap top 500
...
```

One scheduled run executes the 100, 300 and 500 screens in order, passing exclusions forward so previously reported assets are excluded from later screens. Each screen emits its current/new/deleted lists; the ellipses above abbreviate those messages. A combined coin-information CSV follows when enabled.
