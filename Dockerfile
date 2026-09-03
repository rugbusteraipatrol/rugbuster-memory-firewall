FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends --yes gosu \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY evidence ./evidence
COPY scripts ./scripts
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 rugbuster \
    && mkdir -p /data /app/runtime \
    && chown -R rugbuster:rugbuster /data /app/runtime \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

ENV RUGBUSTER_MEMORY_DB=/data/memory.db \
    RUGBUSTER_PROJECT_ROOT=/app \
    RUGBUSTER_SEED_VERIFIED_CASE=/app/evidence/avax-repeat-deployer-case.json \
    RUGBUSTER_X402_SETTLEMENT_LOG=/data/x402-settlements.jsonl

EXPOSE 8080
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "exec python -m uvicorn rugbuster_memory_firewall.api:create_app --factory --host 0.0.0.0 --port ${PORT}"]
