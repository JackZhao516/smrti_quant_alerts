#!/bin/bash

nohup python3 -m smrti_quant_alerts.main "$1" > "$1.log" 2>&1 &
