# Recursive Continuation Rules

1. Preserve tuple lineage on each replay cycle.
2. Never drop invariant failures; log and gate downstream replay.
3. Carry semantic debt forward with explicit mitigation target.
