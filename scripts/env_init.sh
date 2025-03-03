#!/bin/bash
REQUIRED_VER="3.8"
PYTHON_VER=$(python3 --version 2>&1)
PYTHON_VER=${PYTHON_VER#"Python "}
if [ "$(printf '%s\n' "$REQUIRED_VER" "$PYTHON_VER" | sort -V | head -n1)" = "$REQUIRED_VER" ]; then
        echo "Python version check has passed. $PYTHON_VER >= $REQUIRED_VER."
else
        echo "Python version must be at least 3.8. We recommend you download Python 3.8.10"
        exit 1
fi

# install ta-lib c library
source scripts/install_ta_lib.sh

python3 -m venv env
source env/bin/activate
pip install setuptools
pip install TA-Lib --global-option=build_ext --global-option="-L/usr/lib/"
pip install -r requirements.txt --no-cache-dir
pip install binance-connector==3.5.0 # Have to install this separately to avoid a dependency conflict
python3 setup.py develop