#!/bin/bash

nohup python3 smrti_quant_alerts/alert_system.py "$1" > "$1.log" 2>&1 &
