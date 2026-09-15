# Canonical RH-06 verified HTTP inference image.
FROM python:3.12-slim AS builder

WORKDIR /build
COPY inference-runtime /build/inference-runtime
COPY serving/requirements.txt /build/serving-requirements.txt
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels /build/inference-runtime \
    && pip install --no-cache-dir --user /build/wheels/inforsight_inference_runtime-1.0.0-py3-none-any.whl \
    && pip install --no-cache-dir --user -r /build/serving-requirements.txt

# Final runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root system user
RUN groupadd -r inforsight && useradd -r -g inforsight -s /sbin/nologin -d /app inforsight

COPY --from=builder --chown=inforsight:inforsight /root/.local /app/.local
ENV PATH=/app/.local/bin:$PATH
ENV PYTHONPATH=/app

COPY docs/experiments/phase-02-10-model-bundle.json /app/model/model-bundle.json
COPY serving /app/serving

ENV INFORSIGHT_MODEL_BUNDLE_PATH=/app/model/model-bundle.json \
    INFORSIGHT_EXPECTED_BUNDLE_SHA256=7ac292136d5201f16b02d7bbbaf0448f58124d4209df76e34db6f2f37f12c656 \
    INFORSIGHT_EXPECTED_BUNDLE_ID=inforsight-v6-logistic-platt-20260817 \
    INFORSIGHT_EXPECTED_BUNDLE_VERSION=1.0.0 \
    INFORSIGHT_REQUIRE_TRUSTED_BUNDLE=true

USER inforsight

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8000"]
