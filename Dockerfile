FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 SMRTI_CONFIG_DIR=/config
WORKDIR /app
COPY pyproject.toml setup.py ./
COPY smrti_quant_alerts ./smrti_quant_alerts
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home alerts \
    && mkdir /data && chown alerts:alerts /data
USER alerts
WORKDIR /data
ENTRYPOINT ["smrti-alerts"]
CMD ["--help"]
