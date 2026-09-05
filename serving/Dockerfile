# Multi-stage lightweight production container for Inforsight Model Serving Gateway
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY serving/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root system user
RUN groupadd -r inforsight && useradd -r -g inforsight -s /sbin/nologin -d /app inforsight

# Copy Python packages from builder
COPY --from=builder /root/.local /home/inforsight/.local
ENV PATH=/home/inforsight/.local/bin:$PATH
ENV PYTHONPATH=/app/simulator/src:/app

# Copy application code and frozen model bundle
COPY simulator/src/inforsight_simulator /app/simulator/src/inforsight_simulator
COPY docs/experiments/phase-02-10-model-bundle.json /app/docs/experiments/phase-02-10-model-bundle.json
COPY serving /app/serving

ENV INFORSIGHT_MODEL_BUNDLE_PATH=/app/docs/experiments/phase-02-10-model-bundle.json

USER inforsight

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
