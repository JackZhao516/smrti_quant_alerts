#!/bin/bash
REQUIRED_VER="3.12"
PYTHON_VER=$(python3 --version 2>&1)
PYTHON_VER=${PYTHON_VER#"Python "}
if [ "$(printf '%s\n' "$REQUIRED_VER" "$PYTHON_VER" | sort -V | head -n1)" = "$REQUIRED_VER" ]; then
        echo "Python version check has passed. $PYTHON_VER >= $REQUIRED_VER."
else
        echo "Python version must be at least 3.12. We recommend you download Python 3.12.8"
        exit 1
fi

# install ta-lib c library
source scripts/install_ta_lib.sh
sudo ln -sf /usr/lib/libta-lib.so.0.6.4 /usr/lib/libta_lib.so.0
sudo ln -sf /usr/lib/libta-lib.so.0.6.4 /usr/lib/libta_lib.so

python3 -m venv env
source env/bin/activate
pip install setuptools
pip install numpy==1.26.4  # Pin numpy version to avoid conflicts
# Set environment variables for TA-Lib C library paths
export TA_INCLUDE_PATH=/usr/include
export TA_LIBRARY_PATH=/usr/lib
pip install TA-Lib
pip install -r requirements.txt --no-cache-dir
pip install binance-connector==3.5.0 # Have to install this separately to avoid a dependency conflict
python3 setup.py develop
