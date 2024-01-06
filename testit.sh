#!/bin/bash

printf "### Running PEP8 ###\n"
find smrti_quant_alerts tests -name \*.py -exec pycodestyle --max-line-length=120 {} +


printf "\n\n### Running pytest ###\n"
pytest tests/* --cov smrti_quant_alerts --cov-report term-missing --disable-warnings --cov-fail-under=60

# clean up

rm -rf .coverage*