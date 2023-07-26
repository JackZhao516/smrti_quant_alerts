# Smrti Quant Alerts


[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/JackZhao516/smrti_quant_alerts/blob/main/LICENSE)
![smrti_quant_alert Python Versions](https://img.shields.io/pypi/pyversions/python-bitget?logo=pypi)

This repo includes several real-time alerts for crypto trading, built with Coingecko and Binance APIs. Alerts are sent to Telegram groups/channels.

 

## Get Started and Documentation
* pre-requisites: coingecko api token, telegram bot token, telegram group/channel ids. Fill in all the required tokens in ``token.json``.
* Run on server in areas where Binance and Coingecko apis are not banned.
## Install
    pip install -r requirements.txt
    python setup.py develop
## Usage

> 1. Change your API KEY and your SECRET KEY in ``token.json``

> 2. Run ``./start.sh <alert_type>``
> Available alert types: ``market_cap``, ``price_volume``, ``sequential``, 
> ``alts``, ``alert_100``, ``alert_300``, ``alert_500``, ``funding_rate``

## Structure
> 1. python scripts to run those alerts are in ``alert_system.py``

> 2. alerts are defined in ``alerts/``, and will be sent to telegram groups/channels defined in ``token.json``

> 3. ``get_exchange_list.py`` gets required exchange/coin lists from Binance and Coingecko APIs

> 4. ``error.py`` defines error handling functions and ``telegram_bot.py`` defines telegram bot functions

## Alert Type Description
* ``market_cap``: ``alerts/coingecko_market_cap_alert.py``: a daily report of newly deleted and newly added
top 100/200/300/400/500 market cap coins. 
* ``price_volume``: ``alerts/binance_price_volume_alert.py``: real-time alerts for coins with large price and volume changes in 15min/1h timeframe.
* ``alts``: ``alerts/coingecko_alts_alert.py``: daily report of top 500-3000 market cap alts coin with 24H price and volume change both larger than 50%.
* ``alert_100, alert_300, alert_500``: ``alerts/top_market_cap_spot_over_ma_alert.py``: daily report of top 100/300/500 market cap coins/exchanges with spot price over 4H MA200.
* ``sequential``: sequentially execute ``alert_100, alert_300, alert_500``.
* ``funding_rate``: ``alerts/binance_bi_hourly_future_funding_rate_alert.py``: bi-hourly alerts for future exchanges with funding rate larger than +-0.2%.

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

## Donate / Sponsor
I develop and maintain these alerts on my own in my spare time. 
Donations are greatly appreciated. 

* **Web3 Address**:  `0xbe7E9903cE3E4A0e717d2F71EBd8d4A4576B91D5`

## Contribution
* Star/Watch/Fork this repository.
