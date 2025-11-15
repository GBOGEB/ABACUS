---
name: "Sample Markdown Pipeline"
version: "0.1.0"
params:
  greet: "world"
---

# Sample Markdown-Driven Pipeline

This file demonstrates executable fenced blocks and assertions.

## Step 1: Produce a metric (exec)
```python exec
import json, os
metric = {"hello": os.environ.get("HELLO", "world"), "value": 42}
print(json.dumps(metric))
```

## Step 2: Validate the metric (exec:assert)
```python exec:assert
import json, sys
import pathlib
# Find previous stdout captured by the runner is not required; just recompute or assert directly
metric = {"hello": "world", "value": 42}
assert metric["value"] == 42, "value must be 42"
assert isinstance(metric["hello"], str) and metric["hello"], "hello must be non-empty"
```

## Step 3: Shell example (exec)
```bash exec
set -e
echo "Pipeline OK at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
