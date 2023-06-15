# Smrti Quant Alerts


[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/JackZhao516/smrti_quant_alerts/blob/main/LICENSE)
![smrti_quant_alert Python Versions](https://img.shields.io/pypi/pyversions/python-bitget?logo=pypi)

This repo includes several real-time alerts for crypto trading, built with Coingecko and Binance APIs. Alerts are sent to Telegram groups/channels.

 

# Get Started and Documentation
* pre-requisites: binance api token, coingecko api token, telegram bot token, telegram group/channel ids. Fill in all the required tokens in ``token.json``.
* Run on server in areas where Binance and Coingecko apis are not banned.
# Install
    pip install -r requirements.txt
# Usage

> 1. Change your API KEY and your SECRET KEY in ``token.json``

> 2. Run ``./start.sh <alert_type>``
> Available alert types: ``market_cap``, ``price_volume``, ``sequential``, ``alts``, ``alert_100``, ``alert_300``, ``alert_500``

> 3. python scripts to run those alerts are in ``alert_system.py``
### Alert Type Description
* ``"market_cap"``: ``alerts/coingecko_market_cap_alert.py``: a daily report of newly deleted and newly added
top 100/200/300/400/500 market cap coins. 
* ``price_volume``: ``alerts/binance_price_volume_alert.py``: real-time alerts for coins with large price and volume changes in 15min/1h timeframe.
* ``alts``: ``alerts/coingecko_alts_alert.py``: daily report of top 500-3000 market cap alts coin with huge price and volume change.
* ``alert_100, alert_300, alert_500``: ``alerts/top_market_cap_spot_over_ma_alert.py``: daily report of top 100/300/500 market cap coins/exchanges with spot price over 4H MA200.
* ``sequential``: sequentially execute ``alert_100, alert_300, alert_500``.

## Donate / Sponsor
I develop and maintain these alerts on my own for free in my spare time. 
Donations are greatly appreciated. 

* **Web3 Address**:  `0xbe7E9903cE3E4A0e717d2F71EBd8d4A4576B91D5`

## Contribution
* Star/Watch/Fork this repository.
