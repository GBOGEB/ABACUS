# Slim PR and full validation model

## Decision

ABACUS uses two CI execution tiers:

- **Slim PR** provides rapid assurance for proposed changes.
- **Full validation** preserves broad system evidence without running the entire estate on
  every pull request.

The machine-readable authority is `ci/governance/workflow_policy.json`. This document is
operational guidance, not a second policy source.

## Slim PR assurance

The default lane contains the canonical governance, core CI/smoke, security, dependency,
CodeQL, Semgrep, OSV, formatting, YAML/document validation and branch-analysis workflows.
Domain workflows may still run when their path filters explicitly match the change.

A slim run answers: is this proposed change structurally valid, testable, secure enough for
review, and governed by the current workflow policy?

## Full validation

The full lane retains broad ABACUS matrices and the DMAIC, DOW, federation, deployment,
runtime, execution-spine, session, V2.3 and book pipelines. It runs through applicable
main/develop pushes, schedules, manual dispatches and lifecycle events.

A full run answers: does the integrated repository, including specialised and historical
surfaces, still reproduce its wider evidence set?

## Escalation to full

Run or await full validation when a change:

1. modifies a release, deployment or generated outward artefact;
2. changes shared runtime, bridge, federation or orchestration contracts;
3. changes DMAIC, DOW, PCA or Bradley–Terry calculation behaviour;
4. changes security policy or dependency resolution;
5. is a release candidate, scheduled control run or explicit reviewer request.

## Evidence rules

- Queued is not passed.
- Skipped is a conditional outcome, not positive test evidence.
- Local evidence supports diagnosis but does not replace the relevant GitHub gate.
- PCA and Bradley–Terry are analytical evidence; they are not CI-policy authority.
- CODEX and ABACUS exchange authority through versioned manifests and hashes.
- Full validation is larger by design; slim validation is not permission to omit a relevant
  domain or release gate.

## Fan-out observations

| Probe | Checks | Queued | Skipped | Interpretation |
|---|---:|---:|---:|---|
| PR #685 | 71 | 65 | 6 | Pre-tier governance baseline |
| PR #688 Python head | 56 | 50 | 6 | Governance isolation confirmed |
| PR #690 | 32 | 28 | 4 | Tier transition PR |
| PR #691 | 26 | 22 | 4 | Focused workflow/test correction |

This documentation-only PR is the first steady-state slim probe. Its final check count must
be recorded after GitHub has registered all workflows; completion remains separate from
coverage until checks finish.
