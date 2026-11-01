<!-- markdownlint-disable MD013 MD060 -->

# LDAB / DAB disjoint worker fan-out (proposal-only)

Status: tooling candidate. Authority: ABACUS #1860 and #1929; no merger authority.
`authority_transfer=false`, `formal_credit_delta=0`, `engineering_credit_delta=0`.

This adds `scripts/ldab_scale_plan.py`, a deterministic planner that splits a
frozen Flake8 (DAB) census into **exclusive file-owner lanes** for 2-8 read-only
proposal workers, issues one port-lease record per worker, and reconciles the lane
results against the global scan. It reuses the existing contracts and does not change
them: `governance/dab/DAB_FULL_RED_GATES.json` (risk tiers, batch caps, protected
holds) and `docs/ci/BANDIT_DISJOINT_SCALE_WAVE.md` (file-level exclusive ownership).

## Rules enforced

- Ownership is by canonical file. Every file belongs to exactly one lane.
- A file holding a protected finding (E999) is HOLD in full. It is never dispatched.
- Batches obey the policy caps: LOW_MECHANICAL <= 12 findings, <= 3 files, one
  family; MEDIUM <= 4 findings in exactly one file.
- Proposal workers are read-only. Exactly one writer mutates the repository.
- Unsafe paths (`..`, absolute, empty) are rejected. Missing evidence is `null` or
  UNKNOWN, never zero.
- The plan is byte-deterministic for identical input.

## Commands

    flake8 . --exit-zero --max-line-length=120 \
      --format='%(path)s|%(row)d|%(code)s' > global.raw
    python scripts/ldab_scale_plan.py plan --raw global.raw --sha "$(git rev-parse HEAD)" \
      --workers 8 --policy governance/dab/DAB_FULL_RED_GATES.json --out plan.json
    python scripts/ldab_scale_plan.py lane-scan --plan plan.json --worker W00 --out lane-W00.json
    python scripts/ldab_scale_plan.py reduce --plan plan.json --results lane-W*.json --out reduce.json
    python scripts/ldab_scale_plan.py verify --plan plan.json --results repair-W*.json \
      --after-raw after.raw --after-command "<plan.scan_command>" --out verify.json

`lane-scan` runs Flake8 in-process (no subprocess). `plan` and `reduce` exit 2 on any
failed reconciliation check.

## Port leases (LLDB lanes)

Each lane carries a `port_lease` record: `docker_publish = 127.0.0.1::4711`, so
Docker picks a free loopback host port, and `host_port = null` until it is observed
with `docker port <container_id> 4711/tcp`. No static host ports are used, so lanes
on one host cannot collide. The lease is intent, not proof: `authenticated=false`
until a native receipt exists. A debugger session counts only with `session_id`,
`runner_id` and `real_probe_steps > 0` (see `BD_LDAB_JOIN_CONTRACT_20261014.md`).

## Measures

| Measure | Definition |
| --- | --- |
| Partition completeness | `sum(lane findings) + hold == global total`; zero duplicate owners; zero stray paths |
| Balance | max lane findings / mean lane findings (target < 1.10) |
| Parallel efficiency | sum(lane seconds) / (lanes x critical-path seconds) |
| Ownership integrity | changed paths subset of owned paths; zero write collisions |
| Net debt delta | `resolved - opened` by (file, rule code); UNKNOWN unless the scan command is identical |
| Gate progress | DAB total against G1 / G2 / G3, E999 hold unchanged |

## Observed (local, not CI)

Flake8 7.4.1 on Python 3.13, 8 lanes, ABACUS main `1217f336`: 10,254 findings,
lanes of 1,281-1,282 findings (imbalance 1.0002), reconciled exactly, no stray paths.
This local scan differs from the CI census configuration, so the totals are not
comparable to the 2,946 / 3,112 reference figures. Wall-clock speedup on a 2-core
host is not evidence of runner speedup.

## Not in this change

- No workflow. A fan-out workflow needs a `ci/governance/workflow_policy.json` rule
  and a regenerated rationalization report, and ships in a separate PR.
- No mutation, repair or auto-merge. Raising the proposal-worker ceiling above 8
  requires an owner change to the DAB policy.
