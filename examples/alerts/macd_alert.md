# macd_alert

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

FMP/EODHD for stock symbols, Binance for crypto symbols; Telegram channel TEST. The supplied CSV mixes stock and crypto pairs.

## Command

```sh
python -m smrti_quant_alerts.main '<macd_alert_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 09:15, Asia/Shanghai; excluded weekdays: Wed, Thu, Fri, Sat, Sun, Mon.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
WARNING - Running <macd_alert_example_name> alert

Telegram:
MACD values for [<encoded symbol-pair keys>]
<MACD summary and crossover analysis>
```

Keep macd_symbols_example.csv in the working directory. Each row defines a left symbol and optional right symbol; the template analyzes 1D, 1W and 1M. Telegram sends the summary and generated report attachment(s). email=false disables Gmail delivery; xlsx=false disables optional per-pair workbooks, not every generated report. Sent report files are removed locally.
