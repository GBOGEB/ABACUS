# ─────────────────────────────────────────────────────────────────────────────
# QPLANT Cryogenic Dashboard — Multi-Stage Docker Build
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Build & test
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

# Copy application code
COPY handover_dashboard/ ./handover_dashboard/
COPY config_service/ ./config_service/
COPY monitoring_dashboard/ ./monitoring_dashboard/
COPY ai_validation/ ./ai_validation/

# Run tests
WORKDIR /app/handover_dashboard
RUN PYTHONPATH=/install/lib/python3.11/site-packages:$PYTHONPATH \
    python -m pytest tests/ -q --tb=short

# ── Stage 2: Production ─────────────────────────────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="QPLANT Engineering Team"
LABEL version="4.4.0"
LABEL description="QPLANT Cryogenic Dashboard with Config Service and Monitoring"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --from=builder /app/handover_dashboard/ ./handover_dashboard/
COPY --from=builder /app/config_service/ ./config_service/
COPY --from=builder /app/monitoring_dashboard/ ./monitoring_dashboard/
COPY --from=builder /app/ai_validation/ ./ai_validation/

# Create non-root user
RUN useradd -m -s /bin/bash qplant && \
    chown -R qplant:qplant /app

USER qplant

# Environment variables
ENV PYTHONPATH=/app
ENV QPLANT_ENV=prod
ENV QPLANT_CONFIG_PATH=/app/handover_dashboard/data/config.yaml
ENV QPLANT_API_PORT=8100
ENV QPLANT_CONFIG_PORT=8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('QPLANT_API_PORT', '8100')}/api/v1/health\")" || exit 1

# Expose ports
EXPOSE 8100 8200

# Default command: start dashboard API (run config service in a separate container/process)
CMD ["sh", "-c", "uvicorn handover_dashboard.api.main:app --host 0.0.0.0 --port ${QPLANT_API_PORT:-8100}"]
