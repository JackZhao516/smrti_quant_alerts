#!/bin/bash

[ ! -d "runtime_logs" ] && mkdir -p "runtime_logs"
nohup python3 -m smrti_quant_alerts.main "$1" > "runtime_logs/$1.log" 2>&1 &
