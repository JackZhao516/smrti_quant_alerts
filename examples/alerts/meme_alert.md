# meme_alert

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

CoinGecko and Binance Spot market-data access; Telegram channel MEME.

## Command

```sh
python -m smrti_quant_alerts.main '<meme_alert_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 08:50, Asia/Shanghai; excluded weekdays: Mon, Wed, Fri, Sat.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
For 2023 listed coins/exchanges with 24H volume larger than 3000000 USD
coins/coin exchanges spot over H1 MA200:
[(BTCUSDT, 1)]

coins/coin exchanges exchanges spot over H1 MA200 newly added:
[BTCUSDT]
```

The implementation selects listings since 2023 with the configured liquidity filter; it does not independently verify that a coin is a meme coin. Newly deleted lists and optional coin-information CSV attachments follow. Empty lists are valid.
