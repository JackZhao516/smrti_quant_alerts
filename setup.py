from setuptools import setup

setup(
    name='smrti_quant_alerts',
    version='0.1.0',
    packages=['smrti_quant_alerts'],
    include_package_data=True,
    install_requires=[
        "binance-connector==2.0.0",
        "numpy==1.24.1",
        "pycoingecko==3.1.0",
        "Requests==2.31.0",
        "pytz~=2022.7.1",
        "responses",
        "pandas",
        "lxml",
        "peewee",
        "polygon-api-client"
    ],
)
