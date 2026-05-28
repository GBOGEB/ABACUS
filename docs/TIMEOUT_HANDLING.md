# KEB/GBOGEB Timeout Handling Guide

## Overview

KEB (Knowledge Execution Bridge) and GBOGEB (Goal-Based Orchestration Graph Execution Bridge) operations now include configurable timeout protection to prevent indefinite hangs from blocking I/O, large file processing, or network calls.

## Configuration

Timeout constants are defined in `local_mcp/knowledge_integration_v2.3.py`:

| Constant | Default | Description |
|---|---|---|
| `DEFAULT_TIMEOUT_SECONDS` | 30 s | General per-operation timeout |
| `KEB_TASK_TIMEOUT` | 60 s | KEB `schedule_agent_task` timeout |
| `GBOGEB_METRIC_TIMEOUT` | 15 s | GBOGEB metric collection timeout |
| `COMPLIANCE_CHECK_TIMEOUT` | 20 s | Compliance check timeout |
| `MAX_RETRY_ATTEMPTS` | 2 | Retry count on timeout |

Override per-call via the `timeout` parameter:

```python
ki.schedule_agent_task("my_task", "agent", func, timeout=120)
ki.check_compliance("rule", check_fn, timeout=45)
```

## How It Works

- Uses `concurrent.futures.ThreadPoolExecutor` with a single worker thread.
- `future.result(timeout=N)` raises `FuturesTimeoutError` if the operation exceeds the limit.
- On timeout the future is cancelled and an `OperationTimeoutError` is raised.
- Timeout events are logged via `[TIMEOUT]` prefix and optionally recorded as metrics.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `[TIMEOUT] KEB task …` | Long-running agent task | Increase `KEB_TASK_TIMEOUT` or break task into chunks |
| `[TIMEOUT] GBOGEB compliance …` | Slow compliance check | Increase `COMPLIANCE_CHECK_TIMEOUT` or simplify check function |
| Repeated timeouts on startup | Missing KEB/GBOGEB core modules | Check `core/keb/` and `core/gbogeb/` exist; fallback mode is fine |

## Changes Made

1. **`local_mcp/__init__.py`** — Created to make `local_mcp` a proper importable Python package.
2. **`local_mcp/knowledge_integration_v2.3.py`** — Added `_run_with_timeout()` utility, `OperationTimeoutError`, and timeout parameters to `schedule_agent_task()` and `check_compliance()`.
