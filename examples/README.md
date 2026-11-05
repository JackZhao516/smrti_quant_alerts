# Alert command-line examples

Each file below names its configs.json.example entry, CLI command, schedule,
required providers and expected console/Telegram/file outputs. These are live-run
instructions with illustrative output; they do not claim a successful live run.

## Setup

Use Python 3.12 and install from the checkout root:

```sh
python -m pip install -r requirements.txt
python -m pip install -e .
cp -n configs.json.example configs.json
cp -n token.json.example token.json
```

Replace credential and Telegram-channel placeholders; copying never authenticates
with providers. Keep the selected example entry, or rename it and use that same name
in the command. Keep referenced symbol files in the working directory. Commands
with quoted `<...>` names work as written; unquoted angle brackets are shell redirection.
Use a test Telegram channel: these commands can send real notifications and email.
The common startup console line is `WARNING - alert system started`; most results
arrive in Telegram, rather than stdout. Scheduled jobs do not run immediately and
remain running after each report. API errors and region/subscription restrictions
are failures, not successful empty results. Stop each process with Ctrl-C.

## One example per alert type

- [price_volume](alerts/price_volume.md)
- [price_increase_alert](alerts/price_increase_alert.md)
- [stock_price_outperformer](alerts/stock_price_outperformer.md)
- [floating_shares](alerts/floating_shares.md)
- [stock_screener](alerts/stock_screener.md)
- [macd_alert](alerts/macd_alert.md)
- [sequential](alerts/sequential.md)
- [meme_alert](alerts/meme_alert.md)
- [alert_100](alerts/alert_100.md)
- [market_cap](alerts/market_cap.md)
- [alts_alert](alerts/alts_alert.md)
- [funding_rate](alerts/funding_rate.md)
- [alert_300](alerts/alert_300.md)
- [alert_500](alerts/alert_500.md)

## Offline calculation replays

These two deterministic replays need no credentials and never send notifications:

```sh
python -m examples.offline crypto
python -m examples.offline stock
```

Expected crypto JSON: symbol BTC, first_count 1, second_count 2,
new_on_second_run false. Expected stock JSON: symbol AAPL, timeframe 1D,
change_percent 10.0. HTTP is blocked and database state uses a temporary directory.
These replay representative calculations; they are separate from the per-alert
live command/output guides above. Run them in separate processes because the
legacy application uses a global database proxy.
