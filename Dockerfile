FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Root requirements delegates to DMAIC_V3/requirements.txt, so both files must
# exist in the build context before the fail-closed dependency installation.
COPY requirements.txt ./requirements.txt
COPY DMAIC_V3/requirements.txt ./DMAIC_V3/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import socket,sys;s=socket.socket();sys.exit(0 if s.connect_ex(('127.0.0.1',8000))==0 else 1)"

# W93 deliberately retains the existing repository-service command until a
# current executable ABACUS application entrypoint is independently proven.
# The deployment proof workflow labels this surface SERVICE_SHELL rather than
# silently promoting it to the DMAIC analytical runtime.
CMD ["python", "-m", "http.server", "8000"]
