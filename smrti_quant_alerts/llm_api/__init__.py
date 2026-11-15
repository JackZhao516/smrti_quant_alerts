"""Compatibility imports for the former llm_api package."""

import sys

from smrti_quant_alerts.gateway import llm_api

LLMAPI = llm_api.LLMAPI
sys.modules[f"{__name__}.llm_api"] = llm_api
