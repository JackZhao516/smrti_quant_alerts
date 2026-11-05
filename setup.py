from setuptools import setup, find_packages

setup(
    name="smrti_quant_alerts",
    version="0.9.0",
    packages=find_packages(include=["smrti_quant_alerts", "smrti_quant_alerts.*"]),
    package_data={"smrti_quant_alerts.pdf_api": ["*.ttf"]},
    python_requires=">=3.12",
    extras_require={"dev": ["pytest", "pytest-cov", "pycodestyle", "ruff==0.17.2"]},
    entry_points={
        "console_scripts": [
            "smrti-alerts=smrti_quant_alerts.main:main",
            "smrti-diagnose=smrti_quant_alerts.diagnostics:main",
        ]
    },
    include_package_data=True,
    install_requires=[
        "TA-Lib>=0.6.4",
        "binance-sdk-spot==13.4.0",
        "binance-sdk-derivatives-trading-usds-futures==18.2.0",
        "numpy==1.26.4",
        "pycoingecko==3.1.0",
        "Requests",
        "pytz",
        "pandas[excel]>=2.2,<4",
        "lxml",
        "peewee",
        "urllib3>=2.0,<3",
        "openai",
        "fpdf2==2.7.9",
    ],
)
