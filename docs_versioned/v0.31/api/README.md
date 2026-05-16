# v0.31 API Documentation
> *Reconstructed from code — 2026-05-16 22:34*

## Canonical Index API
```python
import json
with open('ABACUS-v031/canonical.index.json') as f:
    index = json.load(f)
# Returns: dict with artifact locations, types, and metadata
```

## DOW Engine Configuration
```yaml
# ABACUS-v031/dow_engine_config.yaml
# Defines: pipeline stages, phase ordering, DOW governance rules
```

## Direct Improvements Runner
```python
# ABACUS-v031/run_direct_improvements.py
# Entry point for executing direct improvements against canonical baseline
```
