# Smrti Quant Alerts


[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/cuongitl/python-bitget/-/blob/main/LICENSE)
[![smrti_quant_alert Python Versions](https://img.shields.io/pypi/pyversions/python-bitget?logo=pypi)]

This repo includes several real-time alerts for crypto trading, built with Coingecko and Binance APIs. Alerts are sent to Telegram groups/channels.

 

# Get Started and Documentation
pre-requisites: binance api token, coingecko api token, telegram bot token, telegram group/channel ids. Fill in all the required tokens in ``token.json``.

# Install
    pip install -r requirements.txt
# Usage

> 1. Change your API KEY and your SECRET KEY in ``token.json``

> 2. Run ``./start.sh <alert_type>``
> Available alert types: ``market_cap``, ``price_volume``, ``sequential``, ``alts``, ``alert_100``, ``alert_300``, ``alert_500``
### Alert Type Description
* ``market_cap``: a weekly report of newly deleted and newly added
top 200 & 500 market cap coins.
* ``price_volume``: real-time alerts for coins with large price and volume changes in 15min/1h timeframe.
* ``alts``: daily report of top 500-3000 market cap alts coin with huge price and volume change.
* ``alert_100, alert_300, alert_500``: bi-daily report of top 100/300/500 market cap coins/exchanges with spot price over 4H MA200.
* ``sequential``: sequentially execute ``alert_100, alert_300, alert_500``.

## Donate / Sponsor
I develop and maintain these alerts on my own for free in my spare time. 
Donations are greatly appreciated. 

* **Web3 Address**:  `0xbe7E9903cE3E4A0e717d2F71EBd8d4A4576B91D5`

## Contribution
* Star/Watch/Fork this repository.
