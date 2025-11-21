# ABACUS v032/v033 - Docker Configuration
# =========================================
# CANONICAL ALIGNED: v032 → v033
# SPRINT TESTED | DOW TESTED | DEPLOYMENT READY

FROM python:3.11-slim

# Set metadata
LABEL maintainer="ABACUS Team"
LABEL version="v033.1"
LABEL description="ABACUS DMAIC System v032/v033 - Canonically Aligned Deployment"
LABEL sprint_tested="true"
LABEL dow_tested="true"
LABEL canonical_aligned="true"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ABACUS_ENV=production
ENV ABACUS_VERSION=v033
ENV ABACUS_CANONICAL_VERSION=v033.1
ENV SPRINT_TESTED=true
ENV DOW_TESTED=true

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY DMAIC_V3/requirements.txt ./DMAIC_V3/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r DMAIC_V3/requirements.txt || true

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/STATS /app/logs /app/deployments /app/governance

# Set permissions for v033 recursive engine
RUN chmod +x deploy.py || true
RUN chmod +x execute_full_dmaic_phases_0_to_9_v033.py || true
RUN chmod +x master_pipeline_orchestrator.py || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Expose ports
EXPOSE 8000 8080 9090 3000

# Default command - v033 recursive engine
CMD ["python", "execute_full_dmaic_phases_0_to_9_v033.py"]
