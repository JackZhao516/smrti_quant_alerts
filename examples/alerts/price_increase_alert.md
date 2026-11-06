# price_increase_alert

Follow [setup and output conventions](../README.md) first. Run from the checkout root with this exact entry retained in configs.json.

## Requirements

CoinGecko; Telegram channel CG_PRICE_INCREASE.

## Command

```sh
python -m smrti_quant_alerts.main '<price_increase_alert_example_name>'
```

This uses the matching entry in configs.json.example. The quotes are required around names containing `<` and `>`.
Schedule: 09:30, Asia/Shanghai; excluded weekdays: Tue, Wed, Thu, Fri, Sat, Sun.
The process stays running; scheduled alerts wait for their next eligible minute. Stop with Ctrl-C.

## Expected output

Illustrative output shape, not a captured live-provider result. Timestamp prefixes, symbols, amounts, ordering and counts vary.
Unless explicitly marked as console output, messages below arrive through Telegram.

```text
Top 100 coins in the top 0 - 500 Market Cap Coins with the biggest price increase in the last 14D timeframe: ['BTC: 12.5%']
```

Telegram reports positive percentage changes among the configured market-cap range after its liquidity filter. Coin labels depend on provider IDs/symbol formatting. Optional coin-info CSV attachments may follow.
