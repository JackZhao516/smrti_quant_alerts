# alts_alert

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

CoinGecko; Telegram channel ALTS.

## Command

```sh
python -m smrti_quant_alerts.main '<alts_alert_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00, Asia/Shanghai; excluded weekdays: none.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
Alts coins bi-hourly alerts (price increase by 50%, volume increase by 50% and >= 10k, market cap >= 100k), in market cap desc order: []
```

Telegram returns a coin list, including an empty list when nothing qualifies. The current implementation actually filters market cap at >= 1,000,000 USD; its legacy message label says 100k.
