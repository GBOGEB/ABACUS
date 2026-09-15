# ─────────────────────────────────────────────────────────────────────────────
# QPLANT Cryogenic Dashboard — Multi-Stage Docker Build
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build & runtime-contract test
# Stage 2: Production runtime
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache layer)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy the canonical repository SSOT. Runtime injection may override this via
# SSOT_CONFIG_PATH/QPLANT_CONFIG_PATH, but image build/tests must never depend
# on a non-existent handover_dashboard/data/config.yaml duplicate.
COPY config.yaml ./config.yaml

# Copy runtime application code. The API imports the shared authentication
# package from the QPLANT root, so it is part of the executable image contract.
COPY handover_dashboard/ ./handover_dashboard/
COPY authentication/ ./authentication/
COPY config_service/ ./config_service/
COPY monitoring_dashboard/ ./monitoring_dashboard/
COPY ai_validation/ ./ai_validation/

# Run only runtime-relevant tests inside the image build. Release-output,
# generated-document and manifest tests remain in their dedicated CI lanes and
# are deliberately not converted into production image payload.
WORKDIR /app/handover_dashboard
RUN PYTHONPATH=/app:/install/lib/python3.11/site-packages:$PYTHONPATH \
    python -m pytest \
      tests/test_config_loader.py \
      tests/test_calculations.py \
      tests/test_api.py \
      -k "not visualization_catalog and not compressor_availability_chart" \
      -q --tb=short

# ── Stage 2: Production ─────────────────────────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="QPLANT Engineering Team"
LABEL version="4.4.0"
LABEL description="QPLANT Cryogenic Dashboard with Config Service and Monitoring"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy canonical fallback SSOT and runtime application code from builder
COPY --from=builder /app/config.yaml ./config.yaml
COPY --from=builder /app/handover_dashboard/ ./handover_dashboard/
COPY --from=builder /app/authentication/ ./authentication/
COPY --from=builder /app/config_service/ ./config_service/
COPY --from=builder /app/monitoring_dashboard/ ./monitoring_dashboard/
COPY --from=builder /app/ai_validation/ ./ai_validation/

# Kubernetes `runAsNonRoot` requires a verifiable numeric runtime identity.
# Keep the friendly account name, but make the image contract explicit and
# deterministic at UID/GID 10001 so admission and container creation agree.
RUN groupadd --gid 10001 qplant && \
    useradd --uid 10001 --gid 10001 --create-home --shell /bin/bash qplant && \
    chown -R 10001:10001 /app

USER 10001:10001

# Environment variables
ENV PYTHONPATH=/app
ENV QPLANT_ENV=prod
ENV QPLANT_CONFIG_PATH=/app/config.yaml
ENV QPLANT_API_PORT=8100
ENV QPLANT_CONFIG_PORT=8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('QPLANT_API_PORT', '8100')}/api/v1/health\")" || exit 1

# Expose ports
EXPOSE 8100 8200

# Default command: start dashboard API (run config service in a separate container/process)
CMD ["sh", "-c", "uvicorn handover_dashboard.api.main:app --host 0.0.0.0 --port ${QPLANT_API_PORT:-8100}"]
