# Smrti Quant Alerts


[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/JackZhao516/smrti_quant_alerts/blob/main/LICENSE)
![smrti_quant_alert Python Versions](https://img.shields.io/pypi/pyversions/python-bitget?logo=pypi)

This repo includes several real-time alerts for crypto trading, built with Coingecko and Binance APIs. Alerts are sent to Telegram groups/channels.
## Next Steps
* Rebuild ``price_volume`` alert in a more oop manner. [IN PROGRESS]
* Incorporate sqlite3 database to store data instead of csv/json files. [IN PROGRESS]
* Let users set all the alert args in ``settings.json``. [IN PROGRESS]
* Rebuild the main entry ``alert_system.py``. [IN PROGRESS]
* Enhance error handling.
* Cut out the telegram messages into functions and make them more customizable.
* Improve test coverage.
* Enhance documentation.
* Setup CI/CD.
* Setup Docker.

## Get Started and Documentation
* pre-requisites: 
  * ``coingecko pro api token``: all coingecko alerts
  * ``Finnhub api token``, ``Financial Modeling Prep api token``: stock alert
  * ``telegram bot token``, ``telegram group/channel ids`` for all alerts
  * Fill in the required tokens in ``token.json`` for the alerts you want to run
* Run on server in areas where Binance and Coingecko apis are not banned.
## Install
    pip install -r requirements.txt
    python setup.py develop
## Usage

> 1. Change your API KEY and your Telegram Group ids in ``token.json``

> 2. Run ``./start.sh <alert_type>``
> Available alert types: ``market_cap``, ``price_volume``, ``sequential``, 
> ``alts``, ``alert_100``, ``alert_300``, ``alert_500``, ``funding_rate``, 
> ``meme_alert``, ``stock_alert``

## Structure
> 1. python scripts to run those alerts are in ``alert_system.py``

> 2. alerts are defined in ``alerts/``, and will be sent to telegram groups/channels defined in ``token.json``

> 3. ``get_exchange_list.py`` gets required exchange/coin lists from Binance and Coingecko APIs

> 4. ``error.py`` defines error handling functions and ``telegram_bot.py`` implements a simplified message queue for telegram bot to accommodate the rate limit of telegram bot api

> 5. coin: ``CoingeckoCoin``. exchange: ``BinanceExchange``. stock: ``StockSymbol``. All are defined in ``data_type.py``

> 6. alerts are set to run daily/bi-hourly/hourly/quarter-hourly, frequencies are defined in the ``alert_system.py``, the timezone is defined in ``utility.py``

## Alert Type Description
* ``market_cap``: ``alerts/coingecko_market_cap_alert.py``: a daily report of newly deleted and newly added
top 100/200/300/400/500 market cap coins. 
* ``price_volume``: ``alerts/binance_price_volume_alert.py``: real-time alerts for coins with large price and volume changes in 15min/1h timeframe.
* ``alts``: ``alerts/coingecko_alts_alert.py``: daily report of top 500-3000 market cap alts coin with 24H price and volume increase both larger than 50%.
* ``alert_100, alert_300, alert_500``: ``alerts/spot_over_ma_alert.py``: daily report of top 100/300/500 market cap coins/exchanges with spot price over 4H SMA200.
* ``sequential``: sequentially execute ``alert_100, alert_300, alert_500``.
* ``funding_rate``: ``alerts/binance_bi_hourly_future_funding_rate_alert.py``: bi-hourly alerts for future exchanges with funding rate larger than +-0.2%.
* ``meme_alert``: ``alerts/spot_over_ma_alert.py``: daily report of all coins/exchanges on coingecko/binance with daily volume over 3 million USD and with spot price over 1H SMA200.
* ``stock_alert``: ``alerts/stock_alert.py``: daily report of top 20 SP500 and Nasdaq 100 stocks with highest daily price change.

### More on ``price_volume`` alert
* Tracking all spot exchanges on Binance, and automatically add new exchanges to the alert list.
* Contains 4 alerts to four different telegram groups/channels: ``price_alert_15min``, ``price_alert_1h``, ``volume_alert_1h``, ``volume_alert_15min``.
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

## Donate / Sponsor
I develop and maintain these alerts on my own in my spare time. 
Donations are greatly appreciated. 

* **Web3 Address**:  `0xbe7E9903cE3E4A0e717d2F71EBd8d4A4576B91D5`

## Contribution
* Star/Watch/Fork this repository.
