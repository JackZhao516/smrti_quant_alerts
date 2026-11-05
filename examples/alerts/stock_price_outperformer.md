# stock_price_outperformer

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

FMP and EODHD stock-data access; Telegram channel STOCK. AI/email options are false in the template.

## Command

```sh
python -m smrti_quant_alerts.main '<stock_alert_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 09:15, Asia/Shanghai; excluded weekdays: Wed, Thu, Fri, Sat, Sun, Mon.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
Top 50 stocks from SP500 and Nasdaq with the highest price increase with timeframe 1d:
Stock: Price Change Percentage
['AAPL: 3.25% (New)']
```

Telegram sends ranked lists for each configured timeframe and stock_alert_<uuid>.csv. (New) marks additions relative to the previous stored list; * marks membership in stock-screener results. PDF/AI reports require their corresponding enabled options and an OpenAI key.
