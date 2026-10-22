# Pipeline / DAG Change Decision Brief

**Intent and observable output:** <!-- Functional I/O contract, not a file dump. -->

**Before -> after:** <!-- Behavioral difference, topological delta or workflow change. -->

**Affected DAG nodes / path lease:** <!-- Sources, workers, producers and consumers. -->

**Dependencies / side entry or exit:** <!-- Blocking, parallel and asynchronous edges. -->

## 1. Test and scheduling contract

**Admission: HOLD pending native tests, safety, policy and independent review.**

| Requirement | Observation | Source |
|---|---|---|
| Exact SHA / run:attempt / workflow selection | UNKNOWN | |
| Parallel/async ordering and idempotency | PENDING | |
| Reverse / negative / retry / cancellation tests | PENDING | |
| Worker queue length, wait and runtime (comparable cohort) | UNKNOWN | |
| Security, coverage, governance | PENDING | |

**First red (step/signature), causal root and owner:** UNKNOWN

## 2. Reviewer decision

**Expected gain and measurement cohort:** <!-- Measure like-for-like conditions. -->

**Rollback / fail-closed mode:** <!-- Explicit recovery or isolation. -->

**Human review focus and next owner:** <!-- Nontrivial state transitions. -->

**Human review:** [ABACUS review tracker](https://gbogeb.github.io/ABACUS/file_review_tracker.html). No self-approval.

## 3. Optional machine evidence projection

<!-- abacus-pr-evidence:start -->
Pending exact-head evidence; this projection cannot grant admission.
<!-- abacus-pr-evidence:end -->
