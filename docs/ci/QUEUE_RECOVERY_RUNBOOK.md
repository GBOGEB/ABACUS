# Actions queue recovery runbook

## Objective
Restore bounded GitHub Actions arrival rate, free hosted-runner capacity, and preserve a dedicated governed W04 evidence path.

## Immediate operator actions
1. Cancel stale historical `CI/CD Monitor, Issue Creator & Tracker` runs created by `deployment_status` before the trigger was removed.
2. Do not rerun broad historical push/security/CD jobs unless they are required by an open release gate.
3. Verify queued count decreases across two consecutive observations before launching new discretionary workflows.
4. Run `scripts/preflight.sh` before repository pushes where a local/MCP worker is available.
5. Once capacity exists, dispatch `QPS W04 DOW receipt contract` and capture its run/artifact/hash lineage.

## Capacity escalation
If the arrival rate is stable but W04 still cannot start, provision additional GitHub Actions capacity or an ephemeral self-hosted runner pool. A self-hosted pool must use a dedicated label and should initially serve governed runtime jobs only. Do not redirect W04 away from GitHub Actions; GitHub run/artifact provenance remains required.

## Evidence boundary
Preflight, queue recovery, runner scaling and workflow completion do not create QPS engineering/compliance credit. W04 findings become usable only after receipt validation, exact run/artifact/hash binding and QPS ACCEPT/REJECT/DEFER disposition.
