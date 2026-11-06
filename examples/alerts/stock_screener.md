# stock_screener

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

FMP and EODHD stock-data access. Set GMAIL before enabling email; the template sets email=false.

## Command

```sh
python -m smrti_quant_alerts.main '<stock_screener_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 23:50, US/Eastern; excluded weekdays: Sat, Sun.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
WARNING - Total stocks: 250
WARNING - Stock Screener Alert finished
```

These are console log messages, not a Telegram report. The default computes the four screens and updates stock-screener database state; generated report files are cleaned up after the run. Set alert_input_args.email=true to receive the XLSX/PDF results through Gmail. No matching stocks is valid; errors appear in logs.
