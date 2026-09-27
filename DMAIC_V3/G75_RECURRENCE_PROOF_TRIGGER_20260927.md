# G75 recurrence proof trigger

Purpose: provenance-only trigger for the governed DMAIC V3 recurrence required before G75 promotion.

- baseline_main_sha: `39dce7766ce5ee6901e661e42b66d08fe1cb41db`
- trigger_class: `PROVENANCE_ONLY`
- production_change: `false`
- test_change: `false`
- threshold_change: `false`
- denominator_change: `false`
- required_hard_floor_pct: `75`
- authority_transfer: `false`
- formal_credit_delta: `0`
- engineering_credit_delta: `0`

This file exists only under `DMAIC_V3/**` so the repository-native DMAIC V3 workflow executes on the exact PR head and, after merge, on the exact merge SHA. It grants no promotion by itself.
