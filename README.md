# Smrti Quant Alerts


[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/JackZhao516/smrti_quant_alerts/blob/main/LICENSE)
![smrti_quant_alert Python Versions](https://img.shields.io/pypi/pyversions/python-bitget?logo=pypi)

This repo includes several real-time alerts for crypto/stock trading, built with 
[CoinGecko](https://www.coingecko.com/), [Binance](https://www.binance.com/en), 
[EODHD](https://eodhd.com/), and [Financial Modeling Prep](https://site.financialmodelingprep.com/) APIs. 
Alerts are sent to [Telegram](https://telegram.org/) groups/channels.

## Next Steps
* Improve test coverage. [*In Progress*]
* Write examples for each alert.
* Enhance documentation.
* Setup Docker.
* Add a gui for setting up/running alerts.

## Get Started and Documentation
* pre-requisites: 
  * ``All coingecko alerts``: [CoinGecko pro api token](https://www.coingecko.com/en/api/pricing), 
    at least ``Analyst`` subscription
  * ``stock_alert``: [Financial Modeling Prep api token](https://site.financialmodelingprep.com/), 
    starter subscription needed; [EODHD api token](https://eodhd.com/pricing),``All in one`` subscription
  * ``All alerts``: [telegram bot token](https://core.telegram.org/); 
    ``telegram group/channel ids``(whole part after the # in https://web.telegram.org/a/#-XXXXXXXX, starting with "-")
  * Fill in the required tokens in 
    [*token.json*](https://github.com/JackZhao516/smrti_quant_alerts/blob/main/token.json.example) 
    for the alerts you want to run
  * Set all the parameters in 
    [*configs.json*](https://github.com/JackZhao516/smrti_quant_alerts/blob/main/configs.json.example) 
    for the alerts you want to run
  * [python3.12](https://www.python.org/downloads/release/python-3120/) or higher
* Run on server in areas where [Binance](https://www.binance.com/en) and 
  [CoinGecko](https://www.coingecko.com/) apis are not banned.
## Install
    ./scripts/env_init.sh

## Test
    ./scripts/testit.sh

## Clean Up
    ./scripts/env_clean.sh

## Usage

> 1. Change your API KEY and your Telegram Group ids in ``token.json``

> 2. Run ``./scripts/start.sh <alert_name>``
> alert_names are set in ``configs.json``.

> 3. Available ``alert_type``: ``market_cap``, ``price_volume``, ``sequential``, 
> ``alts_alert``, ``alert_100``, ``alert_300``, ``alert_500``, ``funding_rate``, 
> ``meme_alert``, ``stock_price_outperformer``, ``price_increase_alert``, ``macd_alert``,
> ``floating_shares``, ``stock_screener``

## Structure
> 1. python scripts to run those alerts are in ``main.py``

> 2. alerts are defined in ``alerts/``, and will be sent to telegram groups/channels defined in ``token.json``

> 3. ``stock_crypto_api/`` defines interactions with stock/crypto apis

> 4. ``exception/`` defines error handling functions and ``telegram_api/`` 
     implements a simplified message queue for telegram bot to accommodate the rate limit of telegram bot api

> 5. coin: ``CoingeckoCoin``. exchange: ``BinanceExchange``. stock: ``StockSymbol``. All are defined in ``data_type/``

> 6. alerts are set to run daily/bi-hourly/hourly/quarter-hourly, 
     frequencies and timezones are defined in the ``configs.json``

## Alert Type Description
* ``market_cap``: ``alerts/crypto_alerts/coingecko_market_cap_alert.py``: a daily report of newly deleted and newly added
top 100/200/300/400/500 market cap coins. 
* ``price_volume``: ``alerts/crypto_alerts/binance_price_volume_alert.py``: real-time alerts for coins with large price 
  and volume changes in 15min/1h timeframe.
* ``alts_alert``: ``alerts/crypto_alerts/coingecko_alts_alert.py``: daily report of top 500-3000 market cap alts coin with 24H price 
  and volume increase both larger than 50%.
* ``alert_100, alert_300, alert_500``: ``alerts/crypto_alerts/coingecko_binance_spot_over_ma_alert.py``: daily report of 
  top 100/300/500 market cap coins/exchanges with spot price over 4H SMA200.
* ``sequential``: sequentially execute ``alert_100, alert_300, alert_500``.
* ``funding_rate``: ``alerts/crypto_alerts/binance_future_funding_rate_alert.py``: bi-hourly alerts for 
  future exchanges with funding rate larger than +-0.2%.
* ``meme_alert``: ``alerts/crypto_alerts/coingecko_binance_spot_over_ma_alert.py``: daily report of all coins/exchanges on coingecko/binance 
  with daily volume over 3 million USD and with spot price over 1H SMA200.
* ``stock_price_outperformer``: ``alerts/stock_alerts/stock_price_top_performer_alert.py``: daily report of stocks with 
  highest daily price change.
* ``price_increase_alert``: ``alerts/crypto_alerts/coingecko_price_increase_alert.py``: daily report of top [start, end] 
  market cap coins with the highest price increase percentage in a give timeframe.
* ``macd_alert``: ``alerts/comprehensive_alerts/macd_alert.py``: MACD (Moving Average Convergence Divergence) 
  analysis for stocks and crypto pairs across multiple timeframes, with Excel and email reports of MACD crossovers and trends.
* ``floating_shares``: ``alerts/stock_alerts/floating_shares_alert.py``: daily report of floating shares 
  changes (7-day and 90-day) for specified stock symbols, organized by industry sectors, includes 8-K filings summary.
* ``stock_screener``: ``alerts/stock_alerts/stock_screener_alert.py``: comprehensive stock screening system 
  applying various financial filters (growth scores, revenue growth, operating margins, valuation metrics) to identify growth stocks.

### More on ``price_volume`` alert
* Tracking all spot exchanges on Binance, and automatically add new exchanges to the alert list.
* Contains 4 alerts to four different telegram groups/channels: ``price_alert_15min``, ``price_alert_1h``, 
  ``volume_alert_1h``, ``volume_alert_15min``.
* Setting thresholds defined in ``settings.json``.
* ``price_alert_15min``: alert for coins with price change larger than ``15m_price_change_percentage`` in 15min timeframe.
* ``price_alert_1h``: alert for coins with price change larger than ``1h_price_change_percentage`` in 1h timeframe.
* ``volume_alert_15min``: alert for coins over amount threshold ``15m_volume_usd`` in USD:
  * if second bar is 10X first bar and third bar is 10X first bar
  * if second bar is 50X first bar
  * if third bar is 50X first bar
* ``volume_alert_1h``: alert for coins over amount threshold ``1h_volume_usd`` in USD:
  * if second bar is 10X first bar
* Every sub alert has a daily counter and monthly counter, which will be reset to 0 at 00:00 UTC everyday and every month.

### More on ``alert_100/300/500, sequential, meme_alert`` alert
* In the telegram group/channel, the alert contain 3 parts: 
  * Coins/exchanges with spot price over SMA 200
  * Coins/exchanges newly added this time compared to last time
  * Coins/exchanges newly deleted this time compared to last time
  * Counts of each captured coin/exchange for how many times it has been sequentially captured

## Contribution
* Star/Watch/Fork this repository.
