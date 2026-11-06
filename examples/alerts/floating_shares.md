# floating_shares

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

FMP float/SEC/universe access; Telegram channel TEST; Gmail configuration is required because this alert always sends email.

## Command

```sh
python -m smrti_quant_alerts.main '<floating_shares_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 23:50, US/Eastern; excluded weekdays: Sat, Sun.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
<floating_shares_example_name>
Filter by symbols: ['TSLA', 'NVDA']

~ TSLA:
    · 7d: 2.0%
    · 90d: 5.0%
```

Use the included floating_shares_symbols_example.txt (one ticker per line). Telegram and email attach file_8k_summary_<uuid>.csv and floating_shares_<uuid>.xlsx, then temporary local copies are deleted. Spreadsheet columns are stock, 7d change %, 90d change %. Without sufficient dated snapshots, missing changes are N/A and absent from the text, not fabricated as 0%; persist runtime_database.
