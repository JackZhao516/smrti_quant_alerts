#!/bin/bash
set -euo pipefail
python3 -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ required"'
python3 -m venv env
source env/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
