#!/bin/bash

nohup python3 -m smrti_quant_alerts.alert_system "$1" > "$1.log" 2>&1 &
