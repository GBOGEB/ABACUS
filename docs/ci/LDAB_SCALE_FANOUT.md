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
- The worker count is bounded by the owner's DAB policy, not by the Actions matrix:
  `proposal_workers.max` is 8 for LOW_MECHANICAL and 4 for MEDIUM, so `--risk ALL`
  allows at most 4 lanes and `--risk LOW_MECHANICAL` at most 8. A larger request is
  rejected (exit 2) and no plan is written.
- Unsafe paths (`..`, absolute, drive-qualified such as `C:\x`, UNC, NUL, empty) are
  rejected. Missing evidence is `null` or UNKNOWN, never zero.
- Scan identity is recorded by the producer (`--scan-command`, `--scanner-version`).
  Deltas are UNKNOWN unless the plan recorded both and the after-scan reports an
  identical pair. The reducer also reports whether the lanes' Flake8 version matches.
- `reduce` rejects any lane receipt whose `exact_sha` differs from the plan, duplicate
  worker ids, and a Flake8 version that differs from the plan's recorded one.
- `verify` needs explicit evidence: a known `worker_id` and an explicit
  `changed_paths` array (`[]` only when supplied). A missing field is invalid, not a
  clean zero-change proposal.
- The plan is byte-deterministic for identical input.

## Commands

    flake8 . --exit-zero --max-line-length=120 \
      --format='%(path)s|%(row)d|%(code)s' > global.raw
    python scripts/ldab_scale_plan.py plan --raw global.raw --sha "$(git rev-parse HEAD)" \
      --workers 4 --risk ALL --policy governance/dab/DAB_FULL_RED_GATES.json \
      --scan-command "flake8 . --exit-zero --max-line-length=120" \
      --scanner-version "$(python -c 'import flake8;print(flake8.__version__)')" \
      --out plan.json
    python scripts/ldab_scale_plan.py lane-scan --plan plan.json --worker W00 --out lane-W00.json
    python scripts/ldab_scale_plan.py reduce --plan plan.json --results lane-W*.json --out reduce.json
    python scripts/ldab_scale_plan.py verify --plan plan.json --results repair-W*.json \
      --after-raw after.raw --after-command "<same --scan-command>" \
      --after-version "<same --scanner-version>" --out verify.json

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
| Partition completeness | `sum(lane findings) + hold + unassigned == global total`; zero duplicate owners; zero stray paths; every lane receipt on the plan SHA |
| Balance | max lane findings / mean lane findings (target < 1.10) |
| Parallel efficiency | sum(lane seconds) / (lanes x critical-path seconds) |
| Ownership integrity | changed paths subset of owned paths; zero write collisions |
| Net debt delta | `resolved - opened` by (file, rule code); UNKNOWN unless the scan command is identical |
| Gate progress | DAB total against G1 / G2 / G3, E999 hold unchanged |

## Observed (local, not CI)

Flake8 7.4.1 on Python 3.13, ABACUS main `1217f336`, 10,254 findings. An earlier
8-lane run (before the policy cap was enforced) split into lanes of 1,281-1,282
findings (imbalance 1.0002) and reconciled exactly with no stray paths. With the cap
enforced, `--risk ALL` is limited to 4 lanes and 8 lanes need `--risk LOW_MECHANICAL`.
This local scan differs from the CI census configuration, so the totals are not
comparable to the 2,946 / 3,112 reference figures. Wall-clock speedup on a 2-core
host is not evidence of runner speedup.

## Not in this change

- No workflow. A fan-out workflow needs a `ci/governance/workflow_policy.json` rule
  and a regenerated rationalization report, and ships in a separate PR.
- No mutation, repair or auto-merge. The worker ceiling is read from the DAB policy;
  raising it is an owner change to `governance/dab/DAB_FULL_RED_GATES.json`.
