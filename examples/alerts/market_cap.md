# market_cap

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

CoinGecko; Telegram channel CG_MAR_CAP.

## Command

```sh
python -m smrti_quant_alerts.main '<market_cap_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 00:00, Asia/Shanghai; excluded weekdays: none.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
Top 100 Market Cap Report:
Deleted: []
Added: []
(Added in market cap desc order)
```

Telegram sends one report per configured rank cutoff (100, 200, 300, 400, 500). Empty lists mean no membership changes between the constructor snapshot and the run snapshot; this is a valid result.
