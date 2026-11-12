# Install and operate

Python 3.12+ is required. From the checkout root run `./scripts/env_init.sh`,
then activate `env`. Installation uses normal Python wheels; no script runs sudo
or writes to system library directories. If a TA-Lib wheel is unavailable for your
platform, install its native build prerequisites according to TA-Lib upstream.

For a wheel installation use `pip install .` (or `pip install '.[dev]'` for tests).
All alert subpackages and the PDF font are included. Run `smrti-alerts --help` or
`python -m smrti_quant_alerts.main --help` without credentials.

Set `SMRTI_CONFIG_DIR` to the directory containing `token.json`, `configs.json`, and
relative symbol files before starting a process. The default is the working
directory. Run from that directory so symbol-file paths also resolve there.
Database, share-history, report, and log directories should be writable and private.

## API checks and permissions

`python -m smrti_quant_alerts.diagnostics` checks credentials without making requests.
Add `--live --provider fmp` (or another provider) to issue one read-only probe.
A successful probe checks reachability, not every endpoint, subscription, model,
or WebSocket permission. Live checks can consume API quota. Gmail is not contacted.
The tool never sends messages, email, orders, or prints API keys.

- FMP uses documented `/stable` endpoints. A 401/403 requires correct credentials
  or plan permissions; the application does not fall back to obsolete routes.
- FMP `shares-float` provides current snapshots. Persist `runtime_database` across
  restarts to accumulate 7/90-day history. Missing history is unavailable, not 0%.
- EODHD historical series contain completed adjusted bars. Raw live quotes stay
  separate; they are not spliced into adjusted MACD history.
- Binance uses official modular Spot/USDS Futures SDKs. HTTP 451 is a deployment
  region restriction, not a signal to retry or route around the restriction.
- CoinGecko `COINGECKO_API_TIER` selects `pro`, `demo`, or `public`; Pro/Demo keys
  are sent in headers. Endpoint availability/granularity still depends on the plan.
- OpenAI settings live under `OPENAI`: `MODEL` defaults to `gpt-4.1` and
  `WEB_SEARCH` enables actual Responses search tools. Search can incur extra cost;
  disable it to use supplied information only. Sources come from URL annotations.

On API errors, check diagnostics and logs before restarting. Avoid publishing
configuration files or old Telegram messages containing credential-bearing links;
regenerate a token if it was exposed by the legacy blue-text link behavior.

Schedules execute once per configured local minute, polling at most once per
minute; excluded weekdays and timezones apply. Missed slots are not replayed.
A nonexistent DST slot is skipped. Restart after changing schedule configuration.
