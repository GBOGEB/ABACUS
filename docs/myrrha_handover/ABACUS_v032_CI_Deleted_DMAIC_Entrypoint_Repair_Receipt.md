# ABACUS v032 CI — Deleted DMAIC Entrypoint Repair Receipt

**Status:** historical repair evidence; remote post-fix execution remained approval-gated in the captured state.  
**Raw provenance:** `Pasted text(13).txt` (duplicate family includes `Pasted text(14).txt`).  
**Raw SHA256:** `1668285a9bcb4c9374d5bde895f991598e4975bd0f87af3e583187a720de8b06`

## Context

The captured ABACUS investigation moved past aggregate CI failures and identified one concrete workflow defect in the ABACUS v032 CI/CD pipeline.

## Root cause

`abacus-cicd.yml` referenced a deleted entrypoint:

`ABACUS-v032/execute_full_dmaic_phases_0_to_8.py`

The missing file caused the `Test DMAIC Phases` step to fail with a file-not-found condition and cascaded into `DMAIC Full Cycle` and the final `CI Summary` failure.

## Repair recorded in the source

The capture reports repair commit:

`a130c6a`

The workflow references were changed to the existing script:

`ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py`

The change was applied to both affected workflow references.

## Validation recorded

Local/structural validation in the source:

- `bash scripts/verify_workflows.sh` — PASS;
- `python -m py_compile ABACUS-v032/execute_full_dmaic_phases_0_to_9_v033.py` — PASS.

The source also records the before-state failure family:

- `Test DMAIC Phases` failing;
- `DMAIC Full Cycle` failing as a cascade;
- `CI Summary` failing as a cascade.

## Remote execution boundary

After the repair was pushed, new workflow runs were created for the new HEAD but were shown as `action_required`; jobs had not executed yet. Therefore the source proves:

**repair committed + static/local validation passed**, but **does not prove post-fix remote CI success**.

That distinction should be preserved in any historical status model.

## Next gate if revisited

Bind the exact post-`a130c6a` workflow run that obtained runner admission and executed the repaired `Test DMAIC Phases` path. Promote from `REPAIR_VALIDATED_LOCALLY` to `REMOTE_REPAIR_CONFIRMED` only if that run passes the previously failing chain.

## Provenance and authority boundary

This is a human rewrite of an historical mixed transcript. Only the source-supported root cause, repair commit, validation commands and remote-execution boundary were retained. No current ABACUS CI state is inferred from this receipt.
