"""Compatibility imports for the former HTTP client path."""

import sys

from smrti_quant_alerts.gateway import http_client

sys.modules[__name__] = http_client
