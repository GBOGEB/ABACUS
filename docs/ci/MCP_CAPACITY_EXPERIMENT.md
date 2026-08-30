# MCP capacity / health experiment

## Purpose
Size temporary ABACUS/MCP worker capacity from observed queue and service behaviour rather than a fixed pool size. This is operational capacity evidence only.

## Health plane
Run `scripts/mcp_health_server.py` on localhost. Default ABACUS port is `127.0.0.1:8766`; override with `MCP_HEALTH_PORT`. Endpoints: `/health`, `/ready`, `/metrics`; `/debug/*` is disabled unless `MCP_DEBUG=1`. Do not put secrets, environment values or evidence payloads in the state file.

## Iterations
1. T0: measure queue, active runs, completion rate and service-time distribution without dedicated capacity.
2. T1: 2 workers for 10 min.
3. T2: 4 workers for 10 min only if marginal jobs/worker-hour remains useful.
4. T3: 8 workers for 15 min only if T2 remains capacity-limited.
5. Cooldown: return to baseline and measure queue slope for 10 min.

Record at least 5-minute observations when running interactively: queued, active, completed, failed, P50/P95 service time, worker utilisation, jobs/worker-hour, queue net-drain/min and cross-repo CODEX queue/active.

## Adaptive fit
Pipe observation JSON lines to `scripts/mcp_capacity_fit.py`. It deliberately recommends only 2/4/8 workers to preserve interpretable dose-response experiments. Selection uses measured jobs per worker-minute and current net drain; do not scale merely because queue depth is large.

## PCA-style factors
Track queue arrival pressure, hosted capacity, dedicated capacity, job heaviness/service-time tail, workflow fan-out, stale backlog, MCP latency/error rate and priority starvation. Treat PCA as exploratory until enough repeated observations exist for a formal fit.

## BT-style intervention ordering
Pairwise-rank interventions by governed W04 acceleration, total queue relief, marginal jobs/worker-hour, cross-repo no-harm, operational cost and governance preservation. Prefer the smallest pool that wins materially over the preceding size.

## DMAIC
Define: queue starvation and long-tail occupancy. Measure: queue/active/service-time/utilisation. Analyse: PCA-style factor separation plus marginal capacity response. Improve: bounded 2/4/8 pulses. Control: retain the smallest fit-for-purpose pool only after repeated benefit with no adverse CODEX effect.

## Stop / rollback rules
Scale back if jobs/worker-hour falls by >30% versus the preceding phase, queue drain improves by <10%, failure/error rate materially increases, or CODEX/W04 latency worsens materially. Never infer engineering/compliance/evidence credit from capacity metrics.
