# alert_100

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

CoinGecko and Binance Spot market-data access; Telegram channel CG_SUM.

## Command

```sh
python -m smrti_quant_alerts.main '<alert_100_example_name>'
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

Top 100 coins/coin exchanges exchanges spot over H4 MA200 newly added:
[BTCUSDT]

Top 100 coins/coin exchanges exchanges spot over H4 MA200 newly deleted:
[]
```

Lists and counter values are illustrative and depend on stored history. Coin-information CSV attachments are enabled by alert_coins_info=true. Empty lists are valid.
