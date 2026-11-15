"""Compatibility imports for the former email_api package."""

import sys

from smrti_quant_alerts.gateway import email_api

EmailApi = email_api.EmailApi
sys.modules[f"{__name__}.email_api"] = email_api
