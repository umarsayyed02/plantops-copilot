FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG INSTALL_SEMANTIC=false

COPY requirements.txt requirements-semantic.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_SEMANTIC" = "true" ]; then \
      pip install --no-cache-dir -r requirements-semantic.txt; \
    fi

COPY app ./app
COPY data/raw ./data/raw
COPY evaluation/benchmark.json ./evaluation/benchmark.json

RUN groupadd --system plantops && \
    useradd --system --gid plantops --home-dir /app plantops && \
    mkdir -p data/index data/feedback data/uploads data/models && \
    chown -R plantops:plantops /app

ENV PLANTOPS_DATA_DIR=/app/data

USER plantops

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/health', timeout=3)" || exit 1

CMD ["python", "-m", "app.server"]

