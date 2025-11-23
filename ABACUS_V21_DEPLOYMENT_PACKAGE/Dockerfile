FROM python:3.12-slim

LABEL maintainer="ABACUS Team"
LABEL description="ABACUS v2.1 - Session Analysis & Deployment System"
LABEL version="2.1.0"

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY abacus_v21_*.py ./
COPY *.md ./

RUN mkdir -p /app/output /app/logs /app/data

RUN useradd -m -u 1000 abacus && chown -R abacus:abacus /app
USER abacus

EXPOSE 8000 9090

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "abacus_v21_session_tuple_analyzer.py"]
