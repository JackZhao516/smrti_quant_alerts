from setuptools import setup

setup(
    name='smrti_quant_alerts',
    version='0.9.0',
    packages=['smrti_quant_alerts'],
    include_package_data=True,
    install_requires=[
        "binance-futures-connector>=4.0.0",
        "binance-connector>=3.5.0",
        "numpy",
        "pycoingecko==3.1.0",
        "Requests",
        "pytz",
        "pandas",
        "lxml",
        "peewee",
        "urllib3>=1.26.9,<2.0.0",
        "openai",
        "fpdf2==2.7.9",
        "pycodestyle",
        "pytest",
        "pytest-cov"
    ],
)
