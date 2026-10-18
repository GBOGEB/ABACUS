# ABACUS W33 — Bounded priority admission, pooling and full MIP

**Source-owner:** ABACUS, `core/execution_backbone/backbone.py`. **CODEX owner:** Mycelium scheduling proposals and executable DAG; separate authenticated gateway. **QPS:** no engineering-truth or acceptance transfer. `MERGE_ADMISSION=HOLD`.

## D — Define and original root

The old dispatcher removed a task from its priority queue and immediately called `ThreadPoolExecutor.submit` without waiting for a free worker. This placed potentially unbounded low-priority work in an internal executor queue ahead of subsequently enqueued urgent work. `queue_size` then appeared to reach zero even though tasks had not begun. Original inability to report active/admitted count made a queue-drain result misleading.

Scope is the **existing local Python ExecutionBackbone**, NOT hosted GitHub Actions slots or an authenticated remote dispatch gateway.

## M — Independent population and telemetry

| Metric | Baseline (before W33) | W33 qualified acceptance |
|---|---|---|
| Local configured slots | explicit `max_workers` | retained and clearly local |
| Actually running tasks | not reported | `currently_running <= max_workers` |
| Waiting, not admitted | queue size understated if executor buffered | `waiting_queue_size` remains visible until slot admitted |
| Admitted not started | unreported | `admitted_not_started` and total `admitted_inflight` |
| Outstanding | queue only (incomplete) | waiting + admitted, no task lost |
| Queue wait / service P95 | not sampled | observed sample sizes and percentiles, unknown before samples |
| Peak concurrency | not measured | bounded `peak_running <= max_workers` |
| Remote GitHub runner capacity | unknown | remains NULL (no conversion of local config into remote capacity) |
| Formal source/security/review acceptance | independent / withheld | remains HOLD |

## I — Improve

Use a bounded semaphore **before** removing the next priority task; dequeue at most `max_workers` into the executor. Stable sequence ordering among equal priorities, no unbounded completed-future ledger, no priority inversion under saturated waiting queues, explicit non-draining stop accounting, and an extended existing DOW/KEB receipt. No new executor, resource autoscaler or second scheduler was installed.

Native DoV: 13 focused saturation/aging/negative/reverse tests plus the two existing status-emitter tests. Four OS/Python test cells. The frozen W33 observation counts are local-source only until each native job terminates and uploads its own SHA-bound hash receipt.

## P — Analysis and predictions

Track at least three *like-for-like* queue loading waves: 1→2→4 eligible workers for a bounded local experiment; evaluate queue P95, runtime P95, throughput/worker-minute and actual drain. **Do not increase to 8 just because queue is long.** Recommend the next capacity step only when measured queue relief improves by ≥10%, error rate does not increase and the pool proves saturation. Stop enlargement if throughput per worker drops >30%, improvement <10%, or backend governance/other repo queues are adversely affected. No inference of Six Sigma variance with fewer than sufficiently many comparable observations.

## C — Control, replay, governance

Every completed native cell must return exact SHA, run ID, attempt, test result and `runtime_status.json` SHA-256. Compare previous/current/new source selection, and keep unverified denominator null rather than zero. If N+1=N three successive *comparable* phases and the actionable queue/dependency obligations are discharged (or formally parked with owner), declare the specific local lane stable; **never** promote remote/GitHub fleet-wide stable from local pool telemetry.

No remote dispatch, worker account creation, automatic PR merge, scanner waiver, or engineering acceptance in this slice. The CODEX authenticated gateway remains disabled for mutation.
